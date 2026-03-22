import hmac
import hashlib
import json
import logging
import threading

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import RawPost

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET"])
def webhook_verify(request):
    """
    GET /webhook/facebook/
    Meta hub.challenge verification — required before any post data flows in.
    """
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge")

    if mode == "subscribe" and token == settings.META_VERIFY_TOKEN:
        return HttpResponse(challenge, status=200, content_type="text/plain")

    return HttpResponse("Forbidden", status=403)


@csrf_exempt
@require_http_methods(["POST"])
def webhook_receive(request):
    """
    POST /webhook/facebook/
    Receives incoming Facebook posts. Validates HMAC-SHA256 signature,
    saves new RawPost records, spawns background thread for NLP processing,
    returns HTTP 200 immediately — never blocks on NLP work.
    """
    # --- Signature validation ---
    signature_header = request.META.get("HTTP_X_HUB_SIGNATURE_256", "")
    if not _verify_signature(request.body, signature_header):
        return HttpResponse("Forbidden", status=403)

    # --- Parse payload ---
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        logger.warning("Webhook received invalid JSON payload")
        return HttpResponse("Bad Request", status=400)

    # --- Extract and save posts, then trigger async processing ---
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            post_id = value.get("post_id") or entry.get("id")
            message = value.get("message", "")

            if not post_id:
                continue

            raw_post, created = RawPost.objects.get_or_create(
                facebook_post_id=post_id,
                defaults={"post_text": message},
            )

            # Only trigger pipeline for newly created posts
            if created:
                _trigger_pipeline(raw_post)

    # HTTP 200 is sent before any NLP thread does any work
    return HttpResponse("OK", status=200)


def _trigger_pipeline(raw_post: RawPost) -> None:
    """
    Spawn a background thread to run the NLP pipeline.
    Imported lazily to avoid circular dependencies.
    The HTTP response is always sent before this thread starts work.
    """
    def run():
        try:
            # Lazy import — pipeline depends on triage models not yet migrated
            from apps.triage.pipeline import process_post
            process_post(raw_post)
        except Exception:
            logger.exception(
                "Pipeline failed for RawPost %s", raw_post.facebook_post_id
            )

    thread = threading.Thread(target=run, daemon=True)
    thread.start()


def _verify_signature(body: bytes, signature_header: str) -> bool:
    """
    Validate X-Hub-Signature-256 header using HMAC-SHA256.
    Returns False if header is missing, malformed, or doesn't match.
    """
    if not signature_header.startswith("sha256="):
        return False

    expected = signature_header[len("sha256="):]
    secret = settings.META_APP_SECRET.encode("utf-8")

    computed = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, expected)