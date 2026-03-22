import logging

logger = logging.getLogger(__name__)


def process_post(raw_post):
    """
    NLP pipeline entry point.
    Implemented by AI Engineer in TASK-024.
    Stub exists so the import in webhook/views.py doesn't crash.
    """
    logger.info("Pipeline stub called for RawPost %s — AI engineer implements TASK-024", 
                raw_post.facebook_post_id)