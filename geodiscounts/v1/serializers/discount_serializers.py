"""
Serializers for the Discount Discovery System.

This module provides serializers for the Discount and SharedDiscount models.
"""

from rest_framework import serializers
from geodiscounts.models import Discount, SharedDiscount, Retailer, Category
from .retailer_serializers import RetailerSerializer
from .fields import PointField


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for the Category model.

    Fields:
        - id: The primary key of the category.
        - name: The name of the category.
        - image: URL to the category's image.
    """
    class Meta:
        model = Category
        fields = ['id', 'name', 'image']


class DiscountSerializer(serializers.ModelSerializer):
    """
    Serializer for the Discount model.

    Fields:
        - id: The primary key of the discount.
        - retailer: The retailer offering the discount (nested).
        - description: Description of the discount.
        - discount_code: Unique code for redeeming the discount.
        - discount_value: The value of the discount.
        - is_active: Whether the discount is currently active.
        - expiration_date: Expiration date of the discount.
        - location: Geographic location where the discount is valid.
        - created_at: Timestamp when the discount was created.
        - updated_at: Timestamp when the discount was last updated.
    """

    retailer = RetailerSerializer(read_only=True)
    retailer_id = serializers.PrimaryKeyRelatedField(
        queryset=Retailer.objects.all(),
        write_only=True,
        source='retailer'
    )
    location = PointField()

    class Meta:
        model = Discount
        fields = [
            'id', 'retailer', 'retailer_id', 'description', 'discount_code',
            'discount_value', 'is_active', 'expiration_date', 'location',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SharedDiscountSerializer(serializers.ModelSerializer):
    """
    Serializer for the SharedDiscount model.

    Fields:
        - id: The primary key of the shared discount.
        - discount: The related discount (nested).
        - group_name: Name of the group sharing the discount.
        - participants: List of participant user IDs.
        - min_participants: Minimum number of participants required.
        - max_participants: Maximum number of participants allowed.
        - status: Status of the shared discount.
        - created_at: Timestamp when the shared discount was created.
        - updated_at: Timestamp when the shared discount was last updated.
    """

    discount = DiscountSerializer(read_only=True)
    discount_id = serializers.PrimaryKeyRelatedField(
        queryset=Discount.objects.all(),
        write_only=True,
        source='discount'
    )

    class Meta:
        model = SharedDiscount
        fields = [
            'id', 'discount', 'discount_id', 'group_name', 'participants',
            'min_participants', 'max_participants', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at'] 