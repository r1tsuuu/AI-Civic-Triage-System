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
    TASK-032: Paginated report list with filtering
    
    Features:
    - Default sort by urgency score (descending)
    - Filters: category, status, barangay, date range
    - Pagination: 20 per page
    - Displays low confidence warnings
    """
    model = RawPost
    template_name = 'dashboard/list_view.html'
    context_object_name = 'reports'
    paginate_by = 20
    
    def get_queryset(self):
        # Placeholder: SWE-2 will implement filtering logic
        return RawPost.objects.all()


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
