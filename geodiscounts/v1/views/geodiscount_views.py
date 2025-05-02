"""
API Views for the Discount Discovery System.

This module contains API endpoints for:
- Fetching all available discount categories (cached for 30 minutes).
- Fetching all available discounts.
- Finding nearby discounts based on user IP.
- Searching for discounts using vector embeddings.

Each endpoint is documented and uses Django Rest Framework (DRF) for serialization.
Caching is enabled where applicable to optimize performance.

Author: Your Name
Date: YYYY-MM-DD
"""

import re
import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from django.core.cache import cache
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_202_ACCEPTED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_504_GATEWAY_TIMEOUT,
)
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny

from geodiscounts.models import Discount, Category, WebSocketDiscountRequest
from geodiscounts.v1.serializers.discount_serializers import DiscountSerializer, CategorySerializer
from geodiscounts.v1.utils.ip_geolocation import (
    get_location_from_ip,
    validate_max_distance,
)
from geodiscounts.v1.utils.vector_utils import PostgreSQLVectorClient
from geodiscounts.v1.tasks import publish_discount_request
from coupon_core.utils.logging import geo_logger, geo_structured_logger, log_execution

# drf-yasg imports for OpenAPI documentation
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from rest_framework.request import Request
from django.utils import timezone

# Greeting patterns
GREETING_PATTERNS = re.compile(r'^(hi|hello|hey|greetings)$', re.IGNORECASE)
MAX_DISTANCE_PARAM=10
client = PostgreSQLVectorClient()


class CategoryView(APIView):
    """
    API endpoint to retrieve all available discount categories.

    - Categories are cached for 30 minutes to optimize performance and reduce database load.
    - Uses atomic caching to reduce redundant queries.
    """
    # Removed serializer_class to prevent automatic inclusion in the Swagger spec.
    permission_classes = [AllowAny]  # Public access

    @swagger_auto_schema(
        operation_description="Fetches all discount categories. Caches results for 30 minutes.",
        responses={
            HTTP_200_OK: openapi.Response(
                description="Success.",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "name": openapi.Schema(type=openapi.TYPE_STRING),
                            "image": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                        },
                    ),
                ),
            ),
            HTTP_404_NOT_FOUND: openapi.Response(
                description="No categories found.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal server error.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(type=openapi.TYPE_STRING),
                        "details": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    @log_execution(geo_logger, 'category_list')
    def get(self, request) -> Response:
        """Get all available discount categories."""
        cache_key = "categories_list"
        try:
            categories = cache.get(cache_key)
            if categories is None:
                category_queryset = Category.objects.only("id", "name", "image")
                if not category_queryset.exists():
                    geo_structured_logger.info(
                        geo_logger,
                        "No categories found",
                        "category_list",
                        {'user_id': getattr(request.user, 'id', None)}
                    )
                    return Response(
                        {"message": "No categories available."},
                        status=HTTP_404_NOT_FOUND,
                    )
                serializer = CategorySerializer(category_queryset, many=True)
                categories = serializer.data
                cache.set(cache_key, categories, timeout=1800)
                
            geo_structured_logger.info(
                geo_logger,
                "Categories retrieved successfully",
                "category_list",
                {
                    'user_id': getattr(request.user, 'id', None),
                    'count': len(categories)
                }
            )
            return Response(categories, status=HTTP_200_OK)
            
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error retrieving categories",
                "category_list",
                e,
                {'user_id': getattr(request.user, 'id', None)}
            )
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DiscountListView(APIView):
    """
    API endpoint to fetch all available discounts.
    
    This view provides a list of all active discounts in the system, with optional
    filtering and sorting capabilities. The response includes detailed information
    about each discount, including retailer details, discount value, and location.
    """
    
    @swagger_auto_schema(
        operation_description="Returns a list of all discounts in the system.",
        responses={
            HTTP_200_OK: openapi.Response(
                description="Success.",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "retailer": openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "name": openapi.Schema(type=openapi.TYPE_STRING),
                                },
                            ),
                            "description": openapi.Schema(type=openapi.TYPE_STRING),
                            "discount_code": openapi.Schema(type=openapi.TYPE_STRING),
                            "discount_value": openapi.Schema(type=openapi.TYPE_NUMBER),
                            "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            "expiration_date": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                            "location": openapi.Schema(type=openapi.TYPE_STRING),
                            "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                            "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                        },
                    ),
                ),
            ),
            HTTP_404_NOT_FOUND: openapi.Response(
                description="No discounts found.",
                examples={"application/json": {"message": "No discounts available."}},
            ),
            HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal server error.",
                examples={
                    "application/json": {
                        "error": "An unexpected error occurred.",
                        "details": "Detailed error message...",
                    }
                },
            ),
        },
    )
    @log_execution(geo_logger, 'discount_list')
    def get(self, request: Request) -> Response:
        """
        Retrieve a list of all available discounts.
        
        Args:
            request: The HTTP request
            
        Returns:
            Response containing a list of discounts or an error message
            
        Raises:
            None: All exceptions are caught and returned as error responses
        """
        try:
            discounts = Discount.objects.all()
            if not discounts.exists():
                geo_structured_logger.info(
                    geo_logger,
                    "No discounts found",
                    "discount_list",
                    {'user_id': request.user.id if request.user.is_authenticated else None}
                )
                return Response(
                    {"message": "No discounts available."},
                    status=HTTP_404_NOT_FOUND,
                )
                
            serializer = DiscountSerializer(discounts, many=True)
            geo_structured_logger.info(
                geo_logger,
                "Retrieved discounts successfully",
                "discount_list",
                {
                    'user_id': request.user.id if request.user.is_authenticated else None,
                    'count': len(serializer.data)
                }
            )
            return Response(serializer.data, status=HTTP_200_OK)
            
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error retrieving discounts",
                "discount_list",
                e,
                {'user_id': request.user.id if request.user.is_authenticated else None}
            )
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=HTTP_500_INTERNAL_SERVER_ERROR,
            )


