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
def webhook_facebook(request):
    """
    GET  /webhook/  — Meta hub.challenge verification handshake.
    POST /webhook/  — Receive Facebook page feed events.

    Meta sends the verification GET and all event POSTs to the same callback
    URL, so both methods must live on the same path.
    """
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == settings.META_VERIFY_TOKEN:
            return HttpResponse(challenge, status=200, content_type="text/plain")

        return HttpResponse("Forbidden", status=403)

    if request.method == "POST":
        signature_header = request.META.get("HTTP_X_HUB_SIGNATURE_256", "")
        if not _verify_signature(request.body, signature_header):
            return HttpResponse("Forbidden", status=403)

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            logger.warning("Webhook received invalid JSON payload")
            return HttpResponse("Bad Request", status=400)

        _process_payload(payload)
        return HttpResponse("OK", status=200)

    return HttpResponse("Method Not Allowed", status=405)


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
    _process_payload(payload)

    # HTTP 200 is sent before any NLP thread does any work
    return HttpResponse("OK", status=200)


def _process_payload(payload: dict) -> None:
    """
    Walk a Meta feed webhook payload and save new RawPost records.

    Meta fires the feed subscription for new posts, edited posts, comments,
    reactions, and deletions.  We only want brand-new top-level page posts:
      item == "post"  AND  verb == "add"

    Any other combination (comments, reactions, edits, removes) is logged and
    skipped so it never reaches the NLP pipeline or the database.
    """
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            item = value.get("item")
            verb = value.get("verb")

            # Skip anything that is not a brand-new top-level post
            if item != "post" or verb != "add":
                logger.debug(
                    "Skipping feed event: item=%s verb=%s", item, verb
                )
                continue

            post_id = value.get("post_id")
            message = value.get("message", "")
            created_time = value.get("created_time")  # Unix timestamp from Meta

            if not post_id:
                logger.warning("Feed event missing post_id, skipping")
                continue

            if not message:
                logger.info(
                    "Post %s has no message text (photo/link only?), skipping",
                    post_id,
                )
                continue

            logger.info(
                "Incoming post: post_id=%s created_time=%s message_preview=%.80r",
                post_id, created_time, message,
            )

            raw_post, created = RawPost.objects.get_or_create(
                facebook_post_id=post_id,
                defaults={"post_text": message},
            )

            if created:
                logger.info("Saved RawPost %s — triggering NLP pipeline", post_id)
                _trigger_pipeline(raw_post)
            else:
                logger.info("Duplicate post_id=%s, pipeline not re-triggered", post_id)


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