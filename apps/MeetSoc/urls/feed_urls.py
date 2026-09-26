from django.urls import path

from apps.MeetSoc import views as v

urlpatterns = [
    path("feed/", v.FeedView.as_view(), name="feed"),
    path("feed/stories/", v.FeedStoriesView.as_view(), name="feed-stories"),
    path("feed/hide/<uuid:post_id>/", v.FeedHideView.as_view(), name="feed-hide"),
    path("feed/snooze/<uuid:user_id>/", v.FeedSnoozeView.as_view(), name="feed-snooze"),
    path("feed/saved/", v.SavedPostsView.as_view(), name="feed-saved"),
]
