"""
sender.py tests — simulated AutoReply (demo / hackathon mode, no Graph API).
templates_config.py tests — reply text per category.
"""

import uuid
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.webhook.models import RawPost
from apps.triage.models import Report
from apps.response.models import AutoReply
from apps.response.sender import send_reply
from apps.response.templates_config import (
    get_reply_text,
    get_status_update_text,
    REPLY_TEMPLATES,
)


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
# templates_config
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

    def test_status_update_text_for_resolved_uses_category_template(self):
        resolved = get_status_update_text('disaster_flooding', 'resolved')
        self.assertEqual(resolved, get_reply_text('disaster_flooding'))

    def test_status_update_text_for_dismissed_returns_decline_message(self):
        dismissed = get_status_update_text('other', 'dismissed')
        self.assertIn('duplicate', dismissed)


# ---------------------------------------------------------------------------
# send_reply() — simulation mode (no real Graph API call)
# ---------------------------------------------------------------------------

class SendReplySimulationTests(TestCase):
    """send_reply() always creates a successful simulated AutoReply."""

    def setUp(self):
        self.report = _make_report('disaster_flooding', 'sim')

    def test_returns_autoreply_instance(self):
        reply = send_reply(self.report)
        self.assertIsInstance(reply, AutoReply)

    def test_graph_api_success_is_true(self):
        reply = send_reply(self.report)
        self.assertTrue(reply.graph_api_success)

    def test_sent_at_is_set(self):
        reply = send_reply(self.report)
        self.assertIsNotNone(reply.sent_at)

    def test_error_message_is_none(self):
        reply = send_reply(self.report)
        self.assertIsNone(reply.error_message)

    def test_reply_text_matches_category(self):
        reply = send_reply(self.report)
        self.assertEqual(reply.reply_text, get_reply_text(self.report.category))

    def test_autoreply_saved_to_database(self):
        send_reply(self.report)
        self.assertEqual(AutoReply.objects.filter(report=self.report).count(), 1)

    def test_each_category_gets_correct_text(self):
        categories = ['disaster_flooding', 'transportation_traffic',
                      'public_infrastructure', 'public_safety', 'other']
        for cat in categories:
            report = _make_report(cat, f'cat_{cat}')
            reply = send_reply(report)
            self.assertEqual(reply.reply_text, get_reply_text(cat),
                             f"Wrong reply text for category {cat}")


class SendReplyFallbackTests(TestCase):
    """send_reply() never raises even when the DB write fails."""

    def setUp(self):
        self.report = _make_report('public_safety', 'fallback')

    @patch('apps.response.models.AutoReply.objects.create',
           side_effect=Exception('DB connection lost'))
    def test_db_failure_does_not_raise(self, _mock_create):
        # Must not raise even when AutoReply.objects.create fails
        result = send_reply(self.report)
        # Returns None only if both the primary and fallback create fail
        # (both are mocked to raise here, so result is None)
        self.assertIsNone(result)

    def test_always_returns_autoreply_or_none(self):
        result = send_reply(self.report)
        self.assertTrue(result is None or isinstance(result, AutoReply))
