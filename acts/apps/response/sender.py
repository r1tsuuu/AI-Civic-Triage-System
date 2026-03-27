"""
Automated response sender.

Calls the Meta Graph API to post a reply comment on the original Facebook post.
If META_PAGE_ACCESS_TOKEN is not configured, creates a demo-mode AutoReply record
(graph_api_success=False, error_message starts with "META_PAGE_ACCESS_TOKEN not
configured") so the dashboard can display a neutral "Demo Mode" banner instead of
a red error card.

Production upgrade: set META_PAGE_ACCESS_TOKEN in .env — no code changes needed.
"""
import logging
import threading

import requests
from decouple import config
from django.utils import timezone

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v18.0"


def send_reply(report):
    """Post the automated LGU reply to the original Facebook post.

    Always returns an AutoReply instance. Never raises.
    """
    from apps.response.models import AutoReply
    from apps.response.templates_config import get_reply_text

    reply_text = get_reply_text(report.category)

    try:
        token = config('META_PAGE_ACCESS_TOKEN', default='')
        if not token:
            logger.info(
                "META_PAGE_ACCESS_TOKEN not set — creating demo-mode AutoReply for report %s",
                report.id,
            )
            return AutoReply.objects.create(
                report=report,
                reply_text=reply_text,
                sent_at=None,
                graph_api_success=False,
                error_message=(
                    "META_PAGE_ACCESS_TOKEN not configured — "
                    "running in demo mode. Set env var to enable real replies."
                ),
            )

        post_id = report.raw_post.facebook_post_id
        url = f"{GRAPH_API_BASE}/{post_id}/comments"
        response = requests.post(url, data={
            'message': reply_text,
            'access_token': token,
        })

        if response.status_code == 200:
            logger.info("Graph API reply sent for report %s", report.id)
            return AutoReply.objects.create(
                report=report,
                reply_text=reply_text,
                sent_at=timezone.now(),
                graph_api_success=True,
                error_message=None,
            )
        else:
            error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            logger.warning("Graph API non-200 for report %s: %s", report.id, error_msg)
            return AutoReply.objects.create(
                report=report,
                reply_text=reply_text,
                sent_at=None,
                graph_api_success=False,
                error_message=error_msg,
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
    """Spawn a daemon thread so the HTTP call never blocks the request."""
    threading.Thread(target=send_reply, args=(report,), daemon=True).start()
