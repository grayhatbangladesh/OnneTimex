import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone


class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close(code=4401)
            return
        self.call_id = str(self.scope["url_route"]["kwargs"]["call_id"])
        if not await self._can_join_call():
            await self.close(code=4403)
            return
        self.room_group_name = f"call_{self.call_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        cache.set(
            f"call_room:{self.call_id}:{self.user.id}",
            {"user": str(self.user.id), "joined_at": timezone.now().isoformat()},
            timeout=3600,
        )
        await self.accept()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "call.joined",
                "user_id": str(self.user.id),
                "from_channel": self.channel_name,
            },
        )

    async def disconnect(self, code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
        event_type = data.get("type")
        handlers = {
            "call.offer": self.relay,
            "call.answer": self.relay,
            "call.ice_candidate": self.relay,
            "call.accept": self.relay,
            "call.decline": self.relay,
            "call.end": self.relay,
            "call.mute_toggle": self.relay,
            "call.video_toggle": self.relay,
            "call.screen_share": self.relay,
        }
        fn = handlers.get(event_type)
        if fn:
            await fn(data)

    async def relay(self, data):
        data["from_user_id"] = str(self.user.id)
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "call.signal", "payload": data},
        )

    @database_sync_to_async
    def _can_join_call(self):
        from apps.MeetChat.models import Call

        return Call.objects.filter(
            Q(pk=self.call_id)
            & (Q(caller_id=self.user.id) | Q(call_participants__user_id=self.user.id))
        ).exists()

    async def call_signal(self, event):
        payload = event["payload"]
        if payload.get("from_user_id") == str(self.user.id):
            return
        await self.send(text_data=json.dumps(payload))

    async def call_joined(self, event):
        if event.get("from_channel") == self.channel_name:
            return
        await self.send(text_data=json.dumps({
            "type": "call.joined",
            "user_id": event["user_id"],
        }))
