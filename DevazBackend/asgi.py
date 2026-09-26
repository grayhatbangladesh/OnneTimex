"""
ASGI config for DevazBackend project (HTTP + WebSocket).

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DevazBackend.settings")

django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from apps.MeetSoc.websocket.middleware import JWTAuthMiddlewareStack
from apps.MeetSoc.websocket.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        # HTTP → Django (REST API)
        "http": django_asgi_app,
        # WebSocket → channels (chat, notifications, calls)
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
