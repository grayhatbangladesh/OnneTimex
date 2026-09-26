from django.urls import path

from apps.MeetSoc import views as v

urlpatterns = [
    path("memories/", v.MemoriesListView.as_view(), name="memories-list"),
    path("memories/activity/", v.UserActivityView.as_view(), name="memories-activity"),
]
