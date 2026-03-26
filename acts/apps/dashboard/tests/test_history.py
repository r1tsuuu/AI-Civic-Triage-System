"""
TASK-034: History View Tests
=============================

Tests for HistoryView and HistoryExportView. Uses real triage.StatusChange
records (Phase 2 integration) — no mock data.
"""

import uuid
from django.test import TestCase, Client
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone

from apps.webhook.models import RawPost
from apps.triage.models import Report, StatusChange


def _authed_client():
    client = Client()
    session = client.session
    session['demo_authed'] = True
    session.save()
    return client


def _make_report_with_transition(suffix, from_status='reported', to_status='acknowledged'):
    """Create a RawPost + Report and one StatusChange."""
    raw_post = RawPost.objects.create(
        facebook_post_id=f'hist_{suffix}_{uuid.uuid4().hex[:8]}',
        post_text=f'History test post {suffix}',
        received_at=timezone.now(),
        processed=True,
    )
    report = Report.objects.create(
        raw_post=raw_post,
        category='other',
        classifier_confidence=0.8,
        urgency_score=5.0,
        status=to_status,
    )
    StatusChange.objects.create(
        report=report,
        from_status=from_status,
        to_status=to_status,
        changed_by='demo',
        note='Test transition',
    )
    return report


class HistoryViewTests(TestCase):

    def setUp(self):
        self.client = _authed_client()
        # Create 3 reports, each with 1 status change
        self.reports = [_make_report_with_transition(i) for i in range(3)]

    def test_history_view_returns_200(self):
        url = reverse('dashboard:history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_history_view_uses_correct_template(self):
        url = reverse('dashboard:history')
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'dashboard/history.html')

    def test_status_changes_in_context(self):
        url = reverse('dashboard:history')
        response = self.client.get(url)
        self.assertIn('status_changes', response.context)

    def test_status_changes_appear_in_template(self):
        url = reverse('dashboard:history')
        response = self.client.get(url)
        self.assertContains(response, 'Status Change History')
        self.assertContains(response, 'history-timeline')

    def test_timeline_shows_report_ids(self):
        url = reverse('dashboard:history')
        response = self.client.get(url)
        for report in self.reports:
            self.assertContains(response, str(report.id))

    def test_timeline_shows_status_transitions(self):
        url = reverse('dashboard:history')
        response = self.client.get(url)
        self.assertContains(response, 'transition-badge')

    def test_timeline_shows_timestamps(self):
        url = reverse('dashboard:history')
        response = self.client.get(url)
        self.assertContains(response, 'timestamp')

    def test_filter_bar_displayed(self):
        url = reverse('dashboard:history')
        response = self.client.get(url)
        self.assertContains(response, 'From Date')
        self.assertContains(response, 'To Date')
        self.assertContains(response, 'Report ID')

    def test_export_button_displayed(self):
        url = reverse('dashboard:history')
        response = self.client.get(url)
        self.assertContains(response, 'Export CSV')

    def test_filter_by_date_range(self):
        url = reverse('dashboard:history')
        today = timezone.now().date()
        response = self.client.get(url, {'date_from': str(today), 'date_to': str(today)})
        self.assertEqual(response.status_code, 200)
        self.assertIn('status_changes', response.context)

    def test_filter_by_report_id(self):
        url = reverse('dashboard:history')
        report_id = str(self.reports[0].id)
        response = self.client.get(url, {'report_id': report_id})
        self.assertEqual(response.status_code, 200)
        self.assertIn('status_changes', response.context)

    def test_pagination(self):
        url = reverse('dashboard:history')
        response = self.client.get(url)
        self.assertIn('paginator', response.context)
        self.assertIn('page_obj', response.context)

    def test_total_changes_count(self):
        url = reverse('dashboard:history')
        response = self.client.get(url)
        self.assertIn('total_changes', response.context)
        self.assertIsInstance(response.context['total_changes'], int)
        # We created 3 status changes in setUp
        self.assertEqual(response.context['total_changes'], 3)

    def test_filter_preserves_in_pagination(self):
        url = reverse('dashboard:history')
        report_id = str(self.reports[0].id)
        response = self.client.get(url, {'report_id': report_id})
        if response.context['paginator'].num_pages > 1:
            self.assertContains(response, f'report_id={report_id}')

    def test_status_changes_are_orm_objects(self):
        url = reverse('dashboard:history')
        response = self.client.get(url)
        status_changes = response.context['status_changes']
        if status_changes:
            change = status_changes[0]
            self.assertTrue(hasattr(change, 'from_status'))
            self.assertTrue(hasattr(change, 'to_status'))
            self.assertTrue(hasattr(change, 'changed_at'))
            self.assertTrue(hasattr(change, 'changed_by'))

    def test_empty_state_message(self):
        url = reverse('dashboard:history')
        response = self.client.get(url, {'report_id': 'nonexistent-xxxx'})
        self.assertEqual(response.status_code, 200)
        if len(response.context['status_changes']) == 0:
            self.assertContains(response, 'No status changes found')


