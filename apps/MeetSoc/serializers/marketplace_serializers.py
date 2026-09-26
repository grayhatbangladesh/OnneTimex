from rest_framework import serializers

from apps.MeetSoc.models import Product, ProductMedia
from apps.accounts.serializers import UserPublicLiteSerializer


class ProductMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductMedia
        fields = ("id", "file", "order")


class ProductSerializer(serializers.ModelSerializer):
    seller = UserPublicLiteSerializer(read_only=True)
    media_items = ProductMediaSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "title",
            "description",
            "price",
            "category",
            "condition",
            "location",
            "status",
            "views_count",
            "media_items",
            "seller",
            "created_at",
        )
        read_only_fields = ("id", "views_count", "created_at")
