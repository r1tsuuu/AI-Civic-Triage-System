"""
Tests for TASK-031: Stats view (Phase 2 integration)
"""

import uuid
from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse

from apps.webhook.models import RawPost
from apps.triage.models import Report


def _make_report(suffix, category='other', status='reported', location_text=None):
    raw_post = RawPost.objects.create(
        facebook_post_id=f'stats_{suffix}_{uuid.uuid4().hex[:8]}',
        post_text=f'Stats test post {suffix}',
        received_at=timezone.now(),
        processed=True,
    )
    return Report.objects.create(
        raw_post=raw_post,
        category=category,
        classifier_confidence=0.8,
        urgency_score=5.0,
        status=status,
        location_text=location_text,
    )


class StatsViewTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.stats_url = reverse('dashboard:stats')

        session = self.client.session
        session['demo_authed'] = True
        session.save()

        # Create 5 recent reports (created_at = now via auto_now_add)
        self.recent_reports = [_make_report(f'r{i}') for i in range(5)]

        # Create 3 "old" reports and backdate them via update()
        old_reports = [_make_report(f'o{i}') for i in range(3)]
        now = timezone.now()
        for r in old_reports:
            Report.objects.filter(pk=r.pk).update(
                created_at=now - timedelta(hours=30)
            )

    def test_stats_view_returns_200(self):
        response = self.client.get(self.stats_url)
        self.assertEqual(response.status_code, 200)

    def test_stats_view_uses_correct_template(self):
        response = self.client.get(self.stats_url)
        self.assertTemplateUsed(response, 'dashboard/stats.html')

    def test_reports_24h_count_is_correct(self):
        response = self.client.get(self.stats_url)
        self.assertIn('stats', response.context)
        stats = response.context['stats']
        self.assertGreaterEqual(stats['reports_24h'], 5)

    def test_stats_context_has_all_required_fields(self):
        response = self.client.get(self.stats_url)
        stats = response.context['stats']
        required_fields = [
            'reports_24h',
            'reports_24h_change',
            'resolution_rate',
            'resolution_rate_change',
            'most_affected_barangay',
            'most_affected_count',
            'most_reported_category',
            'most_reported_count',
        ]
        for field in required_fields:
            self.assertIn(field, stats, f"Missing required field: {field}")

    def test_reports_24h_older_than_24_hours_are_excluded(self):
        # 8 total Reports created in setUp, but only 5 are recent
        total = Report.objects.count()
        self.assertEqual(total, 8)
        stats = self.client.get(self.stats_url).context['stats']
        self.assertEqual(stats['reports_24h'], 5)

    def test_stats_view_with_no_reports(self):
        Report.objects.all().delete()
        response = self.client.get(self.stats_url)
        self.assertEqual(response.status_code, 200)
        stats = response.context['stats']
        self.assertEqual(stats['reports_24h'], 0)

    def test_resolution_rate_field_is_present(self):
        response = self.client.get(self.stats_url)
        stats = response.context['stats']
        self.assertIsNotNone(stats['resolution_rate'])
        self.assertIsInstance(stats['resolution_rate'], int)

    def test_most_affected_barangay_field_is_string(self):
        response = self.client.get(self.stats_url)
        stats = response.context['stats']
        self.assertIsInstance(stats['most_affected_barangay'], str)

    def test_most_reported_category_field_is_string(self):
        response = self.client.get(self.stats_url)
        stats = response.context['stats']
        self.assertIsInstance(stats['most_reported_category'], str)
