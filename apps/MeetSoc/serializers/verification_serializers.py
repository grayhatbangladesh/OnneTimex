from rest_framework import serializers

from apps.MeetSoc.models import (
    BlueVerificationRequest,
    SubscriptionPlan,
    UserSubscription,
)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = (
            "id",
            "name",
            "description",
            "price_bdt",
            "price_usd",
            "duration_days",
            "features",
            "is_active",
            "sort_order",
        )


class BlueVerificationRequestSerializer(serializers.ModelSerializer):
    is_active_badge = serializers.BooleanField(read_only=True)
    plan_name = serializers.SerializerMethodField()
    plan_price = serializers.SerializerMethodField()

    class Meta:
        model = BlueVerificationRequest
        fields = (
            "id",
            "plan",
            "plan_name",
            "plan_price",
            "status",
            "nid_front",
            "nid_back",
            "note",
            "admin_note",
            "approved_at",
            "valid_from",
            "valid_until",
            "is_active_badge",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "status",
            "admin_note",
            "approved_at",
            "valid_from",
            "valid_until",
            "created_at",
            "updated_at",
        )

    def get_plan_name(self, obj):
        return obj.plan.name if obj.plan else None

    def get_plan_price(self, obj):
        return float(obj.plan.price_bdt) if obj.plan else None


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.SerializerMethodField()
    plan_price = serializers.SerializerMethodField()

    class Meta:
        model = UserSubscription
        fields = (
            "id",
            "plan",
            "plan_name",
            "plan_price",
            "verification_request",
            "payment",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
        )
        read_only_fields = (
            "start_date",
            "end_date",
            "created_at",
        )

    def get_plan_name(self, obj):
        return obj.plan.name if obj.plan else None

    def get_plan_price(self, obj):
        return float(obj.plan.price_bdt) if obj.plan else None
