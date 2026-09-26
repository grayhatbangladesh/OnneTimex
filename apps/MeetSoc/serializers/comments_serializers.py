from rest_framework import serializers

from apps.MeetSoc.models import Comment
from apps.accounts.serializers import UserPublicLiteSerializer

ANONYMOUS_AUTHOR = {
    "id": "",
    "username": "anonymous",
    "fullName": "Anonymous",
    "profile": {"avatar": ""},
}


class CommentSerializer(serializers.ModelSerializer):
    author = UserPublicLiteSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = (
            "id",
            "post",
            "author",
            "parent",
            "content",
            "media",
            "reactions_count",
            "replies_count",
            "is_edited",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "reactions_count", "replies_count", "is_edited", "created_at", "updated_at")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.post and instance.post.is_anonymous:
            data["author"] = ANONYMOUS_AUTHOR
        return data


class CommentDetailSerializer(CommentSerializer):
    class Meta(CommentSerializer.Meta):
        fields = CommentSerializer.Meta.fields
