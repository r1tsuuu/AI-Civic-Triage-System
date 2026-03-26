"""
Unit tests for apps/triage/pipeline.py — process_post() orchestration.
All NLP components are mocked; only DB interactions are real.
"""
import uuid
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone

from apps.webhook.models import RawPost
from apps.triage.models import Report
from apps.triage.pipeline import process_post


def _make_raw_post(text='Test civic complaint'):
    return RawPost.objects.create(
        facebook_post_id=f'pipeline_{uuid.uuid4().hex[:8]}',
        post_text=text,
        received_at=timezone.now(),
        processed=False,
    )


class ProcessPostSuccessTests(TestCase):

    @patch('apps.triage.pipeline.compute_score', return_value=5.0)
    @patch('apps.triage.pipeline.geocode', return_value=(13.94, 121.16, 'high'))
    @patch('apps.triage.pipeline.extract_locations', return_value=['Bigben'])
    @patch('apps.triage.pipeline.classify', return_value=('disaster_flooding', 0.88))
    def test_returns_report_instance(self, mock_clf, mock_ner, mock_geo, mock_score):
        rp = _make_raw_post()
        result = process_post(rp)
        self.assertIsInstance(result, Report)

    @patch('apps.triage.pipeline.compute_score', return_value=5.0)
    @patch('apps.triage.pipeline.geocode', return_value=(13.94, 121.16, 'high'))
    @patch('apps.triage.pipeline.extract_locations', return_value=['Bigben'])
    @patch('apps.triage.pipeline.classify', return_value=('disaster_flooding', 0.88))
    def test_report_saved_to_database(self, mock_clf, mock_ner, mock_geo, mock_score):
        rp = _make_raw_post()
        report = process_post(rp)
        self.assertTrue(Report.objects.filter(pk=report.pk).exists())

    @patch('apps.triage.pipeline.compute_score', return_value=5.0)
    @patch('apps.triage.pipeline.geocode', return_value=(13.94, 121.16, 'high'))
    @patch('apps.triage.pipeline.extract_locations', return_value=['Bigben'])
    @patch('apps.triage.pipeline.classify', return_value=('disaster_flooding', 0.88))
    def test_report_category_set_from_classifier(self, mock_clf, mock_ner, mock_geo, mock_score):
        rp = _make_raw_post()
        report = process_post(rp)
        self.assertEqual(report.category, 'disaster_flooding')

    @patch('apps.triage.pipeline.compute_score', return_value=5.0)
    @patch('apps.triage.pipeline.geocode', return_value=(13.94, 121.16, 'high'))
    @patch('apps.triage.pipeline.extract_locations', return_value=['Bigben'])
    @patch('apps.triage.pipeline.classify', return_value=('disaster_flooding', 0.88))
    def test_report_confidence_set(self, mock_clf, mock_ner, mock_geo, mock_score):
        rp = _make_raw_post()
        report = process_post(rp)
        self.assertAlmostEqual(report.classifier_confidence, 0.88)

    @patch('apps.triage.pipeline.compute_score', return_value=5.0)
    @patch('apps.triage.pipeline.geocode', return_value=(13.94, 121.16, 'high'))
    @patch('apps.triage.pipeline.extract_locations', return_value=['Bigben'])
    @patch('apps.triage.pipeline.classify', return_value=('disaster_flooding', 0.88))
    def test_report_urgency_score_set(self, mock_clf, mock_ner, mock_geo, mock_score):
        rp = _make_raw_post()
        report = process_post(rp)
        self.assertEqual(report.urgency_score, 5.0)

    @patch('apps.triage.pipeline.compute_score', return_value=5.0)
    @patch('apps.triage.pipeline.geocode', return_value=(13.94, 121.16, 'high'))
    @patch('apps.triage.pipeline.extract_locations', return_value=['Bigben'])
    @patch('apps.triage.pipeline.classify', return_value=('disaster_flooding', 0.88))
    def test_report_location_set(self, mock_clf, mock_ner, mock_geo, mock_score):
        rp = _make_raw_post()
        report = process_post(rp)
        self.assertEqual(report.location_text, 'Bigben')
        self.assertAlmostEqual(report.latitude, 13.94)
        self.assertAlmostEqual(report.longitude, 121.16)
        self.assertEqual(report.location_confidence, 'high')

    @patch('apps.triage.pipeline.compute_score', return_value=5.0)
    @patch('apps.triage.pipeline.geocode', return_value=(13.94, 121.16, 'high'))
    @patch('apps.triage.pipeline.extract_locations', return_value=['Bigben'])
    @patch('apps.triage.pipeline.classify', return_value=('disaster_flooding', 0.88))
    def test_report_status_is_reported(self, mock_clf, mock_ner, mock_geo, mock_score):
        rp = _make_raw_post()
        report = process_post(rp)
        self.assertEqual(report.status, 'reported')

    @patch('apps.triage.pipeline.compute_score', return_value=5.0)
    @patch('apps.triage.pipeline.geocode', return_value=(13.94, 121.16, 'high'))
    @patch('apps.triage.pipeline.extract_locations', return_value=['Bigben'])
    @patch('apps.triage.pipeline.classify', return_value=('disaster_flooding', 0.88))
    def test_raw_post_marked_processed(self, mock_clf, mock_ner, mock_geo, mock_score):
        rp = _make_raw_post()
        process_post(rp)
        rp.refresh_from_db()
        self.assertTrue(rp.processed)


class ProcessPostNoLocationTests(TestCase):

    @patch('apps.triage.pipeline.compute_score', return_value=3.0)
    @patch('apps.triage.pipeline.extract_locations', return_value=[])
    @patch('apps.triage.pipeline.classify', return_value=('other', 0.6))
    def test_no_location_sets_unresolved(self, mock_clf, mock_ner, mock_score):
        rp = _make_raw_post()
        report = process_post(rp)
        self.assertIsNone(report.latitude)
        self.assertIsNone(report.longitude)
        self.assertIsNone(report.location_text)
        self.assertEqual(report.location_confidence, 'unresolved')


class ProcessPostFallbackTests(TestCase):

    @patch('apps.triage.pipeline.classify', side_effect=Exception('classifier exploded'))
    def test_catastrophic_failure_still_creates_report(self, mock_clf):
        rp = _make_raw_post()
        report = process_post(rp)
        self.assertIsNotNone(report)
        self.assertIsInstance(report, Report)

    @patch('apps.triage.pipeline.classify', side_effect=Exception('classifier exploded'))
    def test_fallback_report_has_other_category(self, mock_clf):
        rp = _make_raw_post()
        report = process_post(rp)
        self.assertEqual(report.category, 'other')

    @patch('apps.triage.pipeline.classify', side_effect=Exception('classifier exploded'))
    def test_fallback_report_has_zero_confidence(self, mock_clf):
        rp = _make_raw_post()
        report = process_post(rp)
        self.assertEqual(report.classifier_confidence, 0.0)

    @patch('apps.triage.pipeline.classify', side_effect=Exception('classifier exploded'))
    def test_process_post_never_raises(self, mock_clf):
        rp = _make_raw_post()
        try:
            process_post(rp)
        except Exception:
            self.fail('process_post() raised an exception to the caller')
