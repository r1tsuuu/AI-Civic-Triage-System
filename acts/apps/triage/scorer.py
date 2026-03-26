import logging

logger = logging.getLogger(__name__)

DISTRESS_VOCAB = ['tulong', 'rescue', 'saklolo', 'hindi na kaya', 'naiipit']
FLOOD_DEPTH_VOCAB = ['lampas tao', 'hanggang dibdib', 'lampas tuhod']
VULNERABLE_VOCAB = ['may matanda', 'may bata', 'may buntis']
STRANDED_VOCAB = ['di makalabas', 'may stranded']


def compute_score(text: str, has_image: bool = False, reaction_count: int = 0) -> float:
    score, _ = compute_score_with_breakdown(text, has_image, reaction_count)
    return score


def compute_score_with_breakdown(text: str, has_image: bool = False, reaction_count: int = 0):
    """
    Returns (score: float, breakdown: dict).
    breakdown keys: distress, flood_depth, vulnerable, stranded, image, reactions
    Each value is the points contributed by that signal (0.0 if not triggered).
    Never raises.
    """
    try:
        if not text:
            return 0.0, {'distress': 0.0, 'flood_depth': 0.0, 'vulnerable': 0.0,
                         'stranded': 0.0, 'image': 0.0, 'reactions': 0.0}

        text_lower = text.lower()
        breakdown = {'distress': 0.0, 'flood_depth': 0.0, 'vulnerable': 0.0,
                     'stranded': 0.0, 'image': 0.0, 'reactions': 0.0}

        for w in DISTRESS_VOCAB:
            if w in text_lower:
                breakdown['distress'] = 3.0
                break

        for w in FLOOD_DEPTH_VOCAB:
            if w in text_lower:
                breakdown['flood_depth'] = 2.0
                break

        for w in VULNERABLE_VOCAB:
            if w in text_lower:
                breakdown['vulnerable'] = 2.0
                break

        for w in STRANDED_VOCAB:
            if w in text_lower:
                breakdown['stranded'] = 2.0
                break

        if has_image:
            breakdown['image'] = 0.5

        if reaction_count > 20:
            breakdown['reactions'] = 0.5

        score = min(sum(breakdown.values()), 10.0)
        return float(score), breakdown

    except Exception as e:
        logger.error(f"Error computing urgency score: {e}")
        return 0.0, {'distress': 0.0, 'flood_depth': 0.0, 'vulnerable': 0.0,
                     'stranded': 0.0, 'image': 0.0, 'reactions': 0.0}
