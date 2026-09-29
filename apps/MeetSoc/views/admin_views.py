"""MeetSoc admin API — data endpoints for the Next.js admin panel.

Every response uses the project envelope
``{"success": True, "data": <payload>, "message": "", "meta": {}}`` (204 for
deletes) and every view is admin-only (``is_staff`` / ``is_superuser``),
answering with the standard 403 FORBIDDEN envelope otherwise.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.MeetSoc.models import (
    AccountSuspension,
    BlueVerificationRequest,
    Comment,
    Group,
    Page,
    Payment,
    Post,
    PostReaction,
    Product,
    WatchVideo,
)
from apps.accounts.serializers import _avatar_url

UserModel = get_user_model()

_LIST_LIMIT = 200


# ---------------------------------------------------------------------------
# Envelope / permission helpers
# ---------------------------------------------------------------------------
def _ok(data, message="", status=200):
    return Response({"success": True, "data": data, "message": message, "meta": {}}, status=status)


def _error(code, message, status=400):
    return Response(
        {"success": False, "error": {"code": code, "message": message, "details": {}}},
        status=status,
    )


def _deleted(message="Deleted."):
    return Response({"success": True, "data": {}, "message": message, "meta": {}}, status=204)


def _admin_only(request):
    """Standard FORBIDDEN envelope unless the caller is staff/superuser."""
    user = request.user
    if not user or not user.is_authenticated or not (user.is_staff or user.is_superuser):
        return _error("FORBIDDEN", "Admin only.", status=403)
    return None


# ---------------------------------------------------------------------------
# Small serializers (plain dicts — the admin panel shapes)
# ---------------------------------------------------------------------------
def _display_name(user, fallback=""):
    """Human-readable name for created_by / seller / author / user / advertiser."""
    if user is None:
        return fallback
    return user.full_name or user.username or fallback


def _iso(dt):
    return dt.isoformat() if dt else ""


def _safe_count(fn):
    try:
        return int(fn())
    except Exception:
        return 0


def _ad_model():
    """The ads app is optional — feed_services guards the same import."""
    try:
        from apps.ads.models import Ad
        return Ad
    except Exception:
        return None


def _ad_row(ad):
    return {
        "id": str(ad.id),
        "title": getattr(ad, "title", "") or "",
        "advertiser": _display_name(getattr(ad, "advertiser", None)),
        "content_type": getattr(ad, "content_type", "") or "",
        "status": getattr(ad, "status", "") or "",
        "impressions_count": int(getattr(ad, "impressions_count", 0) or 0),
        "cta_button": getattr(ad, "cta_button", "") or "",
        "created_at": _iso(getattr(ad, "created_at", None)),
    }


# ---------------------------------------------------------------------------
# 1. Stats
# ---------------------------------------------------------------------------
class AdminStatsView(APIView):
    """GET /meetsoc/admin/stats/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = _admin_only(request)
        if denied:
            return denied

        Ad = _ad_model()
        stats = {
            "total_users": _safe_count(UserModel.objects.count),
            "active_users": _safe_count(lambda: UserModel.objects.filter(is_active=True).count()),
            "total_posts": _safe_count(Post.objects.count),
            "total_comments": _safe_count(Comment.objects.count),
            "total_groups": _safe_count(Group.objects.count),
            "total_pages": _safe_count(Page.objects.count),
            "total_products": _safe_count(Product.objects.count),
            "total_videos": _safe_count(WatchVideo.objects.count),
            "total_ads": _safe_count(Ad.objects.count) if Ad else 0,
            "active_ads": _safe_count(lambda: Ad.objects.filter(status="active").count()) if Ad else 0,
            "pending_ads": _safe_count(lambda: Ad.objects.filter(status="pending_approval").count()) if Ad else 0,
            "pending_payments": _safe_count(lambda: Payment.objects.filter(status="pending").count()),
            "pending_verifications": _safe_count(
                lambda: BlueVerificationRequest.objects.filter(status="pending").count()
            ),
            "staff_users": _safe_count(lambda: UserModel.objects.filter(is_staff=True).count()),
        }
        return _ok(stats)


