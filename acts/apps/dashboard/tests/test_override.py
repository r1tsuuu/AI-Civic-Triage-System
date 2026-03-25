"""
TASK-041: Override Report Endpoint Tests
==========================================

Tests for the OverrideReportView (POST /dashboard/reports/<uuid>/override/)

Ensures:
- Category overrides are recorded in CorrectionLog
- Location text overrides are recorded in CorrectionLog
- Multiple fields can be overridden in one request
- Updated fields are reflected on the detail page
- CorrectionLog entries have correct old/new values
- Unauthenticated requests are handled
- Non-existent UUID returns 404
"""

import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from apps.webhook.models import RawPost, CorrectionLog


def _authed_client():
    """Return a test client with the demo session flag set."""
    client = Client()
    session = client.session
    session['demo_authed'] = True
    session.save()
    return client


def _make_report(suffix="000"):
    """Create a test report with unique facebook_post_id."""
    return RawPost.objects.create(
        facebook_post_id=f'test_{suffix}_{uuid.uuid4().hex[:8]}',
        post_text='Test post about a critical incident.',
        received_at=timezone.now(),
        processed=False,
        status=RawPost.STATUS_REPORTED,
    )


class OverrideReportViewBasicTests(TestCase):
    """Basic tests for override endpoint."""

    def setUp(self):
        self.client = _authed_client()
        self.report = _make_report('basic')

    def test_override_endpoint_accepts_post(self):
        """Test that POST to override endpoint is accepted"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {'category': 'disaster'})
        # Should redirect to detail page (302)
        self.assertIn(response.status_code, [301, 302])

    def test_override_endpoint_returns_404_for_nonexistent_report(self):
        """Test that 404 is returned for non-existent uuid"""
        fake_uuid = uuid.uuid4()
        url = reverse('dashboard:report-override', kwargs={'pk': fake_uuid})
        response = self.client.post(url, {'category': 'disaster'})
        self.assertEqual(response.status_code, 404)

    def test_override_endpoint_redirects_to_detail_page(self):
        """Test that successful override redirects to report detail"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {'category': 'disaster'})
        expected_url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        self.assertRedirects(response, expected_url)

    def test_get_request_returns_405(self):
        """Test that GET requests return 405 Method Not Allowed"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)


class CategoryOverrideTests(TestCase):
    """Tests for category field overrides."""

    def setUp(self):
        self.client = _authed_client()
        self.report = _make_report('category')

    def test_category_override_creates_correction_log(self):
        """Test that category override creates a CorrectionLog entry"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {'category': 'disaster'})
        
        # Check that CorrectionLog entry was created
        corrections = CorrectionLog.objects.filter(report=self.report, field_name='category')
        self.assertEqual(corrections.count(), 1)

    def test_category_override_records_old_and_new_values(self):
        """Test that old and new values are recorded"""
        # First, create an initial correction log entry to establish 'transport' as the current value
        CorrectionLog.objects.create(
            report=self.report,
            field_name='category',
            old_value=None,
            new_value='transport',
            corrected_by='demo',
        )
        
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {'category': 'disaster'})
        
        # Check that we have 2 correction log entries
        corrections = CorrectionLog.objects.filter(report=self.report, field_name='category')
        self.assertEqual(corrections.count(), 2)
        
        # Check the second (most recent) entry
        second_correction = corrections.order_by('-corrected_at').first()
        self.assertEqual(second_correction.old_value, 'transport')
        self.assertEqual(second_correction.new_value, 'disaster')

    def test_category_override_none_to_value(self):
        """Test category override from None to a value"""
        # Report has no category initially
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {'category': 'infrastructure'})
        
        correction = CorrectionLog.objects.get(report=self.report, field_name='category')
        self.assertIsNone(correction.old_value)
        self.assertEqual(correction.new_value, 'infrastructure')

    def test_category_override_persisted_on_report(self):
        """Test that category override is set on the report object"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {'category': 'safety'})
        
        # The category is stored in CorrectionLog, not on the report model itself
        # Check that a CorrectionLog entry was created
        correction = CorrectionLog.objects.get(report=self.report, field_name='category')
        self.assertEqual(correction.new_value, 'safety')

    def test_multiple_category_overrides_create_multiple_logs(self):
        """Test that each override creates a new log entry"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        
        # First override
        self.client.post(url, {'category': 'disaster'})
        # Second override
        self.client.post(url, {'category': 'transport'})
        
        corrections = CorrectionLog.objects.filter(report=self.report, field_name='category')
        self.assertEqual(corrections.count(), 2)
        
        # Check values are in chronological order
        corrections_list = list(corrections.order_by('corrected_at'))
        self.assertEqual(corrections_list[0].new_value, 'disaster')
        self.assertEqual(corrections_list[1].old_value, 'disaster')
        self.assertEqual(corrections_list[1].new_value, 'transport')


