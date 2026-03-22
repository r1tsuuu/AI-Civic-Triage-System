from django.urls import path
from . import gate_views

app_name = "dashboard"

urlpatterns = [
    # TASK-001: logout clears demo session flag
    path("logout/", gate_views.gate_logout, name="logout"),

    # TASK-031–034, TASK-040–041, TASK-070: wired in Phase 3+
]