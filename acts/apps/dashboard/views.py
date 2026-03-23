"""
Dashboard Views - Core moderator interface
========================================

This module contains all dashboard views for the ACTS demo interface.
Assigned to SWE-2 for implementation in TASK-031 through TASK-041.
"""

from django.views.generic import TemplateView, ListView, DetailView, View
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from apps.webhook.models import RawPost
from django.db.models import Count, Q
from datetime import timedelta


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
            report.confidence = round(random.uniform(0.5, 1.0), 2)
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
    """
    model = RawPost
    template_name = 'dashboard/report_detail.html'
    context_object_name = 'report'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Placeholder: SWE-2 will implement with real data
        context['status_changes'] = []
        context['auto_reply'] = None
        return context


class HistoryView(ListView):
    """
    TASK-034: Status change history timeline
    
    Features:
    - Timeline of all status changes
    - Filters: date range, report ID search
    - Export to CSV
    """
    template_name = 'dashboard/history.html'
    context_object_name = 'status_changes'
    
    def get_queryset(self):
        # Placeholder: SWE-2 will implement
        return []


class HistoryExportView(View):
    """
    TASK-034: CSV export of status history
    
    Returns properly formatted CSV with:
    - Timestamp, Report ID, Status transition, Notes
    """
    def get(self, request):
        # Placeholder: SWE-2 will implement CSV generation
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="acts_history_export.csv"'
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

