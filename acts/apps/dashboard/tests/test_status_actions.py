"""
TASK-040: Status Action Endpoint Tests
=======================================

Tests for:
- AcknowledgeReportView  POST /dashboard/reports/<uuid>/acknowledge/
- InProgressReportView   POST /dashboard/reports/<uuid>/in-progress/
- ResolveReportView      POST /dashboard/reports/<uuid>/resolve/
- DismissReportView      POST /dashboard/reports/<uuid>/dismiss/

Uses triage.Report as the primary model (Phase 2 integration).
"""

import uuid
from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.mock_fb.models import MockComment
from apps.response.templates_config import get_status_update_text
from apps.webhook.models import RawPost
from apps.triage.models import Report, StatusChange


def _authed_client():
    client = Client()
    session = client.session
    session['demo_authed'] = True
    session.save()
    return client


def _make_report(status='reported', suffix="000"):
    raw_post = RawPost.objects.create(
        facebook_post_id=f'test_{suffix}_{uuid.uuid4().hex[:8]}',
        post_text='Test post',
        received_at=timezone.now(),
        processed=True,
    )
    return Report.objects.create(
        raw_post=raw_post,
        category='other',
        classifier_confidence=0.8,
        urgency_score=3.0,
        status=status,
    )


@patch('apps.response.sender.send_reply_async')  # prevent daemon threads from racing test teardown
class TransitionPipelineTests(TestCase):
    """Happy-path: the full pipeline reported→ack→in_progress→resolved."""

    def setUp(self):
        self.client = _authed_client()

    def test_acknowledge_from_reported(self, _mock_sender):
        report = _make_report('reported', '001')
        url = reverse('dashboard:acknowledge', kwargs={'pk': report.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('dashboard:report_detail', kwargs={'pk': report.pk}),
            fetch_redirect_response=False,
        )
        report.refresh_from_db()
        self.assertEqual(report.status, 'acknowledged')

    def test_in_progress_from_acknowledged(self, _mock_sender):
        report = _make_report('acknowledged', '002')
        url = reverse('dashboard:in_progress', kwargs={'pk': report.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.status, 'in_progress')

    def test_resolve_from_in_progress(self, _mock_sender):
        report = _make_report('in_progress', '003')
        url = reverse('dashboard:resolve', kwargs={'pk': report.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.status, 'resolved')

    def test_full_pipeline(self, _mock_sender):
        """End-to-end: reported → acknowledged → in_progress → resolved."""
        report = _make_report('reported', '004')

        self.client.post(reverse('dashboard:acknowledge', kwargs={'pk': report.pk}))
        report.refresh_from_db()
        self.assertEqual(report.status, 'acknowledged')

        self.client.post(reverse('dashboard:in_progress', kwargs={'pk': report.pk}))
        report.refresh_from_db()
        self.assertEqual(report.status, 'in_progress')

        self.client.post(reverse('dashboard:resolve', kwargs={'pk': report.pk}))
        report.refresh_from_db()
        self.assertEqual(report.status, 'resolved')

    def test_status_changes_created(self, _mock_sender):
        """Each transition must create a StatusChange record."""
        report = _make_report('reported', '005')

        self.client.post(reverse('dashboard:acknowledge', kwargs={'pk': report.pk}))
        self.assertEqual(StatusChange.objects.filter(report=report).count(), 1)

        self.client.post(reverse('dashboard:in_progress', kwargs={'pk': report.pk}))
        self.assertEqual(StatusChange.objects.filter(report=report).count(), 2)

        self.client.post(reverse('dashboard:resolve', kwargs={'pk': report.pk}))
        self.assertEqual(StatusChange.objects.filter(report=report).count(), 3)


class DismissTests(TestCase):
    """Dismiss is allowed from any non-terminal status."""

    def setUp(self):
        self.client = _authed_client()

    def test_dismiss_from_reported(self):
        report = _make_report('reported', '010')
        url = reverse('dashboard:dismiss', kwargs={'pk': report.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.status, 'dismissed')

    def test_dismiss_from_acknowledged(self):
        report = _make_report('acknowledged', '011')
        self.client.post(reverse('dashboard:dismiss', kwargs={'pk': report.pk}))
        report.refresh_from_db()
        self.assertEqual(report.status, 'dismissed')

    def test_dismiss_from_in_progress(self):
        report = _make_report('in_progress', '012')
        self.client.post(reverse('dashboard:dismiss', kwargs={'pk': report.pk}))
        report.refresh_from_db()
        self.assertEqual(report.status, 'dismissed')

    def test_dismiss_creates_mock_comment_from_template(self):
        report = _make_report('reported', '013')
        self.client.post(reverse('dashboard:dismiss', kwargs={'pk': report.pk}))
        comment = MockComment.objects.filter(raw_post=report.raw_post).order_by('-created_at').first()
        self.assertIsNotNone(comment)
        self.assertEqual(
            comment.text,
            get_status_update_text(report.category, "dismissed"),
        )


class InvalidTransitionTests(TestCase):
    """Forbidden transitions produce an error message and don't change the status."""

    def setUp(self):
        self.client = _authed_client()

    def _assert_blocked(self, report, action_name):
        old_status = report.status
        url = reverse(action_name, kwargs={'pk': report.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.status, old_status)

    def test_cannot_skip_to_resolved_from_reported(self):
        report = _make_report('reported', '020')
        self._assert_blocked(report, 'dashboard:resolve')

    def test_cannot_skip_to_in_progress_from_reported(self):
        report = _make_report('reported', '021')
        self._assert_blocked(report, 'dashboard:in_progress')

    def test_cannot_re_acknowledge_already_acknowledged(self):
        report = _make_report('acknowledged', '022')
        self._assert_blocked(report, 'dashboard:acknowledge')

    def test_cannot_transition_from_resolved(self):
        report = _make_report('resolved', '023')
        self._assert_blocked(report, 'dashboard:dismiss')

    def test_cannot_transition_from_dismissed(self):
        report = _make_report('dismissed', '024')
        self._assert_blocked(report, 'dashboard:acknowledge')


class ActionViewEdgeCaseTests(TestCase):
    """Edge cases: auth, 404, GET method."""

    def setUp(self):
        self.report = _make_report('reported', '030')
        self.authed = _authed_client()
        self.unauthed = Client()

    def test_unauthenticated_post_redirects_to_gate(self):
        url = reverse('dashboard:acknowledge', kwargs={'pk': self.report.pk})
        response = self.unauthed.post(url)
        self.assertEqual(response.status_code, 302)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'reported')

    def test_nonexistent_uuid_returns_404(self):
        nonexistent_pk = uuid.uuid4()
        self.assertFalse(Report.objects.filter(pk=nonexistent_pk).exists())
        url = reverse('dashboard:acknowledge', kwargs={'pk': nonexistent_pk})
        response = self.authed.post(url)
        self.assertEqual(response.status_code, 404)

    def test_get_request_returns_405(self):
        url = reverse('dashboard:acknowledge', kwargs={'pk': self.report.pk})
        response = self.authed.get(url)
        self.assertEqual(response.status_code, 405)

    def test_get_in_progress_returns_405(self):
        url = reverse('dashboard:in_progress', kwargs={'pk': self.report.pk})
        response = self.authed.get(url)
        self.assertEqual(response.status_code, 405)

    def test_get_resolve_returns_405(self):
        url = reverse('dashboard:resolve', kwargs={'pk': self.report.pk})
        response = self.authed.get(url)
        self.assertEqual(response.status_code, 405)

    def test_get_dismiss_returns_405(self):
        url = reverse('dashboard:dismiss', kwargs={'pk': self.report.pk})
        response = self.authed.get(url)
        self.assertEqual(response.status_code, 405)


@patch('apps.response.sender.send_reply_async')  # prevent daemon threads from racing test teardown
class SuccessMessageTests(TestCase):

    def setUp(self):
        self.client = _authed_client()

    def test_success_message_after_acknowledge(self, _mock_sender):
        report = _make_report('reported', '040')
        url = reverse('dashboard:acknowledge', kwargs={'pk': report.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.status, 'acknowledged')

    def test_success_message_after_resolve(self, _mock_sender):
        report = _make_report('in_progress', '041')
        url = reverse('dashboard:resolve', kwargs={'pk': report.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.status, 'resolved')

    def test_resolve_creates_mock_comment_from_template(self, _mock_sender):
        report = _make_report('in_progress', '042')
        self.client.post(reverse('dashboard:resolve', kwargs={'pk': report.pk}))
        comment = MockComment.objects.filter(raw_post=report.raw_post).order_by('-created_at').first()
        self.assertIsNotNone(comment)
        self.assertEqual(
            comment.text,
            get_status_update_text(report.category, "resolved"),
        )
