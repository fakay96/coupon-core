"""Service for handling discount crawler operations in the Django app.

This service manages the interaction between the Django app and the discount crawler service,
handling all Django-specific operations like database interactions and model management.
"""

from typing import Dict, Any, List, Optional
from django.contrib.gis.geos import Point
from django.utils import timezone
from django.core.cache import cache
from redis import Redis
import json
import os

from geodiscounts.models import WebSocketDiscountRequest, Discount, Category
from geodiscounts.v1.serializers.websocket_serializers import WebSocketDiscountRequestSerializer

class DiscountCrawlerService:
    """Service for managing discount crawler operations."""
    
    def __init__(self):
        """Initialize the service with Redis client."""
        self.redis_client = Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            password=os.getenv('REDIS_PASSWORD', None)
        )
    
    def create_discount_request(
        self,
        user_id: str,
        location: Point,
        radius: float,
        category_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> WebSocketDiscountRequest:
        """Create a new discount request.
        
        Args:
            user_id: ID of the user making the request
            location: Location for the discount search
            radius: Search radius in kilometers
            category_id: Optional category ID to filter by
            filters: Optional additional filters
            
        Returns:
            WebSocketDiscountRequest: The created request object
        """
        request_data = {
            'user_id': user_id,
            'location': location,
            'radius': radius,
            'category_id': category_id,
            'filters': filters or {}
        }
        
        serializer = WebSocketDiscountRequestSerializer(data=request_data)
        serializer.is_valid(raise_exception=True)
        return serializer.save()
    
    def publish_discount_request(self, request: WebSocketDiscountRequest) -> None:
        """Publish a discount request to the crawler service.
        
        Args:
            request: The discount request to publish
        """
        payload = {
            'request_id': request.request_id,
            'type': 'discount_request',
            'service': 'geodiscounts',
            'data': {
                'location': {
                    'latitude': request.location.y,
                    'longitude': request.location.x
                },
                'radius': request.radius,
                'category': request.category_id,
                'filters': request.filters,
                'callback_channel': f"discount_request_{request.request_id}"
            }
        }
        
        self.redis_client.publish(
            'discount_crawler_requests',
            json.dumps(payload)
        )
    
    def update_request_status(
        self,
        request_id: str,
        status: str,
        results: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update the status of a discount request.
        
        Args:
            request_id: ID of the request to update
            status: New status
            results: Optional results to update
        """
        request = WebSocketDiscountRequest.objects.get(request_id=request_id)
        request.status = status
        if results:
            request.results = results
        request.save()
    
    def get_discounts_by_location(
        self,
        location: Point,
        radius: float,
        category: Optional[Category] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Discount]:
        """Get discounts near a location.
        
        Args:
            location: Location to search around
            radius: Search radius in kilometers
            category: Optional category to filter by
            filters: Optional additional filters
            
        Returns:
            List[Discount]: List of matching discounts
        """
        query = Discount.objects.filter(
            is_active=True,
            expiration_date__gt=timezone.now()
        )
        
        # Apply location filter
        query = query.filter(
            location__distance_lte=(location, radius * 1000)  # Convert km to meters
        )
        
        # Apply category filter
        if category:
            query = query.filter(category=category)
            
        # Apply additional filters
        if filters:
            if 'min_discount' in filters:
                query = query.filter(discount_value__gte=filters['min_discount'])
            if 'max_discount' in filters:
                query = query.filter(discount_value__lte=filters['max_discount'])
                
        return list(query)
    
    def process_crawler_results(
        self,
        request_id: str,
        results: List[Dict[str, Any]]
    ) -> None:
        """Process results from the crawler service.
        
        Args:
            request_id: ID of the request
            results: List of discount results
        """
        # Update request status
        self.update_request_status(
            request_id,
            'completed',
            {'results': results}
        )
        
        # Cache results
        cache_key = f"discount_results:{request_id}"
        cache.set(cache_key, results, timeout=3600)  # Cache for 1 hour 