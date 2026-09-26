from django.urls import path

from apps.MeetChat import views as v

urlpatterns = [
    path("conversations/", v.ConversationListCreateView.as_view(), name="conversations"),
    path("conversations/direct/", v.DirectConversationView.as_view(), name="conversations-direct"),
    path("conversations/<uuid:conversation_id>/", v.ConversationDetailView.as_view(), name="conversations-detail"),
    path(
        "conversations/<uuid:conversation_id>/messages/",
        v.MessageListCreateView.as_view(),
        name="conversations-messages",
    ),
    path("conversations/<uuid:conversation_id>/members/", v.ConversationMemberView.as_view(), name="conversations-members"),
    path(
        "conversations/<uuid:conversation_id>/members/<uuid:user_id>/",
        v.ConversationMemberView.as_view(),
        name="conversations-members-remove",
    ),
    path("conversations/<uuid:conversation_id>/read/", v.MarkReadView.as_view(), name="conversations-read"),
    path("messages/<uuid:message_id>/", v.MessageDetailView.as_view(), name="messages-detail"),
    path("messages/<uuid:message_id>/react/", v.MessageReactView.as_view(), name="messages-react"),
    path("users/online-status/", v.OnlineStatusView.as_view(), name="online-status"),
]
