"""
Tests for the Geodiscount models.
"""
from django.test import TestCase
from django.contrib.gis.geos import Point
from django.utils import timezone
from django.core.exceptions import ValidationError
import pytest
from datetime import timedelta

from geodiscounts.models import Retailer, Discount, SharedDiscount

@pytest.mark.django_db
class TestDiscountModel:
    def test_create_discount(self):
        """Test discount creation with valid data."""
        retailer = Retailer.objects.create(
            name="Test Retailer",
            contact_info="test@example.com",
            location=Point(1.0, 1.0)
        )
        discount = Discount.objects.create(
            retailer=retailer,
            description="Test Description",
            discount_code="TEST123",
            discount_value=10.0,
            is_active=True,
            expiration_date=timezone.now() + timedelta(days=7),
            location=Point(1.0, 1.0)
        )
        assert discount.description == "Test Description"
        assert discount.discount_value == 10.0
        assert discount.is_active

    def test_discount_validation(self):
        """Test discount validation rules."""
        retailer = Retailer.objects.create(
            name="Test Retailer",
            contact_info="test@example.com",
            location=Point(1.0, 1.0)
        )
        with pytest.raises(ValidationError):
            Discount.objects.create(
                retailer=retailer,
                description="Test Description",
                discount_code="TEST123",
                discount_value=-1.0,  # Invalid value
                expiration_date=timezone.now() + timedelta(days=7),
                location=Point(1.0, 1.0)
            )

    def test_discount_date_validation(self):
        """Test discount date validation."""
        retailer = Retailer.objects.create(
            name="Test Retailer",
            contact_info="test@example.com",
            location=Point(1.0, 1.0)
        )
        with pytest.raises(ValidationError):
            Discount.objects.create(
                retailer=retailer,
                description="Test Description",
                discount_code="TEST123",
                discount_value=10.0,
                expiration_date=timezone.now() - timedelta(days=1),  # Past date
                location=Point(1.0, 1.0)
            )

@pytest.mark.django_db
class TestRetailerModel:
    def test_create_retailer(self):
        """Test retailer creation with valid data."""
        retailer = Retailer.objects.create(
            name="Test Retailer",
            contact_info="test@example.com",
            location=Point(1.0, 1.0)
        )
        assert retailer.name == "Test Retailer"
        assert retailer.contact_info == "test@example.com"
        assert isinstance(retailer.location, Point)

    def test_retailer_name_unique(self):
        """Test retailer name uniqueness."""
        Retailer.objects.create(
            name="Test Retailer",
            contact_info="test@example.com",
            location=Point(1.0, 1.0)
        )
        with pytest.raises(Exception):
            Retailer.objects.create(
                name="Test Retailer",  # Same name
                contact_info="another@example.com",
                location=Point(2.0, 2.0)
            )

@pytest.mark.django_db
class TestSharedDiscount:
    def test_create_shared_discount(self):
        """Test shared discount creation."""
        retailer = Retailer.objects.create(
            name="Test Retailer",
            contact_info="test@example.com",
            location=Point(1.0, 1.0)
        )
        discount = Discount.objects.create(
            retailer=retailer,
            description="Test Description",
            discount_code="TEST123",
            discount_value=10.0,
            expiration_date=timezone.now() + timedelta(days=7),
            location=Point(1.0, 1.0)
        )
        shared_discount = SharedDiscount.objects.create(
            discount=discount,
            group_name="Test Group",
            participants=[1, 2, 3],
            min_participants=2,
            max_participants=5
        )
        assert shared_discount.group_name == "Test Group"
        assert len(shared_discount.participants) == 3
        assert shared_discount.min_participants == 2
        assert shared_discount.max_participants == 5

    def test_shared_discount_validation(self):
        """Test shared discount validation."""
        retailer = Retailer.objects.create(
            name="Test Retailer",
            contact_info="test@example.com",
            location=Point(1.0, 1.0)
        )
        discount = Discount.objects.create(
            retailer=retailer,
            description="Test Description",
            discount_code="TEST123",
            discount_value=10.0,
            expiration_date=timezone.now() + timedelta(days=7),
            location=Point(1.0, 1.0)
        )
        with pytest.raises(ValidationError):
            SharedDiscount.objects.create(
                discount=discount,
                group_name="Test Group",
                participants=[1],  # Too few participants
                min_participants=2,
                max_participants=5
            ) 