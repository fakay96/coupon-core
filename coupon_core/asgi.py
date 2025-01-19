"""
ASGI config for coupon_core project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from results.routing import websocket_urlpatterns

# Set the settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coupon_core.settings")

# Default ASGI application for HTTP
django_application = get_asgi_application()

# Import WebSocket URL patterns from the results app

# ProtocolTypeRouter for HTTP and WebSocket
application = ProtocolTypeRouter(
    {
        "http": django_application,
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
