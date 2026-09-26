from django.urls import path

from apps.MeetChat import views as mv
from apps.MeetSoc import views as v

urlpatterns = [
    path("users/me/", v.MeView.as_view(), name="users-me"),
    path("users/me/avatar/", v.AvatarUpdateView.as_view(), name="users-me-avatar"),
    path("users/me/cover/", v.CoverUpdateView.as_view(), name="users-me-cover"),
    path("users/online-status/", mv.OnlineStatusView.as_view(), name="online-status"),
    path("users/blocked/", v.BlockedListView.as_view(), name="users-blocked"),
    path("users/people-you-may-know/", v.PeopleYouMayKnowView.as_view(), name="users-pymk"),
    path("users/by-username/<str:username>/", v.UsernameProfileView.as_view(), name="users-by-username"),
    path("users/<uuid:user_id>/", v.PublicProfileView.as_view(), name="users-public"),
    path("users/<uuid:user_id>/posts/", v.UserPostsView.as_view(), name="users-posts"),
    path("users/<uuid:user_id>/photos/", v.UserPhotosView.as_view(), name="users-photos"),
    path("users/<uuid:user_id>/videos/", v.UserVideosView.as_view(), name="users-videos"),
    path("users/<uuid:user_id>/friends/", v.UserFriendsView.as_view(), name="users-friends"),
    path("users/<uuid:user_id>/followers/", v.FollowersListView.as_view(), name="users-followers"),
    path("users/<uuid:user_id>/following/", v.FollowingListView.as_view(), name="users-following"),
    path("friends/request/<uuid:user_id>/", v.FriendRequestView.as_view(), name="friends-request"),
    path("friends/accept/<uuid:user_id>/", v.FriendAcceptView.as_view(), name="friends-accept"),
    path("friends/decline/<uuid:user_id>/", v.FriendDeclineView.as_view(), name="friends-decline"),
    path("friends/unfriend/<uuid:user_id>/", v.FriendUnfriendView.as_view(), name="friends-unfriend"),
    path("friends/requests/", v.FriendRequestsListView.as_view(), name="friends-requests"),
    path("friends/requests/outgoing/", v.FriendRequestsOutgoingView.as_view(), name="friends-requests-outgoing"),
    path("friends/myfriends/", v.MyFriendsView.as_view(), name="friends-myfriends"),
    path("friends/suggestions/", v.FriendSuggestionsView.as_view(), name="friends-suggestions"),
    path("friends/follow/<uuid:user_id>/", v.FollowUserView.as_view(), name="friends-follow"),
    path("friends/unfollow/<uuid:user_id>/", v.UnfollowUserView.as_view(), name="friends-unfollow"),
    path("users/block/<uuid:user_id>/", v.BlockUserView.as_view(), name="users-block"),
    path("users/unblock/<uuid:user_id>/", v.UnblockUserView.as_view(), name="users-unblock"),
]
