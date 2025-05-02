"""
Serializers for the discount-related models.

This module provides serializers for converting discount models to and from JSON,
with proper validation and error handling.
"""

from typing import Dict, Any, Optional
from rest_framework import serializers
from django.utils import timezone
from coupon_core.utils.logging import geo_logger, geo_structured_logger

from geodiscounts.models import Discount, Category, SharedDiscount

class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for the Category model.
    
    Handles serialization and deserialization of category data, including
    validation of required fields and proper error handling.
    """
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'image', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_name(self, value: str) -> str:
        """
        Validate the category name.
        
        Args:
            value: The category name to validate
            
        Returns:
            The validated name
            
        Raises:
            serializers.ValidationError: If the name is invalid
        """
        if len(value.strip()) < 2:
            geo_structured_logger.warning(
                geo_logger,
                "Invalid category name length",
                "category_validate_name",
                {'name': value}
            )
            raise serializers.ValidationError("Category name must be at least 2 characters long")
        return value

    def create(self, validated_data: Dict[str, Any]) -> Category:
        """
        Create a new category.
        
        Args:
            validated_data: The validated data for creating the category
            
        Returns:
            The created category instance
        """
        try:
            category = super().create(validated_data)
            geo_structured_logger.info(
                geo_logger,
                "Category created successfully",
                "category_create",
                {
                    'category_id': category.id,
                    'name': category.name
                }
            )
            return category
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error creating category",
                "category_create",
                e,
                {'name': validated_data.get('name')}
            )
            raise

class DiscountSerializer(serializers.ModelSerializer):
    """
    Serializer for the Discount model.
    
    Handles serialization and deserialization of discount data, including
    validation of required fields, expiration dates, and proper error handling.
    """
    
    retailer_name = serializers.CharField(source='retailer.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Discount
        fields = [
            'id', 'retailer', 'retailer_name', 'category', 'category_name',
            'description', 'discount_code', 'discount_value', 'is_active',
            'expiration_date', 'location', 'image', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_expiration_date(self, value: timezone.datetime) -> timezone.datetime:
        """
        Validate the expiration date.
        
        Args:
            value: The expiration date to validate
            
        Returns:
            The validated expiration date
            
        Raises:
            serializers.ValidationError: If the expiration date is invalid
        """
        if value <= timezone.now():
            geo_structured_logger.warning(
                geo_logger,
                "Invalid expiration date",
                "discount_validate_expiration",
                {'expiration_date': value.isoformat()}
            )
            raise serializers.ValidationError("Expiration date must be in the future")
        return value

    def validate_discount_value(self, value: float) -> float:
        """
        Validate the discount value.
        
        Args:
            value: The discount value to validate
            
        Returns:
            The validated discount value
            
        Raises:
            serializers.ValidationError: If the discount value is invalid
        """
        if value <= 0:
            geo_structured_logger.warning(
                geo_logger,
                "Invalid discount value",
                "discount_validate_value",
                {'value': value}
            )
            raise serializers.ValidationError("Discount value must be greater than 0")
        return value

    def create(self, validated_data: Dict[str, Any]) -> Discount:
        """
        Create a new discount.
        
        Args:
            validated_data: The validated data for creating the discount
            
        Returns:
            The created discount instance
        """
        try:
            discount = super().create(validated_data)
            geo_structured_logger.info(
                geo_logger,
                "Discount created successfully",
                "discount_create",
                {
                    'discount_id': discount.id,
                    'retailer_id': discount.retailer.id,
                    'category_id': discount.category.id if discount.category else None
                }
            )
            return discount
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error creating discount",
                "discount_create",
                e,
                {
                    'retailer_id': validated_data.get('retailer').id,
                    'category_id': validated_data.get('category').id if validated_data.get('category') else None
                }
            )
            raise

    def update(self, instance: Discount, validated_data: Dict[str, Any]) -> Discount:
        """
        Update an existing discount.
        
        Args:
            instance: The discount instance to update
            validated_data: The validated data for updating the discount
            
        Returns:
            The updated discount instance
        """
        try:
            discount = super().update(instance, validated_data)
            geo_structured_logger.info(
                geo_logger,
                "Discount updated successfully",
                "discount_update",
                {
                    'discount_id': discount.id,
                    'retailer_id': discount.retailer.id,
                    'category_id': discount.category.id if discount.category else None
                }
            )
            return discount
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error updating discount",
                "discount_update",
                e,
                {
                    'discount_id': instance.id,
                    'retailer_id': instance.retailer.id,
                    'category_id': instance.category.id if instance.category else None
                }
            )
            raise

class SharedDiscountSerializer(serializers.ModelSerializer):
    """
    Serializer for the SharedDiscount model.
    
    Handles serialization and deserialization of shared discount data,
    including validation of participants and proper error handling.
    """
    
    discount_details = DiscountSerializer(source='discount', read_only=True)
    participant_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SharedDiscount
        fields = [
            'id', 'discount', 'discount_details', 'group_name',
            'participants', 'participant_count', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_participant_count(self, obj: SharedDiscount) -> int:
        """
        Get the number of participants in the shared discount.
        
        Args:
            obj: The shared discount instance
            
        Returns:
            The number of participants
        """
        return obj.participants.count()

    def validate_status(self, value: str) -> str:
        """
        Validate the shared discount status.
        
        Args:
            value: The status to validate
            
        Returns:
            The validated status
            
        Raises:
            serializers.ValidationError: If the status is invalid
        """
        if value not in dict(SharedDiscount.STATUS_CHOICES):
            geo_structured_logger.warning(
                geo_logger,
                "Invalid shared discount status",
                "shared_discount_validate_status",
                {'status': value}
            )
            raise serializers.ValidationError("Invalid status")
        return value

    def create(self, validated_data: Dict[str, Any]) -> SharedDiscount:
        """
        Create a new shared discount.
        
        Args:
            validated_data: The validated data for creating the shared discount
            
        Returns:
            The created shared discount instance
        """
        try:
            shared_discount = super().create(validated_data)
            geo_structured_logger.info(
                geo_logger,
                "Shared discount created successfully",
                "shared_discount_create",
                {
                    'shared_discount_id': shared_discount.id,
                    'discount_id': shared_discount.discount.id,
                    'group_name': shared_discount.group_name
                }
            )
            return shared_discount
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error creating shared discount",
                "shared_discount_create",
                e,
                {
                    'discount_id': validated_data.get('discount').id,
                    'group_name': validated_data.get('group_name')
                }
            )
            raise 