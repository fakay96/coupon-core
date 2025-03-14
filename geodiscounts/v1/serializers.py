"""
Serializers for the Discount Discovery System.

These serializers transform model instances into JSON format and validate
incoming data for Retailer, Discount, Category, and SharedDiscount models.

Author: Your Name
Date: YYYY-MM-DD
"""

from rest_framework import serializers
from geodiscounts.models import Discount, Retailer, SharedDiscount, Category


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for the Category model.

    Fields:
        - id: The primary key of the category.
        - name: The name of the category.
        - image: Image representing the category.
    """

    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "image",
        ]
        read_only_fields = ["id"]


class RetailerSerializer(serializers.ModelSerializer):
    """
    Serializer for the Retailer model.

    Fields:
        - id: The primary key of the retailer.
        - name: The name of the retailer.
        - contact_info: Contact details of the retailer.
        - location: The geographic location of the **retailer itself** (store, office, etc.).
    """

    class Meta:
        model = Retailer
        fields = [
            "id",
            "name",
            "contact_info",
            "location",
        ]
        read_only_fields = ["id"]


class DiscountSerializer(serializers.ModelSerializer):
    """
    Serializer for the Discount model.

    Fields:
        - id: The primary key of the discount.
        - retailer: The retailer offering the discount (nested).
        - category: The category the discount belongs to (nested).
        - description: Description of the discount.
        - discount_code: Unique code for redeeming the discount.
        - expiration_date: Expiration date of the discount.
        - location: The specific **valid location** of the discount (can differ from retailer).
        - image: Optional image for the discount.
    """

    retailer = RetailerSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Discount
        fields = [
            "id",
            "retailer",
            "category",
            "description",
            "discount_code",
            "expiration_date",
            "location",
            "image",
        ]
        read_only_fields = ["id"]


class SharedDiscountSerializer(serializers.ModelSerializer):
    """
    Serializer for the SharedDiscount model.

    Fields:
        - id: The primary key of the shared discount.
        - discount: The related discount (nested).
        - group_name: Name of the group sharing the discount.
        - participants: List of participants in the shared discount.
        - status: Status of the shared discount (active, completed, or expired).
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
        ]
        read_only_fields = ["id"]
