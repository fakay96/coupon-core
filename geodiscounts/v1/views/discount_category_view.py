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

from geodiscounts.models import Discount, Category, Retailer
from geodiscounts.v1.serializers import DiscountSerializer
from geodiscounts.v1.serializers.discount_serializers import CategorySerializer
from geodiscounts.v1.services.geo_services import GeoService
from geodiscounts.v1.utils.redis_utils import DISCOUNT_CHANNEL, redis_client

LOGGER = logging.getLogger(__name__)


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
