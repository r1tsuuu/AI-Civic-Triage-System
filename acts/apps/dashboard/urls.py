from django.urls import path
from . import gate_views
from . import views

app_name = "dashboard"

urlpatterns = [
    # Logout
    path("logout/", gate_views.gate_logout, name="logout"),

    # Stats view — dashboard homepage
    path("", views.StatsView.as_view(), name="stats"),

    # Stats data API
    path("stats/data/", views.StatsDataView.as_view(), name="stats_data"),

    # Report list
    path("reports/", views.ReportListView.as_view(), name="report_list"),

    # Map view — must come before reports/<uuid:pk>/ to avoid UUID matching "map"
    path("reports/map/", views.MapView.as_view(), name="map_view"),
    path("reports/map/data/", views.ReportsGeoJSONView.as_view(), name="map_data"),

    # Report detail
    path("reports/<uuid:pk>/", views.ReportDetailView.as_view(), name="report_detail"),

    # Status action endpoints
    path("reports/<uuid:pk>/acknowledge/", views.AcknowledgeReportView.as_view(), name="acknowledge"),
    path("reports/<uuid:pk>/in-progress/", views.InProgressReportView.as_view(), name="in_progress"),
    path("reports/<uuid:pk>/resolve/", views.ResolveReportView.as_view(), name="resolve"),
    path("reports/<uuid:pk>/dismiss/", views.DismissReportView.as_view(), name="dismiss"),
    path("reports/<uuid:pk>/override/", views.OverrideReportView.as_view(), name="override"),
    path("reports/<uuid:pk>/notes/", views.SaveRoutingNotesView.as_view(), name="save_notes"),
    path("reports/<uuid:pk>/flag/", views.FlagReportView.as_view(), name="flag_report"),

    # History
    path("history/", views.HistoryView.as_view(), name="history"),
    path("history/export/", views.HistoryExportView.as_view(), name="history_export"),
]
