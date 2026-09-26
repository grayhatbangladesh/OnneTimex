from django.urls import path

from apps.MeetSoc.views.feed_views import SavePostView
from apps.MeetSoc import views as v
from apps.MeetSoc.views.posts_views_category import CategoryListView, TagListView

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("tags/", TagListView.as_view(), name="tag-list"),
    path("posts/", v.PostListCreateView.as_view(), name="posts-list-create"),
    path("posts/<uuid:post_id>/", v.PostDetailView.as_view(), name="posts-detail"),
    path("posts/<uuid:post_id>/share/", v.PostShareView.as_view(), name="posts-share"),
    path("posts/<uuid:post_id>/shares/", v.PostSharesListView.as_view(), name="posts-shares"),
    path("posts/<uuid:post_id>/view/", v.PostViewRegisterView.as_view(), name="posts-view"),
    path("stories/", v.StoriesFeedView.as_view(), name="stories-feed"),
    path("stories/<uuid:story_id>/", v.StoryDetailView.as_view(), name="stories-detail"),
    path("stories/<uuid:story_id>/view/", v.StoryViewView.as_view(), name="stories-view"),
    path("stories/<uuid:story_id>/viewers/", v.StoryViewersView.as_view(), name="stories-viewers"),
    path("stories/<uuid:story_id>/comments/", v.StoryCommentListCreateView.as_view(), name="stories-comments"),
    path("stories/<uuid:story_id>/react/", v.StoryReactView.as_view(), name="stories-react"),
    path("stories/archive/", v.StoryArchiveView.as_view(), name="stories-archive"),
    path("posts/<uuid:post_id>/save/", SavePostView.as_view(), name="post-save"),
    path("posts/<uuid:post_id>/react/", v.PostReactView.as_view(), name="post-react"),
    path("posts/<uuid:post_id>/reactions/", v.PostReactionsListView.as_view(), name="post-reactions"),
]
