import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close(code=4401)
            return
        self.group_name = f"notification_user_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        count = await self._unread_count()
        await self.send(
            text_data=json.dumps({"type": "unread_count", "count": count}),
        )

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    @database_sync_to_async
    def _unread_count(self):
        from apps.MeetSoc.models import Notification

        c = cache.get(f"unread_notif:{self.user.id}")
        if c is not None:
            return int(c)
        count = Notification.objects.filter(recipient=self.user, is_read=False).count()
        cache.set(f"unread_notif:{self.user.id}", count, timeout=None)
        return count

    async def notify(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification",
                    "data": event.get("notification", {}),
                }
            )
        )

    async def unread_count(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "unread_count",
                    "count": event.get("count", 0),
                }
            )
        )

    async def call_incoming(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "call_incoming",
                    "call_id": event.get("call_id", ""),
                    "call_type": event.get("call_type", "video"),
                    "caller_id": event.get("caller_id", ""),
                    "caller_name": event.get("caller_name", ""),
                    "caller_avatar": event.get("caller_avatar", ""),
                }
            )
        )

    async def call_accepted(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "call_accepted",
                    "call_id": event.get("call_id", ""),
                    "call_type": event.get("call_type", ""),
                    "caller_id": event.get("caller_id", ""),
                    "caller_name": event.get("caller_name", ""),
                    "caller_avatar": event.get("caller_avatar", ""),
                }
            )
        )

    async def call_declined(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "call_declined",
                    "call_id": event.get("call_id", ""),
                    "call_type": event.get("call_type", ""),
                    "caller_id": event.get("caller_id", ""),
                    "caller_name": event.get("caller_name", ""),
                    "caller_avatar": event.get("caller_avatar", ""),
                }
            )
        )

    async def call_ended(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "call_ended",
                    "call_id": event.get("call_id", ""),
                    "call_type": event.get("call_type", ""),
                    "caller_id": event.get("caller_id", ""),
                    "caller_name": event.get("caller_name", ""),
                    "caller_avatar": event.get("caller_avatar", ""),
                }
            )
        )
