"""WebSocket consumers for handling real-time discount requests.

This module provides WebSocket consumers that handle client connections
and coordinate with the discount crawler service through Redis.
"""

import json
import uuid
import os
from typing import Dict, Any
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.gis.geos import Point

from geodiscounts.v1.services.discount_crawler_service import DiscountCrawlerService

class DiscountRequestConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for handling discount requests."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.crawler_service = DiscountCrawlerService()
        self.request_id = None
        self.channel_name = None
        self.websocket_domain = os.getenv('WEBSOCKET_DOMAIN', 'localhost')
        self.websocket_protocol = os.getenv('WEBSOCKET_PROTOCOL', 'ws')
    
    async def connect(self):
        """Handle WebSocket connection."""
        # Validate origin if needed
        origin = self.scope.get('headers', {}).get(b'origin', b'').decode()
        if origin and not origin.startswith(f"{self.websocket_protocol}://{self.websocket_domain}"):
            await self.close(code=4001)
            return
            
        self.request_id = str(uuid.uuid4())
        self.channel_name = f"discount_request_{self.request_id}"
        
        # Accept the connection
        await self.accept()
        
        # Subscribe to Redis channel for this request
        await self.channel_layer.group_add(
            self.channel_name,
            self.channel_name
        )
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if self.channel_name:
            await self.channel_layer.group_discard(
                self.channel_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            request_type = data.get('type')
            
            if request_type == 'discount_request':
                await self.handle_discount_request(data)
            else:
                await self.send_error('Invalid request type')
                
        except json.JSONDecodeError:
            await self.send_error('Invalid JSON format')
        except Exception as e:
            await self.send_error(str(e))
    
    async def handle_discount_request(self, data: Dict[str, Any]) -> None:
        """Process a discount request and forward it to crawler agents.
        
        Args:
            data: The request data containing location and filters
        """
        try:
            # Validate request data
            location = data.get('location')
            if not location:
                await self.send_error('Location is required')
                return
            
            # Create Point object
            point = Point(
                float(location.get('longitude', 0)),
                float(location.get('latitude', 0))
            )
            
            # Create discount request
            request = await database_sync_to_async(self.crawler_service.create_discount_request)(
                user_id=self.scope['user'].id,
                location=point,
                radius=float(data.get('radius', 10)),
                category_id=data.get('category_id'),
                filters=data.get('filters', {})
            )
            
            # Publish request to crawler service
            await database_sync_to_async(self.crawler_service.publish_discount_request)(request)
            
            # Send acknowledgment to client
            await self.send(text_data=json.dumps({
                'type': 'request_received',
                'request_id': self.request_id,
                'message': 'Request received and being processed'
            }))
            
        except Exception as e:
            await self.send_error(str(e))
    
    async def send_error(self, message: str) -> None:
        """Send error message to client.
        
        Args:
            message: The error message to send
        """
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
    
    async def crawler_update(self, event):
        """Handle updates from crawler agents.
        
        Args:
            event: The event data from crawler agents
        """
        data = event['data']
        update_type = data.get('type')
        
        if update_type == 'processing_started':
            await database_sync_to_async(self.crawler_service.update_request_status)(
                self.request_id,
                'processing'
            )
        elif update_type == 'results_ready':
            await database_sync_to_async(self.crawler_service.process_crawler_results)(
                self.request_id,
                data.get('data', {})
            )
        elif update_type == 'error':
            await database_sync_to_async(self.crawler_service.update_request_status)(
                self.request_id,
                'failed'
            )
        
        await self.send(text_data=json.dumps(data)) 