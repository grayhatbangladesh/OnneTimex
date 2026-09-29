from rest_framework import serializers

from apps.MeetSoc.models import Group, GroupMembership, GroupInvite
from apps.accounts.serializers import UserPublicLiteSerializer


class GroupMembershipSerializer(serializers.ModelSerializer):
    user = UserPublicLiteSerializer(read_only=True)

    class Meta:
        model = GroupMembership
        fields = (
            "id",
            "group",
            "user",
            "role",
            "status",
            "joined_at",
        )
        read_only_fields = ("id", "joined_at")


class GroupInviteSerializer(serializers.ModelSerializer):
    # Model fields are `invited_by` / `invited_user`.
    inviter = UserPublicLiteSerializer(source="invited_by", read_only=True)
    invitee = UserPublicLiteSerializer(source="invited_user", read_only=True)

    class Meta:
        model = GroupInvite
        fields = (
            "id",
            "group",
            "inviter",
            "invitee",
            "status",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class GroupSerializer(serializers.ModelSerializer):
    created_by = UserPublicLiteSerializer(read_only=True)
    memberships = GroupMembershipSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "cover_photo",
            "avatar",
            "privacy",
            "category",
            "rules",
            "members_count",
            "posts_count",
            "created_by",
            "memberships",
            "created_at",
        )
        read_only_fields = ("id", "members_count", "posts_count", "created_at")
