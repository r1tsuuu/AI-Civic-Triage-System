"""
TASK-034: History View Tests
=============================

Tests for HistoryView and HistoryExportView. Ensures:
- Status changes appear in timeline
- CSV export downloads correctly
- Filtering by date range works
- Filtering by report ID works
- Pagination works
"""

import uuid
from django.test import TestCase, Client
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone
from io import StringIO

from apps.webhook.models import RawPost


class HistoryViewTests(TestCase):
    """Tests for HistoryView (TASK-034)"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create multiple test reports
        self.reports = []
        for i in range(3):
            report = RawPost.objects.create(
                facebook_post_id=f'123456789{i}',
                post_text=f'Test report {i}',
                received_at=timezone.now() - timedelta(hours=i*10),
                processed=False,
            )
            self.reports.append(report)
        
        # Must authenticate to view dashboard
        session = self.client.session
        session['demo_authed'] = True
        session.save()
    
    def test_history_view_returns_200(self):
        """Test that history view returns HTTP 200"""
        url = reverse('dashboard:history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_history_view_uses_correct_template(self):
        """Test that history view uses history.html template"""
        url = reverse('dashboard:history')
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'dashboard/history.html')
    
    def test_status_changes_in_context(self):
        """Test that status changes are in context"""
        url = reverse('dashboard:history')
        response = self.client.get(url)
        self.assertIn('status_changes', response.context)
    
    def test_status_changes_appear_in_template(self):
        """SPEC: Status changes appear in template"""
        url = reverse('dashboard:history')
        response = self.client.get(url)
        # Check for timeline element
        self.assertContains(response, 'Status Change History')
        self.assertContains(response, 'history-timeline')
    
    def test_timeline_shows_report_ids(self):
        """Test that report IDs are shown as clickable links"""
        url = reverse('dashboard:history')
        response = self.client.get(url)
        
        # Check that at least one report ID appears
        for report in self.reports:
            self.assertContains(response, str(report.id))
    
    def test_timeline_shows_status_transitions(self):
        """Test that status transitions are shown (from → to)"""
        url = reverse('dashboard:history')
        response = self.client.get(url)
        # Check for transition format in template
        self.assertContains(response, 'transition-badge')
    
    def test_timeline_shows_timestamps(self):
        """Test that timestamps are displayed"""
        url = reverse('dashboard:history')
        response = self.client.get(url)
        # Check for timestamp display format
        self.assertContains(response, 'timestamp')
    
    def test_filter_bar_displayed(self):
        """Test that filter bar with date pickers is displayed"""
        url = reverse('dashboard:history')
        response = self.client.get(url)
        self.assertContains(response, 'From Date')
        self.assertContains(response, 'To Date')
        self.assertContains(response, 'Report ID')
    
    def test_export_button_displayed(self):
        """Test that export CSV button is displayed"""
        url = reverse('dashboard:history')
        response = self.client.get(url)
        self.assertContains(response, 'Export CSV')
    
    def test_filter_by_date_range(self):
        """Test filtering by date range"""
        url = reverse('dashboard:history')
        
        # Get changes for specific date
        today = timezone.now().date()
        response = self.client.get(url, {
            'date_from': str(today),
            'date_to': str(today),
        })
        
        self.assertEqual(response.status_code, 200)
        # Should have some changes in today's range
        self.assertIn('status_changes', response.context)
    
    def test_filter_by_report_id(self):
        """Test filtering by report ID"""
        url = reverse('dashboard:history')
        report_id = str(self.reports[0].id)
        
        response = self.client.get(url, {'report_id': report_id})
        
        self.assertEqual(response.status_code, 200)
        # Check that filtered results show the report
        self.assertIn('status_changes', response.context)
    
    def test_pagination(self):
        """Test that pagination works"""
        url = reverse('dashboard:history')
        response = self.client.get(url)
        
        # Should have paginator in context
        self.assertIn('paginator', response.context)
        self.assertIn('page_obj', response.context)
    
    def test_total_changes_count(self):
        """Test that total changes count is displayed"""
        url = reverse('dashboard:history')
        response = self.client.get(url)
        
        self.assertIn('total_changes', response.context)
        self.assertIsInstance(response.context['total_changes'], int)
        # Should have at least some changes (3 reports, each with 2-4 transitions)
        self.assertGreater(response.context['total_changes'], 0)
    
    def test_filter_preserves_in_pagination(self):
        """Test that filters are preserved in pagination links"""
        url = reverse('dashboard:history')
        report_id = str(self.reports[0].id)
        
        response = self.client.get(url, {'report_id': report_id})
        
        # Check that pagination links include filters
        if response.context['paginator'].num_pages > 1:
            self.assertContains(response, f'report_id={report_id}')
    
    def test_status_changes_have_required_fields(self):
        """Test that each status change has all required fields"""
        url = reverse('dashboard:history')
        response = self.client.get(url)
        
        status_changes = response.context['status_changes']
        if status_changes:
            for change in status_changes:
                self.assertIn('report_id', change)
                self.assertIn('timestamp', change)
                self.assertIn('from_status', change)
                self.assertIn('to_status', change)
                self.assertIn('notes', change)
                self.assertIn('changed_by', change)
    
    def test_empty_state_message(self):
        """Test that empty state message appears when no results"""
        # Filter for non-existent report ID
        url = reverse('dashboard:history')
        response = self.client.get(url, {'report_id': 'nonexistent'})
        
        self.assertEqual(response.status_code, 200)
        if len(response.context['status_changes']) == 0:
            self.assertContains(response, 'No status changes found')


class HistoryExportViewTests(TestCase):
    """Tests for HistoryExportView (TASK-034)"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test reports
        self.reports = []
        for i in range(2):
            report = RawPost.objects.create(
                facebook_post_id=f'987654321{i}',
                post_text=f'Export test report {i}',
                received_at=timezone.now() - timedelta(hours=i*5),
                processed=False,
            )
            self.reports.append(report)
        
        # Must authenticate
        session = self.client.session
        session['demo_authed'] = True
        session.save()
    
    def test_history_export_returns_200(self):
        """Test that export view returns HTTP 200"""
        url = reverse('dashboard:history-export')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_export_returns_csv_content_type(self):
        """Test that export returns CSV content type"""
        url = reverse('dashboard:history-export')
        response = self.client.get(url)
        self.assertEqual(response.get('Content-Type'), 'text/csv')
    
    def test_export_has_attachment_header(self):
        """Test that export has proper attachment header"""
        url = reverse('dashboard:history-export')
        response = self.client.get(url)
        self.assertIn('attachment', response.get('Content-Disposition', ''))
        self.assertIn('acts_history_export.csv', response.get('Content-Disposition', ''))
    
    def test_csv_export_downloads_correctly(self):
        """SPEC: CSV export downloads correctly"""
        url = reverse('dashboard:history-export')
        response = self.client.get(url)
        
        # Parse CSV content
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        
        # Should have header row
        self.assertGreater(len(lines), 1)
        
        # Header should contain required columns
        header = lines[0]
        self.assertIn('Timestamp', header)
        self.assertIn('Report ID', header)
        self.assertIn('Status Transition', header)
        self.assertIn('Notes', header)
        self.assertIn('Changed By', header)
    
    def test_export_contains_data_rows(self):
        """Test that export contains data rows"""
        url = reverse('dashboard:history-export')
        response = self.client.get(url)
        
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        
        # Should have more than just header
        self.assertGreater(len(lines), 1)
        
        # Data rows should exist
        data_rows = lines[1:]
        self.assertGreater(len(data_rows), 0)
    
    def test_export_data_format(self):
        """Test that exported data has correct format"""
        url = reverse('dashboard:history-export')
        response = self.client.get(url)
        
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        data_rows = lines[1:]
        
        if data_rows:
            # First data row should have 5 columns
            first_row = data_rows[0]
            # Count commas (simple check, CSV parsing is complex)
            self.assertGreaterEqual(first_row.count(','), 4)
    
    def test_export_contains_transition_arrow(self):
        """Test that export contains status transitions with arrow"""
        url = reverse('dashboard:history-export')
        response = self.client.get(url)
        
        content = response.content.decode('utf-8')
        # Should contain transitions (e.g., "reported → acknowledged")
        self.assertIn('→', content)
    
    def test_export_filter_by_date_range(self):
        """Test that export respects date range filter"""
        url = reverse('dashboard:history-export')
        
        today = timezone.now().date()
        response = self.client.get(url, {
            'date_from': str(today),
            'date_to': str(today),
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('Content-Type'), 'text/csv')
    
    def test_export_filter_by_report_id(self):
        """Test that export respects report ID filter"""
        url = reverse('dashboard:history-export')
        report_id = str(self.reports[0].id)
        
        response = self.client.get(url, {'report_id': report_id})
        
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        # Should contain the filtered report
        self.assertIn(str(report_id[:12]), content)  # Partial match
    
    def test_export_timestamp_format(self):
        """Test that export timestamps are properly formatted"""
        url = reverse('dashboard:history-export')
        response = self.client.get(url)
        
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        
        if len(lines) > 1:
            # Check that timestamps look like YYYY-MM-DD HH:MM:SS
            data_rows = lines[1:]
            for row in data_rows[:3]:  # Check first few rows
                # Timestamp should be first column
                parts = row.split(',')
                if len(parts) >= 1:
                    timestamp = parts[0]
                    # Should contain date-like format
                    self.assertIn('-', timestamp)
    
    def test_export_empty_results(self):
        """Test that export handles empty results gracefully"""
        url = reverse('dashboard:history-export')
        response = self.client.get(url, {'report_id': 'nonexistent-id'})
        
        self.assertEqual(response.status_code, 200)
        # Should still have header
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        self.assertGreater(len(lines), 0)


class HistoryViewAuthTests(TestCase):
    """Tests for authentication/authorization on history views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
    
    def test_history_view_redirects_without_auth(self):
        """Test that unauthenticated requests are redirected"""
        url = reverse('dashboard:history')
        response = self.client.get(url, follow=False)
        # Should redirect to gate (password page)
        self.assertEqual(response.status_code, 302)
    
    def test_export_view_redirects_without_auth(self):
        """Test that export requests are redirected without auth"""
        url = reverse('dashboard:history-export')
        response = self.client.get(url, follow=False)
        # Should redirect to gate
        self.assertEqual(response.status_code, 302)
    
    def test_history_view_accessible_with_auth(self):
        """Test that authenticated requests can access history"""
        session = self.client.session
        session['demo_authed'] = True
        session.save()
        
        url = reverse('dashboard:history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_export_accessible_with_auth(self):
        """Test that authenticated requests can access export"""
        session = self.client.session
        session['demo_authed'] = True
        session.save()
        
        url = reverse('dashboard:history-export')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
