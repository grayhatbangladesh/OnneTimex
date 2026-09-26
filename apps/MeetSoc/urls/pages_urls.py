from django.urls import path

from apps.MeetSoc import views as v

urlpatterns = [
    path("pages/my/", v.PageMyView.as_view(), name="pages-my"),
    path("pages/followed/", v.PageFollowedView.as_view(), name="pages-followed"),
    path("pages/switch/", v.PageAccountSwitchView.as_view(), name="pages-switch"),
    path("pages/", v.PageListCreateView.as_view(), name="pages-list"),
    path("pages/<slug:slug>/", v.PageDetailView.as_view(), name="pages-detail"),
    path("pages/<slug:slug>/like/", v.PageLikeView.as_view(), name="pages-like"),
    path("pages/<slug:slug>/follow/", v.PageFollowView.as_view(), name="pages-follow"),
    path("pages/<slug:slug>/unfollow/", v.PageUnfollowView.as_view(), name="pages-unfollow"),
    path("pages/<slug:slug>/posts/", v.PagePostsView.as_view(), name="pages-posts"),
    path("pages/<slug:slug>/followers/", v.PageFollowersView.as_view(), name="pages-followers"),
    path("pages/<slug:slug>/admins/", v.PageAdminsView.as_view(), name="pages-admins"),
    path("pages/<slug:slug>/insights/", v.PageInsightsView.as_view(), name="pages-insights"),
]
