from django.urls import path

from apps.MeetChat import views as v

urlpatterns = [
    path("calls/initiate/", v.CallInitiateView.as_view(), name="calls-initiate"),
    path("calls/<uuid:call_id>/accept/", v.CallAcceptView.as_view(), name="calls-accept"),
    path("calls/<uuid:call_id>/decline/", v.CallDeclineView.as_view(), name="calls-decline"),
    path("calls/<uuid:call_id>/end/", v.CallEndView.as_view(), name="calls-end"),
    path("calls/history/", v.CallHistoryView.as_view(), name="calls-history"),
    path("calls/ice-servers/", v.IceServersView.as_view(), name="calls-ice"),
]
