"""
Root URL configuration for ACTS.
Each app owns its own urls.py; this file only includes them.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Django admin — useful for demo inspection of raw data
    path("admin/", admin.site.urls),

    # Webhook intake (public — verified by Meta)
    path("webhook/", include("apps.webhook.urls")),

    # LGU moderator dashboard (protected by DashboardPasswordGate middleware)
    path("dashboard/", include("apps.dashboard.urls")),

    # Automated response app has no user-facing URLs — omitted from routing
    # (sender is called programmatically from views)
]
