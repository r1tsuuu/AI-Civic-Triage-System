"""
TASK-033: Report Detail View Tests
Uses triage.Report as the primary model (Phase 2 integration).
"""

import uuid
from django.test import TestCase, Client
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone

from apps.webhook.models import RawPost
from apps.triage.models import Report


def _make_report(suffix="000"):
    raw_post = RawPost.objects.create(
        facebook_post_id=f'detail_{suffix}_{uuid.uuid4().hex[:8]}',
        post_text='Flooding reported in Barangay Sabang, Lipa City. Several families affected.',
        received_at=timezone.now() - timedelta(hours=2),
        processed=True,
    )
    return Report.objects.create(
        raw_post=raw_post,
        category='disaster_flooding',
        classifier_confidence=0.82,
        urgency_score=7.5,
        location_text='Sabang',
        latitude=13.94,
        longitude=121.16,
        status='reported',
    )


class ReportDetailViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.report = _make_report('main')
        session = self.client.session
        session['demo_authed'] = True
        session.save()

    def test_detail_view_returns_200(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_detail_view_uses_correct_template(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'dashboard/report_detail.html')

    def test_post_text_visible_in_response(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, self.report.raw_post.post_text)

    def test_status_history_in_context(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Status History')
        self.assertIn('status_changes', response.context)
        self.assertIsInstance(response.context['status_changes'], list)

    def test_classification_data_in_context(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        report = response.context['report']
        self.assertTrue(hasattr(report, 'urgency_score'))
        self.assertTrue(hasattr(report, 'classifier_confidence'))
        self.assertTrue(hasattr(report, 'category'))

    def test_urgency_score_is_float_0_to_10(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        urgency = response.context['report'].urgency_score
        self.assertIsInstance(urgency, float)
        self.assertGreaterEqual(urgency, 0.0)
        self.assertLessEqual(urgency, 10.0)

    def test_confidence_is_float_0_to_1(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        report = response.context['report']
        # Both classifier_confidence and the compat alias 'confidence' must be set
        self.assertIsInstance(report.classifier_confidence, float)
        self.assertGreaterEqual(report.classifier_confidence, 0.0)
        self.assertLessEqual(report.classifier_confidence, 1.0)
        self.assertEqual(report.confidence, report.classifier_confidence)

    def test_category_is_valid_choice(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        category = response.context['report'].category
        valid_categories = [
            'disaster_flooding', 'transportation_traffic', 'public_infrastructure',
            'public_safety', 'other',
        ]
        self.assertIn(category, valid_categories)

    def test_auto_reply_in_context(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertIn('auto_reply', response.context)

    def test_available_next_statuses_in_context(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertIn('available_next_statuses', response.context)
        self.assertIsInstance(response.context['available_next_statuses'], list)

    def test_signal_breakdown_in_context(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        signal_breakdown = response.context['signal_breakdown']
        for key in ['distress', 'flood_depth', 'vulnerable', 'stranded']:
            self.assertIn(key, signal_breakdown)

    def test_classification_panel_displayed(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Classification')

    def test_location_panel_displayed(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Location Map')

    def test_action_buttons_section_displayed(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Actions')

    def test_status_stepper_displayed(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Status Progression')

    def test_routing_notes_section_displayed(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Routing Notes')

    def test_override_form_displayed(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Override Classification')

    def test_report_id_displayed(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, str(self.report.pk))

    def test_received_timestamp_displayed(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Received')

    def test_detail_view_404_for_invalid_id(self):
        invalid_uuid = uuid.uuid4()
        url = reverse('dashboard:report_detail', kwargs={'pk': invalid_uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_confidence_threshold_present(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        report = response.context['report']
        self.assertTrue(hasattr(report, 'confidence_threshold'))

    def test_has_low_confidence_flag_present(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        report = response.context['report']
        self.assertTrue(hasattr(report, 'has_low_confidence'))
        self.assertIsInstance(report.has_low_confidence, bool)

    def test_location_coordinates(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        report = response.context['report']
        self.assertTrue(hasattr(report, 'latitude'))
        self.assertTrue(hasattr(report, 'longitude'))
        # Our fixture sets coordinates
        self.assertIsNotNone(report.latitude)
        self.assertIsNotNone(report.longitude)

    def test_current_status_is_set(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        report = response.context['report']
        self.assertTrue(hasattr(report, 'current_status'))
        valid_statuses = ['reported', 'acknowledged', 'in_progress', 'resolved', 'dismissed']
        self.assertIn(report.current_status, valid_statuses)

    def test_all_statuses_in_context(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertIn('all_statuses', response.context)
        expected = ['reported', 'acknowledged', 'in_progress', 'resolved']
        self.assertEqual(response.context['all_statuses'], expected)

    def test_category_options_in_context(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertIn('category_options', response.context)
        options = response.context['category_options']
        for expected in ['disaster_flooding', 'public_safety', 'other']:
            self.assertIn(expected, options)


class ReportDetailViewAuthTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.report = _make_report('auth')

    def test_detail_view_redirects_without_auth(self):
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url, follow=False)
        self.assertEqual(response.status_code, 302)

    def test_detail_view_accessible_with_auth(self):
        session = self.client.session
        session['demo_authed'] = True
        session.save()
        url = reverse('dashboard:report_detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
