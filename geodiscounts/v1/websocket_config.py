"""WebSocket configuration for geodiscounts service.

This module provides configuration settings for WebSocket connections.
"""

import os
from typing import Dict, Any

# WebSocket settings
WEBSOCKET_CONFIG: Dict[str, Any] = {
    'domain': os.getenv('WEBSOCKET_DOMAIN', 'localhost'),
    'protocol': os.getenv('WEBSOCKET_PROTOCOL', 'ws'),
    'port': int(os.getenv('WEBSOCKET_PORT', 8000)),
    'path': os.getenv('WEBSOCKET_PATH', '/ws/discount-requests/'),
    'allowed_origins': os.getenv('WEBSOCKET_ALLOWED_ORIGINS', '').split(',') if os.getenv('WEBSOCKET_ALLOWED_ORIGINS') else [],
    'heartbeat_interval': int(os.getenv('WEBSOCKET_HEARTBEAT_INTERVAL', 30)),
    'max_message_size': int(os.getenv('WEBSOCKET_MAX_MESSAGE_SIZE', 1024 * 1024)),  # 1MB default
}

# Redis settings for WebSocket
REDIS_CONFIG: Dict[str, Any] = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', 6379)),
    'db': int(os.getenv('REDIS_DB', 0)),
    'password': os.getenv('REDIS_PASSWORD', None),
    'channel_prefix': os.getenv('REDIS_CHANNEL_PREFIX', 'discount_request_'),
    'request_channel': os.getenv('REDIS_REQUEST_CHANNEL', 'discount_crawler_requests'),
} 