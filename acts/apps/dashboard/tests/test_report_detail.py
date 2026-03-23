"""
TASK-033: Report Detail View Tests
===================================

Tests for the ReportDetailView. Ensures:
- Post text is visible
- Status history timeline shown
- Classification panel displays
- All sections render correctly
"""

import uuid
from django.test import TestCase, Client
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone

from apps.webhook.models import RawPost


class ReportDetailViewTests(TestCase):
    """Tests for ReportDetailView (TASK-033)"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create a test report
        self.report = RawPost.objects.create(
            facebook_post_id='123456789',
            post_text='Flooding reported in Barangay Cabanatuan. Several families affected.',
            received_at=timezone.now() - timedelta(hours=2),
            processed=False,
        )
        
        # Must authenticate to view dashboard
        session = self.client.session
        session['demo_authed'] = True
        session.save()
    
    def test_detail_view_returns_200(self):
        """Test that detail view returns HTTP 200 for valid report"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_detail_view_uses_correct_template(self):
        """Test that detail view uses report_detail.html template"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'dashboard/report_detail.html')
    
    def test_post_text_visible_in_context(self):
        """SPEC: Post text is visible"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, self.report.post_text)
    
    def test_status_history_shown_in_template(self):
        """SPEC: Status history is shown"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        # Check that status history section exists
        self.assertContains(response, 'Status History')
        # Check that status history context variable is present
        self.assertIn('status_changes', response.context)
    
    def test_status_changes_is_list(self):
        """Test that status_changes context is a list"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        status_changes = response.context['status_changes']
        self.assertIsInstance(status_changes, list)
    
    def test_status_changes_have_required_fields(self):
        """Test that each status change has required fields"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        status_changes = response.context['status_changes']
        
        if status_changes:  # If there are status changes
            for change in status_changes:
                self.assertIn('to_status', change)
                self.assertIn('timestamp', change)
                self.assertIn('notes', change)
    
    def test_classification_data_in_context(self):
        """Test that classification data (urgency, confidence, category) is in context"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        report = response.context['report']
        
        self.assertTrue(hasattr(report, 'urgency_score'))
        self.assertTrue(hasattr(report, 'confidence'))
        self.assertTrue(hasattr(report, 'category'))
        self.assertTrue(hasattr(report, 'barangay'))
    
    def test_urgency_score_is_integer_1_to_100(self):
        """Test that urgency_score is int between 1 and 100"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        urgency = response.context['report'].urgency_score
        
        self.assertIsInstance(urgency, int)
        self.assertGreaterEqual(urgency, 1)
        self.assertLessEqual(urgency, 100)
    
    def test_confidence_is_float_0_to_1(self):
        """Test that confidence is float between 0.5 and 1.0"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        confidence = response.context['report'].confidence
        
        self.assertIsInstance(confidence, float)
        self.assertGreaterEqual(confidence, 0.5)
        self.assertLessEqual(confidence, 1.0)
    
    def test_category_is_valid_choice(self):
        """Test that category is one of the valid categories"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        category = response.context['report'].category
        
        valid_categories = ['disaster', 'transport', 'infrastructure', 'safety', 'other']
        self.assertIn(category, valid_categories)
    
    def test_auto_reply_in_context(self):
        """Test that auto_reply is in context"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertIn('auto_reply', response.context)
    
    def test_available_next_statuses_in_context(self):
        """Test that available_next_statuses is in context"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertIn('available_next_statuses', response.context)
        self.assertIsInstance(response.context['available_next_statuses'], list)
    
    def test_signal_breakdown_in_context(self):
        """Test that signal_breakdown is in context with scores"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        signal_breakdown = response.context['signal_breakdown']
        
        self.assertIn('keyword_score', signal_breakdown)
        self.assertIn('location_score', signal_breakdown)
        self.assertIn('time_score', signal_breakdown)
        self.assertIn('consistency_score', signal_breakdown)
    
    def test_classification_panel_displayed(self):
        """Test that classification panel exists in template"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Classification')
    
    def test_location_panel_displayed(self):
        """Test that location panel exists in template"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Location Map')
    
    def test_action_buttons_section_displayed(self):
        """Test that action buttons section exists"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Actions')
    
    def test_status_stepper_displayed(self):
        """Test that status stepper/progression is displayed"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Status Progression')
    
    def test_routing_notes_section_displayed(self):
        """Test that routing notes section is displayed"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Routing Notes')
    
    def test_override_form_displayed(self):
        """Test that override form is displayed"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Override Classification')
    
    def test_report_id_displayed(self):
        """Test that report ID is displayed in detail view"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, str(self.report.pk))
    
    def test_received_timestamp_displayed(self):
        """Test that received timestamp is displayed"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Received')
    
    def test_detail_view_404_for_invalid_id(self):
        """Test that detail view returns 404 for invalid report ID"""
        invalid_uuid = uuid.uuid4()
        url = reverse('dashboard:report-detail', kwargs={'pk': invalid_uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
    
    def test_confidence_threshold_present(self):
        """Test that confidence_threshold is set on report"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        report = response.context['report']
        
        self.assertTrue(hasattr(report, 'confidence_threshold'))
        self.assertEqual(report.confidence_threshold, 0.75)
    
    def test_has_low_confidence_flag_present(self):
        """Test that has_low_confidence flag is set based on threshold"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        report = response.context['report']
        
        self.assertTrue(hasattr(report, 'has_low_confidence'))
        self.assertIsInstance(report.has_low_confidence, bool)
        
        # Verify logic: low_confidence = confidence < threshold
        if report.confidence < report.confidence_threshold:
            self.assertTrue(report.has_low_confidence)
        else:
            self.assertFalse(report.has_low_confidence)
    
    def test_location_coordinates_may_be_none(self):
        """Test that location coordinates can be None (NER not extracted)"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        report = response.context['report']
        
        self.assertTrue(hasattr(report, 'latitude'))
        self.assertTrue(hasattr(report, 'longitude'))
        # Coordinates can be None on some requests (mocked random)
    
    def test_location_coordinates_valid_range(self):
        """Test that if coordinates are set, they're in valid range for Philippines"""
        # Send multiple requests to get both cases (with and without coordinates)
        urls_with_coords = []
        urls_without_coords = []
        
        for i in range(10):
            url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
            response = self.client.get(url)
            report = response.context['report']
            
            if report.latitude is not None:
                urls_with_coords.append((report.latitude, report.longitude))
            else:
                urls_without_coords.append(None)
        
        # If we got coordinates, verify they're reasonable
        for lat, lng in urls_with_coords:
            self.assertGreaterEqual(lat, 14.5)
            self.assertLessEqual(lat, 15.5)
            self.assertGreaterEqual(lng, 120.5)
            self.assertLessEqual(lng, 121.5)
    
    def test_current_status_is_set(self):
        """Test that current_status is set on the report"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        report = response.context['report']
        
        self.assertTrue(hasattr(report, 'current_status'))
        valid_statuses = ['reported', 'acknowledged', 'in-progress', 'resolved']
        self.assertIn(report.current_status, valid_statuses)
    
    def test_routing_notes_present_in_context(self):
        """Test that routing_notes are present on report"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        report = response.context['report']
        
        self.assertTrue(hasattr(report, 'routing_notes'))
        self.assertIsNotNone(report.routing_notes)
    
    def test_barangay_is_set(self):
        """Test that barangay is set on the report"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        report = response.context['report']
        
        self.assertTrue(hasattr(report, 'barangay'))
        valid_barangays = ['Cabanatuan', 'San Fernando', 'Talugtug', 'General Nakar', 
                          'Amadeo', 'Imus', 'Tagaytay', 'Cavite City', 'Noveleta', 'Bacoor']
        self.assertIn(report.barangay, valid_barangays)
    
    def test_all_statuses_in_context(self):
        """Test that all_statuses list is in context"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        
        self.assertIn('all_statuses', response.context)
        all_statuses = response.context['all_statuses']
        expected = ['reported', 'acknowledged', 'in-progress', 'resolved']
        self.assertEqual(all_statuses, expected)
    
    def test_category_options_in_context(self):
        """Test that category_options list is in context"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        
        self.assertIn('category_options', response.context)
        category_options = response.context['category_options']
        expected = ['disaster', 'transport', 'infrastructure', 'safety', 'other']
        self.assertEqual(category_options, expected)


class ReportDetailViewAuthTests(TestCase):
    """Tests for authentication/authorization on detail view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.report = RawPost.objects.create(
            facebook_post_id='123456789',
            post_text='Test report',
            received_at=timezone.now(),
            processed=False,
        )
    
    def test_detail_view_redirects_without_auth(self):
        """Test that unauthenticated requests are redirected"""
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url, follow=False)
        # Should redirect to gate (password page)
        self.assertEqual(response.status_code, 302)
    
    def test_detail_view_accessible_with_auth(self):
        """Test that authenticated requests can access detail view"""
        session = self.client.session
        session['demo_authed'] = True
        session.save()
        
        url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
