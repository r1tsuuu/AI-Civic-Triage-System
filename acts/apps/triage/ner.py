import os
import time
import logging
import requests
import spacy
from fuzzywuzzy import process
import pandas as pd

logger = logging.getLogger(__name__)

_NLP = None
_GAZETTEER = None
_LAST_REQ = 0.0

def _get_nlp():
    global _NLP
    if _NLP is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(base_dir, 'ml', 'models', 'ner_model_v1')
        try:
            if os.path.exists(model_path):
                _NLP = spacy.load(model_path)
            else:
                _NLP = spacy.load("xx_ent_wiki_sm")
        except OSError:
            logger.error("Model xx_ent_wiki_sm not found, downloading fallback...")
            try:
                import spacy.cli
                spacy.cli.download("xx_ent_wiki_sm")
                _NLP = spacy.load("xx_ent_wiki_sm")
            except Exception as e:
                logger.error(f"Fallback download failed: {e}")
                _NLP = spacy.blank("xx")
    return _NLP

def _get_gazetteer():
    global _GAZETTEER
    if _GAZETTEER is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        gaz_path = os.path.join(base_dir, 'ml', 'data', 'gazetteer.csv')
        try:
            df = pd.read_csv(gaz_path)
            _GAZETTEER = {row['location_name']: (float(row['latitude']), float(row['longitude'])) for _, row in df.iterrows()}
        except Exception as e:
            logger.error(f"Error loading gazetteer: {e}")
            _GAZETTEER = {}
    return _GAZETTEER

def extract_locations(text: str) -> list:
    try:
        nlp = _get_nlp()
        doc = nlp(text)
        locs = []
        for ent in doc.ents:
            if ent.label_ in ["LOC", "GPE"]:
                locs.append(ent.text)
        return list(set(locs))
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return []

def geocode(location_string: str):
    global _LAST_REQ
    try:
        gaz = _get_gazetteer()
        if gaz:
            choices = list(gaz.keys())
            match = process.extractOne(location_string, choices)
            if match and match[1] > 85:
                lat, lon = gaz[match[0]]
                return (lat, lon, "high")
                
        now = time.time()
        since_last = now - _LAST_REQ
        if since_last < 1.0:
            time.sleep(1.0 - since_last)
            
        _LAST_REQ = time.time()
        
        headers = {'User-Agent': 'TriagePipelineHackathonLipa/1.0'}
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': f"{location_string}, Lipa City, Batangas, Philippines",
            'format': 'json',
            'limit': 1
        }
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return (float(data[0]['lat']), float(data[0]['lon']), "medium")
                
        return (None, None, "unresolved")
    except Exception as e:
        logger.error(f"Geocode failed: {e}")
        return (None, None, "unresolved")
