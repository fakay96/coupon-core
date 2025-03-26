"""
Tests for the Geodiscount models.
"""
from django.test import TestCase
from django.contrib.gis.geos import Point
from django.utils import timezone
from django.core.exceptions import ValidationError

from geodiscounts.models import Retailer, Discount, SharedDiscount

class RetailerModelTest(TestCase):
    """Tests for the Retailer model."""

    databases = {'default', 'geodiscounts_db'}

    def setUp(self):
        """Set up test environment."""
        self.retailer = Retailer.objects.create(
            name="Test Retailer",
            contact_info="test@example.com",
            location=Point(1.0, 1.0)
        )

    def test_retailer_str(self):
        """Test string representation of Retailer."""
        self.assertEqual(str(self.retailer), "Test Retailer")

    def test_retailer_name_unique(self):
        """Test that retailer names must be unique."""
        with self.assertRaises(Exception):
            Retailer.objects.create(
                name="Test Retailer",  # Same name as in setUp
                contact_info="another@example.com",
                location=Point(2.0, 2.0)
            )

    def test_retailer_location_validation(self):
        """Test location validation."""
        with self.assertRaises(Exception):
            Retailer.objects.create(
                name="Invalid Location",
                contact_info="test@example.com",
                location="invalid"
            )

class DiscountModelTest(TestCase):
    """Tests for the Discount model."""

    databases = {'default', 'geodiscounts_db'}

    def setUp(self):
        """Set up test environment."""
        self.retailer = Retailer.objects.create(
            name="Test Retailer",
            contact_info="test@example.com",
            location=Point(1.0, 1.0)
        )
        self.discount = Discount.objects.create(
            retailer=self.retailer,
            description="Test Discount",
            discount_code="TEST123",
            expiration_date=timezone.now() + timezone.timedelta(days=7),
            location=Point(1.0, 1.0)
        )

    def test_discount_str(self):
        """Test string representation of Discount."""
        expected = f"{self.retailer.name} - {self.discount.description[:30]}"
        self.assertEqual(str(self.discount), expected)

    def test_discount_code_unique(self):
        """Test that discount codes must be unique."""
        with self.assertRaises(Exception):
            Discount.objects.create(
                retailer=self.retailer,
                description="Another Discount",
                discount_code="TEST123",  # Same code as in setUp
                expiration_date=timezone.now() + timezone.timedelta(days=7),
                location=Point(2.0, 2.0)
            )

    def test_discount_expiration(self):
        """Test discount expiration."""
        expired_discount = Discount.objects.create(
            retailer=self.retailer,
            description="Expired Discount",
            discount_code="EXPIRED123",
            expiration_date=timezone.now() - timezone.timedelta(days=1),
            location=Point(1.0, 1.0)
        )
        self.assertTrue(expired_discount.expiration_date < timezone.now())

class SharedDiscountModelTest(TestCase):
    """Tests for the SharedDiscount model."""

    databases = {'default', 'geodiscounts_db'}

    def setUp(self):
        """Set up test environment."""
        self.retailer = Retailer.objects.create(
            name="Test Retailer",
            contact_info="test@example.com",
            location=Point(1.0, 1.0)
        )
        self.discount = Discount.objects.create(
            retailer=self.retailer,
            description="Test Discount",
            discount_code="TEST123",
            expiration_date=timezone.now() + timezone.timedelta(days=7),
            location=Point(1.0, 1.0)
        )
        self.shared_discount = SharedDiscount.objects.create(
            discount=self.discount,
            group_name="Test Group",
            participants=["user1@example.com", "user2@example.com"],
            status="active"
        )

    def test_shared_discount_str(self):
        """Test string representation of SharedDiscount."""
        expected = f"{self.shared_discount.group_name} - {self.discount.discount_code}"
        self.assertEqual(str(self.shared_discount), expected)

    def test_shared_discount_participants(self):
        """Test participants field."""
        self.assertIsInstance(self.shared_discount.participants, list)
        self.assertEqual(len(self.shared_discount.participants), 2)
        self.assertIn("user1@example.com", self.shared_discount.participants)

    def test_shared_discount_status_choices(self):
        """Test status choices validation."""
        shared_discount = SharedDiscount(
            discount=self.discount,
            group_name="Invalid Status",
            participants=["user1@example.com"],
            status="invalid"  # Invalid status
        )
        with self.assertRaises(ValidationError):
            shared_discount.full_clean() 