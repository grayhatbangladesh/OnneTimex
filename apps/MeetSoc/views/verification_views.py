import uuid
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.MeetSoc.models import Payment, PaymentMethod
from apps.MeetSoc.models import BlueVerificationRequest, SubscriptionPlan, UserSubscription
from apps.MeetSoc.serializers import (
    BlueVerificationRequestSerializer,
    SubscriptionPlanSerializer,
    UserSubscriptionSerializer,
)


class SubscriptionPlanListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True)
        return Response(
            {
                "success": True,
                "data": SubscriptionPlanSerializer(plans, many=True).data,
                "message": "",
                "meta": {},
            }
        )


class BlueVerificationMyStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        latest = (
            BlueVerificationRequest.objects.filter(user=request.user)
            .order_by("-created_at")
            .first()
        )
        active = BlueVerificationRequest.get_active_for_user(request.user)
        active_sub = None
        if active and hasattr(active, "subscription"):
            active_sub = UserSubscriptionSerializer(active.subscription).data if active.subscription_id else None

        return Response(
            {
                "success": True,
                "data": {
                    "has_blue_badge": bool(active),
                    "badge_valid_until": active.valid_until if active else None,
                    "latest_request": BlueVerificationRequestSerializer(latest).data if latest else None,
                    "active_subscription": active_sub,
                },
                "message": "",
                "meta": {},
            }
        )


class BlueVerificationApplyView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        pending = BlueVerificationRequest.objects.filter(
            user=request.user,
            status="pending",
        ).exists()
        if pending:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "ALREADY_PENDING",
                        "message": "A verification request is already pending.",
                        "details": {},
                    },
                },
                status=400,
            )

        plan_id = request.data.get("plan_id")
        plan = None
        if plan_id:
            try:
                plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
            except (SubscriptionPlan.DoesNotExist, ValueError):
                return Response(
                    {
                        "success": False,
                        "error": {
                            "code": "INVALID_PLAN",
                            "message": "Invalid or inactive subscription plan.",
                            "details": {},
                        },
                    },
                    status=400,
                )

        nid_front = request.FILES.get("nid_front")
        nid_back = request.FILES.get("nid_back")

        if not nid_front or not nid_back:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "NID_REQUIRED",
                        "message": "Both NID front and back images are required.",
                        "details": {},
                    },
                },
                status=400,
            )

        obj = BlueVerificationRequest.objects.create(
            user=request.user,
            plan=plan,
            status="pending",
            nid_front=nid_front,
            nid_back=nid_back,
            note=request.data.get("note", ""),
        )

        return Response(
            {
                "success": True,
                "data": BlueVerificationRequestSerializer(obj).data,
                "message": "Verification request submitted. Please complete payment to activate.",
                "meta": {},
            },
            status=201,
        )


class PurchaseSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        plan_id = request.data.get("plan_id")
        if not plan_id:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "PLAN_REQUIRED",
                        "message": "Subscription plan ID is required.",
                        "details": {},
                    },
                },
                status=400,
            )

        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except (SubscriptionPlan.DoesNotExist, ValueError):
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "INVALID_PLAN",
                        "message": "Invalid or inactive subscription plan.",
                        "details": {},
                    },
                },
                status=400,
            )

        pending = BlueVerificationRequest.objects.filter(
            user=request.user,
            status="pending",
        ).exists()
        if pending:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "ALREADY_PENDING",
                        "message": "A verification request is already pending.",
                        "details": {},
                    },
                },
                status=400,
            )

        nid_front = request.FILES.get("nid_front")
        nid_back = request.FILES.get("nid_back")

        if not nid_front or not nid_back:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "NID_REQUIRED",
                        "message": "Both NID front and back images are required.",
                        "details": {},
                    },
                },
                status=400,
            )

        transaction_id = request.data.get("transaction_id", "")
        sender_number = request.data.get("sender_number", "")
        payment_method_id = request.data.get("payment_method_id")
        screenshot = request.FILES.get("screenshot")

        if not transaction_id or not payment_method_id:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "PAYMENT_INFO_REQUIRED",
                        "message": "Transaction ID and payment method are required.",
                        "details": {},
                    },
                },
                status=400,
            )

        try:
            payment_method = PaymentMethod.objects.get(id=payment_method_id, is_active=True)
        except (PaymentMethod.DoesNotExist, ValueError):
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "INVALID_PAYMENT_METHOD",
                        "message": "Invalid payment method.",
                        "details": {},
                    },
                },
                status=400,
            )

        vr = BlueVerificationRequest.objects.create(
            user=request.user,
            plan=plan,
            status="pending",
            nid_front=nid_front,
            nid_back=nid_back,
            note=request.data.get("note", ""),
        )

        payment = Payment.objects.create(
            user=request.user,
            payment_method=payment_method,
            amount=plan.price_bdt,
            currency="BDT",
            transaction_id=transaction_id,
            sender_number=sender_number,
            screenshot=screenshot,
            status="pending",
        )

        return Response(
            {
                "success": True,
                "data": {
                    "verification_request": BlueVerificationRequestSerializer(vr).data,
                    "payment": {
                        "id": str(payment.id),
                        "amount": float(payment.amount),
                        "currency": payment.currency,
                        "status": payment.status,
                    },
                },
                "message": "Verification request and payment submitted. Awaiting admin approval.",
                "meta": {},
            },
            status=201,
        )


class PaymentMethodListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        methods = PaymentMethod.objects.filter(is_active=True)
        data = [
            {
                "id": str(m.id),
                "name": m.name,
                "number": m.number,
                "help_text": m.help_text,
                "icon": m.icon.url if m.icon else None,
            }
            for m in methods
        ]
        return Response(
            {
                "success": True,
                "data": data,
                "message": "",
                "meta": {},
            }
        )
