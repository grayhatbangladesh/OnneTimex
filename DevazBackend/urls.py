from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("account/", include("apps.accounts.urls")),
    path("meetsoc/", include("apps.MeetSoc.urls.main")),
    path("meetchat/", include("apps.MeetChat.urls.main")),
]