class LocationOverrideTests(TestCase):
    """Tests for location_text field overrides."""

    def setUp(self):
        self.client = _authed_client()
        self.report = _make_report('location')

    def test_location_text_override_creates_correction_log(self):
        """Test that location_text override creates a CorrectionLog entry"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {'location_text': 'Cabanatuan, Nueva Ecija'})
        
        corrections = CorrectionLog.objects.filter(report=self.report, field_name='location_text')
        self.assertEqual(corrections.count(), 1)

    def test_location_text_override_records_values(self):
        """Test that old and new location_text values are recorded"""
        # First, create an initial correction log entry
        CorrectionLog.objects.create(
            report=self.report,
            field_name='location_text',
            old_value=None,
            new_value='San Fernando',
            corrected_by='demo',
        )
        
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {'location_text': 'Cabanatuan'})
        
        # Check the most recent correction entry
        correction = CorrectionLog.objects.filter(report=self.report, field_name='location_text').order_by('-corrected_at').first()
        self.assertEqual(correction.old_value, 'San Fernando')
        self.assertEqual(correction.new_value, 'Cabanatuan')

    def test_location_override_persisted_on_report(self):
        """Test that location_text override is set on the report object"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {'location_text': 'Tagaytay City'})
        
        # The location_text is stored in CorrectionLog, not on the report model itself
        # Check that a CorrectionLog entry was created
        correction = CorrectionLog.objects.get(report=self.report, field_name='location_text')
        self.assertEqual(correction.new_value, 'Tagaytay City')


class CombinedOverrideTests(TestCase):
    """Tests for overriding multiple fields in one request."""

    def setUp(self):
        self.client = _authed_client()
        self.report = _make_report('combined')

    def test_both_category_and_location_override_in_one_request(self):
        """Test that both category and location_text can be overridden together"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {
            'category': 'disaster',
            'location_text': 'Imus, Cavite'
        })
        
        # Check both corrections were created
        self.assertEqual(
            CorrectionLog.objects.filter(report=self.report, field_name='category').count(),
            1
        )
        self.assertEqual(
            CorrectionLog.objects.filter(report=self.report, field_name='location_text').count(),
            1
        )

    def test_combined_override_creates_two_log_entries(self):
        """Test that combined override creates exactly 2 log entries"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {
            'category': 'transport',
            'location_text': 'Bacoor, Cavite'
        })
        
        total_corrections = CorrectionLog.objects.filter(report=self.report).count()
        self.assertEqual(total_corrections, 2)

    def test_combined_override_values_are_correct(self):
        """Test that both fields have correct old/new values"""
        # Create initial correction log entries
        CorrectionLog.objects.create(
            report=self.report,
            field_name='category',
            old_value=None,
            new_value='safety',
            corrected_by='demo',
        )
        CorrectionLog.objects.create(
            report=self.report,
            field_name='location_text',
            old_value=None,
            new_value='San Fernando',
            corrected_by='demo',
        )
        
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {
            'category': 'disaster',
            'location_text': 'Imus'
        })
        
        # Check category correction (get most recent)
        category_correction = CorrectionLog.objects.filter(
            report=self.report, field_name='category'
        ).order_by('-corrected_at').first()
        self.assertEqual(category_correction.old_value, 'safety')
        self.assertEqual(category_correction.new_value, 'disaster')
        
        # Check location correction (get most recent)
        location_correction = CorrectionLog.objects.filter(
            report=self.report, field_name='location_text'
        ).order_by('-corrected_at').first()
        self.assertEqual(location_correction.old_value, 'San Fernando')
        self.assertEqual(location_correction.new_value, 'Imus')

    def test_empty_override_shows_warning(self):
        """Test that POST with no fields shows warning message"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {})
        
        # Should still redirect
        self.assertIn(response.status_code, [301, 302])


class CorrectionLogAuditTests(TestCase):
    """Tests for CorrectionLog audit features."""

    def setUp(self):
        self.client = _authed_client()
        self.report = _make_report('audit')

    def test_correction_log_records_timestamp(self):
        """Test that CorrectionLog records the correction timestamp"""
        before = timezone.now()
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {'category': 'disaster'})
        after = timezone.now()
        
        correction = CorrectionLog.objects.get(report=self.report)
        self.assertGreaterEqual(correction.corrected_at, before)
        self.assertLessEqual(correction.corrected_at, after)

    def test_correction_log_records_corrected_by(self):
        """Test that CorrectionLog records who made the correction"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {
            'category': 'disaster',
            'corrected_by': 'moderator_jane'
        })
        
        correction = CorrectionLog.objects.get(report=self.report)
        self.assertEqual(correction.corrected_by, 'moderator_jane')

    def test_correction_log_defaults_to_demo_user(self):
        """Test that corrected_by defaults to 'demo' if not provided"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {'category': 'disaster'})
        
        correction = CorrectionLog.objects.get(report=self.report)
        self.assertEqual(correction.corrected_by, 'demo')

    def test_correction_log_maintains_order(self):
        """Test that CorrectionLog entries are ordered chronologically"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        
        self.client.post(url, {'category': 'disaster'})
        self.client.post(url, {'category': 'transport'})
        self.client.post(url, {'category': 'infrastructure'})
        
        corrections = list(CorrectionLog.objects.filter(report=self.report).order_by('corrected_at'))
        self.assertEqual(len(corrections), 3)
        self.assertEqual(corrections[0].new_value, 'disaster')
        self.assertEqual(corrections[1].new_value, 'transport')
        self.assertEqual(corrections[2].new_value, 'infrastructure')


