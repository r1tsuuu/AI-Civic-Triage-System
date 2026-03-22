from django.urls import path
from . import views

app_name = "webhook"

urlpatterns = [
    path("facebook/", views.webhook_verify, name="facebook"),
]