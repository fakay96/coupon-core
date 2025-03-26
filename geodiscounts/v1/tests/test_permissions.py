"""
Tests for permissions in the Geodiscount API.

This module tests:
1. Merchant permissions
2. Staff permissions
3. Anonymous user permissions
4. Object-level permissions
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from geodiscounts.v1.permissions import (
    IsMerchantOwner,
    IsStaffOrReadOnly,
    IsOwnerOrReadOnly
)
from geodiscounts.models import Discount, Retailer
from rest_framework.views import APIView
from rest_framework import status
from django.contrib.gis.geos import Point
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class MockView(APIView):
    """Mock view for testing permissions."""
    pass

class MerchantPermissionsTest(TestCase):
    """Tests for merchant permissions."""

    def setUp(self):
        """Set up test environment."""
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com'
        )
        self.retailer = Retailer.objects.create(
            name='Test Business',
            owner=self.user,
            location=Point(0, 0)
        )
        self.permission = IsMerchantOwner()
        self.view = MockView()

    def test_merchant_owner_permission(self):
        """Test merchant owner permissions."""
        # Test owner access
        request = self.factory.get('/')
        request.user = self.user
        self.assertTrue(
            self.permission.has_object_permission(request, self.view, self.retailer)
        )

        # Test non-owner access
        request.user = self.other_user
        self.assertFalse(
            self.permission.has_object_permission(request, self.view, self.retailer)
        )

    def test_merchant_owner_safe_methods(self):
        """Test merchant owner permissions for safe methods."""
        request = self.factory.get('/')
        request.user = self.other_user
        self.assertTrue(
            self.permission.has_permission(request, self.view)
        )

    def test_merchant_owner_unsafe_methods(self):
        """Test merchant owner permissions for unsafe methods."""
        # Test POST request
        request = self.factory.post('/')
        request.user = self.other_user
        self.assertFalse(
            self.permission.has_permission(request, self.view)
        )

        # Test owner POST request
        request.user = self.user
        self.assertTrue(
            self.permission.has_permission(request, self.view)
        )


class StaffPermissionsTest(TestCase):
    """Tests for staff permissions."""

    def setUp(self):
        """Set up test environment."""
        self.factory = APIRequestFactory()
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            is_staff=True
        )
        self.normal_user = User.objects.create_user(
            username='normaluser',
            email='normal@example.com'
        )
        self.permission = IsStaffOrReadOnly()
        self.view = MockView()

    def test_staff_permission(self):
        """Test staff permissions."""
        # Test staff access
        request = self.factory.post('/')
        request.user = self.staff_user
        self.assertTrue(
            self.permission.has_permission(request, self.view)
        )

        # Test non-staff access
        request.user = self.normal_user
        self.assertFalse(
            self.permission.has_permission(request, self.view)
        )

    def test_staff_safe_methods(self):
        """Test staff permissions for safe methods."""
        request = self.factory.get('/')
        request.user = self.normal_user
        self.assertTrue(
            self.permission.has_permission(request, self.view)
        )

    def test_staff_unsafe_methods(self):
        """Test staff permissions for unsafe methods."""
        # Test DELETE request
        request = self.factory.delete('/')
        request.user = self.normal_user
        self.assertFalse(
            self.permission.has_permission(request, self.view)
        )

        # Test staff DELETE request
        request.user = self.staff_user
        self.assertTrue(
            self.permission.has_permission(request, self.view)
        )


class OwnerPermissionsTest(TestCase):
    """Tests for owner permissions."""

    def setUp(self):
        """Set up test environment."""
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com'
        )
        self.retailer = Retailer.objects.create(
            name='Test Business',
            owner=self.user,
            location=Point(0, 0)
        )
        self.discount = Discount.objects.create(
            retailer=self.retailer,
            description='Test Description',
            discount_code='TEST123',
            discount_value=10.0,
            expiration_date=timezone.now() + timedelta(days=7),
            location=Point(0, 0)
        )
        self.permission = IsOwnerOrReadOnly()
        self.view = MockView()

    def test_owner_permission(self):
        """Test owner permissions."""
        # Test owner access
        request = self.factory.put('/')
        request.user = self.user
        self.assertTrue(
            self.permission.has_object_permission(request, self.view, self.discount)
        )

        # Test non-owner access
        request.user = self.other_user
        self.assertFalse(
            self.permission.has_object_permission(request, self.view, self.discount)
        )

    def test_owner_safe_methods(self):
        """Test owner permissions for safe methods."""
        request = self.factory.get('/')
        request.user = self.other_user
        self.assertTrue(
            self.permission.has_object_permission(request, self.view, self.discount)
        )

    def test_owner_unsafe_methods(self):
        """Test owner permissions for unsafe methods."""
        # Test PATCH request
        request = self.factory.patch('/')
        request.user = self.other_user
        self.assertFalse(
            self.permission.has_object_permission(request, self.view, self.discount)
        )

        # Test owner PATCH request
        request.user = self.user
        self.assertTrue(
            self.permission.has_object_permission(request, self.view, self.discount)
        )


class AnonymousUserPermissionsTest(TestCase):
    """Tests for anonymous user permissions."""

    def setUp(self):
        """Set up test environment."""
        self.factory = APIRequestFactory()
        self.anonymous_user = User.objects.create_user(
            username='anonymous',
            email='anonymous@example.com'
        )
        self.merchant_user = User.objects.create_user(
            username='merchant',
            email='merchant@example.com'
        )
        self.retailer = Retailer.objects.create(
            name='Test Business',
            owner=self.merchant_user,
            location=Point(0, 0)
        )
        self.discount = Discount.objects.create(
            retailer=self.retailer,
            description='Test Description',
            discount_code='TEST123',
            discount_value=10.0,
            expiration_date=timezone.now() + timedelta(days=7),
            location=Point(0, 0)
        )
        self.permission = IsOwnerOrReadOnly()
        self.view = MockView()

    def test_anonymous_safe_methods(self):
        """Test anonymous permissions for safe methods."""
        request = self.factory.get('/')
        request.user = self.anonymous_user
        self.assertTrue(
            self.permission.has_object_permission(request, self.view, self.discount)
        )

    def test_anonymous_unsafe_methods(self):
        """Test anonymous permissions for unsafe methods."""
        # Test POST request
        request = self.factory.post('/')
        request.user = self.anonymous_user
        self.assertFalse(
            self.permission.has_object_permission(request, self.view, self.discount)
        )

        # Test PUT request
        request = self.factory.put('/')
        request.user = self.anonymous_user
        self.assertFalse(
            self.permission.has_object_permission(request, self.view, self.discount)
        )

        # Test DELETE request
        request = self.factory.delete('/')
        request.user = self.anonymous_user
        self.assertFalse(
            self.permission.has_object_permission(request, self.view, self.discount)
        ) 