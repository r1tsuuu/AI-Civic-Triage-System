"""
Dashboard Views - Core moderator interface
========================================

This module contains all dashboard views for the ACTS demo interface.
Assigned to SWE-2 for implementation in TASK-031 through TASK-041.
"""

from __future__ import annotations
from typing import ClassVar, TypedDict

from django.views.generic import TemplateView, ListView, DetailView, View
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from apps.webhook.models import RawPost, CorrectionLog
from apps.triage.exceptions import InvalidTransitionError
from django.db.models import Count, Q
from datetime import timedelta, datetime
from django.core.paginator import Paginator


class StatusChangeDict(TypedDict):
    """Shape of each mock status-change entry in HistoryView / HistoryExportView."""
    id: str
    report_id: object          
    timestamp: datetime
    from_status: str
    to_status: str
    notes: str
    changed_by: str


class StatsView(TemplateView):
    """
    TASK-031: Dashboard statistics view
    
    Displays:
    - Reports received in last 24 hours (real query from RawPost)
    - Resolution rate as percentage (fixture data - pending StatusChange model)
    - Most affected barangay (fixture data - pending location field in RawPost)
    - Most reported category (fixture data - pending classification in triage app)
    
    Note: Using fixture data for stats pending completion of triage pipeline models.
    24-hour count is real-time from RawPost.received_at.
    """
    template_name = 'dashboard/stats.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Real query: Reports received in last 24 hours
        now = timezone.now()
        twenty_four_hours_ago = now - timedelta(hours=24)
        reports_24h = RawPost.objects.filter(
            received_at__gte=twenty_four_hours_ago
        ).count()
        
        # Fixture data (pending triage pipeline implementation)
        # In production, these will be calculated from:
        # - StatusChange model for resolution_rate
        # - Classification model for most_reported_category
        # - Location field in RawPost/Classification for most_affected_barangay
        
        context['stats'] = {
            'reports_24h': reports_24h,
            'reports_24h_change': 12,  # fixture: trend indicator
            'resolution_rate': 78,  # fixture: calculated from StatusChange.resolved / total
            'resolution_rate_change': 5,  # fixture: trend indicator
            'most_affected_barangay': 'Cabanatuan',  # fixture: pending location data
            'most_affected_count': 24,  # fixture: count in that barangay
            'most_reported_category': 'Disaster',  # fixture: pending classification data
            'most_reported_count': 18,  # fixture: count in that category
        }
        
        return context


