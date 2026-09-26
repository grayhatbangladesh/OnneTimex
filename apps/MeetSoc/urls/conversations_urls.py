from django.urls import path
from apps.MeetSoc import views as v

urlpatterns = [
    path("conversations/", v.ConversationListView.as_view(), name="conversations-list"),
    path("conversations/<str:conversation_id>/", v.ConversationDetailView.as_view(), name="conversations-detail"),
    path("conversations/<str:conversation_id>/messages/", v.ConversationMessagesView.as_view(), name="conversations-messages"),
    path("conversations/direct/", v.ConversationDirectView.as_view(), name="conversations-direct"),
]
