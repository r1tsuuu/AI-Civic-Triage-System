from django.urls import path
from . import views

app_name = "webhook"

urlpatterns = [
    path("facebook/", views.webhook_verify, name="facebook_verify"),
    path("facebook/receive/", views.webhook_receive, name="facebook_receive"),
]