class HistoryExportViewTests(TestCase):

    def setUp(self):
        self.client = _authed_client()
        # Create 2 reports with status changes
        self.reports = [_make_report_with_transition(f'exp{i}') for i in range(2)]

    def test_history_export_returns_200(self):
        url = reverse('dashboard:history_export')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_export_returns_csv_content_type(self):
        url = reverse('dashboard:history_export')
        response = self.client.get(url)
        self.assertEqual(response.get('Content-Type'), 'text/csv')

    def test_export_has_attachment_header(self):
        url = reverse('dashboard:history_export')
        response = self.client.get(url)
        self.assertIn('attachment', response.get('Content-Disposition', ''))
        self.assertIn('acts_history_export.csv', response.get('Content-Disposition', ''))

    def test_csv_export_downloads_correctly(self):
        url = reverse('dashboard:history_export')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        self.assertGreater(len(lines), 1)
        header = lines[0]
        self.assertIn('Timestamp', header)
        self.assertIn('Report ID', header)
        self.assertIn('From Status', header)
        self.assertIn('To Status', header)
        self.assertIn('Note', header)
        self.assertIn('Changed By', header)

    def test_export_contains_data_rows(self):
        url = reverse('dashboard:history_export')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        self.assertGreater(len(lines), 1)
        data_rows = lines[1:]
        self.assertGreater(len(data_rows), 0)

    def test_export_data_format(self):
        url = reverse('dashboard:history_export')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        data_rows = lines[1:]
        if data_rows:
            first_row = data_rows[0]
            self.assertGreaterEqual(first_row.count(','), 4)

    def test_export_filter_by_date_range(self):
        url = reverse('dashboard:history_export')
        today = timezone.now().date()
        response = self.client.get(url, {'date_from': str(today), 'date_to': str(today)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('Content-Type'), 'text/csv')

    def test_export_filter_by_report_id(self):
        url = reverse('dashboard:history_export')
        report_id = str(self.reports[0].id)
        response = self.client.get(url, {'report_id': report_id})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn(str(report_id)[:12], content)

    def test_export_timestamp_format(self):
        url = reverse('dashboard:history_export')
        response = self.client.get(url)
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        if len(lines) > 1:
            data_rows = lines[1:]
            for row in data_rows[:3]:
                parts = row.split(',')
                if len(parts) >= 1:
                    self.assertIn('-', parts[0])

    def test_export_empty_results(self):
        url = reverse('dashboard:history_export')
        response = self.client.get(url, {'report_id': 'nonexistent-id'})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        self.assertGreater(len(lines), 0)


class HistoryViewAuthTests(TestCase):

    def setUp(self):
        self.client = Client()

    def test_history_view_redirects_without_auth(self):
        url = reverse('dashboard:history')
        response = self.client.get(url, follow=False)
        self.assertEqual(response.status_code, 302)

    def test_export_view_redirects_without_auth(self):
        url = reverse('dashboard:history_export')
        response = self.client.get(url, follow=False)
        self.assertEqual(response.status_code, 302)

    def test_history_view_accessible_with_auth(self):
        session = self.client.session
        session['demo_authed'] = True
        session.save()
        url = reverse('dashboard:history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_export_accessible_with_auth(self):
        session = self.client.session
        session['demo_authed'] = True
        session.save()
        url = reverse('dashboard:history_export')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
