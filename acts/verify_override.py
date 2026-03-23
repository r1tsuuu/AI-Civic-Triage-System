#!/usr/bin/env python
"""
Simple verification script for TASK-041: Override endpoint
Tests the core functionality without running the full test suite.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.test import Client, override_settings
from django.urls import reverse
from apps.webhook.models import RawPost, CorrectionLog
from django.utils import timezone
import uuid

@override_settings(ALLOWED_HOSTS=['*'])
def test_override_functionality():
    """Test the override endpoint functionality"""
    print("=" * 60)
    print("TASK-041: Override Endpoint Functionality Tests")
    print("=" * 60)
    
    # Clean up previous test data
    tests_run = 0
    tests_passed = 0
    
    # Create auth client once
    def _create_authed_client():
        client = Client()
        session = client.session
        session['demo_authed'] = True
        session.save()
        return client
    
    # TEST 1: Category override creates correction log
    print("\nTEST 1: Category override creates correction log")
    tests_run += 1
    try:
        report = RawPost.objects.create(
            facebook_post_id=f'test_cat_{uuid.uuid4().hex[:8]}',
            post_text='Test incident report',
            received_at=timezone.now(),
            processed=False,
            status=RawPost.STATUS_REPORTED,
        )
        
        client = _create_authed_client()
        url = reverse('dashboard:report-override', kwargs={'pk': report.pk})
        response = client.post(url, {'category': 'disaster'}, SERVER_NAME='localhost')
        
        print(f"  Response status: {response.status_code}")
        if response.status_code in (301, 302):
            print(f"  Redirect to: {response.get('Location', 'N/A')}")
        
        corrections = CorrectionLog.objects.filter(report=report, field_name='category')
        print(f"  Corrections in DB: {corrections.count()}")
        assert corrections.count() == 1, f"Expected 1 correction, got {corrections.count()}"
        
        correction = corrections.first()
        assert correction.new_value == 'disaster', f"Expected 'disaster', got {correction.new_value}"
        
        print("  PASSED: Category override creates CorrectionLog")
        tests_passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
    
    # TEST 2: Location text override creates correction log
    print("\nTEST 2: Location text override creates correction log")
    tests_run += 1
    try:
        report = RawPost.objects.create(
            facebook_post_id=f'test_loc_{uuid.uuid4().hex[:8]}',
            post_text='Test incident report',
            received_at=timezone.now(),
            processed=False,
            status=RawPost.STATUS_REPORTED,
        )
        
        client = _create_authed_client()
        url = reverse('dashboard:report-override', kwargs={'pk': report.pk})
        response = client.post(url, {'location_text': 'Cabanatuan'}, SERVER_NAME='localhost')
        
        corrections = CorrectionLog.objects.filter(report=report, field_name='location_text')
        assert corrections.count() == 1, f"Expected 1 correction, got {corrections.count()}"
        
        correction = corrections.first()
        assert correction.new_value == 'Cabanatuan', f"Expected 'Cabanatuan', got {correction.new_value}"
        
        print("  PASSED: Location text override creates CorrectionLog")
        tests_passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
    
    # TEST 3: Both fields can be overridden in one request
    print("\nTEST 3: Both fields can be overridden in one request")
    tests_run += 1
    try:
        report = RawPost.objects.create(
            facebook_post_id=f'test_both_{uuid.uuid4().hex[:8]}',
            post_text='Test incident report',
            received_at=timezone.now(),
            processed=False,
            status=RawPost.STATUS_REPORTED,
        )
        
        client = _create_authed_client()
        url = reverse('dashboard:report-override', kwargs={'pk': report.pk})
        response = client.post(url, {
            'category': 'transport',
            'location_text': 'Imus'
        }, SERVER_NAME='localhost')
        
        category_corrections = CorrectionLog.objects.filter(report=report, field_name='category')
        location_corrections = CorrectionLog.objects.filter(report=report, field_name='location_text')
        
        assert category_corrections.count() == 1, f"Expected 1 category correction, got {category_corrections.count()}"
        assert location_corrections.count() == 1, f"Expected 1 location correction, got {location_corrections.count()}"
        
        print("  PASSED: Both fields overridden in single request")
        tests_passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
    
    # TEST 4: Multiple overrides create multiple logs
    print("\nTEST 4: Multiple overrides create multiple logs")
    tests_run += 1
    try:
        report = RawPost.objects.create(
            facebook_post_id=f'test_multi_{uuid.uuid4().hex[:8]}',
            post_text='Test incident report',
            received_at=timezone.now(),
            processed=False,
            status=RawPost.STATUS_REPORTED,
        )
        
        client = _create_authed_client()
        url = reverse('dashboard:report-override', kwargs={'pk': report.pk})
        
        # First override
        response1 = client.post(url, {'category': 'disaster'}, SERVER_NAME='localhost')
        # Second override
        response2 = client.post(url, {'category': 'transport'}, SERVER_NAME='localhost')
        
        corrections = CorrectionLog.objects.filter(report=report, field_name='category')
        assert corrections.count() == 2, f"Expected 2 corrections, got {corrections.count()}"
        
        # Verify sequence
        corrections_list = list(corrections.order_by('corrected_at'))
        assert corrections_list[0].new_value == 'disaster'
        assert corrections_list[1].old_value == 'disaster'
        assert corrections_list[1].new_value == 'transport'
        
        print("  PASSED: Multiple overrides create multiple logs")
        tests_passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
    
    # TEST 5: CorrectionLog records are retrieved on detail page
    print("\nTEST 5: CorrectionLog entries are created with all required fields")
    tests_run += 1
    try:
        report = RawPost.objects.create(
            facebook_post_id=f'test_fields_{uuid.uuid4().hex[:8]}',
            post_text='Test incident report',
            received_at=timezone.now(),
            processed=False,
            status=RawPost.STATUS_REPORTED,
        )
        
        client = _create_authed_client()
        url = reverse('dashboard:report-override', kwargs={'pk': report.pk})
        response = client.post(url, {
            'category': 'disaster',
            'corrected_by': 'moderator_jane'
        }, SERVER_NAME='localhost')
        
        correction = CorrectionLog.objects.get(report=report, field_name='category')
        assert correction.corrected_by == 'moderator_jane', f"Expected 'moderator_jane', got {correction.corrected_by}"
        assert correction.corrected_at is not None
        assert correction.report_id == report.id
        
        print("  PASSED: CorrectionLog has all required fields")
        tests_passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"SUMMARY: {tests_passed}/{tests_run} tests passed")
    print("=" * 60)
    
    return tests_passed == tests_run


if __name__ == '__main__':
    success = test_override_functionality()
    sys.exit(0 if success else 1)
