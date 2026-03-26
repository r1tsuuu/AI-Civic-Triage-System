from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from apps.dashboard.gate_views import gate_view


def health(request):
    return HttpResponse("ok")


urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("gate/", gate_view, name="gate"),
    path("webhook/", include("apps.webhook.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("fb/", include("apps.mock_fb.urls")),
]