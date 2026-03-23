"""
Dashboard Views - Core moderator interface
========================================

This module contains all dashboard views for the ACTS demo interface.
Assigned to SWE-2 for implementation in TASK-031 through TASK-041.
"""

from django.views.generic import TemplateView, ListView, DetailView, View
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from triage.models import RawPost
from django.db.models import Count, Q
from datetime import timedelta


class StatsView(TemplateView):
    """
    TASK-031: Dashboard statistics view
    
    Displays:
    - Reports received in last 24 hours
    - Resolution rate as percentage
    - Most affected barangay
    - Most reported category
    """
    template_name = 'dashboard/stats.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Placeholder: SWE-2 will implement with real queries
        context['stats'] = {
            'reports_24h': 0,
            'resolution_rate': 0,
            'most_affected_barangay': 'Loading...',
            'most_reported_category': 'Loading...',
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
