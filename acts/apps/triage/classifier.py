import os
import logging
import joblib

logger = logging.getLogger(__name__)

_MODEL = None


def _model_path() -> str:
    """
    Return the absolute path to the classifier pickle file.
    Reads NLP_MODEL_PATH from Django settings when available;
    falls back to the hardcoded default path next to ml/.
    """
    try:
        from django.conf import settings
        rel = getattr(settings, "NLP_MODEL_PATH", None)
        if rel:
            # NLP_MODEL_PATH is relative to the acts/ project root
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            return os.path.join(base_dir, rel)
    except Exception:
        pass
    # Fallback: resolve from this file's location
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, "ml", "models", "classifier_v2.pkl")


def _get_model():
    global _MODEL
    if _MODEL is None:
        path = _model_path()
        try:
            if os.path.exists(path):
                _MODEL = joblib.load(path)
                logger.info(f"Classifier model loaded from {path}")
            else:
                logger.error(f"Classifier model file not found at {path}")
        except Exception as e:
            logger.error(f"Error loading classifier model: {e}")
    return _MODEL


def classify(text: str):
    """
    Returns (category, confidence).
    If model is missing or prediction fails, returns ('other', 0.0).
    """
    try:
        model = _get_model()
        if model is None:
            return ("other", 0.0)

        probas = model.predict_proba([text])[0]
        max_idx = probas.argmax()
        category = model.classes_[max_idx]
        confidence = float(probas[max_idx])
        return (category, confidence)
    except Exception as e:
        logger.error(f"Error during classification: {e}")
        return ("other", 0.0)