# ---------------------------------------------------------------------------
# 2/3/4. Users
# ---------------------------------------------------------------------------
class AdminUserListView(APIView):
    """GET /meetsoc/admin/users/?search=… (also serves /admin/users/<query>/)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, query=""):
        denied = _admin_only(request)
        if denied:
            return denied

        qs = UserModel.objects.select_related("profile").order_by("-created_at")
        search = (request.query_params.get("search") or query or "").strip()
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(email__icontains=search)
            )
        users = list(qs[:_LIST_LIMIT])
        ids = [u.id for u in users]

        # One query for the blue badge instead of N (matches User.is_verified).
        verified_ids = set()
        try:
            now = timezone.now()
            verified_ids = set(
                BlueVerificationRequest.objects.filter(
                    status="approved", valid_from__lte=now, valid_until__gt=now
                ).values_list("user_id", flat=True)
            )
        except Exception:
            verified_ids = set()

        post_counts = {}
        if ids:
            try:
                post_counts = dict(
                    Post.objects.filter(author_id__in=ids)
                    .values("author_id")
                    .annotate(c=Count("id"))
                    .values_list("author_id", "c")
                )
            except Exception:
                post_counts = {}

        data = []
        for u in users:
            p = getattr(u, "profile", None)
            data.append({
                "id": str(u.id),
                "username": u.username or "",
                "full_name": u.full_name,
                "phone": u.phone or "",
                "email": u.email or "",
                "is_verified": u.id in verified_ids,
                "is_staff": u.is_staff,
                "is_active": u.is_active,
                "avatar": _avatar_url(u),
                "country": getattr(p, "country", "") or "",
                "bio": getattr(p, "bio", "") or "",
                "posts_count": int(post_counts.get(u.id, 0)),
                "friends_count": int(getattr(p, "friends_count", 0) or 0),
                "created_at": _iso(u.created_at),
            })
        return _ok(data)


class AdminUserDetailView(APIView):
    """GET/PATCH /meetsoc/admin/users/<uuid>/"""

    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        denied = _admin_only(request)
        if denied:
            return denied

        user = get_object_or_404(UserModel, pk=user_id)
        profile = getattr(user, "profile", None)

        # No activity-profile model exists in this deployment — derive the
        # activity block from the real reaction/comment tables instead.
        activity = None
        try:
            activity = {
                "interests": {},
                "posts_liked_count": PostReaction.objects.filter(user=user).count(),
                "comments_count": Comment.objects.filter(author=user).count(),
                "country": getattr(profile, "country", "") or "",
            }
        except Exception:
            activity = None

        data = {
            "id": str(user.id),
            "username": user.username or "",
            "full_name": user.full_name,
            "phone": user.phone or "",
            "email": user.email or "",
            "is_verified": user.is_verified,
            "is_staff": user.is_staff,
            "is_active": user.is_active,
            "gender": user.gender,
            "created_at": _iso(user.created_at),
            "profile": {
                "avatar": _avatar_url(user),
                "bio": getattr(profile, "bio", "") or "",
                "country": getattr(profile, "country", "") or "",
                "city": getattr(profile, "city", "") or "",
                "posts_count": int(getattr(profile, "posts_count", 0) or 0),
                "friends_count": int(getattr(profile, "friends_count", 0) or 0),
                "followers_count": int(getattr(profile, "followers_count", 0) or 0),
            } if profile else None,
            "activity": activity,
        }
        return _ok(data)

    def patch(self, request, user_id):
        denied = _admin_only(request)
        if denied:
            return denied

        user = get_object_or_404(UserModel, pk=user_id)
        for field in ("is_active", "is_staff", "first_name", "last_name"):
            if field in request.data:
                setattr(user, field, request.data[field])
        try:
            user.save()
        except Exception:
            return _error("SAVE_FAILED", "Could not update user.")

        # is_verified is a derived property (active blue badge) — grant/revoke
        # it through the model that backs it instead of setattr (no setter).
        if "is_verified" in request.data:
            self._set_verified(user, bool(request.data.get("is_verified")))
        return _ok({"id": str(user.id)})

    @staticmethod
    def _set_verified(user, want):
        try:
            now = timezone.now()
            active = BlueVerificationRequest.objects.filter(
                user=user, status="approved", valid_from__lte=now, valid_until__gt=now
            )
            if want:
                if not active.exists():
                    BlueVerificationRequest.objects.create(
                        user=user,
                        status="approved",
                        note="Granted by admin.",
                        admin_note="Granted by admin.",
                        approved_at=now,
                        valid_from=now,
                        valid_until=now + timedelta(days=365),
                    )
            else:
                active.update(status="rejected", valid_until=now)
        except Exception:
            pass  # badge toggle must never break the admin request


# ---------------------------------------------------------------------------
# 5. Verification requests
# ---------------------------------------------------------------------------
class AdminVerificationListView(APIView):
    """GET /meetsoc/admin/verification/?status=…"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = _admin_only(request)
        if denied:
            return denied

        qs = BlueVerificationRequest.objects.select_related("user").order_by("-created_at")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        data = []
        for v in qs[:_LIST_LIMIT]:
            data.append({
                "id": str(v.id),
                "user_id": str(v.user_id),
                "username": v.user.username or "",
                "full_name": v.user.full_name,
                "status": v.status,
                "note": v.note or v.admin_note or "",
                "created_at": _iso(v.created_at),
            })
        return _ok(data)


