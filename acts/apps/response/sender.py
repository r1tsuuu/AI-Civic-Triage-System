"""
Automated response sender.

Demo mode: instead of calling the real Meta Graph API, we create a simulated
AutoReply record (graph_api_success=True).  This gives the dashboard a real DB
record to display ("✓ Simulated response sent") and keeps the closed-loop story
intact for the hackathon demo.

Production upgrade path:
  1. Set META_PAGE_ACCESS_TOKEN in .env
  2. Replace _simulated_post() body with an actual requests.post() call to:
     POST https://graph.facebook.com/v18.0/{facebook_post_id}/comments
  3. Remove the simulated path
"""
import logging
import threading

from django.utils import timezone

logger = logging.getLogger(__name__)


def send_reply(report) -> None:
    """
    Build and persist the automated LGU reply for a resolved report.

    Called in a background daemon thread so the HTTP response is never
    blocked.  The status transition to 'resolved' is committed BEFORE this
    runs — failure here never rolls back the transition.
    """
    try:
        from apps.response.models import AutoReply
        from apps.response.templates_config import get_reply_text

        reply_text = get_reply_text(report.category)
        success, error_msg = _simulated_post(report, reply_text)

        AutoReply.objects.create(
            report=report,
            reply_text=reply_text,
            sent_at=timezone.now() if success else None,
            graph_api_success=success,
            error_message=error_msg,
        )
        logger.info(
            "AutoReply created for report %s (category=%s, success=%s)",
            report.id, report.category, success,
        )

    except Exception as exc:
        logger.error("send_reply failed for report %s: %s", report.id, exc, exc_info=True)
        # Last-resort record so the detail page always has something to show.
        try:
            from apps.response.models import AutoReply
            AutoReply.objects.create(
                report=report,
                reply_text='',
                sent_at=None,
                graph_api_success=False,
                error_message=str(exc),
            )
        except Exception as inner:
            logger.error("Could not save fallback AutoReply: %s", inner)


def _simulated_post(report, reply_text: str) -> tuple[bool, str | None]:
    """
    Simulate a successful Graph API comment reply.
    Returns (success: bool, error_message: str | None).
    """
    logger.info(
        "DEMO — simulated Facebook comment on post %s: %r",
        getattr(report.raw_post, 'facebook_post_id', '?'),
        reply_text[:80],
    )
    return True, None


def send_reply_async(report) -> None:
    """
    Convenience wrapper: spawn a daemon thread and call send_reply().
    Always call this from views — never call send_reply() directly from a
    request handler so the HTTP response is never blocked.
    """
    threading.Thread(target=send_reply, args=(report,), daemon=True).start()
