from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.MeetSoc.models import Report
from apps.MeetSoc.serializers import ReportSerializer


class ReportCreateView(APIView):
    """File a report against content (post, comment, profile, etc.)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        content_type = request.data.get("content_type")
        content_id = request.data.get("content_id")
        reason = request.data.get("reason")
        description = request.data.get("description", "")

        if not content_type or not content_id or not reason:
            return Response(
                {"success": False, "error": {"message": "content_type, content_id, and reason are required."}},
                status=400,
            )

        # Check if user already reported this content
        existing = Report.objects.filter(
            reporter=request.user,
            content_type=content_type,
            content_id=content_id,
        ).exclude(status="dismissed").exists()

        if existing:
            return Response(
                {"success": False, "error": {"message": "You have already reported this content."}},
                status=400,
            )

        report = Report.objects.create(
            reporter=request.user,
            content_type=content_type,
            content_id=content_id,
            reason=reason,
            description=description,
        )

        return Response({
            "success": True,
            "data": ReportSerializer(report, context={"request": request}).data,
            "message": "Report submitted. Our team will review it.",
            "meta": {},
        }, status=201)


class ReportListView(APIView):
    """List reports filed by the current user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Report.objects.filter(reporter=request.user).select_related("reporter", "reporter__profile", "reviewed_by")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        return Response({
            "success": True,
            "data": ReportSerializer(qs, many=True, context={"request": request}).data,
            "message": "",
            "meta": {},
        })


