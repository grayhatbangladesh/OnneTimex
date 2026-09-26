from django.urls import path

from apps.MeetSoc import views as v

urlpatterns = [
    path("posts/<uuid:post_id>/comments/", v.CommentListCreateView.as_view(), name="post-comments"),
    path("comments/<uuid:comment_id>/", v.CommentDetailView.as_view(), name="comments-detail"),
    path("comments/<uuid:comment_id>/replies/", v.CommentReplyListCreateView.as_view(), name="comments-replies"),
    path("comments/<uuid:comment_id>/react/", v.CommentReactView.as_view(), name="comments-react"),
]
