"""
TASK-051: sender.py tests — Graph API send_reply() with mocked HTTP calls.
TASK-050: templates_config.py tests — reply text per category.
"""

import uuid
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone

from apps.webhook.models import RawPost
from apps.triage.models import Report
from apps.response.models import AutoReply
from apps.response.sender import send_reply
from apps.response.templates_config import get_reply_text, REPLY_TEMPLATES


def _make_report(category='disaster_flooding', suffix='000'):
    raw_post = RawPost.objects.create(
        facebook_post_id=f'test_{suffix}_{uuid.uuid4().hex[:8]}',
        post_text='Test post for sender',
        received_at=timezone.now(),
        processed=True,
    )
    return Report.objects.create(
        raw_post=raw_post,
        category=category,
        classifier_confidence=0.85,
        urgency_score=5.0,
        status='resolved',
    )


# ---------------------------------------------------------------------------
# TASK-050: templates_config
# ---------------------------------------------------------------------------

class ReplyTemplatesTests(TestCase):

    def test_all_known_categories_return_text(self):
        for category in REPLY_TEMPLATES:
            text = get_reply_text(category)
            self.assertGreater(len(text), 20, f"Empty template for {category}")

    def test_unknown_category_returns_default(self):
        text = get_reply_text('unknown_xyz')
        self.assertGreater(len(text), 20)

    def test_default_includes_lgu_name(self):
        text = get_reply_text('unknown_xyz', lgu_name='Lipa City LGU')
        self.assertIn('Lipa City LGU', text)

    def test_known_category_does_not_include_lgu_name_placeholder(self):
        # Named templates don't use {lgu_name}, so the placeholder should not appear raw
        text = get_reply_text('disaster_flooding')
        self.assertNotIn('{lgu_name}', text)

    def test_disaster_flooding_template_in_filipino(self):
        text = get_reply_text('disaster_flooding')
        self.assertIn('baha', text)

    def test_transportation_traffic_template_in_filipino(self):
        text = get_reply_text('transportation_traffic')
        self.assertIn('trapiko', text)

    def test_public_infrastructure_template_in_filipino(self):
        text = get_reply_text('public_infrastructure')
        self.assertIn('imprastraktura', text)

    def test_public_safety_template_in_filipino(self):
        text = get_reply_text('public_safety')
        self.assertIn('kaligtasan', text)

    def test_other_template_returns_text(self):
        text = get_reply_text('other')
        self.assertIn('Salamat', text)


# ---------------------------------------------------------------------------
# TASK-051: send_reply() — Graph API sender
# ---------------------------------------------------------------------------

class SendReplySuccessTests(TestCase):

    def setUp(self):
        self.report = _make_report('disaster_flooding', 'success')

    @patch('apps.response.sender.requests.post')
    @patch('apps.response.sender.config', return_value='fake-token-abc')
    def test_success_creates_autoreply_with_true(self, mock_config, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"id": "12345_67890"}'
        mock_post.return_value = mock_response

        reply = send_reply(self.report)

        self.assertIsInstance(reply, AutoReply)
        self.assertTrue(reply.graph_api_success)

    @patch('apps.response.sender.requests.post')
    @patch('apps.response.sender.config', return_value='fake-token-abc')
    def test_success_sets_sent_at(self, mock_config, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"id": "12345_67890"}'
        mock_post.return_value = mock_response

        reply = send_reply(self.report)

        self.assertIsNotNone(reply.sent_at)

    @patch('apps.response.sender.requests.post')
    @patch('apps.response.sender.config', return_value='fake-token-abc')
    def test_success_error_message_is_none(self, mock_config, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"id": "12345_67890"}'
        mock_post.return_value = mock_response

        reply = send_reply(self.report)

        self.assertIsNone(reply.error_message)

    @patch('apps.response.sender.requests.post')
    @patch('apps.response.sender.config', return_value='fake-token-abc')
    def test_success_reply_text_matches_category(self, mock_config, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"id": "12345_67890"}'
        mock_post.return_value = mock_response

        reply = send_reply(self.report)

        expected = get_reply_text(self.report.category)
        self.assertEqual(reply.reply_text, expected)

    @patch('apps.response.sender.requests.post')
    @patch('apps.response.sender.config', return_value='fake-token-abc')
    def test_success_posts_to_correct_url(self, mock_config, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{}'
        mock_post.return_value = mock_response

        send_reply(self.report)

        call_args = mock_post.call_args
        expected_url = (
            f"https://graph.facebook.com/v18.0/"
            f"{self.report.raw_post.facebook_post_id}/comments"
        )
        self.assertEqual(call_args[0][0], expected_url)


class SendReplyFailureTests(TestCase):

    def setUp(self):
        self.report = _make_report('public_safety', 'failure')

    @patch('apps.response.sender.requests.post')
    @patch('apps.response.sender.config', return_value='fake-token-abc')
    def test_non_200_creates_autoreply_with_false(self, mock_config, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"error": {"message": "Invalid token"}}'
        mock_post.return_value = mock_response

        reply = send_reply(self.report)

        self.assertFalse(reply.graph_api_success)

    @patch('apps.response.sender.requests.post')
    @patch('apps.response.sender.config', return_value='fake-token-abc')
    def test_non_200_sent_at_is_none(self, mock_config, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"error": {"message": "Invalid token"}}'
        mock_post.return_value = mock_response

        reply = send_reply(self.report)

        self.assertIsNone(reply.sent_at)

    @patch('apps.response.sender.requests.post')
    @patch('apps.response.sender.config', return_value='fake-token-abc')
    def test_non_200_sets_error_message(self, mock_config, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"error": {"message": "Invalid token"}}'
        mock_post.return_value = mock_response

        reply = send_reply(self.report)

        self.assertIsNotNone(reply.error_message)
        self.assertIn('400', reply.error_message)

    @patch('apps.response.sender.requests.post')
    def test_network_exception_does_not_raise(self, mock_post):
        mock_post.side_effect = Exception('Connection refused')

        # Must not raise
        reply = send_reply(self.report)

        self.assertIsInstance(reply, AutoReply)
        self.assertFalse(reply.graph_api_success)
        self.assertIsNone(reply.sent_at)
        self.assertIn('Connection refused', reply.error_message)

    @patch('apps.response.sender.config', return_value='')
    def test_missing_token_does_not_raise(self, mock_config):
        reply = send_reply(self.report)

        self.assertIsInstance(reply, AutoReply)
        self.assertFalse(reply.graph_api_success)
        self.assertIn('META_PAGE_ACCESS_TOKEN', reply.error_message)

    @patch('apps.response.sender.requests.post')
    @patch('apps.response.sender.config', return_value='fake-token-abc')
    def test_always_returns_autoreply_instance(self, mock_config, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_post.return_value = mock_response

        result = send_reply(self.report)

        self.assertIsInstance(result, AutoReply)

    @patch('apps.response.sender.requests.post')
    @patch('apps.response.sender.config', return_value='fake-token-abc')
    def test_autoreply_saved_to_database(self, mock_config, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{}'
        mock_post.return_value = mock_response

        send_reply(self.report)

        self.assertEqual(AutoReply.objects.filter(report=self.report).count(), 1)
