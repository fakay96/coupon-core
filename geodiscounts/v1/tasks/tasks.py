"""
Celery tasks for the Geodiscount API.

This module defines background tasks for:
1. Discount expiration and cleanup
2. Notifications
3. Analytics updates
4. Location processing
5. Merchant synchronization
6. WebSocket request handling
"""

from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
import logging
from typing import Dict, Any, List, Optional
from django.contrib.gis.geos import Point
import json
from coupon_core.utils.logging import celery_logger, celery_structured_logger, log_execution

from geodiscounts.models import Discount, Location, Retailer, WebSocketDiscountRequest
from geodiscounts.v1.services.discount_crawler_service import DiscountCrawlerService
from geodiscounts.v1.utils.event_bus import EventBus

logger = logging.getLogger(__name__)
event_bus = EventBus()

@shared_task(bind=True, max_retries=3)
@log_execution(celery_logger, 'cleanup_expired_discounts')
def cleanup_expired_discounts(self) -> None:
    """
    Clean up expired discounts by deactivating them.
    
    This task:
    1. Finds all expired discounts
    2. Deactivates them
    3. Logs the cleanup action
    """
    try:
        with transaction.atomic():
            expired_discounts = Discount.objects.filter(
                expiration_date__lt=timezone.now(),
                is_active=True
            )
            
            count = expired_discounts.update(is_active=False)
            celery_structured_logger.info(
                celery_logger,
                f"Deactivated {count} expired discounts",
                "cleanup_expired_discounts",
                {'count': count}
            )
            
    except Exception as e:
        celery_structured_logger.error(
            celery_logger,
            "Error cleaning up expired discounts",
            "cleanup_expired_discounts",
            e
        )
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3)
def notify_discount_expiration(self) -> None:
    """
    Send notifications for expired discounts.
    
    This task:
    1. Finds recently expired discounts
    2. Sends notifications to relevant users
    3. Logs notification status
    """
    try:
        expired_discounts = Discount.objects.filter(
            expiration_date__lt=timezone.now(),
            is_active=False,
            notification_sent=False
        )
        
        for discount in expired_discounts:
            send_notification(
                discount.retailer.contact_info,
                f"Discount {discount.discount_code} has expired"
            )
            
            discount.notification_sent = True
            discount.save()
            
    except Exception as e:
        logger.error(f"Error sending expiration notifications: {str(e)}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3)
def update_discount_status(self) -> None:
    """
    Update status of discounts based on expiration.
    
    This task:
    1. Updates status of active discounts
    2. Handles expired discounts
    3. Updates analytics
    """
    try:
        now = timezone.now()
        
        # Update active discounts
        active_discounts = Discount.objects.filter(
            expiration_date__gt=now,
            is_active=True
        )
        active_discounts.update(status="active")
        
        # Update expired discounts
        expired_discounts = Discount.objects.filter(
            expiration_date__lt=now,
            is_active=True
        )
        expired_discounts.update(status="expired", is_active=False)
        
    except Exception as e:
        logger.error(f"Error updating discount status: {str(e)}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3)
def process_location_updates(self) -> None:
    """
    Process location updates and validations.
    
    This task:
    1. Updates location timestamps
    2. Validates location data
    3. Handles invalid locations
    """
    try:
        locations = Location.objects.filter(is_valid=True)
        
        for location in locations:
            location.last_updated = timezone.now()
            location.save()
            
    except Exception as e:
        logger.error(f"Error processing location updates: {str(e)}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3)
def cleanup_invalid_locations(self) -> None:
    """
    Clean up invalid locations.
    
    This task:
    1. Finds invalid locations
    2. Removes them from the system
    3. Logs cleanup actions
    """
    try:
        with transaction.atomic():
            invalid_locations = Location.objects.filter(is_valid=False)
            count = invalid_locations.count()
            invalid_locations.delete()
            logger.info(f"Cleaned up {count} invalid locations")
            
    except Exception as e:
        logger.error(f"Error cleaning up invalid locations: {str(e)}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3)
def sync_merchant_discounts(self, merchant_id: int) -> None:
    """
    Synchronize discounts with merchant API.
    
    Args:
        merchant_id: ID of the merchant to sync
        
    This task:
    1. Fetches discounts from merchant API
    2. Updates local discount records
    3. Handles synchronization errors
    """
    try:
        merchant = Retailer.objects.get(id=merchant_id)
        
        # Get discounts from merchant API
        api_discounts = sync_with_merchant_api(merchant_id)
        
        with transaction.atomic():
            for api_discount in api_discounts:
                Discount.objects.update_or_create(
                    retailer=merchant,
                    discount_code=api_discount['code'],
                    defaults={
                        'discount_value': api_discount['value'],
                        'expiration_date': api_discount['expires_at']
                    }
                )
                
    except Exception as e:
        logger.error(f"Error syncing merchant discounts: {str(e)}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3)
def cleanup_merchant_discounts(self, merchant_id: int) -> None:
    """
    Clean up merchant discounts.
    
    Args:
        merchant_id: ID of the merchant to clean up
        
    This task:
    1. Removes expired merchant discounts
    2. Updates merchant analytics
    3. Logs cleanup actions
    """
    try:
        with transaction.atomic():
            merchant = Retailer.objects.get(id=merchant_id)
            discounts = Discount.objects.filter(retailer=merchant)
            count = discounts.count()
            discounts.delete()
            logger.info(f"Cleaned up {count} discounts for merchant {merchant_id}")
            
    except Exception as e:
        logger.error(f"Error cleaning up merchant discounts: {str(e)}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3)
def process_discount_updates(self) -> None:
    """
    Process discount updates in a chain.
    
    This task:
    1. Chains multiple discount-related tasks
    2. Ensures proper order of execution
    3. Handles task dependencies
    """
    from celery import chain
    
    try:
        # Create task chain
        task_chain = chain(
            cleanup_expired_discounts.s(),
            notify_discount_expiration.s(),
            update_discount_status.s()
        )
        
        # Execute chain
        task_chain()
        
    except Exception as e:
        logger.error(f"Error processing discount updates: {str(e)}")
        raise self.retry(exc=e)

def send_notification(recipient: str, message: str) -> None:
    """
    Send a notification email.
    
    Args:
        recipient: Email address of the recipient
        message: Message content
    """
    try:
        send_mail(
            subject="Discount Notification",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=True
        )
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")

def sync_with_merchant_api(merchant_id: int) -> List[Dict[str, Any]]:
    """
    Sync with merchant API.
    
    Args:
        merchant_id: ID of the merchant
        
    Returns:
        List of discount data from the merchant API
    """
    # This is a placeholder for actual API integration
    # In a real implementation, this would make API calls to the merchant's system
    return []

@shared_task(bind=True, max_retries=3)
@log_execution(celery_logger, 'publish_discount_request')
def publish_discount_request(
    self,
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
        request_id: UUID of the WebSocketDiscountRequest
        user_id: ID of the user making the request
        latitude: Latitude of the search location
        longitude: Longitude of the search location
        radius: Search radius in meters
        category_id: Optional category ID to filter results
        conversation_history: Optional list of conversation messages
        
    Raises:
        WebSocketDiscountRequest.DoesNotExist: If request not found
        Exception: For other errors during publishing
    """
    try:
        # Create Point object for location
        location = Point(longitude, latitude)
        
        # Get request object
        request = WebSocketDiscountRequest.objects.get(request_id=request_id)
        
        # Update request status
        request.status = "processing"
        request.save()
        
        # Prepare event payload
        event = {
            "request_id": str(request_id),
            "user_id": user_id,
            "location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "radius": radius,
            "category_id": category_id,
            "conversation_history": conversation_history or []
        }
        
        # Publish event to crawler service
        event_bus.publish("discount_requests", event)
        celery_structured_logger.info(
            celery_logger,
            "Published discount request to crawler service",
            "publish_discount_request",
            {
                'request_id': request_id,
                'user_id': user_id,
                'location': {'latitude': latitude, 'longitude': longitude},
                'radius': radius
            }
        )
        
    except WebSocketDiscountRequest.DoesNotExist:
        celery_structured_logger.error(
            celery_logger,
            "WebSocketDiscountRequest not found",
            "publish_discount_request",
            None,
            {'request_id': request_id}
        )
        raise
    except Exception as e:
        celery_structured_logger.error(
            celery_logger,
            "Error publishing discount request",
            "publish_discount_request",
            e,
            {
                'request_id': request_id,
                'user_id': user_id,
                'location': {'latitude': latitude, 'longitude': longitude},
                'radius': radius
            }
        )
        raise self.retry(exc=e)

@shared_task
@log_execution(celery_logger, 'handle_websocket_url_callback')
def handle_websocket_url_callback(request_id: str, websocket_url: str) -> None:
    """
    Handle callback from crawler service with WebSocket URL.
    
    Args:
        request_id: UUID of the WebSocketDiscountRequest
        websocket_url: URL for WebSocket connection
        
    Raises:
        WebSocketDiscountRequest.DoesNotExist: If request not found
    """
    try:
        request = WebSocketDiscountRequest.objects.get(request_id=request_id)
        request.websocket_url = websocket_url
        request.status = "ready"
        request.save()
        celery_structured_logger.info(
            celery_logger,
            "Updated WebSocket URL for request",
            "handle_websocket_url_callback",
            {
                'request_id': request_id,
                'status': 'ready'
            }
        )
    except WebSocketDiscountRequest.DoesNotExist:
        celery_structured_logger.error(
            celery_logger,
            "WebSocketDiscountRequest not found",
            "handle_websocket_url_callback",
            None,
            {'request_id': request_id}
        )
        raise
    except Exception as e:
        celery_structured_logger.error(
            celery_logger,
            "Error updating WebSocket URL",
            "handle_websocket_url_callback",
            e,
            {
                'request_id': request_id,
                'websocket_url': websocket_url
            }
        )
        raise

@shared_task
@log_execution(celery_logger, 'handle_discount_results')
def handle_discount_results(request_id: str, results: List[Dict[str, Any]]) -> None:
    """
    Handle discount results from the crawler service.
    
    Args:
        request_id: UUID of the WebSocketDiscountRequest
        results: List of discount results
        
    Raises:
        WebSocketDiscountRequest.DoesNotExist: If request not found
    """
    try:
        request = WebSocketDiscountRequest.objects.get(request_id=request_id)
        request.results = results
        request.status = "completed"
        request.save()
        celery_structured_logger.info(
            celery_logger,
            "Updated results for request",
            "handle_discount_results",
            {
                'request_id': request_id,
                'status': 'completed',
                'result_count': len(results)
            }
        )
    except WebSocketDiscountRequest.DoesNotExist:
        celery_structured_logger.error(
            celery_logger,
            "WebSocketDiscountRequest not found",
            "handle_discount_results",
            None,
            {'request_id': request_id}
        )
        raise
    except Exception as e:
        celery_structured_logger.error(
            celery_logger,
            "Error updating results",
            "handle_discount_results",
            e,
            {
                'request_id': request_id,
                'result_count': len(results)
            }
        )
        raise

# Subscribe to websocket_url callbacks
def websocket_url_callback(event: Dict[str, Any]) -> None:
    """Handle websocket_url callback events."""
    request_id = event.get("request_id")
    websocket_url = event.get("websocket_url")
    if request_id and websocket_url:
        handle_websocket_url_callback.delay(request_id, websocket_url)

# Subscribe to discount results
def discount_results_callback(event: Dict[str, Any]) -> None:
    """Handle discount results events."""
    request_id = event.get("request_id")
    results = event.get("results")
    if request_id and results:
        handle_discount_results.delay(request_id, results)

# Subscribe to both callbacks
event_bus.subscribe("websocket_url_callbacks", websocket_url_callback)
event_bus.subscribe("discount_results", discount_results_callback) 