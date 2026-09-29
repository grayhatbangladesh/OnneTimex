from django.urls import path

from apps.MeetSoc import views as v

urlpatterns = [
    path("groups/", v.GroupListCreateView.as_view(), name="groups-list"),
    path("groups/my/", v.GroupMyView.as_view(), name="groups-my"),
    path("groups/<slug:slug>/", v.GroupDetailView.as_view(), name="groups-detail"),
    path("groups/<slug:slug>/join/", v.GroupJoinView.as_view(), name="groups-join"),
    path("groups/<slug:slug>/leave/", v.GroupLeaveView.as_view(), name="groups-leave"),
    path("groups/<slug:slug>/members/", v.GroupMembersView.as_view(), name="groups-members"),
    path("groups/<slug:slug>/invite/", v.GroupInviteView.as_view(), name="groups-invite"),
    path("groups/<slug:slug>/members/<uuid:uid>/", v.GroupMemberRoleView.as_view(), name="groups-member"),
    path("groups/<slug:slug>/posts/", v.GroupPostsView.as_view(), name="groups-posts"),
    path("groups/<slug:slug>/media/", v.GroupMediaView.as_view(), name="groups-media"),
    path("groups/<slug:slug>/events/", v.GroupEventsView.as_view(), name="groups-events"),
    path("groups/<slug:slug>/pending/", v.GroupPendingView.as_view(), name="groups-pending"),
    path("groups/<slug:slug>/approve/<uuid:uid>/", v.GroupApproveView.as_view(), name="groups-approve"),
    path("groups/<slug:slug>/ban/<uuid:uid>/", v.GroupBanView.as_view(), name="groups-ban"),
]
