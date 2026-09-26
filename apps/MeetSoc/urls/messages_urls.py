from django.urls import path
from apps.MeetSoc import views as v

urlpatterns = [
    path("messages/", v.ConversationMessagesView.as_view(), name="messages-list"),
    path("messages/<str:message_id>/", v.ConversationMessagesView.as_view(), name="messages-detail"),
    path("messages/<str:message_id>/react/", v.ConversationMessagesView.as_view(), name="messages-react"),
]
