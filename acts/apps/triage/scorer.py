import logging

logger = logging.getLogger(__name__)

DISTRESS_VOCAB = ['tulong', 'rescue', 'saklolo', 'hindi na kaya', 'naiipit']
FLOOD_DEPTH_VOCAB = ['lampas tao', 'hanggang dibdib', 'lampas tuhod']
VULNERABLE_VOCAB = ['may matanda', 'may bata', 'may buntis']
STRANDED_VOCAB = ['di makalabas', 'may stranded', 'naiipit']

def compute_score(text: str, has_image: bool = False, reaction_count: int = 0) -> float:
    try:
        score = 0.0
        if not text:
            return score
            
        text_lower = text.lower()
        
        for w in DISTRESS_VOCAB:
            if w in text_lower:
                score += 3.0
                break
                
        for w in FLOOD_DEPTH_VOCAB:
            if w in text_lower:
                score += 2.0
                break
                
        for w in VULNERABLE_VOCAB:
            if w in text_lower:
                score += 2.0
                break
                
        for w in STRANDED_VOCAB:
            if w in text_lower:
                score += 2.0
                break
                
        if has_image:
            score += 0.5
            
        if reaction_count > 20:
            score += 0.5
            
        return min(float(score), 10.0)
    except Exception as e:
        logger.error(f"Error computing urgency score: {e}")
        return 0.0
