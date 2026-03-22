import hmac
import hashlib
import json
import logging
import threading

from django.conf import settings
from django.http import HttpResponse, JsonResponse
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