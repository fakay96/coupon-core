"""
Tests for serializers in the Geodiscount API.

This module tests:
1. RetailerSerializer
2. DiscountSerializer
3. SharedDiscountSerializer
4. Serializer validation
5. Nested serialization
"""

from django.test import TestCase
from django.contrib.gis.geos import Point
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from geodiscounts.v1.serializers import (
    RetailerSerializer,
    DiscountSerializer,
    SharedDiscountSerializer,
    PointField
)
from geodiscounts.models import Retailer, Discount, SharedDiscount
from django.contrib.auth import get_user_model
from datetime import timedelta

User = get_user_model()

class PointFieldTest(TestCase):
    """Test PointField serializer."""

    def setUp(self):
        """Set up test environment."""
        self.field = PointField()

    def test_to_representation(self):
        """Test converting Point to dict."""
        point = Point(1.0, 2.0)
        result = self.field.to_representation(point)
        self.assertEqual(result, {'latitude': 2.0, 'longitude': 1.0})

    def test_to_internal_value(self):
        """Test converting dict to Point."""
        data = {'latitude': 2.0, 'longitude': 1.0}
        result = self.field.to_internal_value(data)
        self.assertEqual(result.x, 1.0)
        self.assertEqual(result.y, 2.0)

    def test_invalid_format(self):
        """Test invalid location format."""
        data = {'invalid': 'format'}
        with self.assertRaises(ValidationError):
            self.field.to_internal_value(data)


class RetailerSerializerTest(TestCase):
    """Test RetailerSerializer."""

    databases = {'default', 'geodiscounts_db'}

    def setUp(self):
        """Set up test environment."""
        self.retailer_data = {
            "name": "Test Retailer",
            "contact_info": "test@example.com",
            "location": Point(1.0, 1.0),
        }
        self.retailer = Retailer.objects.create(**self.retailer_data)
        self.serializer = RetailerSerializer(instance=self.retailer)

    def test_contains_expected_fields(self):
        """Test that serializer contains expected fields."""
        data = self.serializer.data
        self.assertEqual(set(data.keys()), {
            'id',
            'name',
            'contact_info',
            'location',
            'owner',
            'created_at',
            'updated_at',
        })

    def test_contact_info_validation(self):
        """Test contact info validation."""
        data = {
            "name": "Another Retailer",  # Different name to avoid uniqueness error
            "contact_info": "invalid",
            "location": Point(1.0, 1.0),
        }
        serializer = RetailerSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('contact_info', serializer.errors)

    def test_location_serialization(self):
        """Test location field serialization."""
        data = self.serializer.data
        self.assertEqual(data['location'], {'latitude': 1.0, 'longitude': 1.0})


class DiscountSerializerTest(TestCase):
    """Test DiscountSerializer."""

    databases = {'default', 'geodiscounts_db'}

    def setUp(self):
        """Set up test environment."""
        self.retailer = Retailer.objects.create(
            name="Test Retailer",
            contact_info="test@example.com",
            location=Point(1.0, 1.0),
        )
        self.discount_data = {
            "retailer": self.retailer,
            "description": "Test Discount",
            "discount_code": "TEST123",
            "discount_value": 10.0,
            "is_active": True,
            "expiration_date": timezone.now() + timezone.timedelta(days=7),
            "location": Point(1.0, 1.0),
        }
        self.discount = Discount.objects.create(**self.discount_data)
        self.serializer = DiscountSerializer(instance=self.discount)

    def test_contains_expected_fields(self):
        """Test that serializer contains expected fields."""
        data = self.serializer.data
        self.assertEqual(set(data.keys()), {
            'id',
            'retailer',
            'description',
            'discount_code',
            'discount_value',
            'is_active',
            'expiration_date',
            'location',
            'created_at',
            'updated_at',
        })

    def test_nested_retailer_serialization(self):
        """Test that retailer is properly nested."""
        data = self.serializer.data
        self.assertEqual(data['retailer']['id'], self.retailer.id)
        self.assertEqual(data['retailer']['name'], self.retailer.name)

    def test_location_serialization(self):
        """Test location field serialization."""
        data = self.serializer.data
        self.assertEqual(data['location'], {'latitude': 1.0, 'longitude': 1.0})


class SharedDiscountSerializerTest(TestCase):
    """Test SharedDiscountSerializer."""

    databases = {'default', 'geodiscounts_db'}

    def setUp(self):
        """Set up test environment."""
        self.retailer = Retailer.objects.create(
            name="Test Retailer",
            contact_info="test@example.com",
            location=Point(1.0, 1.0),
        )
        self.discount = Discount.objects.create(
            retailer=self.retailer,
            description="Test Discount",
            discount_code="TEST123",
            discount_value=10.0,
            is_active=True,
            expiration_date=timezone.now() + timezone.timedelta(days=7),
            location=Point(1.0, 1.0),
        )
        self.shared_discount_data = {
            "discount": self.discount,
            "group_name": "Test Group",
            "participants": ["user1@example.com", "user2@example.com"],
            "min_participants": 2,
            "max_participants": 5,
            "status": "active",
        }
        self.shared_discount = SharedDiscount.objects.create(**self.shared_discount_data)
        self.serializer = SharedDiscountSerializer(instance=self.shared_discount)

    def test_contains_expected_fields(self):
        """Test that serializer contains expected fields."""
        data = self.serializer.data
        self.assertEqual(set(data.keys()), {
            'id',
            'discount',
            'group_name',
            'participants',
            'min_participants',
            'max_participants',
            'status',
            'created_at',
            'updated_at',
        })

    def test_nested_discount_serialization(self):
        """Test that discount is properly nested."""
        data = self.serializer.data
        self.assertEqual(data['discount']['id'], self.discount.id)
        self.assertEqual(data['discount']['description'], self.discount.description) 