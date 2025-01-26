"""
Serializers for the Discount Discovery System.

These serializers transform model instances into JSON format and validate
incoming data for Retailer, Discount, and SharedDiscount models.

Author: Your Name
Date: YYYY-MM-DD
"""

from rest_framework import serializers

from geodiscounts.models import Discount, Retailer, SharedDiscount


class RetailerSerializer(serializers.ModelSerializer):
    """
    Serializer for the Retailer model.

    Fields:
        - id: The primary key of the retailer.
        - name: The name of the retailer.
        - contact_info: Contact details of the retailer.
        - location: Geographic location of the retailer (latitude/longitude).
        - created_at: Timestamp when the retailer was created.
        - updated_at: Timestamp when the retailer was last updated.
    """

    class Meta:
        model = Retailer
        fields = [
            "id",
            "name",
            "contact_info",
            "location",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DiscountSerializer(serializers.ModelSerializer):
    """
    Serializer for the Discount model.

    Fields:
        - id: The primary key of the discount.
        - retailer: The retailer offering the discount (nested).
        - description: Description of the discount.
        - discount_code: Unique code for redeeming the discount.
        - expiration_date: Expiration date of the discount.
        - location: Geographic location where the discount is valid.
        - created_at: Timestamp when the discount was created.
        - updated_at: Timestamp when the discount was last updated.
    """

    retailer = RetailerSerializer(read_only=True)

    class Meta:
        model = Discount
        fields = [
            "id",
            "retailer",
            "description",
            "discount_code",
            "expiration_date",
            "location",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SharedDiscountSerializer(serializers.ModelSerializer):
    """
    Serializer for the SharedDiscount model.

    Fields:
        - id: The primary key of the shared discount.
        - discount: The related discount (nested).
        - group_name: Name of the group sharing the discount.
        - participants: List of participants in the shared discount.
        - status: Status of the shared discount (active, completed, or expired).
        - created_at: Timestamp when the shared discount was created.
        - updated_at: Timestamp when the shared discount was last updated.
    """

    discount = DiscountSerializer(read_only=True)

    class Meta:
        model = SharedDiscount
        fields = [
            "id",
            "discount",
            "group_name",
            "participants",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
