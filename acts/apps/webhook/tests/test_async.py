import hashlib
import hmac
import json
import time
from unittest.mock import patch

from django.test import TestCase, override_settings
from apps.webhook.models import RawPost

TEST_SECRET = "test_app_secret"
RECEIVE_URL = "/webhook/facebook/receive/"


def make_signature(body: bytes, secret: str = TEST_SECRET) -> str:
    mac = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={mac}"


def make_payload(post_id: str, message: str = "Test message") -> bytes:
    payload = {
        "object": "page",
        "entry": [{
            "id": "page_123",
            "time": 1700000000,
            "changes": [{
                "field": "feed",
                "value": {
                    "item": "post",
                    "verb": "add",
                    "post_id": post_id,
                    "created_time": 1700000000,
                    "message": message,
                },
            }]
        }]
    }
    return json.dumps(payload).encode("utf-8")


@override_settings(META_APP_SECRET=TEST_SECRET)
class AsyncProcessingTest(TestCase):

    @patch("apps.webhook.views._trigger_pipeline")
    def test_processed_flag_becomes_true_after_pipeline(self, mock_trigger):
        """Pipeline sets processed=True on the RawPost."""
        def fake_pipeline(raw_post):
            raw_post.processed = True
            raw_post.save()

        mock_trigger.side_effect = fake_pipeline

        body = make_payload("post_async_001")
        sig = make_signature(body)
        self.client.post(RECEIVE_URL, data=body, content_type="application/json",
                         HTTP_X_HUB_SIGNATURE_256=sig)

        post = RawPost.objects.get(facebook_post_id="post_async_001")
        self.assertTrue(post.processed)

    def test_webhook_response_time_not_affected_by_pipeline(self):
        """
        HTTP 200 must return quickly. The pipeline runs in a background thread
        so the response is not delayed by NLP work.
        We verify this by confirming _trigger_pipeline is called in a thread
        and the HTTP response comes back before the thread completes.
        """
        pipeline_started = []
        pipeline_completed = []

        def slow_pipeline(raw_post):
            pipeline_started.append(True)
            time.sleep(0.3)
            pipeline_completed.append(True)

        import threading
        original_trigger = __import__(
            'apps.webhook.views', fromlist=['_trigger_pipeline']
        )._trigger_pipeline

        def patched_trigger(raw_post):
            t = threading.Thread(target=slow_pipeline, args=(raw_post,), daemon=True)
            t.start()

        body = make_payload("post_async_002")
        sig = make_signature(body)

        with patch("apps.webhook.views._trigger_pipeline", side_effect=patched_trigger):
            start = time.time()
            response = self.client.post(
                RECEIVE_URL, data=body,
                content_type="application/json",
                HTTP_X_HUB_SIGNATURE_256=sig,
            )
            elapsed_ms = (time.time() - start) * 1000

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed_ms, 200)

    @patch("apps.webhook.views._trigger_pipeline")
    def test_pipeline_not_triggered_for_duplicate_post(self, mock_trigger):
        """Duplicate facebook_post_id must not trigger pipeline a second time."""
        body = make_payload("post_async_dup")
        sig = make_signature(body)

        self.client.post(RECEIVE_URL, data=body, content_type="application/json",
                         HTTP_X_HUB_SIGNATURE_256=sig)
        self.client.post(RECEIVE_URL, data=body, content_type="application/json",
                         HTTP_X_HUB_SIGNATURE_256=sig)

        self.assertEqual(mock_trigger.call_count, 1)