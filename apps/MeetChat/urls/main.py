"""MeetChat — root HTTP URL aggregator (mounted at /api/chat/)."""
from django.urls import include, path

urlpatterns = [
    path("", include("apps.MeetChat.urls.messages_urls")),
    path("", include("apps.MeetChat.urls.calls_urls")),
]