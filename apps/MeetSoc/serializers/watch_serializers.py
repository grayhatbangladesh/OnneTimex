from rest_framework import serializers

from apps.MeetSoc.models import WatchVideo, WatchVideoComment
from apps.accounts.serializers import UserPublicLiteSerializer


class WatchVideoCommentSerializer(serializers.ModelSerializer):
    author = UserPublicLiteSerializer(read_only=True)

    class Meta:
        model = WatchVideoComment
        fields = ("id", "video", "author", "content", "created_at")
        read_only_fields = ("id", "created_at")


class WatchVideoSerializer(serializers.ModelSerializer):
    author = UserPublicLiteSerializer(read_only=True)
    user_reaction = serializers.SerializerMethodField()

    class Meta:
        model = WatchVideo
        fields = (
            "id",
            "title",
            "description",
            "video_file",
            "thumbnail",
            "duration",
            "category",
            "tags",
            "views_count",
            "likes_count",
            "comments_count",
            "shares_count",
            "author",
            "user_reaction",
            "created_at",
        )
        read_only_fields = ("id", "views_count", "likes_count", "comments_count", "shares_count", "created_at")

    def get_user_reaction(self, obj):
        request = self.context.get("request")
        if not request or not request.user or request.user.is_anonymous:
            return None
        from apps.MeetSoc.models import Reaction
        from django.contrib.contenttypes.models import ContentType
        reaction = Reaction.objects.filter(
            user=request.user,
            content_type=ContentType.objects.get_for_model(WatchVideo),
            object_id=obj.id,
        ).first()
        return reaction.reaction_type if reaction else None
