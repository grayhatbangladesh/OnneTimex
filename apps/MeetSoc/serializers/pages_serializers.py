from rest_framework import serializers

from apps.MeetSoc.models import Page, PageAdmin, PageFollower
from apps.accounts.serializers import UserPublicLiteSerializer


class PageAdminSerializer(serializers.ModelSerializer):
    # The model field is `user`; expose it under the documented `admin` key.
    admin = UserPublicLiteSerializer(source="user", read_only=True)

    class Meta:
        model = PageAdmin
        fields = (
            "id",
            "page",
            "admin",
            "role",
        )


class PageFollowerSerializer(serializers.ModelSerializer):
    user = UserPublicLiteSerializer(read_only=True)

    class Meta:
        model = PageFollower
        fields = (
            "id",
            "page",
            "user",
            "is_liked",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class PageSerializer(serializers.ModelSerializer):
    created_by = UserPublicLiteSerializer(read_only=True)
    followers_rel = PageFollowerSerializer(many=True, read_only=True)

    class Meta:
        model = Page
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "avatar",
            "cover_photo",
            "category",
            "website",
            "email",
            "phone",
            "address",
            "verified",
            "followers_count",
            "likes_count",
            "created_by",
            "followers_rel",
            "created_at",
        )
        read_only_fields = ("id", "followers_count", "likes_count", "verified", "created_at")
