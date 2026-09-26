from rest_framework import serializers

from apps.MeetSoc.models import Payment, PaymentMethod


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["id", "name", "icon", "number", "help_text"]


class PaymentSerializer(serializers.ModelSerializer):
    method_name = serializers.CharField(source="payment_method.name", read_only=True, default="")
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True, default="")

    class Meta:
        model = Payment
        fields = [
            "id", "payment_method", "method_name",
            "amount", "currency",
            "transaction_id", "sender_number", "screenshot",
            "status", "status_display", "admin_note",
            "user_name", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "admin_note", "created_at", "updated_at"]


class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "payment_method", "amount", "currency",
            "transaction_id", "sender_number", "screenshot",
        ]
