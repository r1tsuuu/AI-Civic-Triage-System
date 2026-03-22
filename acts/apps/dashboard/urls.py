from django.urls import path

app_name = "dashboard"

urlpatterns = [
    # TASK-031: GET  /dashboard/           (stats overview)
    # TASK-032: GET  /dashboard/reports/   (list view)
    # TASK-033: GET  /dashboard/reports/<id>/  (detail view)
    # TASK-034: GET  /dashboard/history/   (audit log)
    # TASK-040: POST /dashboard/reports/<id>/acknowledge|in-progress|resolve|dismiss/
    # TASK-041: POST /dashboard/reports/<id>/override/
    # TASK-070: GET  /dashboard/reports/map/
    # Views will be wired here in Phase 3+
]
