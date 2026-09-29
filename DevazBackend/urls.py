from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("account/", include("apps.accounts.urls")),
    path("meetsoc/", include("apps.MeetSoc.urls.main")),
    path("meetchat/", include("apps.MeetChat.urls.main")),
    # Uploaded media must be servable in DEBUG *and* in production (the
    # production disk is ephemeral, but files written during the dyno's lifetime
    # still have to resolve). django.views.static.serve blocks path traversal.
    path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
]

# Redundant in DEBUG (the explicit route above already matches first) but keeps
# the standard Django debug behaviour obvious.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
