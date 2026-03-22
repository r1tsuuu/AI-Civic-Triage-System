from django.contrib import admin
from django.urls import path, include
from apps.dashboard.gate_views import gate_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("gate/", gate_view, name="gate"),
    path("webhook/", include("apps.webhook.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
]