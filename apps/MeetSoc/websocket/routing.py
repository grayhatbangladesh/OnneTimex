from django.urls import path

from apps.MeetSoc.websocket.consumers.call_consumer import CallConsumer
from apps.MeetSoc.websocket.consumers.chat_consumer import ChatConsumer
from apps.MeetSoc.websocket.consumers.notification_consumer import NotificationConsumer

websocket_urlpatterns = [
    path("ws/chat/<uuid:conversation_id>/", ChatConsumer.as_asgi()),
    path("ws/notifications/", NotificationConsumer.as_asgi()),
    path("ws/calls/<uuid:call_id>/", CallConsumer.as_asgi()),
]
