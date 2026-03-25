from django.urls import path
from . import gate_views
from . import views

app_name = "dashboard"

urlpatterns = [
    # TASK-001: logout clears demo session flag
    path("logout/", gate_views.gate_logout, name="logout"),

    # TASK-031: Stats view - dashboard homepage
    path("", views.StatsView.as_view(), name="stats"),

    # TASK-032: Report list view
    path("reports/", views.ReportListView.as_view(), name="report-list"),

    # TASK-033: Report detail view
    path("reports/<uuid:pk>/", views.ReportDetailView.as_view(), name="report-detail"),

    # TASK-034: History view
    path("history/", views.HistoryView.as_view(), name="history"),
    path("history/export/", views.HistoryExportView.as_view(), name="history-export"),

    # TASK-040: Map view
    path("map/", views.MapView.as_view(), name="map"),

    # TASK-040: Status action endpoints
    path("reports/<uuid:pk>/acknowledge/", views.AcknowledgeReportView.as_view(), name="report-acknowledge"),
    path("reports/<uuid:pk>/in-progress/", views.InProgressReportView.as_view(), name="report-in-progress"),
    path("reports/<uuid:pk>/resolve/", views.ResolveReportView.as_view(), name="report-resolve"),
    path("reports/<uuid:pk>/dismiss/", views.DismissReportView.as_view(), name="report-dismiss"),

    # TASK-041: Override endpoint for moderation and API endpoints for map data
    path("reports/<uuid:pk>/override/", views.OverrideReportView.as_view(), name="report-override"),
    path("api/reports/geojson/", views.ReportsGeoJSONView.as_view(), name="reports-geojson"),
]