"""
Tests for TASK-032: Report list view
"""
from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from apps.webhook.models import RawPost
from django.urls import reverse


class ReportListViewTestCase(TestCase):
    """Test the dashboard report list view (TASK-032)"""
    
    def setUp(self):
        """Set up test client and fixtures"""
        self.client = Client()
        self.list_url = reverse('dashboard:report-list')
        
        # Set demo session so middleware allows access
        session = self.client.session
        session['demo_authed'] = True
        session.save()
        
        # Create test RawPost instances
        now = timezone.now()
        
        # Create 25 posts with different timestamps to test pagination
        for i in range(25):
            RawPost.objects.create(
                facebook_post_id=f'post_{i:03d}',
                post_text=f'Test post number {i}: This is a test report about incident {i}',
                received_at=now - timedelta(hours=i)
            )
    
    def test_report_list_view_returns_200(self):
        """Test that the report list view returns HTTP 200 OK"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
    
    def test_report_list_uses_correct_template(self):
        """Test that the report list uses list_view.html template"""
        response = self.client.get(self.list_url)
        self.assertTemplateUsed(response, 'dashboard/list_view.html')
    
    def test_all_reports_appear_in_list(self):
        """Test that all reports appear in the list context"""
        response = self.client.get(self.list_url)
        
        # Should have reports in context
        self.assertIn('reports', response.context)
        reports = response.context['reports']
        
        # Should have at least 20 reports (paginate_by)
        self.assertGreaterEqual(len(reports), 20)
    
    def test_pagination_is_correct(self):
        """Test that pagination works and shows 20 items per page"""
        response = self.client.get(self.list_url)
        
        # First page should have 20 items
        self.assertEqual(len(response.context['reports']), 20)
        self.assertTrue(response.context['is_paginated'])
        
        # Page object should exist
        self.assertIsNotNone(response.context['page_obj'])
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertTrue(response.context['page_obj'].has_next())
    
    def test_second_page_has_remaining_items(self):
        """Test that second page has remaining items (5 in this case)"""
        response = self.client.get(self.list_url + '?page=2')
        
        # Second page should have 5 items (25 total - 20 on first page)
        self.assertEqual(len(response.context['reports']), 5)
        self.assertTrue(response.context['page_obj'].has_previous())
        self.assertFalse(response.context['page_obj'].has_next())
    
    def test_reports_have_mock_classification_data(self):
        """Test that each report has mock classification data attached"""
        response = self.client.get(self.list_url)
        
        reports = response.context['reports']
        self.assertGreater(len(reports), 0)
        
        for report in reports:
            # Check that mock data is present
            self.assertIsNotNone(report.urgency_score)
            self.assertIsNotNone(report.confidence)
            self.assertIsNotNone(report.category)
            self.assertIsNotNone(report.status)
            self.assertIsNotNone(report.barangay)
            
            # Verify data types
            self.assertIsInstance(report.urgency_score, int)
            self.assertIsInstance(report.confidence, float)
            self.assertIsInstance(report.category, str)
            self.assertIsInstance(report.status, str)
            self.assertIsInstance(report.barangay, str)
            
            # Verify valid ranges
            self.assertGreaterEqual(report.urgency_score, 1)
            self.assertLessEqual(report.urgency_score, 100)
            self.assertGreaterEqual(report.confidence, 0.5)
            self.assertLessEqual(report.confidence, 1.0)
    
    def test_default_sort_is_urgency_descending(self):
        """Test that reports are sorted by urgency descending by default"""
        response = self.client.get(self.list_url)
        
        reports = response.context['reports']
        
        # Check that urgency scores are in descending order
        for i in range(1, len(reports)):
            self.assertGreaterEqual(
                reports[i-1].urgency_score,
                reports[i].urgency_score,
                f"Reports should be sorted by urgency descending"
            )
    
    def test_category_filter_works(self):
        """Test that category filter correctly filters reports"""
        # Get available categories from first page
        response = self.client.get(self.list_url)
        category_options = response.context['category_options']
        
        # Test filtering by the first available category
        test_category = category_options[0]
        response = self.client.get(self.list_url + f'?category={test_category}')
        
        reports = response.context['reports']
        
        # All returned reports should have the filter category
        for report in reports:
            self.assertEqual(report.category, test_category)
    
    def test_status_filter_works(self):
        """Test that status filter correctly filters reports"""
        response = self.client.get(self.list_url)
        status_options = response.context['status_options']
        
        # Test filtering by the first available status
        test_status = status_options[0]
        response = self.client.get(self.list_url + f'?status={test_status}')
        
        reports = response.context['reports']
        
        # All returned reports should have the filter status
        for report in reports:
            self.assertEqual(report.status, test_status)
    
    def test_barangay_filter_works(self):
        """Test that barangay filter correctly filters reports"""
        response = self.client.get(self.list_url)
        barangay_options = response.context['barangay_options']
        
        # Test filtering by the first available barangay
        test_barangay = barangay_options[0]
        response = self.client.get(self.list_url + f'?barangay={test_barangay}')
        
        reports = response.context['reports']
        
        # All returned reports should have the filter barangay
        for report in reports:
            self.assertEqual(report.barangay, test_barangay)
    
    def test_combined_filters_work(self):
        """Test that multiple filters can be combined"""
        response = self.client.get(self.list_url)
        category = response.context['category_options'][0]
        status = response.context['status_options'][0]
        
        # Apply both filters
        response = self.client.get(self.list_url + f'?category={category}&status={status}')
        
        reports = response.context['reports']
        
        # All reports should match both filters
        for report in reports:
            self.assertEqual(report.category, category)
            self.assertEqual(report.status, status)
    
    def test_sort_options_available(self):
        """Test that sort options are available in context"""
        response = self.client.get(self.list_url)
        
        self.assertIn('sort_options', response.context)
        sort_options = response.context['sort_options']
        
        # Should have at least 4 sort options
        self.assertGreaterEqual(len(sort_options), 4)
    
    def test_urgency_sort_ascending(self):
        """Test that urgency ascending sort works"""
        response = self.client.get(self.list_url + '?sort=urgency_asc')
        
        reports = response.context['reports']
        
        # Check that urgency scores are in ascending order
        for i in range(1, len(reports)):
            self.assertLessEqual(
                reports[i-1].urgency_score,
                reports[i].urgency_score,
                f"Reports should be sorted by urgency ascending"
            )
    
    def test_low_confidence_tag_displayed(self):
        """Test that low confidence tag is set correctly on reports"""
        response = self.client.get(self.list_url)
        
        reports = response.context['reports']
        confidence_threshold = 0.75
        
        # Check each report's confidence flag
        for report in reports:
            if report.confidence < confidence_threshold:
                self.assertTrue(report.has_low_confidence)
            else:
                self.assertFalse(report.has_low_confidence)
    
    def test_filter_context_values_retained(self):
        """Test that filter values are retained in context after filtering"""
        test_category = 'disaster'
        test_status = 'reported'
        
        response = self.client.get(self.list_url + f'?category={test_category}&status={test_status}')
        
        # Filter values should be in context for form preservation
        self.assertEqual(response.context['category_filter'], test_category)
        self.assertEqual(response.context['status_filter'], test_status)
    
    def test_empty_filter_parameters(self):
        """Test that empty filter parameters don't break the view"""
        response = self.client.get(self.list_url + '?category=&status=&barangay=')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('reports', response.context)
    
    def test_invalid_filter_values_handled_gracefully(self):
        """Test that invalid filter values don't crash the view"""
        response = self.client.get(self.list_url + '?category=invalid_category&status=invalid_status')
        
        self.assertEqual(response.status_code, 200)
        # Should return empty results for invalid filters
        self.assertEqual(len(response.context['reports']), 0)
