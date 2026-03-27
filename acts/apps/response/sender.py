"""
Automated response sender — Demo / Hackathon mode.

The Meta Graph API is NOT used in this build.  Every resolved report
gets a simulated AutoReply (graph_api_success=True) carrying the correct
Taglish response text.  No real HTTP call is ever made.

Production upgrade path (post-hackathon):
  1. Add `import requests` and `from decouple import config`
  2. Replace _simulate_reply() with a real requests.post() call to:
     POST https://graph.facebook.com/v18.0/{facebook_post_id}/comments
  3. Set META_PAGE_ACCESS_TOKEN in .env
"""
import logging
import threading

from django.utils import timezone

logger = logging.getLogger(__name__)


def send_reply(report):
    """Create a simulated AutoReply for a resolved report.

    No real Graph API call is made.  Always returns an AutoReply instance.
    Never raises.
    """
    from apps.response.models import AutoReply
    from apps.response.templates_config import get_reply_text

    reply_text = get_reply_text(report.category)

    try:
        logger.info(
            "DEMO — simulated Facebook reply for report %s (category=%s): %r",
            report.id, report.category, reply_text[:60],
        )
        return AutoReply.objects.create(
            report=report,
            reply_text=reply_text,
            sent_at=timezone.now(),
            graph_api_success=True,
            error_message=None,
        )
    except Exception as exc:
        logger.error("send_reply failed for report %s: %s", report.id, exc, exc_info=True)
        try:
            return AutoReply.objects.create(
                report=report,
                reply_text=reply_text,
                sent_at=None,
                graph_api_success=False,
                error_message=str(exc),
            )
        except Exception as inner:
            logger.error("Could not save fallback AutoReply: %s", inner)
            return None


def send_reply_async(report) -> None:
    """Spawn a daemon thread so the DB write never blocks the HTTP response."""
    threading.Thread(target=send_reply, args=(report,), daemon=True).start()
