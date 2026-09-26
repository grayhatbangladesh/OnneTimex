from rest_framework import serializers
from apps.MeetSoc.models import Report


class ReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.SerializerMethodField()
    reporter_avatar = serializers.SerializerMethodField()
    reason_display = serializers.CharField(source="get_reason_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    content_type_display = serializers.CharField(source="get_content_type_display", read_only=True)

    class Meta:
        model = Report
        fields = [
            "id", "reporter", "reporter_name", "reporter_avatar",
            "content_type", "content_type_display", "content_id",
            "reason", "reason_display", "description",
            "status", "status_display",
            "reviewed_by", "admin_note",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reporter", "status", "reviewed_by", "admin_note",
            "created_at", "updated_at",
        ]

    def get_reporter_name(self, obj):
        if obj.reporter.full_name:
            return obj.reporter.full_name
        return obj.reporter.username

    def get_reporter_avatar(self, obj):
        if hasattr(obj.reporter, "profile") and obj.reporter.profile.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.reporter.profile.avatar.url)
            return obj.reporter.profile.avatar.url
        return None
