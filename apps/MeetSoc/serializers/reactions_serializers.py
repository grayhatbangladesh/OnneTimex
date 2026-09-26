from rest_framework import serializers

from apps.MeetSoc.models import Reaction
from apps.accounts.serializers import UserPublicLiteSerializer


class ReactionSerializer(serializers.ModelSerializer):
    user = UserPublicLiteSerializer(read_only=True)

    class Meta:
        model = Reaction
        fields = (
            "id",
            "user",
            "reaction_type",
            "created_at",
        )
        read_only_fields = ("id", "created_at")
