"""
Unit tests for apps/triage/classifier.py.
Tests both the fallback behaviour (no model file) and the classify() contract.
"""
from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase
from apps.triage.classifier import classify


class ClassifyFallbackTests(SimpleTestCase):

    def test_missing_model_returns_other_zero(self):
        with patch('apps.triage.classifier._get_model', return_value=None):
            category, confidence = classify('any text')
        self.assertEqual(category, 'other')
        self.assertEqual(confidence, 0.0)

    def test_exception_during_prediction_returns_other_zero(self):
        mock_model = MagicMock()
        mock_model.predict_proba.side_effect = Exception('predict failed')
        with patch('apps.triage.classifier._get_model', return_value=mock_model):
            category, confidence = classify('any text')
        self.assertEqual(category, 'other')
        self.assertEqual(confidence, 0.0)

    def test_classify_never_raises(self):
        with patch('apps.triage.classifier._get_model', side_effect=Exception('boom')):
            try:
                result = classify('any text')
            except Exception:
                self.fail('classify() raised an exception to the caller')


class ClassifyWithMockModelTests(SimpleTestCase):

    def _make_mock_model(self, category, confidence):
        import numpy as np
        mock_model = MagicMock()
        mock_model.classes_ = ['disaster_flooding', 'other', 'public_safety',
                               'public_infrastructure', 'transportation_traffic']
        idx = mock_model.classes_.index(category)
        proba = np.zeros(len(mock_model.classes_))
        proba[idx] = confidence
        mock_model.predict_proba.return_value = [proba]
        return mock_model

    def test_returns_tuple_of_two(self):
        model = self._make_mock_model('disaster_flooding', 0.9)
        with patch('apps.triage.classifier._get_model', return_value=model):
            result = classify('baha')
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_returns_correct_category(self):
        model = self._make_mock_model('disaster_flooding', 0.9)
        with patch('apps.triage.classifier._get_model', return_value=model):
            category, _ = classify('baha sa barangay')
        self.assertEqual(category, 'disaster_flooding')

    def test_confidence_is_float(self):
        model = self._make_mock_model('other', 0.75)
        with patch('apps.triage.classifier._get_model', return_value=model):
            _, confidence = classify('random text')
        self.assertIsInstance(confidence, float)

    def test_confidence_in_range(self):
        model = self._make_mock_model('other', 0.75)
        with patch('apps.triage.classifier._get_model', return_value=model):
            _, confidence = classify('random text')
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)

    def test_category_from_valid_set(self):
        valid = {'disaster_flooding', 'transportation_traffic',
                 'public_infrastructure', 'public_safety', 'other'}
        model = self._make_mock_model('public_safety', 0.8)
        with patch('apps.triage.classifier._get_model', return_value=model):
            category, _ = classify('may krimen dito')
        self.assertIn(category, valid)
