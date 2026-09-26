from rest_framework import serializers

from apps.MeetChat.models import Call, CallParticipant
from apps.accounts.serializers import UserPublicLiteSerializer


class CallParticipantSerializer(serializers.ModelSerializer):
    user = UserPublicLiteSerializer(read_only=True)

    class Meta:
        model = CallParticipant
        fields = (
            "id",
            "user",
            "joined_at",
            "left_at",
            "is_muted",
            "is_video_on",
        )


class CallSerializer(serializers.ModelSerializer):
    caller = UserPublicLiteSerializer(read_only=True)
    call_participants = CallParticipantSerializer(many=True, read_only=True)

    class Meta:
        model = Call
        fields = (
            "id",
            "call_type",
            "caller",
            "conversation",
            "status",
            "started_at",
            "ended_at",
            "duration",
            "call_participants",
            "created_at",
        )
        read_only_fields = ("id", "started_at", "ended_at", "duration", "created_at")
