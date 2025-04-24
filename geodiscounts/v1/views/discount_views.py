"""
Views for managing discounts in the Discount Discovery System.

This module provides views for listing, creating, updating, and deleting discounts,
as well as searching for nearby discounts and filtering discounts by various criteria.
"""

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.conf import settings
from django.db import connection
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.gis.db.models.functions import Distance
from django.utils import timezone
from django.core.cache import cache
from typing import List, Dict, Any, Optional
import numpy as np
import logging
import json

from geodiscounts.models import Discount, Category, Retailer, WebSocketDiscountRequest
from geodiscounts.v1.serializers import DiscountSerializer
from geodiscounts.v1.serializers.discount_serializers import CategorySerializer
from geodiscounts.v1.permissions import IsDiscountOwner, IsOwnerOrReadOnly
from geodiscounts.v1.services.geo_services import GeoService
from geodiscounts.v1.utils.embedding_utils import generate_embedding
from geodiscounts.v1.utils.redis_utils import DISCOUNT_CHANNEL, redis_client

LOGGER = logging.getLogger(__name__)

class DiscountListView(generics.ListCreateAPIView):
    """View for listing and creating discounts."""
    
    serializer_class = DiscountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get filtered queryset based on query parameters."""
        queryset = Discount.objects.filter(is_active=True)
        
        # Filter by category if provided
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__name=category)
            
        # Filter by retailer if provided
        retailer = self.request.query_params.get('retailer')
        if retailer:
            queryset = queryset.filter(retailer__name=retailer)
            
        # Filter by location if provided
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')
        radius = self.request.query_params.get('radius', 10)  # Default 10km radius
        
        if lat and lng:
            point = Point(float(lng), float(lat), srid=4326)
            queryset = queryset.filter(
                location__distance_lte=(point, radius * 1000)  # Convert km to meters
            ).annotate(
                distance=Distance('location', point)
            ).order_by('distance')
            
        return queryset
        
    def perform_create(self, serializer):
        """Create a new discount with embedding generation."""
        discount = serializer.save()
        
        # Generate embedding for the discount
        embedding = generate_embedding(discount.description)
        if embedding is not None:
            discount.embedding = embedding.tolist()
            discount.save()
            
        # Publish to Redis channel
        redis_client = redis_client
        redis_client.publish(
            DISCOUNT_CHANNEL,
            json.dumps({
                'type': 'discount_created',
                'discount_id': discount.id,
                'retailer_id': discount.retailer.id,
                'category_id': discount.category.id,
                'location': {
                    'lat': discount.location.y,
                    'lng': discount.location.x
                }
            })
        )

class DiscountDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View for retrieving, updating and deleting discounts."""
    
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_update(self, serializer):
        """Update a discount with embedding generation."""
        discount = serializer.save()
        
        # Generate new embedding if description changed
        if 'description' in serializer.validated_data:
            embedding = generate_embedding(discount.description)
            if embedding is not None:
                discount.embedding = embedding.tolist()
                discount.save()
                
        # Publish to Redis channel
        redis_client = redis_client
        redis_client.publish(
            DISCOUNT_CHANNEL,
            json.dumps({
                'type': 'discount_updated',
                'discount_id': discount.id,
                'retailer_id': discount.retailer.id,
                'category_id': discount.category.id,
                'location': {
                    'lat': discount.location.y,
                    'lng': discount.location.x
                }
            })
        )
        
    def perform_destroy(self, instance):
        """Delete a discount and publish to Redis."""
        # Publish to Redis channel before deletion
        redis_client = redis_client
        redis_client.publish(
            DISCOUNT_CHANNEL,
            json.dumps({
                'type': 'discount_deleted',
                'discount_id': instance.id,
                'retailer_id': instance.retailer.id,
                'category_id': instance.category.id,
                'location': {
                    'lat': instance.location.y,
                    'lng': instance.location.x
                }
            })
        )
        instance.delete()

class CategoryListView(generics.ListCreateAPIView):
    """View for listing and creating categories."""
    
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

# class RetailerListView(generics.ListCreateAPIView):
#     """View for listing and creating retailers."""
    
#     queryset = Retailer.objects.all()
#     serializer_class = RetailerSerializer
#     permission_classes = [IsAuthenticated]

# class WebSocketDiscountRequestView(generics.CreateAPIView):
#     """View for creating WebSocket discount requests."""
    
#     serializer_class = WebSocketDiscountRequestSerializer
#     permission_classes = [IsAuthenticated]
    
#     def perform_create(self, serializer):
#         """Create a new WebSocket discount request."""
#         request = serializer.save(user=self.request.user)
        
#         # Publish to Redis channel
#         redis_client = redis_client
#         redis_client.publish(
#             DISCOUNT_CHANNEL,
#             json.dumps({
#                 'type': 'websocket_request_created',
#                 'request_id': request.request_id,
#                 'user_id': request.user.id,
#                 'location': {
#                     'lat': request.location.y,
#                     'lng': request.location.x
#                 },
#                 'radius': request.radius,
#                 'category_id': request.category.id if request.category else None
#             })
#         )

class NearbyDiscountsView(generics.ListAPIView):
    """
    View for listing discounts near the client's location.

    GET: List nearby discounts

    Location is inferred from request.client_latitude and request.client_longitude
    (set via middleware). If not available, returns an empty list.

    Optional Query Parameters:
        - radius: float (default=5.0, in kilometers)
    """
    serializer_class = DiscountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter discounts by the user's current location (via middleware)."""
        lat = getattr(self.request, "client_latitude", None)
        lon = getattr(self.request, "client_longitude", None)
        radius = float(self.request.query_params.get("radius", 5.0))

        # If location is unavailable, return no results
        if lat is None or lon is None:
            return []  # Empty queryset

        return GeoService.get_nearby_discounts(lat, lon, radius)


class SearchDiscountsView(generics.ListAPIView):
    """
    View for searching discounts.

    GET: Search discounts
    Query Parameters:
        - query: string (optional)
        - min_value: float (optional)
        - max_value: float (optional)
        - is_active: boolean (optional)
    """
    serializer_class = DiscountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter discounts based on search criteria."""
        queryset = Discount.objects.all()
        query = self.request.query_params.get('query', None)
        min_value = self.request.query_params.get('min_value', None)
        max_value = self.request.query_params.get('max_value', None)
        is_active = self.request.query_params.get('is_active', None)

        if query:
            queryset = queryset.filter(description__icontains=query)
        if min_value is not None:
            queryset = queryset.filter(discount_value__gte=float(min_value))
        if max_value is not None:
            queryset = queryset.filter(discount_value__lte=float(max_value))
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset


class CategoryView(generics.ListAPIView):
    """
    View for listing all available discount categories.

    GET: List all categories
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny] 

    @swagger_auto_schema(
        operation_description="List all available discount categories",
        responses={
            200: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                            'image': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                )
            )
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
