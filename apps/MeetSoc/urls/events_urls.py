from django.urls import path
from apps.MeetSoc import views as v

urlpatterns = [
    path("events/", v.EventsListView.as_view(), name="events-list"),
    path("events/<str:event_id>/", v.EventsDetailView.as_view(), name="events-detail"),
]
