import os
import logging
import joblib

logger = logging.getLogger(__name__)

_MODEL = None

def _get_model():
    global _MODEL
    if _MODEL is None:
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            model_path = os.path.join(base_dir, 'ml', 'models', 'classifier_v2.pkl')
            if os.path.exists(model_path):
                _MODEL = joblib.load(model_path)
            else:
                logger.error(f"Model file not found at {model_path}")
        except Exception as e:
            logger.error(f"Error loading classifier model: {e}")
    return _MODEL

def classify(text: str):
    """
    Returns (category, confidence). 
    If model fails, returns ('other', 0.0).
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
