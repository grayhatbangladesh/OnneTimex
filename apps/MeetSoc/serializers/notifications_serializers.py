from rest_framework import serializers

from apps.MeetSoc.models import Notification, NotificationSettings
from apps.accounts.serializers import UserPublicLiteSerializer


class NotificationSerializer(serializers.ModelSerializer):
    actor = UserPublicLiteSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "recipient",
            "actor",
            "notification_type",
            "verb",
            "target_type",
            "target_id",
            "data",
            "is_read",
            "is_seen",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class NotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSettings
        fields = "__all__"