class AdminReportListView(APIView):
    """Admin: list all reports with filters and stats."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response(
                {"success": False, "error": {"message": "Admin only."}},
                status=403,
            )

        qs = Report.objects.all().select_related("reporter", "reporter__profile", "reviewed_by")

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        reason_filter = request.query_params.get("reason")
        if reason_filter:
            qs = qs.filter(reason=reason_filter)

        content_type_filter = request.query_params.get("content_type")
        if content_type_filter:
            qs = qs.filter(content_type=content_type_filter)

        # Stats
        stats = {
            "total": Report.objects.count(),
            "pending": Report.objects.filter(status="pending").count(),
            "reviewed": Report.objects.filter(status="reviewed").count(),
            "resolved": Report.objects.filter(status="resolved").count(),
            "dismissed": Report.objects.filter(status="dismissed").count(),
            "by_reason": dict(Report.objects.values_list("reason").annotate(count=Count("id")).values_list("reason", "count")),
        }

        return Response({
            "success": True,
            "data": {
                "reports": ReportSerializer(qs, many=True, context={"request": request}).data,
                "stats": stats,
            },
            "message": "",
            "meta": {},
        })


class AdminReportActionView(APIView):
    """Admin: resolve, hold, or delete reported content."""

    permission_classes = [IsAuthenticated]

    def post(self, request, report_id):
        if not request.user.is_staff:
            return Response(
                {"success": False, "error": {"message": "Admin only."}},
                status=403,
            )

        report = get_object_or_404(Report, pk=report_id)
        action = request.data.get("action")
        admin_note = request.data.get("admin_note", "")

        if action not in ("resolve", "hold", "delete"):
            return Response(
                {"success": False, "error": {"message": "Invalid action. Use: resolve, hold, delete"}},
                status=400,
            )

        report.reviewed_by = request.user
        report.admin_note = admin_note

        if action == "resolve":
            report.status = "resolved"
            report.save(update_fields=["status", "reviewed_by", "admin_note", "updated_at"])
            self._notify(reporter_id=report.reporter_id, report=report, action="resolved", admin_note=admin_note)

        elif action == "hold":
            report.status = "held"
            report.save(update_fields=["status", "reviewed_by", "admin_note", "updated_at"])
            self._set_on_hold(report, True)
            owner_id = self._get_content_owner_id(report)
            self._notify(reporter_id=report.reporter_id, report=report, action="held", admin_note=admin_note)
            if owner_id and owner_id != report.reporter_id:
                self._notify(reporter_id=owner_id, report=report, action="held", admin_note=admin_note)

        elif action == "delete":
            report.status = "resolved"
            report.save(update_fields=["status", "reviewed_by", "admin_note", "updated_at"])
            owner_id = self._get_content_owner_id(report)
            self._delete_content(report)
            self._notify(reporter_id=report.reporter_id, report=report, action="deleted", admin_note=admin_note)
            if owner_id and owner_id != report.reporter_id:
                self._notify(reporter_id=owner_id, report=report, action="deleted", admin_note=admin_note)

        return Response({
            "success": True,
            "data": ReportSerializer(report, context={"request": request}).data,
            "message": f"Report {action}d.",
            "meta": {},
        })

    def _get_content_owner_id(self, report):
        """Get the user ID of the content owner."""
        ct = report.content_type
        cid = report.content_id
        try:
            if ct == "post":
                from apps.MeetSoc.models import Post
                obj = Post.objects.filter(id=cid).first()
                return obj.author_id if obj else None
            elif ct == "comment":
                from apps.MeetSoc.models import Comment
                obj = Comment.objects.filter(id=cid).first()
                return obj.author_id if obj else None
            elif ct == "page":
                from apps.MeetSoc.models import Page
                obj = Page.objects.filter(id=cid).first()
                return obj.created_by_id if obj else None
            elif ct == "group":
                from apps.MeetSoc.models import Group
                obj = Group.objects.filter(id=cid).first()
                return obj.created_by_id if obj else None
            elif ct == "product":
                from apps.MeetSoc.models import Product
                obj = Product.objects.filter(id=cid).first()
                return obj.seller_id if obj else None
            elif ct == "video":
                from apps.MeetSoc.models import WatchVideo
                obj = WatchVideo.objects.filter(id=cid).first()
                return obj.author_id if obj else None
        except Exception:
            pass
        return None

    def _set_on_hold(self, report, hold):
        """Set is_on_hold on the reported content."""
        ct = report.content_type
        cid = report.content_id
        try:
            if ct == "post":
                from apps.MeetSoc.models import Post
                Post.objects.filter(id=cid).update(is_on_hold=hold)
            elif ct == "comment":
                from apps.MeetSoc.models import Comment
                Comment.objects.filter(id=cid).update(is_on_hold=hold)
            elif ct == "page":
                from apps.MeetSoc.models import Page
                Page.objects.filter(id=cid).update(is_on_hold=hold)
            elif ct == "group":
                from apps.MeetSoc.models import Group
                Group.objects.filter(id=cid).update(is_on_hold=hold)
            elif ct == "product":
                from apps.MeetSoc.models import Product
                Product.objects.filter(id=cid).update(is_on_hold=hold)
            elif ct == "video":
                from apps.MeetSoc.models import WatchVideo
                WatchVideo.objects.filter(id=cid).update(is_on_hold=hold)
            elif ct == "message":
                from apps.MeetChat.models import Message
                Message.objects.filter(id=cid).update(is_on_hold=hold)
        except Exception:
            pass

    def _delete_content(self, report):
        """Delete the reported content."""
        ct = report.content_type
        cid = report.content_id
        try:
            if ct == "post":
                from apps.MeetSoc.models import Post
                Post.objects.filter(id=cid).delete()
            elif ct == "comment":
                from apps.MeetSoc.models import Comment
                Comment.objects.filter(id=cid).delete()
            elif ct == "page":
                from apps.MeetSoc.models import Page
                Page.objects.filter(id=cid).delete()
            elif ct == "group":
                from apps.MeetSoc.models import Group
                Group.objects.filter(id=cid).delete()
            elif ct == "product":
                from apps.MeetSoc.models import Product
                Product.objects.filter(id=cid).delete()
            elif ct == "video":
                from apps.MeetSoc.models import WatchVideo
                WatchVideo.objects.filter(id=cid).delete()
            elif ct == "message":
                from apps.MeetChat.models import Message
                Message.objects.filter(id=cid).update(is_deleted=True)
        except Exception:
            pass

    def _notify(self, reporter_id, report, action, admin_note):
        """Send notification to a user about the report action."""
        try:
            from apps.MeetSoc.tasks.notification_tasks import notify
            note_text = f"\nAdmin message: {admin_note}" if admin_note else ""
            verb = f"Your report on {report.get_content_type_display()} has been {action}.{note_text}"
            notify(
                recipient_id=reporter_id,
                actor_id=report.reviewed_by_id,
                notification_type="report_update",
                verb=verb,
                data={
                    "report_id": str(report.id),
                    "action": action,
                    "content_type": report.content_type,
                    "content_id": str(report.content_id),
                },
                target_type="report",
                target_id=report.id,
            )
        except Exception:
            try:
                from apps.MeetSoc.models import Notification
                note_text = f"\nAdmin message: {admin_note}" if admin_note else ""
                verb = f"Your report on {report.get_content_type_display()} has been {action}.{note_text}"
                Notification.objects.create(
                    recipient_id=reporter_id,
                    actor_id=report.reviewed_by_id,
                    notification_type="report_update",
                    verb=verb,
                )
            except Exception:
                pass
