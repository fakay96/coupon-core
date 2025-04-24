"""WebSocket routing configuration for geodiscounts.

This module defines the WebSocket URL patterns for the geodiscounts service.
"""

from django.urls import re_path
from geodiscounts.v1.consumers import DiscountRequestConsumer
from geodiscounts.v1.websocket_config import WEBSOCKET_CONFIG

websocket_urlpatterns = [
    re_path(
        WEBSOCKET_CONFIG['path'],
        DiscountRequestConsumer.as_asgi(),
        name='discount-requests'
    ),
] 