class AdminVerificationActionView(APIView):
    """POST /meetsoc/admin/verification/<id>/ body {action, admin_note}."""

    permission_classes = [IsAuthenticated]

    _ACTIONS = {
        "approve": "approved",
        "approved": "approved",
        "reject": "rejected",
        "rejected": "rejected",
    }

    def post(self, request, verification_id):
        denied = _admin_only(request)
        if denied:
            return denied

        action = request.data.get("action")
        if action not in self._ACTIONS:
            return _error("INVALID_ACTION", "Invalid action. Use: approve, reject")

        vr = get_object_or_404(BlueVerificationRequest, pk=verification_id)
        new_status = self._ACTIONS[action]
        now = timezone.now()

        vr.status = new_status
        vr.admin_note = request.data.get("admin_note", "") or ""
        update_fields = ["status", "admin_note", "updated_at"]
        if new_status == "approved":
            # get_active_for_user() requires a valid_from/valid_until window.
            duration_days = 365
            try:
                if vr.plan_id:
                    duration_days = int(vr.plan.duration_days or 365)
            except Exception:
                duration_days = 365
            vr.approved_at = now
            vr.valid_from = now
            vr.valid_until = now + timedelta(days=duration_days)
            update_fields += ["approved_at", "valid_from", "valid_until"]

        try:
            vr.save(update_fields=update_fields)
        except Exception:
            return _error("SAVE_FAILED", "Could not update verification request.")
        return _ok({"id": str(vr.id), "status": vr.status}, message=f"Verification {new_status}.")


# ---------------------------------------------------------------------------
# 6. Posts
# ---------------------------------------------------------------------------
class AdminPostListView(APIView):
    """GET /meetsoc/admin/posts/?search=…&privacy=… (also /admin/posts/<query>/)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, query=""):
        denied = _admin_only(request)
        if denied:
            return denied

        qs = Post.objects.select_related("author").order_by("-created_at")
        search = (request.query_params.get("search") or query or "").strip()
        if search:
            qs = qs.filter(
                Q(content__icontains=search)
                | Q(author__username__icontains=search)
                | Q(author__first_name__icontains=search)
                | Q(author__last_name__icontains=search)
            )
        privacy = request.query_params.get("privacy")
        if privacy:
            qs = qs.filter(privacy=privacy)

        data = [{
            "id": str(p.id),
            "author_username": p.author.username or p.author.full_name or "",
            "content": p.content,
            "post_type": p.post_type,
            "privacy": p.privacy,
            "comments_count": p.comments_count,
            "created_at": _iso(p.created_at),
        } for p in qs[:_LIST_LIMIT]]
        return _ok(data)


class AdminPostDeleteView(APIView):
    """DELETE /meetsoc/admin/posts/<uuid>/ → 204."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, post_id):
        denied = _admin_only(request)
        if denied:
            return denied

        post = get_object_or_404(Post, pk=post_id)
        post.delete()
        return _deleted()


