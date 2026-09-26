from django.urls import path
from apps.MeetSoc import views as v

urlpatterns = [
    path("calls/initiate/", v.CallsInitiateView.as_view(), name="calls-initiate"),
    path("calls/<str:call_id>/accept/", v.CallsAcceptView.as_view(), name="calls-accept"),
    path("calls/<str:call_id>/decline/", v.CallsDeclineView.as_view(), name="calls-decline"),
    path("calls/<str:call_id>/end/", v.CallsEndView.as_view(), name="calls-end"),
    path("calls/history/", v.CallsHistoryView.as_view(), name="calls-history"),
    path("calls/ice-servers/", v.CallsIceServersView.as_view(), name="calls-ice-servers"),
]
