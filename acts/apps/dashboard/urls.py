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

    # TASK-041: API endpoints for map data
    path("api/reports/geojson/", views.ReportsGeoJSONView.as_view(), name="reports-geojson"),
]