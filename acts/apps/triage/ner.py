import os
import time
import logging
import requests
import spacy
import spacy.cli
from fuzzywuzzy import process
import pandas as pd

logger = logging.getLogger(__name__)

_NLP = None
_GAZETTEER = None
_LAST_REQ = 0.0

# Alias map per CONSTITUTION.md §16 — resolves informal citizen references to
# canonical gazetteer entries before fuzzy matching.
_ALIAS_MAP = {
    'de la salle': 'De La Salle Lipa',
    'dlsl': 'De La Salle Lipa',
    'dls': 'De La Salle Lipa',
    'cathedral': 'Metropolitan Cathedral of San Sebastian',
    'san sebastian': 'Metropolitan Cathedral of San Sebastian',
    'sm': 'SM City Lipa',
    'sm lipa': 'SM City Lipa',
    'robinsons': 'Robinsons Place Lipa',
    'robinson': 'Robinsons Place Lipa',
    'bigben': 'Bigben Commercial Center',
    'big ben': 'Bigben Commercial Center',
    'palengke': 'Lipa City Public Market',
    'merkado': 'Lipa City Public Market',
    'market': 'Lipa City Public Market',
    'bayan': 'Lipa City Hall',
    'city hall': 'Lipa City Hall',
    'sports complex': 'Lipa City Sports Complex',
    'ospital': 'Ospital ng Lipa',
    'hospital': 'Ospital ng Lipa',
}


def _ner_model_path() -> str:
    """
    Return the absolute path to the NER model directory.
    Reads NER_MODEL_PATH from Django settings when available;
    falls back to the hardcoded default path.
    """
    try:
        from django.conf import settings
        rel = getattr(settings, "NER_MODEL_PATH", None)
        if rel:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            return os.path.join(base_dir, rel)
    except Exception:
        pass
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, "ml", "models", "ner_model_v1")


def _get_nlp():
    global _NLP
    if _NLP is None:
        model_path = _ner_model_path()
        try:
            if os.path.exists(model_path):
                _NLP = spacy.load(model_path)
                logger.info(f"NER model loaded from {model_path}")
            else:
                _NLP = spacy.load("xx_ent_wiki_sm")
                logger.info("NER model not found at configured path; using xx_ent_wiki_sm")
        except OSError:
            logger.error("xx_ent_wiki_sm not found, downloading fallback...")
            try:
                spacy.cli.download("xx_ent_wiki_sm")
                _NLP = spacy.load("xx_ent_wiki_sm")
            except Exception as e:
                logger.error(f"Fallback download failed: {e}")
                _NLP = spacy.blank("xx")
    return _NLP


def _get_gazetteer() -> dict:
    global _GAZETTEER
    if _GAZETTEER is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        gaz_path = os.path.join(base_dir, "ml", "data", "gazetteer.csv")
        try:
            df = pd.read_csv(gaz_path)
            _GAZETTEER = {
                row["location_name"]: (float(row["latitude"]), float(row["longitude"]))
                for _, row in df.iterrows()
            }
            logger.info(f"Gazetteer loaded with {len(_GAZETTEER)} entries from {gaz_path}")
        except Exception as e:
            logger.error(f"Error loading gazetteer: {e}")
            _GAZETTEER = {}
    return _GAZETTEER


def extract_locations(text: str) -> list:
    """
    Returns a list of unique location strings extracted from *text*
    using the spaCy NER model. Returns [] on any failure.
    """
    try:
        nlp = _get_nlp()
        doc = nlp(text)
        locs = [ent.text for ent in doc.ents if ent.label_ in ("LOC", "GPE")]
        return list(dict.fromkeys(locs))  # deduplicate preserving order
    except Exception as e:
        logger.error(f"Location extraction failed: {e}")
        return []


def geocode(location_string: str):
    """
    Returns (latitude, longitude, confidence_level).
    confidence_level is one of: "high" (gazetteer match), "medium" (Nominatim),
    "unresolved" (no match found).
    Never raises.
    """
    global _LAST_REQ
    try:
        # 0. Resolve alias before any matching (CONSTITUTION.md §16)
        canonical = _ALIAS_MAP.get(location_string.lower())
        if canonical:
            logger.debug("Alias resolved: '%s' → '%s'", location_string, canonical)
            location_string = canonical

        # 1. Try local gazetteer first (fast, no network)
        gaz = _get_gazetteer()
        if gaz:
            match = process.extractOne(location_string, list(gaz.keys()))
            if match and match[1] > 85:
                lat, lon = gaz[match[0]]
                return (lat, lon, "high")

        # 2. Fall back to Nominatim (rate-limited to 1 req/sec)
        now = time.time()
        since_last = now - _LAST_REQ
        if since_last < 1.0:
            time.sleep(1.0 - since_last)
        _LAST_REQ = time.time()

        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": f"{location_string}, Lipa City, Batangas, Philippines",
                "format": "json",
                "limit": 1,
            },
            headers={"User-Agent": "TriagePipelineHackathonLipa/1.0"},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return (float(data[0]["lat"]), float(data[0]["lon"]), "medium")

        return (None, None, "unresolved")
    except Exception as e:
        logger.error(f"Geocoding failed for '{location_string}': {e}")
        return (None, None, "unresolved")
