from rest_framework import serializers

from apps.MeetSoc.models import ContentCategory, ContentTag, Post, PostMedia, Story, StoryComment, StoryReaction
from apps.accounts.serializers import UserPublicSerializer, UserPublicLiteSerializer

ANONYMOUS_AUTHOR = {
    "id": "",
    "username": "anonymous",
    "fullName": "Anonymous",
    "profile": {"avatar": ""},
}


class ContentCategoryMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentCategory
        fields = ("id", "name", "slug")


class ContentTagMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentTag
        fields = ("id", "name", "slug")


class PostMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostMedia
        fields = (
            "id", "file", "media_type", "thumbnail", "width", "height", "duration", "order",
        )


class PostListSerializer(serializers.ModelSerializer):
    media_items = PostMediaSerializer(many=True, read_only=True)
    author = UserPublicSerializer(read_only=True)
    category = ContentCategoryMiniSerializer(read_only=True)
    tags = ContentTagMiniSerializer(many=True, read_only=True)
    user_reaction = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "content",
            "post_type",
            "privacy",
            "feeling",
            "location",
            "link_preview",
            "reactions_count",
            "comments_count",
            "shares_count",
            "views_count",
            "created_at",
            "media_items",
            "category",
            "tags",
            "user_reaction",
            "is_anonymous",
        )

    def get_user_reaction(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        if not hasattr(obj, "_user_reaction"):
            return None
        return obj._user_reaction

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_anonymous:
            data["author"] = ANONYMOUS_AUTHOR
        return data


class FeedPostListSerializer(serializers.ModelSerializer):
    """Optimized serializer for feed API with reduced user profile data."""
    media_items = PostMediaSerializer(many=True, read_only=True)
    author = UserPublicLiteSerializer(read_only=True)
    category = ContentCategoryMiniSerializer(read_only=True)
    tags = ContentTagMiniSerializer(many=True, read_only=True)
    user_reaction = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "content",
            "post_type",
            "privacy",
            "feeling",
            "location",
            "link_preview",
            "reactions_count",
            "comments_count",
            "shares_count",
            "views_count",
            "created_at",
            "media_items",
            "category",
            "tags",
            "user_reaction",
            "is_anonymous",
        )

    def get_user_reaction(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        if not hasattr(obj, "_user_reaction"):
            return None
        return obj._user_reaction

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_anonymous:
            data["author"] = ANONYMOUS_AUTHOR
        return data


class PostDetailSerializer(PostListSerializer):
    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + ("updated_at", "shared_post", "group", "page")


class StorySerializer(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField()
    author_avatar = serializers.ReadOnlyField()
    my_reaction = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = (
            "id",
            "author",
            "author_name",
            "author_avatar",
            "media",
            "media_type",
            "text_content",
            "background_color",
            "stickers",
            "music",
            "privacy",
            "views_count",
            "reactions_count",
            "comments_count",
            "my_reaction",
            "expires_at",
            "created_at",
        )

    def get_my_reaction(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            reaction = StoryReaction.objects.filter(story=obj, user=request.user).first()
            if reaction:
                return reaction.reaction_type
        return None


class StoryCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_avatar = serializers.SerializerMethodField()

    class Meta:
        model = StoryComment
        fields = ("id", "story", "author", "author_name", "author_avatar", "parent", "content", "created_at")
        read_only_fields = ("id", "story", "author", "created_at")

    def get_author_name(self, obj):
        return obj.author.full_name if hasattr(obj.author, 'full_name') else obj.author.username

    def get_author_avatar(self, obj):
        if hasattr(obj.author, 'profile') and obj.author.profile.avatar:
            return obj.author.profile.avatar.url
        return None
