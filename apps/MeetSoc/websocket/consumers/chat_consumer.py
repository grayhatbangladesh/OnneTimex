import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close(code=4401)
            return
        self.conversation_id = str(self.scope["url_route"]["kwargs"]["conversation_id"])
        if not await self._is_participant():
            await self.close(code=4403)
            return
        self.room_group_name = f"chat_{self.conversation_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        cache.set(f"online:{self.user.id}", "1", timeout=90)
        cache.set(f"last_seen:{self.user.id}", timezone.now().isoformat(), timeout=None)
        await self.accept()
        unread = await self._unread_payload()
        await self.send(text_data=json.dumps({"type": "chat.unread", "data": unread}))

    async def disconnect(self, code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        if getattr(self, "user", None) and self.user.is_authenticated:
            cache.set(f"last_seen:{self.user.id}", timezone.now().isoformat(), timeout=None)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
        event_type = data.get("type")
        handlers = {
            "chat.message": self.handle_send_message,
            "chat.typing": self.handle_typing,
            "chat.read": self.handle_mark_read,
            "chat.react": self.handle_reaction,
            "chat.delete": self.handle_delete,
            "chat.edit": self.handle_edit,
        }
        fn = handlers.get(event_type)
        if fn:
            await fn(data)

    @database_sync_to_async
    def _is_participant(self):
        from apps.MeetChat.models import ConversationParticipant

        return ConversationParticipant.objects.filter(
            conversation_id=self.conversation_id, user_id=self.user.id
        ).exists()

    @database_sync_to_async
    def _unread_payload(self):
        from apps.MeetChat.models import ConversationParticipant

        cp = ConversationParticipant.objects.filter(
            conversation_id=self.conversation_id, user_id=self.user.id
        ).first()
        return {"conversation_id": self.conversation_id, "unread": cp.unread_count if cp else 0}

    async def handle_send_message(self, data):
        msg = await self._save_message(data)
        if not msg:
            return
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "chat.broadcast", "payload": {"type": "chat.message", "message": msg}},
        )

        participant_ids = await self._other_participant_ids()
        for uid in participant_ids:
            await self._notify_participant(uid, data.get("content", ""))

    async def _notify_participant(self, uid, body):
        """Queue the message notification, falling back to a synchronous create."""
        await self._notify_sync(
            str(uid),
            {
                "actor_id": str(self.user.id),
                "notification_type": "message",
                "verb": "New message",
                "title": "MeetSoc",
                "body": (body or "")[:200],
                "data": {"conversation_id": self.conversation_id},
            },
        )

    @database_sync_to_async
    def _notify_sync(self, uid, notif_data):
        from django.conf import settings

        from apps.MeetSoc.tasks.notification_tasks import (
            _create_and_send_notification,
            send_notification_task,
        )

        if getattr(settings, "CELERY_ENABLED", False):
            try:
                send_notification_task.delay(uid, notif_data)
                return
            except Exception:
                logger.warning("Celery broker unavailable, creating notification synchronously")
        try:
            _create_and_send_notification(uid, notif_data)
        except Exception:
            logger.exception("Synchronous notification creation failed for user %s", uid)

    @database_sync_to_async
    def _save_message(self, data):
        from apps.MeetChat.models import Conversation, ConversationParticipant, Message

        conv = Conversation.objects.filter(pk=self.conversation_id).first()
        if not conv:
            return None
        m = Message.objects.create(
            conversation=conv,
            sender=self.user,
            message_type=data.get("message_type", "text"),
            content=data.get("content", "")[:10000],
            reply_to_id=data.get("reply_to_id"),
        )
        conv.last_message = m
        conv.save(update_fields=["last_message"])
        for cp in ConversationParticipant.objects.filter(conversation=conv).exclude(user=self.user):
            cp.unread_count += 1
            cp.save(update_fields=["unread_count"])
            h = cache.get(f"unread_msg:{cp.user_id}") or {}
            h[str(conv.id)] = cp.unread_count
            cache.set(f"unread_msg:{cp.user_id}", h, timeout=None)
        return {
            "id": str(m.id),
            "sender_id": str(self.user.id),
            "message_type": m.message_type,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }

    @database_sync_to_async
    def _other_participant_ids(self):
        from apps.MeetChat.models import ConversationParticipant

        return list(
            ConversationParticipant.objects.filter(conversation_id=self.conversation_id)
            .exclude(user_id=self.user.id)
            .values_list("user_id", flat=True)
        )

    async def handle_typing(self, data):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat.broadcast",
                "payload": {
                    "type": "chat.typing",
                    "user_id": str(self.user.id),
                    "is_typing": data.get("is_typing", True),
                },
            },
        )

    async def handle_mark_read(self, data):
        await self._mark_read()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat.broadcast",
                "payload": {"type": "chat.read", "user_id": str(self.user.id)},
            },
        )

    @database_sync_to_async
    def _mark_read(self):
        from apps.MeetChat.models import ConversationParticipant, Message, MessageSeen

        cp = ConversationParticipant.objects.filter(
            conversation_id=self.conversation_id, user_id=self.user.id
        ).first()
        if cp:
            cp.unread_count = 0
            cp.last_read_at = timezone.now()
            cp.save(update_fields=["unread_count", "last_read_at"])
        lm = Message.objects.filter(conversation_id=self.conversation_id).order_by("-created_at").first()
        if lm:
            MessageSeen.objects.get_or_create(message=lm, user=self.user)

    async def handle_reaction(self, data):
        await self._apply_reaction(data)
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "chat.broadcast", "payload": {"type": "chat.react", "data": data}},
        )

    @database_sync_to_async
    def _apply_reaction(self, data):
        from apps.MeetChat.models import Message

        mid = data.get("message_id")
        if not mid:
            return
        m = Message.objects.filter(pk=mid, conversation_id=self.conversation_id).first()
        if not m:
            return
        reactions = m.reactions or {}
        emoji = data.get("emoji", "like")
        reactions[emoji] = reactions.get(emoji, 0) + 1
        m.reactions = reactions
        m.save(update_fields=["reactions"])

    async def handle_delete(self, data):
        await self._soft_delete_message(data.get("message_id"))
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "chat.broadcast", "payload": {"type": "chat.delete", "message_id": data.get("message_id")}},
        )

    @database_sync_to_async
    def _soft_delete_message(self, message_id):
        from apps.MeetChat.models import Message

        if not message_id:
            return
        Message.objects.filter(pk=message_id, sender=self.user).update(is_deleted=True)

    async def handle_edit(self, data):
        msg = await self._edit_message(data)
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "chat.broadcast", "payload": {"type": "chat.edit", "message": msg}},
        )

    @database_sync_to_async
    def _edit_message(self, data):
        from apps.MeetChat.models import Message

        mid = data.get("message_id")
        if not mid:
            return None
        m = Message.objects.filter(pk=mid, sender=self.user).first()
        if not m:
            return None
        m.content = data.get("content", m.content)[:10000]
        m.is_edited = True
        m.save(update_fields=["content", "is_edited"])
        return {"id": str(m.id), "content": m.content}

    async def chat_broadcast(self, event):
        await self.send(text_data=json.dumps(event["payload"]))
