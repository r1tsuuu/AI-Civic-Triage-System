from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(META_VERIFY_TOKEN="test_verify_token")
class WebhookVerifyTest(TestCase):

    def url(self):
        return "/webhook/facebook/"

    def test_correct_token_returns_challenge(self):
        response = self.client.get(self.url(), {
            "hub.mode": "subscribe",
            "hub.verify_token": "test_verify_token",
            "hub.challenge": "challenge_abc123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"challenge_abc123")

    def test_wrong_token_returns_403(self):
        response = self.client.get(self.url(), {
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token",
            "hub.challenge": "challenge_abc123",
        })
        self.assertEqual(response.status_code, 403)

    def test_missing_params_returns_403(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 403)

    def test_wrong_mode_returns_403(self):
        response = self.client.get(self.url(), {
            "hub.mode": "unsubscribe",
            "hub.verify_token": "test_verify_token",
            "hub.challenge": "challenge_abc123",
        })
        self.assertEqual(response.status_code, 403)