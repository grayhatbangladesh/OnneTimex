from django.urls import path

from apps.MeetSoc import views as v

urlpatterns = [
    path("watch/videos/", v.WatchListCreateView.as_view(), name="watch-videos"),
    path("watch/videos/<uuid:video_id>/", v.WatchDetailView.as_view(), name="watch-video-detail"),
    path("watch/videos/<uuid:video_id>/react/", v.WatchVideoReactView.as_view(), name="watch-video-react"),
    path("watch/videos/<uuid:video_id>/comments/", v.WatchVideoCommentListView.as_view(), name="watch-video-comments"),
    path("watch/videos/<uuid:video_id>/share/", v.WatchVideoShareView.as_view(), name="watch-video-share"),
]
