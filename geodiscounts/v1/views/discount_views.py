"""
Views for managing discounts in the Discount Discovery System.

This module provides views for listing, creating, updating, and deleting discounts,
as well as searching for nearby discounts and filtering discounts by various criteria.
"""

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.conf import settings
from django.db import connection
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from geodiscounts.models import Discount, Category
from geodiscounts.v1.serializers import DiscountSerializer
from geodiscounts.v1.serializers.discount_serializers import CategorySerializer
from geodiscounts.v1.permissions import IsDiscountOwner, IsOwnerOrReadOnly
from geodiscounts.v1.services.geo_services import GeoService


class DiscountListCreateView(generics.ListCreateAPIView):
    """
    View for listing all discounts and creating new ones.

    GET: List all discounts
    POST: Create a new discount
    """
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """Save the discount with the current user as owner."""
        serializer.save()


class DiscountDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    View for retrieving, updating, and deleting a specific discount.

    GET: Retrieve a discount
    PUT/PATCH: Update a discount
    DELETE: Delete a discount
    """
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer
    permission_classes = [IsAuthenticated, IsDiscountOwner]


class NearbyDiscountsView(generics.ListAPIView):
    """
    View for listing discounts near a specified location.

    GET: List nearby discounts
    Query Parameters:
        - latitude: float (required)
        - longitude: float (required)
        - radius: float (optional, default=5.0, in kilometers)
    """
    serializer_class = DiscountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter discounts by location."""
        latitude = float(self.request.query_params.get('latitude', 0))
        longitude = float(self.request.query_params.get('longitude', 0))
        radius = float(self.request.query_params.get('radius', 5.0))

        return GeoService.get_nearby_discounts(latitude, longitude, radius)


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
    permission_classes = [IsAuthenticated]

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