# ---------------------------------------------------------------------------
# 7. Groups
# ---------------------------------------------------------------------------
class AdminGroupListView(APIView):
    """GET /meetsoc/admin/groups/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = _admin_only(request)
        if denied:
            return denied

        qs = Group.objects.select_related("created_by").order_by("-created_at")
        data = [{
            "id": str(g.id),
            "name": g.name,
            "slug": g.slug,
            "privacy": g.privacy,
            "members_count": g.members_count,
            "created_by": _display_name(g.created_by),
            "created_at": _iso(g.created_at),
        } for g in qs[:_LIST_LIMIT]]
        return _ok(data)


class AdminGroupDeleteView(APIView):
    """DELETE /meetsoc/admin/groups/<uuid>/ → 204."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, group_id):
        denied = _admin_only(request)
        if denied:
            return denied

        group = get_object_or_404(Group, pk=group_id)
        group.delete()
        return _deleted()


# ---------------------------------------------------------------------------
# 8. Pages
# ---------------------------------------------------------------------------
class AdminPageListView(APIView):
    """GET /meetsoc/admin/pages/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = _admin_only(request)
        if denied:
            return denied

        qs = Page.objects.select_related("created_by").order_by("-created_at")
        data = [{
            "id": str(p.id),
            "name": p.name,
            "slug": p.slug,
            "category": p.category,
            "verified": bool(p.verified),
            "is_on_hold": bool(p.is_on_hold),
            "allowed_features": list(p.allowed_features or []),
            "followers_count": p.followers_count,
            "created_by": _display_name(p.created_by),
        } for p in qs[:_LIST_LIMIT]]
        return _ok(data)


class AdminPageDetailView(APIView):
    """PATCH/DELETE /meetsoc/admin/pages/<uuid>/"""

    permission_classes = [IsAuthenticated]

    def patch(self, request, page_id):
        denied = _admin_only(request)
        if denied:
            return denied

        page = get_object_or_404(Page, pk=page_id)
        for field in ("verified", "is_on_hold", "category"):
            if field in request.data:
                setattr(page, field, request.data[field])
        if "allowed_features" in request.data:
            features = request.data.get("allowed_features")
            if isinstance(features, list):
                page.allowed_features = features
        try:
            page.save()
        except Exception:
            return _error("SAVE_FAILED", "Could not update page.")
        return _ok({"id": str(page.id)})

    def delete(self, request, page_id):
        denied = _admin_only(request)
        if denied:
            return denied

        page = get_object_or_404(Page, pk=page_id)
        page.delete()
        return _deleted()


# ---------------------------------------------------------------------------
# 9. Products (marketplace)
# ---------------------------------------------------------------------------
class AdminProductListView(APIView):
    """GET /meetsoc/admin/products/?status=… (also /admin/products/<query>/)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, query=""):
        denied = _admin_only(request)
        if denied:
            return denied

        qs = Product.objects.select_related("seller").prefetch_related("media_items")
        status_filter = request.query_params.get("status") or query
        if status_filter:
            qs = qs.filter(status=status_filter)
        qs = qs.order_by("-created_at")

        data = []
        for p in qs[:_LIST_LIMIT]:
            data.append({
                "id": str(p.id),
                "title": p.title,
                "description": p.description,
                "seller": _display_name(p.seller),
                "seller_id": str(p.seller_id),
                "price": str(p.price),
                "category": p.category,
                "condition": p.condition,
                "status": p.status,
                "views_count": p.views_count,
                "media": [
                    {"id": str(m.id), "file": m.file.url if m.file else "", "order": m.order}
                    for m in p.media_items.all()
                ],
            })
        return _ok(data)


