from rest_framework import serializers

from apps.MeetChat.models import Conversation, ConversationParticipant, Message, MessageSeen
from apps.accounts.serializers import UserPublicLiteSerializer


class ConversationParticipantSerializer(serializers.ModelSerializer):
    user = UserPublicLiteSerializer(read_only=True)

    class Meta:
        model = ConversationParticipant
        fields = (
            "id",
            "user",
            "role",
            "is_muted",
            "last_read_at",
            "unread_count",
            "joined_at",
        )


class MessageSerializer(serializers.ModelSerializer):
    sender = UserPublicLiteSerializer(read_only=True)
    reactions = serializers.SerializerMethodField()
    user_reaction = serializers.SerializerMethodField()
    reply_to_message = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            "id",
            "conversation",
            "sender",
            "message_type",
            "content",
            "media",
            "reply_to",
            "reply_to_message",
            "reactions",
            "user_reaction",
            "is_edited",
            "is_deleted",
            "created_at",
        )
        read_only_fields = ("id", "is_edited", "is_deleted", "created_at")

    def get_reactions(self, obj):
        raw = obj.reactions or {}
        return {e: len(ids) for e, ids in raw.items() if isinstance(ids, list)}

    def get_user_reaction(self, obj):
        request = self.context.get("request")
        if not request or not request.user:
            return None
        raw = obj.reactions or {}
        user_id = str(request.user.id)
        for emoji, ids in raw.items():
            if isinstance(ids, list) and user_id in ids:
                return emoji
        return None

    def get_reply_to_message(self, obj):
        if obj.reply_to:
            return {
                "id": str(obj.reply_to.id),
                "sender": UserPublicLiteSerializer(obj.reply_to.sender, context=self.context).data if obj.reply_to.sender else None,
                "content": obj.reply_to.content[:100] if obj.reply_to.content else "",
                "message_type": obj.reply_to.message_type,
            }
        return None


class ConversationSerializer(serializers.ModelSerializer):
    cp = ConversationParticipantSerializer(many=True, read_only=True)
    last_message = MessageSerializer(read_only=True)

    class Meta:
        model = Conversation
        fields = (
            "id",
            "conversation_type",
            "name",
            "avatar",
            "last_message",
            "cp",
            "created_at",
        )
        read_only_fields = ("id", "created_at")
