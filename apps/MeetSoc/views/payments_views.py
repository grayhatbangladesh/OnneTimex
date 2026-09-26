from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.MeetSoc.models import Notification
from apps.MeetSoc.models import Payment, PaymentMethod, UserWallet, WalletTransaction
from apps.MeetSoc.serializers import PaymentCreateSerializer, PaymentMethodSerializer, PaymentSerializer


def _send_notification(recipient_id, actor_id, verb):
    try:
        from apps.MeetSoc.tasks.notification_tasks import notify
        notify(
            recipient_id=str(recipient_id),
            actor_id=str(actor_id),
            notification_type="payment_update",
            verb=verb,
        )
    except Exception:
        try:
            Notification.objects.create(
                recipient_id=recipient_id,
                actor_id=actor_id,
                notification_type="payment_update",
                verb=verb,
            )
        except Exception:
            pass


class PaymentMethodListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        methods = PaymentMethod.objects.filter(is_active=True)
        return Response({
            "success": True,
            "data": PaymentMethodSerializer(methods, many=True).data,
            "message": "",
            "meta": {},
        })


class PaymentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Payment.objects.filter(user=request.user)
        status = request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        return Response({
            "success": True,
            "data": PaymentSerializer(qs, many=True).data,
            "message": "",
            "meta": {},
        })

    def post(self, request):
        ser = PaymentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        payment = ser.save(user=request.user, status="pending")
        return Response({
            "success": True,
            "data": PaymentSerializer(payment).data,
            "message": "Payment submitted. Waiting for approval.",
            "meta": {},
        }, status=201)


class PaymentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id):
        payment = get_object_or_404(Payment, pk=payment_id, user=request.user)
        return Response({
            "success": True,
            "data": PaymentSerializer(payment).data,
            "message": "",
            "meta": {},
        })


class AdminPaymentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response(
                {"success": False, "error": {"message": "Admin only."}},
                status=403,
            )
        status_filter = request.query_params.get("status", "pending")
        qs = Payment.objects.filter(status=status_filter).select_related("user", "payment_method")
        return Response({
            "success": True,
            "data": PaymentSerializer(qs, many=True).data,
            "message": "",
            "meta": {},
        })


class AdminPaymentActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, payment_id):
        if not request.user.is_staff:
            return Response(
                {"success": False, "error": {"message": "Admin only."}},
                status=403,
            )
        payment = get_object_or_404(Payment, pk=payment_id)
        action = request.data.get("action")
        note = request.data.get("note", "")

        if action == "approve" and payment.status == "pending":
            with transaction.atomic():
                payment.status = "approved"
                payment.admin_note = note
                payment.save(update_fields=["status", "admin_note"])
                # Add to wallet
                wallet = _get_or_create_wallet(payment.user)
                if payment.currency == "BDT":
                    wallet.balance_bdt += payment.amount
                    wallet.save(update_fields=["balance_bdt"])
                else:
                    wallet.balance_usd += payment.amount
                    wallet.save(update_fields=["balance_usd"])
                WalletTransaction.objects.create(
                    wallet=wallet,
                    type="deposit",
                    currency=payment.currency,
                    amount=payment.amount,
                    description=f"Payment approved (#{str(payment.id)[:8]})",
                    related_payment=payment,
                    status="completed",
                )
            # Notify user — approved (outside transaction, best effort)
            _send_notification(
                recipient_id=payment.user_id,
                actor_id=request.user.id,
                verb=f"Your payment of {payment.currency} {payment.amount} has been approved and added to your wallet.",
            )
        elif action == "reject" and payment.status == "pending":
            payment.status = "rejected"
            payment.admin_note = note
            payment.save(update_fields=["status", "admin_note"])
            # Notify user — rejected
            _send_notification(
                recipient_id=payment.user_id,
                actor_id=request.user.id,
                verb=f"Your payment of {payment.currency} {payment.amount} was rejected.{(' Reason: ' + note) if note else ''}",
            )
        else:
            return Response(
                {"success": False, "error": {"message": f"Cannot {action} payment in status {payment.status}."}},
                status=400,
            )
        return Response({
            "success": True,
            "data": PaymentSerializer(payment).data,
            "message": f"Payment {action}d.",
            "meta": {},
        })


def _get_or_create_wallet(user):
    wallet, _ = UserWallet.objects.get_or_create(user=user)
    return wallet


class WalletView(APIView):
    """Get wallet balance."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet = _get_or_create_wallet(request.user)
        return Response({
            "success": True,
            "data": {
                "id": str(wallet.id),
                "balance_bdt": str(wallet.balance_bdt),
                "balance_usd": str(wallet.balance_usd),
            },
            "message": "",
            "meta": {},
        })


class WalletAddView(APIView):
    """Add money to wallet via payment (user submits, admin approves)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        currency = request.data.get("currency", "BDT").upper()
        if currency not in ("BDT", "USD"):
            return Response(
                {"success": False, "error": {"message": "Currency must be BDT or USD."}},
                status=400,
            )

        amount = request.data.get("amount")
        if not amount:
            return Response(
                {"success": False, "error": {"message": "Amount is required."}},
                status=400,
            )

        payment_method_id = request.data.get("payment_method")
        payment_method = None
        if payment_method_id:
            payment_method = get_object_or_404(PaymentMethod, pk=payment_method_id, is_active=True)

        screenshot = request.FILES.get("screenshot")

        payment = Payment.objects.create(
            user=request.user,
            payment_method=payment_method,
            amount=amount,
            currency=currency,
            transaction_id=request.data.get("transaction_id", ""),
            sender_number=request.data.get("sender_number", ""),
            screenshot=screenshot,
            status="pending",
        )

        return Response({
            "success": True,
            "data": PaymentSerializer(payment).data,
            "message": "Payment submitted. Admin will approve and money will be added to your wallet.",
            "meta": {},
        }, status=201)


class WalletHistoryView(APIView):
    """Transaction history."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet = _get_or_create_wallet(request.user)
        txns = WalletTransaction.objects.filter(wallet=wallet).select_related(
            "related_payment", "related_payment__payment_method"
        )[:50]
        data = []
        for t in txns:
            item = {
                "id": str(t.id),
                "type": t.type,
                "currency": t.currency,
                "amount": str(t.amount),
                "description": t.description,
                "status": t.status,
                "admin_note": t.admin_note,
                "created_at": t.created_at.isoformat(),
            }
            if t.related_payment:
                item["payment"] = {
                    "id": str(t.related_payment.id),
                    "method_name": t.related_payment.payment_method.name if t.related_payment.payment_method else "",
                    "transaction_id": t.related_payment.transaction_id,
                    "sender_number": t.related_payment.sender_number,
                    "screenshot": t.related_payment.screenshot.url if t.related_payment.screenshot else None,
                    "status": t.related_payment.status,
                }
            else:
                item["payment"] = None
            data.append(item)
        return Response({
            "success": True,
            "data": data,
            "message": "",
            "meta": {},
        })