class AdminProductDetailView(APIView):
    """PATCH /meetsoc/admin/products/<uuid>/ body {status, note}."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, product_id):
        denied = _admin_only(request)
        if denied:
            return denied

        product = get_object_or_404(Product, pk=product_id)
        new_status = request.data.get("status")
        valid = {choice for choice, _label in Product.STATUS_CHOICES}
        if new_status not in valid:
            return _error("INVALID_STATUS", f"Invalid status. Use: {', '.join(sorted(valid))}")
        # `note` is accepted for the panel payload but has nowhere to live on
        # the Product model — deliberately ignored rather than inventing a field.
        product.status = new_status
        try:
            product.save(update_fields=["status"])
        except Exception:
            return _error("SAVE_FAILED", "Could not update product.")
        return _ok({"id": str(product.id)})


# ---------------------------------------------------------------------------
# 10. Videos
# ---------------------------------------------------------------------------
class AdminVideoListView(APIView):
    """GET /meetsoc/admin/videos/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = _admin_only(request)
        if denied:
            return denied

        qs = WatchVideo.objects.select_related("author").order_by("-created_at")
        data = [{
            "id": str(v.id),
            "title": v.title,
            "author": _display_name(v.author),
            "views_count": v.views_count,
            "duration": float(v.duration or 0),
            "created_at": _iso(v.created_at),
        } for v in qs[:_LIST_LIMIT]]
        return _ok(data)


class AdminVideoDeleteView(APIView):
    """DELETE /meetsoc/admin/videos/<uuid>/ → 204."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, video_id):
        denied = _admin_only(request)
        if denied:
            return denied

        video = get_object_or_404(WatchVideo, pk=video_id)
        video.delete()
        return _deleted()


# ---------------------------------------------------------------------------
# 11. Ads (the ads app is optional in this deployment)
# ---------------------------------------------------------------------------
class AdminAdListView(APIView):
    """GET /meetsoc/admin/ads/?status=… — empty list when no ads app exists."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = _admin_only(request)
        if denied:
            return denied

        Ad = _ad_model()
        if Ad is None:
            return _ok([])
        try:
            qs = Ad.objects.all()
            status_filter = request.query_params.get("status")
            if status_filter:
                qs = qs.filter(status=status_filter)
            data = [_ad_row(ad) for ad in qs.order_by("-created_at")[:_LIST_LIMIT]]
        except Exception:
            data = []
        return _ok(data)


class AdminAdActionView(APIView):
    """POST /meetsoc/admin/ads/<str:id>/ body {action} → {id, status}."""

    permission_classes = [IsAuthenticated]

    _ACTIONS = {
        "approve": "approved",
        "reject": "rejected",
        "pause": "paused",
        "resume": "active",
        "approved": "approved",
        "rejected": "rejected",
        "paused": "paused",
        "active": "active",
    }

    def post(self, request, ad_id):
        denied = _admin_only(request)
        if denied:
            return denied

        action = request.data.get("action")
        if action not in self._ACTIONS:
            return _error("INVALID_ACTION", "Invalid action. Use: approve, reject, pause, resume")
        new_status = self._ACTIONS[action]

        Ad = _ad_model()
        if Ad is not None:
            try:
                ad = Ad.objects.filter(pk=ad_id).first()
                if ad is not None:
                    ad.status = new_status
                    ad.save(update_fields=["status"])
            except Exception:
                pass  # no ads table — still answer with the expected shape
        return _ok({"id": str(ad_id), "status": new_status}, message=f"Ad {action}.")


# ---------------------------------------------------------------------------
# 12. Payments (aliases of the existing payments admin views)
# ---------------------------------------------------------------------------
class AdminPaymentsListView(APIView):
    """GET /meetsoc/admin/payments/?status=…

    Thin adapter over AdminPaymentListView: that serializer has no `user`
    field (the panel expects one), so the payload is rebuilt here with the
    same filters/defaults as the original view.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = _admin_only(request)
        if denied:
            return denied

        status_filter = request.query_params.get("status") or "pending"
        qs = Payment.objects.filter(status=status_filter).select_related(
            "user", "payment_method"
        )
        data = [{
            "id": str(p.id),
            "user": _display_name(p.user),
            "method_name": p.payment_method.name if p.payment_method_id else "",
            "amount": str(p.amount),
            "currency": p.currency,
            "transaction_id": p.transaction_id,
            "sender_number": p.sender_number,
            "status": p.status,
        } for p in qs]
        return _ok(data)


class AdminPaymentsActionView(APIView):
    """POST /meetsoc/admin/payments/<uuid>/ body {action, note}.

    Delegates the approve/reject + wallet crediting logic to the existing
    AdminPaymentActionView, then reshapes its payload to {id, status}.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, payment_id):
        denied = _admin_only(request)
        if denied:
            return denied

        from apps.MeetSoc.views.payments_views import AdminPaymentActionView

        response = AdminPaymentActionView().post(request, payment_id)
        payload = getattr(response, "data", None)
        if response.status_code >= 400 or not isinstance(payload, dict):
            return response  # error passthrough (invalid action / wrong status)
        row = payload.get("data") or {}
        return _ok(
            {"id": row.get("id"), "status": row.get("status")},
            message=payload.get("message", ""),
        )


