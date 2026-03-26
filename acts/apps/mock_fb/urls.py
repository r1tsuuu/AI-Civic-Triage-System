from django.urls import path
from .views import MockFBFeedView, LatestCommentView

app_name = "mock_fb"

urlpatterns = [
    path("", MockFBFeedView.as_view(), name="feed"),
    path("api/latest-comment/", LatestCommentView.as_view(), name="latest_comment"),
]
