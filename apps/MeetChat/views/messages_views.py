from django.db.models import Case, F, When, Value, IntegerField
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.MeetChat.models import Conversation, ConversationParticipant, Message, MessageSeen
from apps.MeetChat.serializers import ConversationSerializer, MessageSerializer
from apps.MeetSoc.core.pagination import StandardPagination


class ConversationListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    serializer_class = ConversationSerializer

    def get(self, request):
        cp = ConversationParticipant.objects.filter(
            user=request.user, unread_count__gt=0
        ).values_list("conversation_id", flat=True)

        qs = Conversation.objects.filter(
            participants=request.user
        ).select_related(
            "last_message", "last_message__sender", "last_message__sender__profile"
        ).prefetch_related(
            "cp", "cp__user", "cp__user__profile"
        )

        qs = qs.annotate(
            _is_unread=Case(
                When(id__in=cp, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by("_is_unread", "-last_message__created_at", "-created_at")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        data = ConversationSerializer(page, many=True, context={"request": request}).data
        return paginator.get_paginated_response(data)

    def post(self, request):
        ctype = request.data.get("conversation_type", "direct")
        name = request.data.get("name")
        user_ids = request.data.get("participant_ids", [])
        conv = Conversation.objects.create(conversation_type=ctype, name=name)
        ConversationParticipant.objects.create(conversation=conv, user=request.user, role="admin")
        for uid in user_ids:
            from django.contrib.auth import get_user_model

            u = get_user_model().objects.filter(pk=uid).first()
            if u:
                ConversationParticipant.objects.get_or_create(conversation=conv, user=u)
        return Response(
            {"success": True, "data": {"id": str(conv.id)}, "message": "Created.", "meta": {}},
            status=201,
        )


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer

    def get(self, request, conversation_id):
        conv = get_object_or_404(
            Conversation.objects.select_related(
                "last_message", "last_message__sender"
            ).prefetch_related(
                "cp", "cp__user", "cp__user__profile"
            ),
            pk=conversation_id,
            participants=request.user,
        )
        data = ConversationSerializer(conv, context={"request": request}).data
        return Response({"success": True, "data": data, "message": "", "meta": {}})

    def put(self, request, conversation_id):
        conv = get_object_or_404(Conversation, pk=conversation_id, participants=request.user)
        conv.name = request.data.get("name", conv.name)
        if request.FILES.get("avatar"):
            conv.avatar = request.FILES["avatar"]
        conv.save()
        return Response({"success": True, "data": {"id": str(conv.id)}, "message": "Updated.", "meta": {}})

    def delete(self, request, conversation_id):
        conv = get_object_or_404(Conversation, pk=conversation_id, participants=request.user)
        ConversationParticipant.objects.filter(conversation=conv, user=request.user).delete()
        return Response({"success": True, "data": {}, "message": "Left.", "meta": {}}, status=204)


class MessageListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    pagination_class = StandardPagination

    def get(self, request, conversation_id):
        conv = get_object_or_404(Conversation, pk=conversation_id, participants=request.user)
        qs = Message.objects.filter(conversation=conv, is_deleted=False).select_related("sender", "sender__profile").order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        data = MessageSerializer(page, many=True, context={"request": request}).data
        return paginator.get_paginated_response(data)

    def post(self, request, conversation_id):
        conv = get_object_or_404(Conversation, pk=conversation_id, participants=request.user)

        # Optional reply target: accept `reply_to` (REST clients) or
        # `reply_to_id` (websocket clients) and only honour messages that
        # belong to this conversation.
        reply = None
        reply_id = request.data.get("reply_to") or request.data.get("reply_to_id")
        if reply_id:
            reply = (
                Message.objects.filter(pk=reply_id, conversation=conv).first()
            )

        m = Message.objects.create(
            conversation=conv,
            sender=request.user,
            message_type=request.data.get("message_type", "text"),
            content=request.data.get("content", ""),
            media=request.FILES.get("media"),
            reply_to=reply,
        )
        conv.last_message = m
        conv.save(update_fields=["last_message"])

        ConversationParticipant.objects.filter(
            conversation=conv
        ).exclude(user=request.user).update(
            unread_count=F("unread_count") + 1
        )

        # Push the message to every websocket listener in this conversation and
        # notify the other participants. Neither may ever break sending a message.
        message_payload = {
            "id": str(m.id),
            "sender_id": str(request.user.id),
            "message_type": m.message_type,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer

            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"chat_{conv.id}",
                    {"type": "chat.broadcast", "payload": {"type": "chat.message", "message": message_payload}},
                )
        except Exception:
            pass

        try:
            from apps.MeetSoc.tasks.notification_tasks import notify

            other_ids = ConversationParticipant.objects.filter(
                conversation=conv
            ).exclude(user=request.user).values_list("user_id", flat=True)
            for uid in other_ids:
                notify(
                    recipient_id=uid,
                    actor_id=request.user.id,
                    notification_type="message",
                    verb="New message",
                    data={"conversation_id": str(conv.id)},
                )
        except Exception:
            pass

        return Response(
            {
                "success": True,
                "data": MessageSerializer(m, context={"request": request}).data,
                "message": "Sent.",
                "meta": {},
            },
            status=201,
        )


class MessageDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer

    def delete(self, request, message_id):
        m = get_object_or_404(Message, pk=message_id, sender=request.user)
        m.is_deleted = True
        m.save(update_fields=["is_deleted"])
        return Response({"success": True, "data": {}, "message": "Deleted.", "meta": {}}, status=204)

    def put(self, request, message_id):
        m = get_object_or_404(Message, pk=message_id, sender=request.user)
        m.content = request.data.get("content", m.content)
        m.is_edited = True
        m.save()
        return Response({"success": True, "data": {"id": str(m.id)}, "message": "Updated.", "meta": {}})


class MessageReactView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer

    def post(self, request, message_id):
        m = get_object_or_404(Message, pk=message_id)
        reactions = m.reactions or {}
        emoji = request.data.get("emoji", "like")
        user_id = str(request.user.id)

        user_list = reactions.get(emoji, [])
        if not isinstance(user_list, list):
            user_list = []

        if user_id in user_list:
            user_list.remove(user_id)
            if not user_list:
                reactions.pop(emoji, None)
            else:
                reactions[emoji] = user_list
        else:
            user_list.append(user_id)
            reactions[emoji] = user_list

        m.reactions = reactions
        m.save(update_fields=["reactions"])

        counts = {e: len(ids) for e, ids in reactions.items() if isinstance(ids, list)}
        return Response({"success": True, "data": {"counts": counts, "user_reaction": emoji if user_id in (reactions.get(emoji) or []) else None}, "message": "", "meta": {}})


class ConversationMemberView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def post(self, request, conversation_id):
        conv = get_object_or_404(Conversation, pk=conversation_id, participants=request.user)
        uid = request.data.get("user_id")
        from django.contrib.auth import get_user_model

        u = get_object_or_404(get_user_model(), pk=uid)
        ConversationParticipant.objects.get_or_create(conversation=conv, user=u)
        return Response({"success": True, "data": {}, "message": "Member added.", "meta": {}})

    def delete(self, request, conversation_id, user_id=None):
        conv = get_object_or_404(Conversation, pk=conversation_id, participants=request.user)
        uid = user_id or request.data.get("user_id")
        if not uid:
            return Response(status=400)
        ConversationParticipant.objects.filter(conversation=conv, user_id=uid).delete()
        return Response({"success": True, "data": {}, "message": "Removed.", "meta": {}}, status=204)


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def post(self, request, conversation_id):
        conv = get_object_or_404(Conversation, pk=conversation_id, participants=request.user)
        ConversationParticipant.objects.filter(
            conversation=conv, user=request.user
        ).update(unread_count=0, last_read_at=timezone.now())
        return Response({"success": True, "data": {}, "message": "Marked as read.", "meta": {}})


class DirectConversationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"success": False, "error": {"code": "MISSING", "message": "user_id required.", "details": {}}}, status=400)
        other = get_object_or_404(User, pk=user_id)
        if other.id == request.user.id:
            return Response({"success": False, "error": {"code": "INVALID", "message": "Cannot message yourself.", "details": {}}}, status=400)

        existing = Conversation.objects.filter(
            conversation_type="direct", participants=request.user
        ).filter(participants=other).first()

        if existing:
            conv = existing
            created = False
        else:
            conv = Conversation.objects.create(conversation_type="direct")
            ConversationParticipant.objects.create(conversation=conv, user=request.user)
            ConversationParticipant.objects.create(conversation=conv, user=other)
            created = True

        return Response(
            {
                "success": True,
                "data": {"id": str(conv.id), "created": created},
                "message": "",
                "meta": {},
            },
            status=201 if created else 200,
        )


class OnlineStatusView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def get(self, request):
        from django.core.cache import cache

        ids = request.query_params.get("ids", "")
        out = {}
        for i in ids.split(","):
            if not i:
                continue
            i = i.strip()
            out[i] = {
                "online": bool(cache.get(f"online:{i}")),
                "last_seen": cache.get(f"last_seen:{i}"),
            }
        return Response({"success": True, "data": out, "message": "", "meta": {}})
