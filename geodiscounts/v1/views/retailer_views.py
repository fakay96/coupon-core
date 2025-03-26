"""
Views for managing retailers in the Discount Discovery System.

This module provides views for:
1. Listing and creating retailers
2. Retrieving, updating, and deleting specific retailers
3. Finding retailers near a specified location
4. Viewing retailer analytics
"""

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.core.exceptions import ValidationError
from django.db import models

from geodiscounts.models import Retailer
from geodiscounts.v1.serializers.retailer_serializers import (
    RetailerSerializer, 
    RetailerAnalyticsSerializer,
    NearbyRetailersSerializer
)
from geodiscounts.v1.permissions import IsOwnerOrReadOnly


class RetailerListCreateView(generics.ListCreateAPIView):
    """
    View for listing all retailers and creating new ones.

    GET: List all retailers
    POST: Create a new retailer
    """
    queryset = Retailer.objects.all()
    serializer_class = RetailerSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """Save the retailer with the current user as owner."""
        serializer.save(owner=self.request.user)


class RetailerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    View for retrieving, updating, and deleting a specific retailer.

    GET: Retrieve a retailer
    PUT/PATCH: Update a retailer
    DELETE: Delete a retailer
    """
    queryset = Retailer.objects.all()
    serializer_class = RetailerSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]


class NearbyRetailersView(generics.ListAPIView):
    """
    View for listing retailers near a specified location.

    GET: List nearby retailers
    Query Parameters:
        - latitude: float (required)
        - longitude: float (required)
        - radius: float (optional, default=5.0, in kilometers)
    """
    serializer_class = NearbyRetailersSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter retailers by location with comprehensive validation.
        """
        try:
            # Validate and convert location parameters
            latitude = float(self.request.query_params.get('latitude'))
            longitude = float(self.request.query_params.get('longitude'))
            radius = float(self.request.query_params.get('radius', 5.0))
            
            # Validate location values
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise ValidationError("Invalid latitude or longitude values")
            
            # Create a geographical point
            search_point = Point(longitude, latitude, srid=4326)
            
            # Find nearby retailers using GeoDjango
            return Retailer.objects.filter(
                location__distance_lte=(search_point, D(km=radius))
            )
        
        except (TypeError, ValueError, ValidationError):
            # Return an empty queryset if parameters are invalid
            return Retailer.objects.none()

    def list(self, request, *args, **kwargs):
        """
        Override list method to provide custom error handling.
        """
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            return Response(
                {'error': 'Invalid location parameters'},
                status=status.HTTP_400_BAD_REQUEST
            )


class RetailerAnalyticsView(generics.RetrieveAPIView):
    """
    View for retrieving analytics data for a specific retailer.
    
    Provides comprehensive metrics about discounts and performance.
    """
    queryset = Retailer.objects.all()
    serializer_class = RetailerAnalyticsSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve and calculate analytics for a specific retailer.
        """
        try:
            retailer = self.get_object()
            
            # Calculate analytics
            analytics = {
                'total_discounts': retailer.discounts.count(),
                'active_discounts': retailer.discounts.filter(is_active=True).count(),
                'expired_discounts': retailer.discounts.filter(is_active=False).count(),
                'avg_discount_value': retailer.discounts.aggregate(
                    avg_value=models.Avg('discount_value')
                )['avg_value'] or 0.0,
                'total_shared_discounts': retailer.discounts.filter(
                    shared_discounts__isnull=False
                ).distinct().count(),
                'active_shared_discounts': retailer.discounts.filter(
                    shared_discounts__status='active'
                ).distinct().count(),
            }
            
            serializer = self.get_serializer(analytics)
            return Response(serializer.data)
        
        except Retailer.DoesNotExist:
            return Response(
                {'error': 'Retailer not found'},
                status=status.HTTP_404_NOT_FOUND
            )