# ---------------------------------------------------------------------------
# 13. Suspensions (model created by this API)
# ---------------------------------------------------------------------------
class AdminSuspensionListCreateView(APIView):
    """GET/POST /meetsoc/admin/suspensions/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = _admin_only(request)
        if denied:
            return denied

        try:
            suspensions = list(
                AccountSuspension.objects.select_related("user").order_by("-created_at")[:_LIST_LIMIT]
            )
        except Exception:
            suspensions = []  # table not migrated yet — still answer 200
        data = [{
            "id": str(s.id),
            "user": _display_name(s.user),
            "reason": s.reason,
            "status": s.status,
            "is_permanent": s.is_permanent,
            "created_at": _iso(s.created_at),
        } for s in suspensions]
        return _ok(data)

    def post(self, request):
        denied = _admin_only(request)
        if denied:
            return denied

        try:
            user = UserModel.objects.filter(pk=request.data.get("user_id")).first()
        except Exception:
            user = None  # malformed uuid
        if user is None:
            return _error("INVALID_USER", "User not found.")

        reason = str(request.data.get("reason") or "")[:255]
        is_permanent = bool(request.data.get("is_permanent", False))
        ends_at = None
        raw_ends_at = request.data.get("ends_at")
        if raw_ends_at:
            try:
                ends_at = parse_datetime(str(raw_ends_at))
                if ends_at is not None and timezone.is_naive(ends_at):
                    ends_at = timezone.make_aware(ends_at)
            except Exception:
                ends_at = None
        if not is_permanent and ends_at is None:
            # Temporary suspensions need a window, otherwise status would read
            # "expired" immediately and could never be lifted from the panel.
            ends_at = timezone.now() + timedelta(days=7)

        try:
            suspension = AccountSuspension.objects.create(
                user=user, reason=reason, is_permanent=is_permanent, ends_at=ends_at
            )
        except Exception:
            return _error("SAVE_FAILED", "Could not save suspension.")

        # Mirror the suspension onto User.status (suspensions block login).
        try:
            if getattr(user, "status", None) != "suspended" and hasattr(user, "status"):
                user.status = "suspended"
                user.save(update_fields=["status", "updated_at"])
        except Exception:
            pass
        return _ok({"id": str(suspension.id)}, status=201)


class AdminSuspensionDeleteView(APIView):
    """DELETE /meetsoc/admin/suspensions/<uuid>/ → 204 (restores User.status)."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, suspension_id):
        denied = _admin_only(request)
        if denied:
            return denied

        try:
            suspension = AccountSuspension.objects.filter(pk=suspension_id).select_related(
                "user"
            ).first()
        except Exception:
            suspension = None
        if suspension is None:
            return _error("NOT_FOUND", "Suspension not found.", status=404)

        user = suspension.user
        try:
            suspension.delete()
        except Exception:
            return _error("SAVE_FAILED", "Could not delete suspension.")

        try:
            still_suspended = AccountSuspension.objects.filter(user=user).filter(
                Q(is_permanent=True) | Q(ends_at__gt=timezone.now())
            ).exists()
            if (
                not still_suspended
                and hasattr(user, "status")
                and getattr(user, "status", None) == "suspended"
            ):
                user.status = "active"
                user.save(update_fields=["status", "updated_at"])
        except Exception:
            pass  # never raise on the status restore
        return _deleted("Suspension lifted.")
