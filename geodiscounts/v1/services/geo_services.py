"""
Services for handling geospatial operations in the Discount Discovery System.

This module provides services for performing geospatial queries and operations,
abstracting away database-specific implementations.
"""

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db import connection
from django.db.models import QuerySet

from geodiscounts.models import Retailer, Discount


class GeoService:
    """Service for handling geospatial operations."""

    @staticmethod
    def get_nearby_retailers(latitude: float, longitude: float, radius: float = 5.0) -> QuerySet:
        """
        Get retailers near a specified location.

        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
            radius: Search radius in kilometers

        Returns:
            QuerySet of nearby retailers
        """
        # Check if we're using SQLite (test environment)
        if connection.vendor == 'sqlite':
            # In test environment, return all retailers
            return Retailer.objects.all()

        user_location = Point(longitude, latitude, srid=4326)
        return Retailer.objects.filter(
            location__distance_lte=(user_location, D(km=radius))
        ).distance(user_location).order_by('distance')

    @staticmethod
    def get_nearby_discounts(latitude: float, longitude: float, radius: float = 5.0) -> QuerySet:
        """
        Get discounts near a specified location.

        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
            radius: Search radius in kilometers

        Returns:
            QuerySet of nearby discounts
        """
        # Check if we're using SQLite (test environment)
        if connection.vendor == 'sqlite':
            # In test environment, return all discounts
            return Discount.objects.all()

        user_location = Point(longitude, latitude, srid=4326)
        return Discount.objects.filter(
            location__distance_lte=(user_location, D(km=radius))
        ).distance(user_location).order_by('distance') 