class NearbyDiscountsView(APIView):
    """
    View for retrieving discounts near the user's location.
    
    This view finds discounts within a specified radius of the user's location,
    which is determined from their IP address. The results are sorted by distance
    and can be filtered by a maximum distance parameter.
    """
    
    @swagger_auto_schema(
        operation_description="Retrieve discounts near the user's location (based on IP address) with an optional max_distance filter.",
        manual_parameters=[MAX_DISTANCE_PARAM],
        responses={
            HTTP_200_OK: openapi.Response(
                description="Success.",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "retailer": openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "name": openapi.Schema(type=openapi.TYPE_STRING),
                                },
                            ),
                            "description": openapi.Schema(type=openapi.TYPE_STRING),
                            "discount_code": openapi.Schema(type=openapi.TYPE_STRING),
                            "discount_value": openapi.Schema(type=openapi.TYPE_NUMBER),
                            "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            "expiration_date": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                            "location": openapi.Schema(type=openapi.TYPE_STRING),
                            "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                            "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                            "distance": openapi.Schema(type=openapi.TYPE_NUMBER, description="Distance in meters"),
                        },
                    ),
                ),
            ),
            HTTP_400_BAD_REQUEST: openapi.Response(
                description="Validation error.",
                examples={"application/json": {"error": "Detailed validation error message."}},
            ),
            HTTP_404_NOT_FOUND: openapi.Response(
                description="No discounts found.",
                examples={"application/json": {"message": "No discounts found near your location."}},
            ),
            HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal server error.",
                examples={
                    "application/json": {
                        "error": "An unexpected error occurred.",
                        "details": "Detailed error message...",
                    }
                },
            ),
        },
    )
    @log_execution(geo_logger, 'nearby_discounts')
    def get(self, request: Request) -> Response:
        """
        Retrieve discounts near the user's location.
        
        Args:
            request: The HTTP request containing optional max_distance parameter
            
        Returns:
            Response containing a list of nearby discounts or an error message
            
        Raises:
            ValidationError: If location cannot be determined or max_distance is invalid
        """
        try:
            ip = getattr(request, "client_ip", None)
            if not ip:
                geo_structured_logger.warning(
                    geo_logger,
                    "Client IP not available",
                    "nearby_discounts",
                    {'user_id': request.user.id if request.user.is_authenticated else None}
                )
                raise ValidationError("Client IP address is not available.")

            location = get_location_from_ip(ip)
            if not location:
                geo_structured_logger.warning(
                    geo_logger,
                    "Location not found from IP",
                    "nearby_discounts",
                    {
                        'user_id': request.user.id if request.user.is_authenticated else None,
                        'ip': ip
                    }
                )
                raise ValidationError("Unable to determine location from IP address.")

            lat, lon = location["latitude"], location["longitude"]
            user_location = Point(lon, lat, srid=4326)

            max_distance = request.GET.get("max_distance")
            if max_distance:
                try:
                    max_distance = validate_max_distance(max_distance)
                except ValueError as e:
                    geo_structured_logger.warning(
                        geo_logger,
                        "Invalid max_distance parameter",
                        "nearby_discounts",
                        {
                            'user_id': request.user.id if request.user.is_authenticated else None,
                            'max_distance': max_distance
                        }
                    )
                    raise ValidationError(str(e))

            discounts = Discount.objects.annotate(
                distance=Distance("location", user_location)
            )
            if max_distance:
                discounts = discounts.filter(distance__lte=max_distance * 1000)
            discounts = discounts.order_by("distance")[:10]
            
            if not discounts.exists():
                geo_structured_logger.info(
                    geo_logger,
                    "No nearby discounts found",
                    "nearby_discounts",
                    {
                        'user_id': request.user.id if request.user.is_authenticated else None,
                        'location': {'latitude': lat, 'longitude': lon},
                        'max_distance': max_distance
                    }
                )
                return Response(
                    {"message": "No discounts found near your location."},
                    status=HTTP_404_NOT_FOUND,
                )

            serializer = DiscountSerializer(discounts, many=True)
            geo_structured_logger.info(
                geo_logger,
                "Retrieved nearby discounts successfully",
                "nearby_discounts",
                {
                    'user_id': request.user.id if request.user.is_authenticated else None,
                    'location': {'latitude': lat, 'longitude': lon},
                    'max_distance': max_distance,
                    'count': len(serializer.data)
                }
            )
            return Response(serializer.data, status=HTTP_200_OK)
            
        except ValidationError as ve:
            geo_structured_logger.warning(
                geo_logger,
                "Validation error in nearby discounts",
                "nearby_discounts",
                {
                    'user_id': request.user.id if request.user.is_authenticated else None,
                    'error': str(ve)
                }
            )
            return Response({"error": str(ve)}, status=HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error retrieving nearby discounts",
                "nearby_discounts",
                e,
                {'user_id': request.user.id if request.user.is_authenticated else None}
            )
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SearchDiscountsView(APIView):
    """
    View for searching discounts based on location and query.
    
    This view handles discount search requests by:
    1. Validating the search query and location parameters
    2. Creating a WebSocketDiscountRequest record
    3. Dispatching the request to the crawler service
    4. Polling for results or returning a WebSocket URL
    
    The view supports both immediate results and real-time updates via WebSocket.
    """
    
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Search for discounts based on location and query",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'query': openapi.Schema(type=openapi.TYPE_STRING, description='Search query'),
                'radius': openapi.Schema(type=openapi.TYPE_NUMBER, description='Search radius in meters (default: 5000)')
            }
        ),
        responses={
            HTTP_200_OK: openapi.Response(
                description="Search results or WebSocket URL",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'results': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                        'websocket_url': openapi.Schema(type=openapi.TYPE_STRING),
                        'type': openapi.Schema(type=openapi.TYPE_STRING, enum=['results', 'websocket', 'greeting']),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            HTTP_400_BAD_REQUEST: openapi.Response(
                description="Invalid request parameters",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            HTTP_504_GATEWAY_TIMEOUT: openapi.Response(
                description="Request timeout",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    @log_execution(geo_logger, 'discount_search')
    def post(self, request: Request) -> Response:
        """
        Handle discount search request.
        
        Args:
            request: The HTTP request containing search parameters
            
        Returns:
            Response with either:
            - WebSocket URL for real-time updates
            - Immediate results if available
            - Error message if request failed
            
        Raises:
            None: All exceptions are caught and returned as error responses
        """
        # Validate query
        query = request.data.get('query', '').strip()
        if not query:
            geo_structured_logger.warning(
                geo_logger,
                "Empty search query",
                "discount_search",
                {'user_id': request.user.id}
            )
            return Response(
                {"error": "Search query is required"},
                status=HTTP_400_BAD_REQUEST
            )
            
        # Check for simple greetings
        greeting_pattern = r'^(hi|hello|hey|greetings|good\s(morning|afternoon|evening))$'
        if re.match(greeting_pattern, query.lower()):
            geo_structured_logger.info(
                geo_logger,
                "Greeting detected",
                "discount_search",
                {'user_id': request.user.id, 'query': query}
            )
            return Response({
                "message": "Hello! How can I help you find discounts today?",
                "type": "greeting"
            })
            
        # Validate location
        try:
            latitude = float(request.client_latitude)
            longitude = float(request.client_longitude)
            radius = float(request.data.get('radius', 5000))  # Default 5km
        except (TypeError, ValueError) as e:
            geo_structured_logger.error(
                geo_logger,
                "Invalid location parameters",
                "discount_search",
                e,
                {
                    'user_id': request.user.id,
                    'latitude': request.data.get('latitude'),
                    'longitude': request.data.get('longitude'),
                    'radius': request.data.get('radius')
                }
            )
            return Response(
                {"error": "Invalid location parameters"},
                status=HTTP_400_BAD_REQUEST
            )
            
        # Create conversation history
        conversation_history: List[Dict[str, Any]] = [{
            "role": "user",
            "content": query,
            "timestamp": timezone.now().isoformat()
        }]
        
        # Create request record and dispatch task
        try:
            with transaction.atomic():
                request_obj = WebSocketDiscountRequest.objects.create(
                    user=request.user,
                    location=Point(longitude, latitude),
                    radius=radius,
                    status="pending",
                    conversation_history=conversation_history
                )
                
                geo_structured_logger.info(
                    geo_logger,
                    "Created discount request",
                    "discount_search",
                    {
                        'user_id': request.user.id,
                        'request_id': str(request_obj.request_id),
                        'query': query,
                        'location': {'latitude': latitude, 'longitude': longitude},
                        'radius': radius
                    }
                )
                
                # Dispatch task
                publish_discount_request.delay(
                    request_id=str(request_obj.request_id),
                    user_id=request.user.id,
                    latitude=latitude,
                    longitude=longitude,
                    radius=radius,
                    conversation_history=conversation_history
                )
                
                # Poll for results or WebSocket URL
                start_time = time.time()
                while time.time() - start_time < 10:  # 10 second timeout
                    request_obj.refresh_from_db()
                    
                    if request_obj.status == "completed":
                        geo_structured_logger.info(
                            geo_logger,
                            "Search completed successfully",
                            "discount_search",
                            {
                                'user_id': request.user.id,
                                'request_id': str(request_obj.request_id),
                                'result_count': len(request_obj.results) if request_obj.results else 0
                            }
                        )
                        return Response({
                            "results": request_obj.results,
                            "type": "results"
                        })
                    elif request_obj.status == "ready" and request_obj.websocket_url:
                        geo_structured_logger.info(
                            geo_logger,
                            "WebSocket URL ready",
                            "discount_search",
                            {
                                'user_id': request.user.id,
                                'request_id': str(request_obj.request_id)
                            }
                        )
                        return Response({
                            "websocket_url": request_obj.websocket_url,
                            "type": "websocket"
                        })
                    elif request_obj.status == "failed":
                        geo_structured_logger.error(
                            geo_logger,
                            "Search request failed",
                            "discount_search",
                            None,
                            {
                                'user_id': request.user.id,
                                'request_id': str(request_obj.request_id)
                            }
                        )
                        return Response(
                            {"error": "Failed to process request"},
                            status=HTTP_500_INTERNAL_SERVER_ERROR
                        )
                        
                    time.sleep(0.5)  # Poll every 500ms
                    
                geo_structured_logger.warning(
                    geo_logger,
                    "Search request timeout",
                    "discount_search",
                    {
                        'user_id': request.user.id,
                        'request_id': str(request_obj.request_id)
                    }
                )
                return Response(
                    {"error": "Request timeout"},
                    status=HTTP_504_GATEWAY_TIMEOUT
                )
                
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error processing discount request",
                "discount_search",
                e,
                {
                    'user_id': request.user.id,
                    'query': query,
                    'location': {'latitude': latitude, 'longitude': longitude},
                    'radius': radius
                }
            )
            return Response(
                {"error": "Internal server error"},
                status=HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    @swagger_auto_schema(
        operation_description="Get results for a specific discount search request",
        responses={
            HTTP_200_OK: openapi.Response(
                description="Request status and results",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'results': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                        'websocket_url': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            HTTP_404_NOT_FOUND: openapi.Response(
                description="Request not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    @log_execution(geo_logger, 'discount_search_status')
    def get(self, request: Request, request_id: str) -> Response:
        """
        Get results for a specific request.
        
        Args:
            request: The HTTP request
            request_id: UUID of the WebSocketDiscountRequest
            
        Returns:
            Response with request status and results if available
            
        Raises:
            None: All exceptions are caught and returned as error responses
        """
        try:
            request_obj = WebSocketDiscountRequest.objects.get(
                request_id=request_id,
                user=request.user
            )
            
            geo_structured_logger.info(
                geo_logger,
                "Retrieved request status",
                "discount_search_status",
                {
                    'user_id': request.user.id,
                    'request_id': request_id,
                    'status': request_obj.status
                }
            )
            
            return Response({
                "status": request_obj.status,
                "results": request_obj.results if request_obj.status == "completed" else None,
                "websocket_url": request_obj.websocket_url if request_obj.status == "ready" else None
            })
            
        except WebSocketDiscountRequest.DoesNotExist:
            geo_structured_logger.warning(
                geo_logger,
                "Request not found",
                "discount_search_status",
                {
                    'user_id': request.user.id,
                    'request_id': request_id
                }
            )
            return Response(
                {"error": "Request not found"},
                status=HTTP_404_NOT_FOUND
            )
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error retrieving request results",
                "discount_search_status",
                e,
                {
                    'user_id': request.user.id,
                    'request_id': request_id
                }
            )
            return Response(
                {"error": "Internal server error"},
                status=HTTP_500_INTERNAL_SERVER_ERROR
            )
