import logging
import requests
from datetime import datetime, timezone
from decouple import config
from apps.response.models import AutoReply
from apps.response.templates_config import get_reply_text

logger = logging.getLogger(__name__)


def send_reply(report) -> AutoReply:
    facebook_post_id = None
    reply_text = ""

    try:
        facebook_post_id = report.raw_post.facebook_post_id
        reply_text = get_reply_text(report.category)
        page_access_token = config('META_PAGE_ACCESS_TOKEN', default='')

        if not page_access_token:
            raise ValueError("META_PAGE_ACCESS_TOKEN is not set in environment")

        url = f"https://graph.facebook.com/v18.0/{facebook_post_id}/comments"
        response = requests.post(
            url,
            data={
                'message': reply_text,
                'access_token': page_access_token,
            },
            timeout=10
        )

        if response.status_code == 200:
            logger.info(
                "AutoReply sent successfully for report %s on post %s",
                report.id, facebook_post_id
            )
            return AutoReply.objects.create(
                report=report,
                reply_text=reply_text,
                sent_at=datetime.now(timezone.utc),
                graph_api_success=True,
                error_message=None,
            )
        else:
            error_msg = f"Graph API returned {response.status_code}: {response.text[:500]}"
            logger.error(
                "AutoReply failed for report %s: %s",
                report.id, error_msg
            )
            return AutoReply.objects.create(
                report=report,
                reply_text=reply_text,
                sent_at=None,
                graph_api_success=False,
                error_message=error_msg,
            )

    except Exception as e:
        error_msg = str(e)
        logger.error(
            "AutoReply exception for report %s: %s",
            report.id, error_msg,
            exc_info=True
        )
        return AutoReply.objects.create(
            report=report,
            reply_text=reply_text,
            sent_at=None,
            graph_api_success=False,
            error_message=error_msg,
        )
