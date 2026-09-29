import json

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.MeetChat.models import Call, CallParticipant
from apps.MeetChat.serializers import CallSerializer
from apps.MeetChat.models import Conversation, ConversationParticipant, Message


def _create_call_log(conv, call, content, request=None):
    m = Message.objects.create(
        conversation=conv,
        sender=call.caller,
        message_type="call_log",
        content=json.dumps({
            "call_id": str(call.id),
            "call_type": call.call_type,
            "status": call.status,
            "duration": call.duration,
            "content": content,
        }),
    )
    conv.last_message = m
    conv.save(update_fields=["last_message"])
    return m


def _notify_call_user(user_id, payload, event_type="call_incoming"):
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"notification_user_{user_id}",
            {"type": event_type, **payload},
        )
    except Exception:
        pass


class CallInitiateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CallSerializer

    def post(self, request):
        conv_id = request.data.get("conversation_id")
        call_type = request.data.get("call_type", "video")
        conv = get_object_or_404(Conversation, pk=conv_id, participants=request.user)
        c = Call.objects.create(
            call_type=call_type,
            caller=request.user,
            conversation=conv,
            status="ringing",
        )

        all_participants = ConversationParticipant.objects.filter(
            conversation=conv
        ).select_related("user")

        for cp in all_participants:
            CallParticipant.objects.get_or_create(call=c, user=cp.user)

        _create_call_log(conv, c, "Outgoing call", request)

        other_participants = ConversationParticipant.objects.filter(
            conversation=conv
        ).exclude(user=request.user).select_related("user")

        for cp in other_participants:
            user = cp.user
            avatar_url = ""
            if hasattr(user, "profile") and user.profile and user.profile.avatar:
                try:
                    avatar_url = user.profile.avatar.url
                except Exception:
                    avatar_url = ""
            _notify_call_user(user.id, {
                "call_id": str(c.id),
                "call_type": call_type,
                "caller_id": str(request.user.id),
                "caller_name": request.user.full_name or request.user.username or str(request.user.id),
                "caller_avatar": avatar_url,
            })

        return Response(
            {
                "success": True,
                "data": {"id": str(c.id), "status": c.status},
                "message": "Call created.",
                "meta": {},
            },
            status=201,
        )


class CallAcceptView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CallSerializer

    def post(self, request, call_id):
        c = get_object_or_404(Call, pk=call_id)
        c.status = "active"
        c.started_at = timezone.now()
        c.save(update_fields=["status", "started_at"])
        CallParticipant.objects.filter(call=c, user=request.user).update(joined_at=timezone.now())

        conv = c.conversation
        call_log_msg = Message.objects.filter(
            conversation=conv, message_type="call_log"
        ).order_by("-created_at").first()
        if call_log_msg:
            data = json.loads(call_log_msg.content)
            data["status"] = "active"
            call_log_msg.content = json.dumps(data)
            call_log_msg.save(update_fields=["content"])

        _notify_call_user(str(c.caller_id), {
            "call_id": str(c.id),
            "call_type": "call_accepted",
            "caller_id": str(request.user.id),
            "caller_name": request.user.full_name or request.user.username or str(request.user.id),
            "caller_avatar": "",
        }, event_type="call_accepted")

        return Response({"success": True, "data": {"id": str(c.id)}, "message": "Accepted.", "meta": {}})


