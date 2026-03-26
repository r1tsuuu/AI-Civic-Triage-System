from django.urls import path
from .views import MockFBFeedView

app_name = "mock_fb"

urlpatterns = [
    path("", MockFBFeedView.as_view(), name="feed"),
]
