"""
Serializers for the retailer-related models.

This module provides serializers for converting retailer models to and from JSON,
with proper validation and error handling.
"""

from typing import Dict, Any, Optional, List
from rest_framework import serializers
from coupon_core.utils.logging import geo_logger, geo_structured_logger

from geodiscounts.models import Retailer


class RetailerSerializer(serializers.ModelSerializer):
    """
    Serializer for the Retailer model.

    Handles serialization and deserialization of retailer data, including
    validation of required fields and proper error handling.
    """

    class Meta:
        model = Retailer
        fields = [
            'id',
            'name',
            'contact_info',
            'location',
            'analytics_data',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_name(self, value: str) -> str:
        """
        Validate the retailer name.

        Args:
            value: The retailer name to validate

        Returns:
            The validated name

        Raises:
            serializers.ValidationError: If the name is invalid
        """
        if len(value.strip()) < 2:
            geo_structured_logger.warning(
                geo_logger,
                "Invalid retailer name length",
                "retailer_validate_name",
                {'name': value}
            )
            raise serializers.ValidationError(
                "Retailer name must be at least 2 characters long"
            )
        return value

    def validate_contact_info(self, value: Optional[str]) -> Optional[str]:
        """
        Validate the retailer contact_info.

        Args:
            value: The contact_info to validate

        Returns:
            The validated contact_info

        Raises:
            serializers.ValidationError: If the contact_info is too long
        """
        if value and len(value) > 1000:
            geo_structured_logger.warning(
                geo_logger,
                "contact_info too long",
                "retailer_validate_contact_info",
                {'length': len(value)}
            )
            raise serializers.ValidationError(
                "Contact info must be under 1000 characters"
            )
        return value

    def create(self, validated_data: Dict[str, Any]) -> Retailer:
        """
        Create a new Retailer instance.

        Args:
            validated_data: The validated data for creating the retailer

        Returns:
            The created Retailer instance
        """
        try:
            retailer = super().create(validated_data)
            geo_structured_logger.info(
                geo_logger,
                "Retailer created successfully",
                "retailer_create",
                {
                    'retailer_id': retailer.id,
                    'name': retailer.name,
                }
            )
            return retailer
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error creating retailer",
                "retailer_create",
                e,
                {'data': validated_data}
            )
            raise

    def update(self, instance: Retailer, validated_data: Dict[str, Any]) -> Retailer:
        """
        Update an existing Retailer instance.

        Args:
            instance: The Retailer instance to update
            validated_data: The validated data for updating the retailer

        Returns:
            The updated Retailer instance
        """
        try:
            retailer = super().update(instance, validated_data)
            geo_structured_logger.info(
                geo_logger,
                "Retailer updated successfully",
                "retailer_update",
                {
                    'retailer_id': retailer.id,
                    'name': retailer.name,
                }
            )
            return retailer
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error updating retailer",
                "retailer_update",
                e,
                {'retailer_id': instance.id}
            )
            raise


class NearbyRetailersSerializer(serializers.ModelSerializer):
    """
    Serializer for nearby retailers, including distance information.
    """
    distance = serializers.SerializerMethodField()

    class Meta:
        model = Retailer
        fields = [
            'id',
            'name',
            'contact_info',
            'location',
            'distance',
        ]

    def get_distance(self, obj: Retailer) -> Optional[float]:
        """
        Return the annotated distance in kilometers if available.

        Args:
            obj: Retailer instance with optional `distance` attribute

        Returns:
            Distance in kilometers, or None if not annotated
        """
        if hasattr(obj, 'distance') and obj.distance is not None:
            # assume .distance is a GEOS Distance object in meters
            return obj.distance.km
        return None


class RetailerAnalyticsSerializer(serializers.Serializer):
    """
    Serializer for retailer analytics data.
    Provides insights into discount performance and metrics.
    """
    total_discounts = serializers.IntegerField()
    active_discounts = serializers.IntegerField()
    expired_discounts = serializers.IntegerField()
    avg_discount_value = serializers.FloatField()
    total_shared_discounts = serializers.IntegerField()
    active_shared_discounts = serializers.IntegerField()

    class Meta:
        fields: List[str] = [
            'total_discounts',
            'active_discounts',
            'expired_discounts',
            'avg_discount_value',
            'total_shared_discounts',
            'active_shared_discounts',
        ]
