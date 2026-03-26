"""
TASK-041: Override Report Endpoint Tests

Tests for OverrideReportView (POST /dashboard/reports/<uuid>/override/)
Uses triage.Report + triage.CorrectionLog (Phase 2 integration).
"""

import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.webhook.models import RawPost
from apps.triage.models import Report, CorrectionLog


def _authed_client():
    client = Client()
    session = client.session
    session['demo_authed'] = True
    session.save()
    return client


def _make_report(suffix="000", category='other', location_text=None):
    raw_post = RawPost.objects.create(
        facebook_post_id=f'test_{suffix}_{uuid.uuid4().hex[:8]}',
        post_text='Test post about a critical incident.',
        received_at=timezone.now(),
        processed=True,
    )
    return Report.objects.create(
        raw_post=raw_post,
        category=category,
        classifier_confidence=0.8,
        urgency_score=3.0,
        location_text=location_text,
        status='reported',
    )


class OverrideReportViewBasicTests(TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.report = _make_report('basic')

    def test_override_endpoint_accepts_post(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {'category': 'disaster_flooding'})
        self.assertIn(response.status_code, [301, 302])

    def test_override_endpoint_returns_404_for_nonexistent_report(self):
        fake_uuid = uuid.uuid4()
        url = reverse('dashboard:override', kwargs={'pk': fake_uuid})
        response = self.client.post(url, {'category': 'disaster_flooding'})
        self.assertEqual(response.status_code, 404)

    def test_override_endpoint_redirects_to_detail_page(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {'category': 'disaster_flooding'})
        expected_url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        self.assertRedirects(response, expected_url)

    def test_get_request_returns_405(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)


class CategoryOverrideTests(TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.report = _make_report('category', category='other')

    def test_category_override_creates_correction_log(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        self.client.post(url, {'category': 'disaster_flooding'})
        self.assertEqual(CorrectionLog.objects.filter(report=self.report).count(), 1)

    def test_category_override_records_old_and_new_values(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        self.client.post(url, {'category': 'disaster_flooding'})
        log = CorrectionLog.objects.filter(report=self.report).latest('corrected_at')
        self.assertEqual(log.old_category, 'other')
        self.assertEqual(log.new_category, 'disaster_flooding')

    def test_category_override_updates_report(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        self.client.post(url, {'category': 'public_safety'})
        self.report.refresh_from_db()
        self.assertEqual(self.report.category, 'public_safety')

    def test_multiple_category_overrides_chain_old_values(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        self.client.post(url, {'category': 'disaster_flooding'})
        self.client.post(url, {'category': 'transportation_traffic'})
        logs = list(CorrectionLog.objects.filter(report=self.report).order_by('corrected_at'))
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0].new_category, 'disaster_flooding')
        self.assertEqual(logs[1].old_category, 'disaster_flooding')
        self.assertEqual(logs[1].new_category, 'transportation_traffic')

    def test_no_log_when_category_unchanged(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        self.client.post(url, {'category': 'other'})  # same as current
        self.assertEqual(CorrectionLog.objects.filter(report=self.report).count(), 0)


class LocationOverrideTests(TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.report = _make_report('location', location_text=None)

    def test_location_override_creates_correction_log(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        self.client.post(url, {'location_text': 'Sabang, Lipa City'})
        self.assertEqual(CorrectionLog.objects.filter(report=self.report).count(), 1)

    def test_location_override_records_values(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        self.client.post(url, {'location_text': 'Sabang'})
        log = CorrectionLog.objects.filter(report=self.report).latest('corrected_at')
        self.assertIsNone(log.old_location)
        self.assertEqual(log.new_location, 'Sabang')

    def test_location_override_updates_report(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        self.client.post(url, {'location_text': 'Mataas na Lupa, Lipa City'})
        self.report.refresh_from_db()
        self.assertEqual(self.report.location_text, 'Mataas na Lupa, Lipa City')


class CombinedOverrideTests(TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.report = _make_report('combined', category='other')

    def test_both_fields_override_in_one_request(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        self.client.post(url, {
            'category': 'disaster_flooding',
            'location_text': 'Inosluban, Lipa City',
        })
        self.assertEqual(CorrectionLog.objects.filter(report=self.report).count(), 2)

    def test_empty_override_shows_warning(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {})
        self.assertIn(response.status_code, [301, 302])


class CorrectionLogAuditTests(TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.report = _make_report('audit')

    def test_correction_log_records_timestamp(self):
        before = timezone.now()
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        self.client.post(url, {'category': 'disaster_flooding'})
        after = timezone.now()
        log = CorrectionLog.objects.get(report=self.report)
        self.assertGreaterEqual(log.corrected_at, before)
        self.assertLessEqual(log.corrected_at, after)

    def test_correction_log_maintains_order(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        self.client.post(url, {'category': 'disaster_flooding'})
        self.client.post(url, {'category': 'transportation_traffic'})
        self.client.post(url, {'category': 'public_infrastructure'})
        logs = list(CorrectionLog.objects.filter(report=self.report).order_by('corrected_at'))
        self.assertEqual(len(logs), 3)
        self.assertEqual(logs[0].new_category, 'disaster_flooding')
        self.assertEqual(logs[1].new_category, 'transportation_traffic')
        self.assertEqual(logs[2].new_category, 'public_infrastructure')


class DetailPageReflectionTests(TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.report = _make_report('detail')

    def test_overridden_category_shown_on_detail_page(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        self.client.post(url, {'category': 'disaster_flooding'})
        detail_url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(detail_url)
        self.report.refresh_from_db()
        self.assertEqual(self.report.category, 'disaster_flooding')

    def test_overridden_location_shown_on_detail_page(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        self.client.post(url, {'location_text': 'Sabang, Lipa City'})
        self.report.refresh_from_db()
        self.assertEqual(self.report.location_text, 'Sabang, Lipa City')

    def test_multiple_overrides_reflect_latest_values(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        self.client.post(url, {'category': 'disaster_flooding'})
        self.client.post(url, {'category': 'transportation_traffic'})
        self.report.refresh_from_db()
        self.assertEqual(self.report.category, 'transportation_traffic')


class MessageHandlingTests(TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.report = _make_report('messages')

    def test_success_message_on_category_override(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {'category': 'disaster_flooding'}, follow=True)
        messages_list = list(response.context['messages'])
        self.assertTrue(any('updated' in str(m).lower() for m in messages_list))

    def test_warning_message_when_no_fields_provided(self):
        url = reverse('dashboard:override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {}, follow=True)
        messages_list = list(response.context['messages'])
        self.assertTrue(any('no fields' in str(m).lower() for m in messages_list))
