"""
Tests for TASK-032: Report list view (Phase 2 integration)
"""

import uuid
from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse

from apps.webhook.models import RawPost
from apps.triage.models import Report


def _authed_client():
    client = Client()
    session = client.session
    session['demo_authed'] = True
    session.save()
    return client


def _make_report(suffix, category='other', status='reported', urgency_score=5.0,
                 classifier_confidence=0.8, location_text=None):
    raw_post = RawPost.objects.create(
        facebook_post_id=f'list_{suffix}_{uuid.uuid4().hex[:8]}',
        post_text=f'Test post {suffix}',
        received_at=timezone.now(),
        processed=True,
    )
    return Report.objects.create(
        raw_post=raw_post,
        category=category,
        classifier_confidence=classifier_confidence,
        urgency_score=urgency_score,
        status=status,
        location_text=location_text,
    )


class ReportListViewTestCase(TestCase):

    def setUp(self):
        self.client = _authed_client()
        self.list_url = reverse('dashboard:report_list')

        # Create 25 reports with varying urgency to test pagination and sort
        for i in range(25):
            _make_report(
                suffix=i,
                category='disaster_flooding' if i % 2 == 0 else 'other',
                status='reported' if i % 3 != 0 else 'acknowledged',
                urgency_score=float(i % 10) + 0.5,
                classifier_confidence=0.9 - (i % 5) * 0.1,
                location_text='Sabang' if i % 4 == 0 else None,
            )

    def test_report_list_view_returns_200(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

    def test_report_list_uses_correct_template(self):
        response = self.client.get(self.list_url)
        self.assertTemplateUsed(response, 'dashboard/list_view.html')

    def test_all_reports_appear_in_list(self):
        response = self.client.get(self.list_url)
        self.assertIn('reports', response.context)
        self.assertGreaterEqual(len(response.context['reports']), 20)

    def test_pagination_is_correct(self):
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.context['reports']), 20)
        self.assertTrue(response.context['is_paginated'])
        self.assertIsNotNone(response.context['page_obj'])
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertTrue(response.context['page_obj'].has_next())

    def test_second_page_has_remaining_items(self):
        response = self.client.get(self.list_url + '?page=2')
        self.assertEqual(len(response.context['reports']), 5)
        self.assertTrue(response.context['page_obj'].has_previous())
        self.assertFalse(response.context['page_obj'].has_next())

    def test_reports_have_real_classification_data(self):
        response = self.client.get(self.list_url)
        reports = response.context['reports']
        self.assertGreater(len(reports), 0)
        for report in reports:
            self.assertIsNotNone(report.urgency_score)
            self.assertIsNotNone(report.classifier_confidence)
            self.assertIsNotNone(report.category)
            self.assertIsNotNone(report.status)
            self.assertIsInstance(report.urgency_score, float)
            self.assertIsInstance(report.classifier_confidence, float)
            self.assertGreaterEqual(report.urgency_score, 0.0)
            self.assertLessEqual(report.urgency_score, 10.0)
            self.assertGreaterEqual(report.classifier_confidence, 0.0)
            self.assertLessEqual(report.classifier_confidence, 1.0)

    def test_confidence_alias_set(self):
        response = self.client.get(self.list_url)
        for report in response.context['reports']:
            self.assertEqual(report.confidence, report.classifier_confidence)

    def test_has_low_confidence_flag_set(self):
        response = self.client.get(self.list_url)
        for report in response.context['reports']:
            self.assertTrue(hasattr(report, 'has_low_confidence'))
            self.assertIsInstance(report.has_low_confidence, bool)

    def test_default_sort_is_urgency_descending(self):
        response = self.client.get(self.list_url)
        reports = response.context['reports']
        for i in range(1, len(reports)):
            self.assertGreaterEqual(
                reports[i - 1].urgency_score,
                reports[i].urgency_score,
            )

    def test_category_filter_works(self):
        response = self.client.get(self.list_url + '?category=disaster_flooding')
        reports = response.context['reports']
        for report in reports:
            self.assertEqual(report.category, 'disaster_flooding')

    def test_status_filter_works(self):
        response = self.client.get(self.list_url + '?status=reported')
        reports = response.context['reports']
        for report in reports:
            self.assertEqual(report.status, 'reported')

    def test_barangay_filter_works(self):
        # Filter by location text substring
        response = self.client.get(self.list_url + '?barangay=Sabang')
        reports = response.context['reports']
        self.assertGreater(len(reports), 0)
        for report in reports:
            self.assertIn('Sabang', report.location_text)

    def test_combined_filters_work(self):
        response = self.client.get(self.list_url + '?category=disaster_flooding&status=reported')
        reports = response.context['reports']
        for report in reports:
            self.assertEqual(report.category, 'disaster_flooding')
            self.assertEqual(report.status, 'reported')

    def test_category_options_in_context(self):
        response = self.client.get(self.list_url)
        self.assertIn('category_options', response.context)
        options = response.context['category_options']
        for expected in ['disaster_flooding', 'public_safety', 'other']:
            self.assertIn(expected, options)

    def test_status_options_in_context(self):
        response = self.client.get(self.list_url)
        self.assertIn('status_options', response.context)
        options = response.context['status_options']
        for expected in ['reported', 'acknowledged', 'resolved']:
            self.assertIn(expected, options)

    def test_barangay_options_in_context(self):
        response = self.client.get(self.list_url)
        self.assertIn('barangay_options', response.context)

    def test_filter_context_values_retained(self):
        response = self.client.get(self.list_url + '?category=disaster_flooding&status=reported')
        self.assertEqual(response.context['category_filter'], 'disaster_flooding')
        self.assertEqual(response.context['status_filter'], 'reported')

    def test_empty_filter_parameters(self):
        response = self.client.get(self.list_url + '?category=&status=&barangay=')
        self.assertEqual(response.status_code, 200)
        self.assertIn('reports', response.context)

    def test_invalid_filter_values_handled_gracefully(self):
        response = self.client.get(self.list_url + '?category=invalid_category&status=invalid_status')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['reports']), 0)


class ReportListViewAuthTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.list_url = reverse('dashboard:report_list')

    def test_list_view_redirects_without_auth(self):
        response = self.client.get(self.list_url, follow=False)
        self.assertEqual(response.status_code, 302)

    def test_list_view_accessible_with_auth(self):
        session = self.client.session
        session['demo_authed'] = True
        session.save()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
