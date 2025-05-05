"""Celery tasks for the geodiscounts app."""

import json
from typing import Dict, Any, Optional
from celery import shared_task
from django.contrib.gis.geos import Point
from django.utils import timezone

from geodiscounts.models import WebSocketDiscountRequest
from geodiscounts.v1.services.discount_crawler_service import DiscountCrawlerService

@shared_task
def publish_discount_request(
    request_id: str,
    user_id: int,
    latitude: float,
    longitude: float,
    radius: float,
    category_id: Optional[int] = None,
    conversation_history: Optional[list] = None
) -> None:
    """
    Publish a discount request to the crawler service.
    
    Args:
        request_id: UUID of the request
        user_id: ID of the user making the request
        latitude: Latitude of the search location
        longitude: Longitude of the search location
        radius: Search radius in kilometers
        category_id: Optional category ID to filter by
        conversation_history: Optional conversation history
    """
    try:
        # Create Point object
        location = Point(longitude, latitude)
        
        # Get the request object
        request = WebSocketDiscountRequest.objects.get(request_id=request_id)
        
        # Update request status to processing
        request.status = "processing"
        request.save()
        
        # Initialize crawler service
        crawler_service = DiscountCrawlerService()
        
        # Publish request to crawler service
        crawler_service.publish_discount_request(request)
        
    except WebSocketDiscountRequest.DoesNotExist:
        # Log error but don't raise to prevent task retry
        print(f"Request {request_id} not found")
    except Exception as e:
        # Log error but don't raise to prevent task retry
        print(f"Error publishing request {request_id}: {str(e)}") 