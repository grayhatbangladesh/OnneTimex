from django.urls import path
from apps.MeetSoc import views as v

urlpatterns = [
    path("gaming/", v.SidebarView.as_view(), name="gaming"),
]
