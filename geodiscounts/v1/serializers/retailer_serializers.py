"""
Serializers for the retailer-related models.

This module provides serializers for converting retailer models to and from JSON,
with proper validation and error handling.
"""

from typing import Dict, Any, Optional
from rest_framework import serializers
from coupon_core.utils.logging import geo_logger, geo_structured_logger

from geodiscounts.models import Retailer, Discount


class RetailerSerializer(serializers.ModelSerializer):
    """
    Serializer for the Retailer model.
    
    Handles serialization and deserialization of retailer data, including
    validation of required fields and proper error handling.
    """
    
    class Meta:
        model = Retailer
        fields = [
            'id', 'name', 'description', 'website', 'logo',
            'location', 'address', 'phone', 'email',
            'is_active', 'created_at', 'updated_at'
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
            raise serializers.ValidationError("Retailer name must be at least 2 characters long")
        return value

    def validate_email(self, value: str) -> str:
        """
        Validate the retailer email.
        
        Args:
            value: The email to validate
            
        Returns:
            The validated email
            
        Raises:
            serializers.ValidationError: If the email is invalid
        """
        if not value or '@' not in value:
            geo_structured_logger.warning(
                geo_logger,
                "Invalid retailer email format",
                "retailer_validate_email",
                {'email': value}
            )
            raise serializers.ValidationError("Invalid email format")
        return value

    def validate_phone(self, value: str) -> str:
        """
        Validate the retailer phone number.
        
        Args:
            value: The phone number to validate
            
        Returns:
            The validated phone number
            
        Raises:
            serializers.ValidationError: If the phone number is invalid
        """
        if value and not value.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            geo_structured_logger.warning(
                geo_logger,
                "Invalid retailer phone format",
                "retailer_validate_phone",
                {'phone': value}
            )
            raise serializers.ValidationError("Phone number must contain only digits, spaces, hyphens, and plus sign")
        return value

    def create(self, validated_data: Dict[str, Any]) -> Retailer:
        """
        Create a new retailer.
        
        Args:
            validated_data: The validated data for creating the retailer
            
        Returns:
            The created retailer instance
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
                    'email': retailer.email
                }
            )
            return retailer
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error creating retailer",
                "retailer_create",
                e,
                {
                    'name': validated_data.get('name'),
                    'email': validated_data.get('email')
                }
            )
            raise

    def update(self, instance: Retailer, validated_data: Dict[str, Any]) -> Retailer:
        """
        Update an existing retailer.
        
        Args:
            instance: The retailer instance to update
            validated_data: The validated data for updating the retailer
            
        Returns:
            The updated retailer instance
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
                    'email': retailer.email
                }
            )
            return retailer
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error updating retailer",
                "retailer_update",
                e,
                {
                    'retailer_id': instance.id,
                    'name': instance.name,
                    'email': instance.email
                }
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
            'distance'
        ]
    
    def get_distance(self, obj):
        """
        Calculate and return distance if available in the queryset.
        """
        # Check if distance has been annotated to the queryset
        if hasattr(obj, 'distance'):
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
        fields = [
            'total_discounts', 
            'active_discounts', 
            'expired_discounts', 
            'avg_discount_value', 
            'total_shared_discounts', 
            'active_shared_discounts'
        ]