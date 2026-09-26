from django.urls import path

from apps.MeetSoc import views as v

urlpatterns = [
    path("posts/<uuid:post_id>/react/", v.PostReactView.as_view(), name="post-react"),
    path("posts/<uuid:post_id>/reactions/", v.PostReactionsListView.as_view(), name="post-reactions"),
    path("comments/<uuid:comment_id>/react/", v.CommentReactView.as_view(), name="comment-react"),
]
