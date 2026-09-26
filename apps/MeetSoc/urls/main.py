"""MeetSoc — root HTTP URL aggregator (mounted at /api/)."""
from django.urls import include, path

urlpatterns = [
    path("", include("apps.MeetSoc.urls.posts_urls")),
    path("", include("apps.MeetSoc.urls.comments_urls")),
    path("", include("apps.MeetSoc.urls.feed_urls")),
    path("", include("apps.MeetSoc.urls.friend_urls")),
    path("", include("apps.MeetSoc.urls.groups_urls")),
    path("", include("apps.MeetSoc.urls.pages_urls")),
    path("", include("apps.MeetSoc.urls.marketplace_urls")),
    path("", include("apps.MeetSoc.urls.memories_urls")),
    path("", include("apps.MeetSoc.urls.watch_urls")),
    path("", include("apps.MeetSoc.urls.reactions_urls")),
    path("", include("apps.MeetSoc.urls.notifications_urls")),
    path("", include("apps.MeetSoc.urls.search_urls")),
    path("", include("apps.MeetSoc.urls.reports_urls")),
    path("", include("apps.MeetSoc.urls.payments_urls")),
    path("", include("apps.MeetSoc.urls.verification_urls")),
    path("", include("apps.MeetSoc.urls.conversations_urls")),
    path("", include("apps.MeetSoc.urls.messages_urls")),
    path("", include("apps.MeetSoc.urls.categories_urls")),
    path("", include("apps.MeetSoc.urls.ads_urls")),
    path("", include("apps.MeetSoc.urls.events_urls")),
    path("", include("apps.MeetSoc.urls.calls_urls")),
    path("", include("apps.MeetSoc.urls.sidebar_urls")),
    path("", include("apps.MeetSoc.urls.gaming_urls")),
]