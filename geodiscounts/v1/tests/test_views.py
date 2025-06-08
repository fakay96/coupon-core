import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.importorskip("django", reason="django not installed")
import pytest
pytest.importorskip("django", reason="django not installed")
"""
Test cases for geodiscount views.

This module tests:
1. Discount creation and management
2. Location-based discount retrieval
3. Discount validation
4. Discount search and filtering
5. Discount redemption and tracking
6. Retailer operations
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.gis.geos import Point
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from geodiscounts.models import Retailer, Discount, SharedDiscount, Location, MerchantDiscount
from datetime import datetime, timedelta
from django.utils import timezone
from unittest.mock import patch, MagicMock
import json
from django.test.utils import override_settings
from django.db.models.signals import post_save
import pytest

User = get_user_model()

def disable_user_signals():
    """Temporarily disable user-related signals."""
    post_save.receivers = []

class RetailerViewTestCase(APITestCase):
    """Test suite for retailer views."""

    databases = {'default', 'geodiscounts_db', 'authentication_shard'}

    @classmethod
    def setUpClass(cls):
        """Set up test class by disabling signals."""
        super().setUpClass()
        disable_user_signals()

    def setUp(self):
        """Set up test environment."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.retailer_data = {
            'name': 'Test Retailer',
            'contact_info': 'test@retailer.com',
            'location': {'latitude': 40.7128, 'longitude': -74.0060},  # New York coordinates
           
        }
        self.retailer = Retailer.objects.create(
            name=self.retailer_data['name'],
            contact_info=self.retailer_data['contact_info'],
            location=Point(self.retailer_data['location']['longitude'], self.retailer_data['location']['latitude']),
           
        )

    def test_retailer_list(self):
        """Test retrieving a list of all retailers."""
        url = reverse('geodiscounts:retailer-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retailer_detail(self):
        """Test retrieving retailer details."""
        url = reverse('geodiscounts:retailer-detail', args=[self.retailer.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retailer_create(self):
        """Test retailer creation."""
        url = reverse('geodiscounts:retailer-list')
        new_retailer_data = {
            'name': 'New Retailer',
            'contact_info': 'new@retailer.com',
            'location': {'latitude': 40.7128, 'longitude': -74.0060},
        }
        response = self.client.post(url, new_retailer_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retailer_update(self):
        """Test retailer update."""
        url = reverse('geodiscounts:retailer-detail', args=[self.retailer.id])
        updated_data = {
            'name': 'Updated Retailer',
            'contact_info': 'updated@retailer.com',
            'location': {'latitude': 40.7128, 'longitude': -74.0060},
        }
        response = self.client.put(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retailer_delete(self):
        """Test retailer deletion."""
        url = reverse('geodiscounts:retailer-detail', args=[self.retailer.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_retailer_nearby(self):
        """Test finding nearby retailers."""
        url = reverse('geodiscounts:retailer-nearby')
        params = {'latitude': 40.7128, 'longitude': -74.0060, 'radius': 10}
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class DiscountViewTestCase(APITestCase):
    """Test suite for discount views."""

    databases = {'default', 'geodiscounts_db', 'authentication_shard'}

    @classmethod
    def setUpClass(cls):
        """Set up test class by disabling signals."""
        super().setUpClass()
        disable_user_signals()

    def setUp(self):
        """Set up test environment."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.retailer = Retailer.objects.create(
            name='Test Retailer',
            contact_info='test@retailer.com',
            location=Point(-74.0060, 40.7128),
        )
        self.discount_data = {
            'retailer': self.retailer.id,
            'description': 'Test Discount',
            'discount_code': 'TEST123',
            'discount_value': 10.00,
            'is_active': True,
            'expiration_date': timezone.now() + timedelta(days=7),
            'location': {'latitude': 40.7128, 'longitude': -74.0060}
        }
        self.discount = Discount.objects.create(
            retailer=self.retailer,
            description=self.discount_data['description'],
            discount_code=self.discount_data['discount_code'],
            discount_value=self.discount_data['discount_value'],
            is_active=self.discount_data['is_active'],
            expiration_date=self.discount_data['expiration_date'],
            location=Point(self.discount_data['location']['longitude'], self.discount_data['location']['latitude'])
        )

    def test_discount_list(self):
        """Test retrieving a list of all discounts."""
        url = reverse('geodiscounts:discount-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_discount_detail(self):
        """Test retrieving discount details."""
        url = reverse('geodiscounts:discount-detail', args=[self.discount.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_discount_create(self):
        """Test discount creation."""
        url = reverse('geodiscounts:discount-list')
        new_discount_data = {
            'retailer_id': self.retailer.id,
            'description': 'New Discount',
            'discount_code': 'NEW123',
            'discount_value': 20.00,
            'is_active': True,
            'expiration_date': timezone.now() + timedelta(days=7),
            'location': {'latitude': 40.7128, 'longitude': -74.0060}
        }
        response = self.client.post(url, new_discount_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_discount_update(self):
        """Test discount update."""
        url = reverse('geodiscounts:discount-detail', args=[self.discount.id])
        updated_data = {
            'retailer_id': self.retailer.id,
            'description': 'Updated Discount',
            'discount_code': 'UPD123',
            'discount_value': 15.00,
            'is_active': True,
            'expiration_date': timezone.now() + timedelta(days=7),
            'location': {'latitude': 40.7128, 'longitude': -74.0060}
        }
        response = self.client.put(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_discount_delete(self):
        """Test discount deletion."""
        url = reverse('geodiscounts:discount-detail', args=[self.discount.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_nearby_discounts(self):
        """Test finding nearby discounts."""
        url = reverse('geodiscounts:discount-nearby')
        params = {'latitude': 40.7128, 'longitude': -74.0060, 'radius': 10}
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class SharedDiscountViewTestCase(APITestCase):
    """Test suite for shared discount views."""

    databases = {'default', 'geodiscounts_db', 'authentication_shard'}

    @classmethod
    def setUpClass(cls):
        """Set up test class by disabling signals."""
        super().setUpClass()
        disable_user_signals()

    def setUp(self):
        """Set up test environment."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.retailer = Retailer.objects.create(
            name='Test Retailer',
            contact_info='test@retailer.com',
            location=Point(-74.0060, 40.7128),
        )
        self.discount = Discount.objects.create(
            retailer=self.retailer,
            description='Test Discount',
            discount_code='TEST123',
            discount_value=10.00,
            is_active=True,
            expiration_date=timezone.now() + timedelta(days=7),
            location=Point(-74.0060, 40.7128)
        )
        self.shared_discount_data = {
            'discount_id': self.discount.id,
            'group_name': 'Test Group',
            'participants': [self.user.id],
            'min_participants': 2,
            'max_participants': 5,
            'status': 'active'
        }
        self.shared_discount = SharedDiscount.objects.create(
            discount=self.discount,
            group_name=self.shared_discount_data['group_name'],
            participants=self.shared_discount_data['participants'],
            min_participants=self.shared_discount_data['min_participants'],
            max_participants=self.shared_discount_data['max_participants'],
            status=self.shared_discount_data['status']
        )

    def test_shared_discount_list(self):
        """Test retrieving a list of all shared discounts."""
        url = reverse('geodiscounts:shared-discount-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_shared_discount_detail(self):
        """Test retrieving shared discount details."""
        url = reverse('geodiscounts:shared-discount-detail', args=[self.shared_discount.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_shared_discount_create(self):
        """Test shared discount creation."""
        url = reverse('geodiscounts:shared-discount-list')
        new_shared_discount_data = {
            'discount_id': self.discount.id,
            'group_name': 'New Group',
            'participants': [self.user.id],
            'min_participants': 2,
            'max_participants': 5,
            'status': 'active'
        }
        response = self.client.post(url, new_shared_discount_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_shared_discount_update(self):
        """Test shared discount update."""
        url = reverse('geodiscounts:shared-discount-detail', args=[self.shared_discount.id])
        updated_data = {
            'discount_id': self.discount.id,
            'group_name': 'Updated Group',
            'participants': [self.user.id],
            'min_participants': 3,
            'max_participants': 6,
            'status': 'active'
        }
        response = self.client.put(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_shared_discount_delete(self):
        """Test shared discount deletion."""
        url = reverse('geodiscounts:shared-discount-detail', args=[self.shared_discount.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

@pytest.mark.django_db
class TestDiscountAPI:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def merchant_user(self):
        return User.objects.create_user(
            email="merchant@example.com",
            password="testpass123",
            first_name="Test",
            last_name="Merchant"
        )

    @pytest.fixture
    def discount_data(self):
        return {
            "title": "Test Discount",
            "description": "Test Description",
            "discount_percentage": 10,
            "start_date": timezone.now(),
            "end_date": timezone.now() + timedelta(days=7),
            "is_active": True
        }

    def test_create_discount(self, api_client, merchant_user, discount_data):
        """Test discount creation by merchant."""
        api_client.force_authenticate(user=merchant_user)
        url = reverse('discount-list')
        response = api_client.post(url, discount_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == discount_data['title']

    def test_list_discounts(self, api_client, merchant_user, discount_data):
        """Test listing discounts."""
        api_client.force_authenticate(user=merchant_user)
        url = reverse('discount-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_discount(self, api_client, merchant_user, discount_data):
        """Test retrieving a specific discount."""
        api_client.force_authenticate(user=merchant_user)
        discount = Discount.objects.create(**discount_data)
        url = reverse('discount-detail', kwargs={'pk': discount.pk})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == discount_data['title']

    def test_update_discount(self, api_client, merchant_user, discount_data):
        """Test updating a discount."""
        api_client.force_authenticate(user=merchant_user)
        discount = Discount.objects.create(**discount_data)
        url = reverse('discount-detail', kwargs={'pk': discount.pk})
        update_data = {'title': 'Updated Discount'}
        response = api_client.patch(url, update_data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Updated Discount'

    def test_delete_discount(self, api_client, merchant_user, discount_data):
        """Test deleting a discount."""
        api_client.force_authenticate(user=merchant_user)
        discount = Discount.objects.create(**discount_data)
        url = reverse('discount-detail', kwargs={'pk': discount.pk})
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

@pytest.mark.django_db
class TestLocationAPI:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def location_data(self):
        return {
            "name": "Test Location",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "radius": 1000
        }

    def test_create_location(self, api_client, location_data):
        """Test location creation."""
        url = reverse('location-list')
        response = api_client.post(url, location_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == location_data['name']

    def test_list_locations(self, api_client):
        """Test listing locations."""
        url = reverse('location-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_location(self, api_client, location_data):
        """Test retrieving a specific location."""
        location = Location.objects.create(**location_data)
        url = reverse('location-detail', kwargs={'pk': location.pk})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == location_data['name']

@pytest.mark.django_db
class TestMerchantDiscountAPI:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def merchant_user(self):
        return User.objects.create_user(
            email="merchant@example.com",
            password="testpass123",
            first_name="Test",
            last_name="Merchant"
        )

    @pytest.fixture
    def merchant_discount_data(self):
        discount = Discount.objects.create(
            title="Test Discount",
            description="Test Description",
            discount_percentage=10,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=7)
        )
        location = Location.objects.create(
            name="Test Location",
            latitude=40.7128,
            longitude=-74.0060,
            radius=1000
        )
        return {
            "discount": discount.id,
            "location": location.id,
            "merchant_id": 1
        }

    def test_create_merchant_discount(self, api_client, merchant_user, merchant_discount_data):
        """Test merchant discount creation."""
        api_client.force_authenticate(user=merchant_user)
        url = reverse('merchant-discount-list')
        response = api_client.post(url, merchant_discount_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_list_merchant_discounts(self, api_client, merchant_user):
        """Test listing merchant discounts."""
        api_client.force_authenticate(user=merchant_user)
        url = reverse('merchant-discount-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK 