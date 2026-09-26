from django.urls import path

from apps.MeetSoc.views.reports_views import AdminReportActionView, AdminReportListView, ReportCreateView, ReportListView

app_name = "reports"

urlpatterns = [
    path("reports/", ReportListView.as_view(), name="report-list"),
    path("reports/create/", ReportCreateView.as_view(), name="report-create"),
    path("reports/admin/", AdminReportListView.as_view(), name="admin-report-list"),
    path("reports/admin/<uuid:report_id>/", AdminReportActionView.as_view(), name="admin-report-action"),
]
