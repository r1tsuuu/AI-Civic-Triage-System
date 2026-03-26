import hashlib
import hmac
import json
import time

from django.test import TestCase, override_settings
from apps.webhook.models import RawPost

TEST_SECRET = "test_app_secret"
RECEIVE_URL = "/webhook/facebook/receive/"


def make_signature(body: bytes, secret: str = TEST_SECRET) -> str:
    mac = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={mac}"


def make_payload(post_id: str, message: str) -> bytes:
    payload = {
        "object": "page",
        "entry": [
            {
                "id": "page_123",
                "time": 1700000000,
                "changes": [
                    {
                        "field": "feed",
                        "value": {
                            "item": "post",
                            "verb": "add",
                            "post_id": post_id,
                            "created_time": 1700000000,
                            "message": message,
                        },
                    }
                ],
            }
        ],
    }
    return json.dumps(payload).encode("utf-8")


@override_settings(META_APP_SECRET=TEST_SECRET)
class WebhookReceiveTest(TestCase):

    def test_valid_signature_creates_rawpost(self):
        body = make_payload("post_001", "Baha na sa amin!")
        response = self.client.post(
            RECEIVE_URL,
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=make_signature(body),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(RawPost.objects.filter(facebook_post_id="post_001").exists())

    def test_invalid_signature_returns_403_no_rawpost(self):
        body = make_payload("post_002", "Walang ilaw sa kalsada.")
        response = self.client.post(
            RECEIVE_URL,
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256="sha256=invalidsignature",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(RawPost.objects.filter(facebook_post_id="post_002").exists())

    def test_missing_signature_returns_403(self):
        body = make_payload("post_003", "May sunog sa Brgy. Marawoy!")
        response = self.client.post(
            RECEIVE_URL,
            data=body,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_duplicate_post_id_is_ignored(self):
        body = make_payload("post_dup", "Duplicate post test.")
        sig = make_signature(body)
        self.client.post(RECEIVE_URL, data=body, content_type="application/json",
                         HTTP_X_HUB_SIGNATURE_256=sig)
        self.client.post(RECEIVE_URL, data=body, content_type="application/json",
                         HTTP_X_HUB_SIGNATURE_256=sig)
        self.assertEqual(RawPost.objects.filter(facebook_post_id="post_dup").count(), 1)

    def test_response_time_under_200ms(self):
        body = make_payload("post_perf", "Performance test.")
        sig = make_signature(body)
        start = time.time()
        self.client.post(RECEIVE_URL, data=body, content_type="application/json",
                         HTTP_X_HUB_SIGNATURE_256=sig)
        elapsed_ms = (time.time() - start) * 1000
        self.assertLess(elapsed_ms, 200)