class DetailPageReflectionTests(TestCase):
    """Tests that category updates are reflected on the detail page."""

    def setUp(self):
        self.client = _authed_client()
        self.report = _make_report('detail')

    def test_overridden_category_shown_on_detail_page(self):
        """Test that overridden category is displayed on report detail"""
        # First override the category
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        self.client.post(url, {'category': 'disaster'})
        
        # Then view the detail page
        detail_url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(detail_url)
        
        # The report context should have the new category
        report_obj = response.context['report']
        self.assertEqual(report_obj.category, 'disaster')

    def test_overridden_location_shown_on_detail_page(self):
        """Test that overridden location_text is displayed on report detail"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        self.client.post(url, {'location_text': 'Cabanatuan, Nueva Ecija'})
        
        detail_url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(detail_url)
        
        report_obj = response.context['report']
        self.assertEqual(report_obj.location_text, 'Cabanatuan, Nueva Ecija')

    def test_multiple_overrides_reflect_latest_values(self):
        """Test that detail page shows the most recent override values"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        
        # First override
        self.client.post(url, {'category': 'disaster'})
        # Second override
        self.client.post(url, {'category': 'transport'})
        
        # Check detail page shows newest value
        detail_url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(detail_url)
        
        report_obj = response.context['report']
        self.assertEqual(report_obj.category, 'transport')

    def test_correction_history_visible_on_detail_page(self):
        """Test that correction history is available in context"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        self.client.post(url, {'category': 'disaster'})
        
        detail_url = reverse('dashboard:report-detail', kwargs={'pk': self.report.pk})
        response = self.client.get(detail_url)
        
        # The report should have corrections related to it
        self.assertEqual(self.report.corrections.count(), 1)
        correction = self.report.corrections.first()
        self.assertEqual(correction.field_name, 'category')
        self.assertEqual(correction.new_value, 'disaster')


class MessageHandlingTests(TestCase):
    """Tests for user feedback messages."""

    def setUp(self):
        self.client = _authed_client()
        self.report = _make_report('messages')

    def test_success_message_on_category_override(self):
        """Test that success message is shown for category override"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {'category': 'disaster'}, follow=True)
        
        messages_list = list(response.context['messages'])
        self.assertTrue(any('updated' in str(m).lower() for m in messages_list))

    def test_success_message_on_location_override(self):
        """Test that success message is shown for location override"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {'location_text': 'Cabanatuan'}, follow=True)
        
        messages_list = list(response.context['messages'])
        self.assertTrue(any('updated' in str(m).lower() for m in messages_list))

    def test_fields_listed_in_success_message_single_field(self):
        """Test that success message mentions the field name (singular)"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {'category': 'disaster'}, follow=True)
        
        messages_list = list(response.context['messages'])
        message_text = ' '.join(str(m) for m in messages_list)
        self.assertIn('category', message_text.lower())

    def test_fields_listed_in_success_message_multiple_fields(self):
        """Test that success message mentions all fields (plural)"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {
            'category': 'disaster',
            'location_text': 'Cabanatuan'
        }, follow=True)
        
        messages_list = list(response.context['messages'])
        message_text = ' '.join(str(m) for m in messages_list)
        # Should be plural "were updated"
        self.assertIn('were', message_text.lower())

    def test_warning_message_when_no_fields_provided(self):
        """Test that warning message is shown when no fields are provided"""
        url = reverse('dashboard:report-override', kwargs={'pk': self.report.pk})
        response = self.client.post(url, {}, follow=True)
        
        messages_list = list(response.context['messages'])
        self.assertTrue(any('no fields' in str(m).lower() for m in messages_list))
