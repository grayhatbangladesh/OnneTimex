from django.urls import path
from apps.MeetSoc import views as v

urlpatterns = [
    path("sidebar/", v.SidebarView.as_view(), name="sidebar"),
]