class CallDeclineView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CallSerializer

    def post(self, request, call_id):
        c = get_object_or_404(Call, pk=call_id)
        end = timezone.now()
        c.status = "declined"
        c.ended_at = end
        if c.started_at:
            c.duration = int((end - c.started_at).total_seconds())
        try:
            c.save(update_fields=["status", "ended_at", "duration"])
        except Exception:
            pass

        conv = c.conversation
        call_log_msg = Message.objects.filter(
            conversation=conv, message_type="call_log"
        ).order_by("-created_at").first()
        if call_log_msg:
            try:
                data = json.loads(call_log_msg.content)
                data["status"] = "declined"
                data["duration"] = c.duration
                if request.user.id != c.caller_id:
                    data["content"] = "Missed call"
                call_log_msg.content = json.dumps(data)
                call_log_msg.save(update_fields=["content"])
            except Exception:
                pass

        _notify_call_user(str(c.caller_id), {
            "call_id": str(c.id),
            "call_type": "call_declined",
            "caller_id": str(request.user.id),
            "caller_name": request.user.full_name or request.user.username or str(request.user.id),
            "caller_avatar": "",
        }, event_type="call_declined")

        return Response({"success": True, "data": {}, "message": "Declined.", "meta": {}})


class CallEndView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CallSerializer

    def post(self, request, call_id):
        c = get_object_or_404(Call, pk=call_id)
        end = timezone.now()
        c.status = "ended"
        c.ended_at = end
        if c.started_at:
            c.duration = int((end - c.started_at).total_seconds())
        try:
            c.save(update_fields=["status", "ended_at", "duration"])
        except Exception:
            pass

        conv = c.conversation
        call_log_msg = Message.objects.filter(
            conversation=conv, message_type="call_log"
        ).order_by("-created_at").first()
        if call_log_msg:
            try:
                data = json.loads(call_log_msg.content)
                data["status"] = "ended"
                data["duration"] = c.duration
                call_log_msg.content = json.dumps(data)
                call_log_msg.save(update_fields=["content"])
            except Exception:
                pass

        _notify_call_user(str(c.caller_id), {
            "call_id": str(c.id),
            "call_type": "call_ended",
            "caller_id": str(request.user.id),
            "caller_name": request.user.full_name or request.user.username or str(request.user.id),
            "caller_avatar": "",
        }, event_type="call_ended")

        return Response({"success": True, "data": {"duration": c.duration}, "message": "Ended.", "meta": {}})


class CallHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CallSerializer

    def get(self, request):
        qs = Call.objects.filter(
            conversation__participants=request.user
        ).order_by("-created_at")[:100]
        data = [
            {
                "id": str(c.id),
                "call_type": c.call_type,
                "status": c.status,
                "duration": c.duration,
                "created_at": c.created_at.isoformat(),
            }
            for c in qs
        ]
        return Response({"success": True, "data": data, "message": "", "meta": {}})


class IceServersView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def get(self, request):
        from django.conf import settings

        ice = [
            {"urls": "stun:stun.l.google.com:19302"},
            {"urls": "stun:stun1.l.google.com:19302"},
            {"urls": "stun:stun2.l.google.com:19302"},
            {"urls": "stun:stun3.l.google.com:19302"},
            {"urls": "stun:stun4.l.google.com:19302"},
            {"urls": "stun:stun01.sipphone.com"},
            {"urls": "stun:stun.ekiga.net"},
            {"urls": "stun:stun.fwdnet.net"},
            {"urls": "stun:stun.ideasip.com"},
            {"urls": "stun:stun.iptel.org"},
            {"urls": "stun:stun.rixtelecom.se"},
            {"urls": "stun:stun.schlund.de"},
            {"urls": "stun:stunserver.org"},
            {"urls": "stun:stun.softjoys.com"},
            {"urls": "stun:stun.voiparound.com"},
            {"urls": "stun:stun.voipbuster.com"},
            {"urls": "stun:stun.voipstunt.com"},
            {"urls": "stun:stun.voxgratia.org"},
            {"urls": "stun:stun.xten.com"},
        ]
        turn_url = getattr(settings, "TURN_SERVER_URL", "") or ""
        if turn_url:
            turn_entry = {"urls": turn_url}
            username = getattr(settings, "TURN_USERNAME", "")
            credential = getattr(settings, "TURN_CREDENTIAL", "")
            if username:
                turn_entry["username"] = username
            if credential:
                turn_entry["credential"] = credential
            ice.append(turn_entry)
        return Response({"success": True, "data": {"ice_servers": ice}, "message": "", "meta": {}})