class ReportListView(ListView):
    """
    TASK-032: Paginated report list with filtering and sorting
    
    Features:
    - Default sort by urgency score (descending) - mock data until triage pipeline complete
    - Filters: category, status, barangay (via GET params)
    - Date range filtering
    - Pagination: 20 per page
    - Displays low confidence warnings (mock threshold: 0.75)
    
    Mock data notes:
    - urgency_score: random 1-100 (pending NER pipeline)
    - confidence: random 0.5-1.0 (pending classifier)
    - category: random from disaster|transport|infrastructure|safety|other (pending classifier)
    - status: random from reported|acknowledged|in_progress|resolved (pending StatusChange model)
    - barangay: random from sample list (pending NER location extraction)
    """
    model = RawPost
    template_name = 'dashboard/list_view.html'
    context_object_name = 'reports'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = RawPost.objects.all()
        
        # Get filter parameters
        category_filter = self.request.GET.get('category')
        status_filter = self.request.GET.get('status')
        barangay_filter = self.request.GET.get('barangay')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        # Filter by date range
        if date_from:
            try:
                from_date = timezone.datetime.fromisoformat(date_from)
                queryset = queryset.filter(received_at__gte=from_date)
            except (ValueError, AttributeError):
                pass
        
        if date_to:
            try:
                to_date = timezone.datetime.fromisoformat(date_to)
                # Add one day to include the whole day
                to_date = to_date + timedelta(days=1)
                queryset = queryset.filter(received_at__lt=to_date)
            except (ValueError, AttributeError):
                pass
        
        # Apply sorting - default we'll use received_at descending, but we'll add urgency in post-processing
        queryset = queryset.order_by('-received_at')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current filter parameters
        context['category_filter'] = self.request.GET.get('category', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['barangay_filter'] = self.request.GET.get('barangay', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        
        # Enrich reports with mock classification data
        # This will be replaced with real data when triage pipeline is complete
        import random
        
        categories = ['disaster', 'transport', 'infrastructure', 'safety', 'other']
        statuses = ['reported', 'acknowledged', 'in-progress', 'resolved']
        barangays = ['Cabanatuan', 'San Fernando', 'Talugtug', 'General Nakar', 'Amadeo', 
                     'Imus', 'Tagaytay', 'Cavite City', 'Noveleta', 'Bacoor']
        
        for report in context['reports']:
            # Add mock classification data
            report.urgency_score = random.randint(1, 100)
            report.confidence = float(round(random.uniform(0.5, 1.0), 2))
            report.category = random.choice(categories)
            report.status = random.choice(statuses)
            report.barangay = random.choice(barangays)
            report.confidence_threshold = 0.75
            report.has_low_confidence = report.confidence < report.confidence_threshold
        
        # Apply client-side filtering on mock data
        category_filter = self.request.GET.get('category')
        status_filter = self.request.GET.get('status')
        barangay_filter = self.request.GET.get('barangay')
        
        filtered_reports = []
        for report in context['reports']:
            if category_filter and report.category != category_filter:
                continue
            if status_filter and report.status != status_filter:
                continue
            if barangay_filter and report.barangay != barangay_filter:
                continue
            filtered_reports.append(report)
        
        # Sort by urgency descending (default)
        sort_by = self.request.GET.get('sort', 'urgency_desc')
        if sort_by == 'urgency_desc':
            filtered_reports.sort(key=lambda x: x.urgency_score, reverse=True)
        elif sort_by == 'urgency_asc':
            filtered_reports.sort(key=lambda x: x.urgency_score)
        elif sort_by == 'date_desc':
            filtered_reports.sort(key=lambda x: x.received_at, reverse=True)
        elif sort_by == 'date_asc':
            filtered_reports.sort(key=lambda x: x.received_at)
        
        context['reports'] = filtered_reports
        
        # Available filter options
        context['category_options'] = categories
        context['status_options'] = statuses
        context['barangay_options'] = barangays
        context['sort_options'] = [
            ('urgency_desc', 'Urgency (High to Low)'),
            ('urgency_asc', 'Urgency (Low to High)'),
            ('date_desc', 'Newest First'),
            ('date_asc', 'Oldest First'),
        ]
        
        return context


class ReportDetailView(DetailView):
    """
    TASK-033: Detailed report view with moderation tools
    
    Displays:
    - Original post text
    - Classification (category, confidence, urgency)
    - Location (map pin or unresolved)
    - Status stepper and history
    - Action buttons (valid next steps only)
    - Override forms (category, location, routing notes)
    
    Mock data notes (pending triage pipeline):
    - Classification fields: urgency_score, confidence, category
    - StatusChange history: mock transitions with timestamps
    - AutoReply: sample AI response
    - Routing notes: sample internal notes
    """
    model = RawPost
    template_name = 'dashboard/report_detail.html'
    context_object_name = 'report'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = context['report']
        
        # Add mock classification data
        import random
        report.urgency_score = random.randint(1, 100)
        report.confidence = float(round(random.uniform(0.5, 1.0), 2))
        
        # Check for category override in CorrectionLog
        category_overrides = CorrectionLog.objects.filter(
            report=report,
            field_name='category'
        ).order_by('-corrected_at')
        
        if category_overrides.exists():
            report.category = category_overrides.first().new_value
        else:
            report.category = random.choice(['disaster', 'transport', 'infrastructure', 'safety', 'other'])
        
        # Check for location_text override in CorrectionLog
        location_overrides = CorrectionLog.objects.filter(
            report=report,
            field_name='location_text'
        ).order_by('-corrected_at')
        
        if location_overrides.exists():
            report.location_text = location_overrides.first().new_value
        else:
            report.location_text = None
        
        report.barangay = random.choice(['Cabanatuan', 'San Fernando', 'Talugtug', 'General Nakar', 
                                        'Amadeo', 'Imus', 'Tagaytay', 'Cavite City', 'Noveleta', 'Bacoor'])
        report.confidence_threshold = 0.75
        report.has_low_confidence = report.confidence < report.confidence_threshold
        
        # Mock routing notes
        report.routing_notes = 'Priority: Medium. Route to Cabanatuan Municipal Health Office for verification.'
        
        # Mock location coordinates (some reports have them, some don't)
        if random.random() > 0.3:  # 70% have coordinates
            report.latitude = float(round(random.uniform(14.5, 15.5), 4))
            report.longitude = float(round(random.uniform(120.5, 121.5), 4))
        else:
            report.latitude = None
            report.longitude = None
        
        # Real status from DB field
        report.current_status = report.status

        # Status history: empty list for now (StatusChange model pending)
        context['status_changes'] = []
        
        # Add correction history to context
        context['corrections'] = report.corrections.all().order_by('-corrected_at')

        # Mock auto-reply
        now = timezone.now()
        context['auto_reply'] = {
            'id': 'ar_001',
            'message': 'Thank you for reporting this incident. Our team is investigating and will provide updates soon.',
            'sent_at': now - timedelta(hours=0.5),
            'status': 'sent',
        }

        # Available actions derived from VALID_TRANSITIONS on the real status
        next_statuses = RawPost.VALID_TRANSITIONS.get(report.status, [])
        context['available_next_statuses'] = next_statuses

        # All possible status options for display
        context['all_statuses'] = [
            RawPost.STATUS_REPORTED,
            RawPost.STATUS_ACKNOWLEDGED,
            RawPost.STATUS_IN_PROGRESS,
            RawPost.STATUS_RESOLVED,
        ]

        # Category options
        context['category_options'] = ['disaster', 'transport', 'infrastructure', 'safety', 'other']

        # Signal breakdown for urgency visualization
        context['signal_breakdown'] = {
            'keyword_score': random.randint(10, 100),
            'location_score': random.randint(10, 100),
            'time_score': random.randint(10, 100),
            'consistency_score': random.randint(10, 100),
        }

        return context


class HistoryView(ListView):
    """
    TASK-034: Status change history timeline
    
    Features:
    - Timeline of all status changes
    - Filters: date range, report ID search
    - Export to CSV
    
    Mock data notes (pending StatusChange model):
    - Returns mock status transitions for all reports
    - Filters by date range and report ID search
    - Sorts by timestamp descending (newest first)
    """
    model = RawPost
    template_name = 'dashboard/history.html'
    context_object_name = 'status_changes'
    paginate_by = 50
    
    def get_queryset(self):
        """Generate mock status change history from all reports"""
        import random
        
        # Get all reports
        all_reports = RawPost.objects.all()
        
        # Generate mock status changes for each report
        all_changes: list[StatusChangeDict] = []
        statuses: list[str] = ['reported', 'acknowledged', 'in-progress', 'resolved']
        
        for report in all_reports:
            now = timezone.now()
            num_transitions = random.randint(2, 4)
            
            for i in range(num_transitions):
                all_changes.append(StatusChangeDict(
                    id=f"{report.id}_{i}",
                    report_id=report.id,
                    timestamp=now - timedelta(hours=random.randint(1, 72)),
                    from_status=statuses[i - 1] if i > 0 else 'reported',
                    to_status=statuses[i],
                    notes=f'Status changed to {statuses[i]}',
                    changed_by=random.choice(['System', 'Moderator', 'Auto']),
                ))
        
        # Sort by timestamp descending
        all_changes.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return all_changes
    
    def get_context_data(self, **kwargs):
        """Apply filters and add context"""
        context = super().get_context_data(**kwargs)
        
        # Get filter parameters
        date_from_str = self.request.GET.get('date_from', '')
        date_to_str = self.request.GET.get('date_to', '')
        report_id_search = self.request.GET.get('report_id', '')
        
        # Get base queryset
        status_changes = self.get_queryset()
        
        # Filter by date range
        if date_from_str:
            try:
                date_from = datetime.strptime(date_from_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                status_changes = [c for c in status_changes if c['timestamp'] >= date_from]
            except ValueError:
                pass
        
        if date_to_str:
            try:
                date_to = datetime.strptime(date_to_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
                status_changes = [c for c in status_changes if c['timestamp'] <= date_to]
            except ValueError:
                pass
        
        # Filter by report ID search
        if report_id_search:
            status_changes = [c for c in status_changes if str(report_id_search).lower() in str(c['report_id']).lower()]
        
        # Add filters to context
        context['date_from'] = date_from_str
        context['date_to'] = date_to_str
        context['report_id'] = report_id_search
        context['total_changes'] = len(status_changes)
        
        # Re-paginate filtered results
        paginator = Paginator(status_changes, self.paginate_by)
        page_number = self.request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj
        context['paginator'] = paginator
        context['status_changes'] = page_obj.object_list
        
        return context


class HistoryExportView(View):
    """
    TASK-034: CSV export of status history
    
    Returns properly formatted CSV with:
    - Timestamp, Report ID, Status transition, Notes, Changed By
    Respects filters: date range and report ID search
    """
    def get(self, request):
        import csv
        import random
        from datetime import datetime as dt
        
        # Get filter parameters
        date_from_str = request.GET.get('date_from', '')
        date_to_str = request.GET.get('date_to', '')
        report_id_search = request.GET.get('report_id', '')
        
        # Generate mock data (same as HistoryView)
        all_reports = RawPost.objects.all()
        all_changes = []
        statuses = ['reported', 'acknowledged', 'in-progress', 'resolved']
        
        for report in all_reports:
            now = timezone.now()
            num_transitions = random.randint(2, 4)
            all_changes_export: list[StatusChangeDict] = []

            for i in range(num_transitions):
                all_changes_export.append(StatusChangeDict(
                    id=f"{report.id}_{i}",
                    report_id=report.id,
                    timestamp=now - timedelta(hours=random.randint(1, 72)),
                    from_status=statuses_export[i - 1] if i > 0 else 'reported',
                    to_status=statuses_export[i],
                    notes=f'Status changed to {statuses_export[i]}',
                    changed_by=random.choice(['System', 'Moderator', 'Auto']),
                ))
            all_changes += all_changes_export
        
        # Sort by timestamp descending
        all_changes.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Apply filters
        if date_from_str:
            try:
                date_from = datetime.strptime(date_from_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                all_changes = [c for c in all_changes if c['timestamp'] >= date_from]
            except ValueError:
                pass
        
        if date_to_str:
            try:
                date_to = datetime.strptime(date_to_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
                all_changes = [c for c in all_changes if c['timestamp'] <= date_to]
            except ValueError:
                pass
        
        if report_id_search:
            all_changes = [c for c in all_changes if str(report_id_search).lower() in str(c['report_id']).lower()]
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="acts_history_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'Report ID', 'Status Transition', 'Notes', 'Changed By'])
        
        for change in all_changes:
            transition = f"{change['from_status']} → {change['to_status']}"
            writer.writerow([
                change['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                str(change['report_id']),
                transition,
                change['notes'],
                change['changed_by'],
            ])
        
        return response


class MapView(TemplateView):
    """
    TASK-040: Interactive map view of all reports
    
    Features:
    - Leaflet.js map centered on Central Luzon
    - Color-coded pins by category
    - High-urgency pins pulse animation
    - Click to view report detail
    """
    template_name = 'dashboard/map.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Placeholder: SWE-2 will implement
        context['map_center'] = {'lat': 14.8, 'lng': 121.0}
        context['map_zoom'] = 10
        return context


class ReportsGeoJSONView(View):
    """
    TASK-041: GeoJSON API endpoint for map markers
    
    Returns:
    - All current reports with coordinates
    - Color-coded by category
    - Urgency score and status
    """
    def get(self, request):
        # Placeholder: SWE-2 will implement GeoJSON generation
        geojson = {
            'type': 'FeatureCollection',
            'features': []
        }
        return JsonResponse(geojson)

class _BaseStatusActionView(View):
    """
    Base class for all status-transition POST views.

    Subclasses set:
        target_status  – the RawPost STATUS_* constant to transition to
        url_name       – name for this action (used in 405 error text)
    """
    target_status: ClassVar[str]  # set by each concrete subclass
    http_method_names = ['post']  # GET → 405 automatically

    def post(self, request, pk):
        report = get_object_or_404(RawPost, pk=pk)
        try:
            report.transition_to(self.target_status, moderator_name="demo")
        except InvalidTransitionError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(
                request,
                f"Report marked as {self.target_status.replace('_', ' ')}."
            )
        return redirect('dashboard:report-detail', pk=pk)


class AcknowledgeReportView(_BaseStatusActionView):
    """TASK-040: POST /dashboard/reports/<uuid>/acknowledge/"""
    target_status = RawPost.STATUS_ACKNOWLEDGED


class InProgressReportView(_BaseStatusActionView):
    """TASK-040: POST /dashboard/reports/<uuid>/in-progress/"""
    target_status = RawPost.STATUS_IN_PROGRESS


class ResolveReportView(_BaseStatusActionView):
    """TASK-040: POST /dashboard/reports/<uuid>/resolve/"""
    target_status = RawPost.STATUS_RESOLVED


class DismissReportView(_BaseStatusActionView):
    """TASK-040: POST /dashboard/reports/<uuid>/dismiss/"""
    target_status = RawPost.STATUS_DISMISSED

class OverrideReportView(View):
    """
    TASK-041: Override report fields (category, location_text)
    
    Accepts POST with optional category and/or location_text parameters.
    Updates those fields on the RawPost instance and creates a CorrectionLog
    entry for each field that was changed.
    
    Returns:
    - JSON response with success/error status
    - Redirect to report detail page on success
    """
    http_method_names = ['post']
    
    def post(self, request, pk):
        report = get_object_or_404(RawPost, pk=pk)
        
        try:
            # Get submitted values
            new_category = request.POST.get('category', '').strip()
            new_location_text = request.POST.get('location_text', '').strip()
            
            # Track what was changed
            changes_made = []
            
            # Handle category override
            if new_category:
                # Get the current/old value from most recent correction log or None
                last_category_correction = CorrectionLog.objects.filter(
                    report=report,
                    field_name='category'
                ).order_by('-corrected_at').first()
                
                if last_category_correction:
                    old_category = last_category_correction.new_value
                else:
                    old_category = None
                
                # Only create a log if the value is changing
                if old_category != new_category:
                    CorrectionLog.objects.create(
                        report=report,
                        field_name='category',
                        old_value=old_category,
                        new_value=new_category,
                        corrected_by=request.POST.get('corrected_by', 'demo'),
                    )
                    # Store on the report object for context in detail view
                    report.category = new_category
                    changes_made.append('category')
            
            # Handle location_text override
            if new_location_text:
                # Get the current/old value from most recent correction log or None
                last_location_correction = CorrectionLog.objects.filter(
                    report=report,
                    field_name='location_text'
                ).order_by('-corrected_at').first()
                
                if last_location_correction:
                    old_location_text = last_location_correction.new_value
                else:
                    old_location_text = None
                
                # Only create a log if the value is changing
                if old_location_text != new_location_text:
                    CorrectionLog.objects.create(
                        report=report,
                        field_name='location_text',
                        old_value=old_location_text,
                        new_value=new_location_text,
                        corrected_by=request.POST.get('corrected_by', 'demo'),
                    )
                    # Store on the report object
                    report.location_text = new_location_text
                    changes_made.append('location_text')
            
            # Success message
            if changes_made:
                fields_text = ' and '.join(changes_made)
                messages.success(
                    request,
                    f"Report {fields_text} {'was' if len(changes_made) == 1 else 'were'} updated."
                )
            else:
                messages.warning(request, "No fields were updated.")
            
        except Exception as e:
            messages.error(request, f"Error updating report: {str(e)}")
        
        return redirect('dashboard:report-detail', pk=pk)
