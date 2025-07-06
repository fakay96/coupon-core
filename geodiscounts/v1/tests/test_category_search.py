"""
Tests for category-based discount search functionality.

This module contains comprehensive tests for the category discount search
endpoints, including pagination, filtering, and error handling.
"""

import pytest
from decimal import Decimal
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.gis.geos import Point
from datetime import timedelta
from unittest.mock import patch, MagicMock

from geodiscounts.models import Category, Discount, Retailer
from geodiscounts.v1.services.discount_search_service import SearchFilters, DiscountSearchService


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
)
class CategoryDiscountSearchTestCase(TestCase):
    """Test case for category-based discount search functionality."""
    
    databases = {'default', 'geodiscounts_db'}

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create test categories (Category model only has name, image, created_at, updated_at)
        self.electronics_category = Category.objects.create(
            name="Electronics"
        )
        self.clothing_category = Category.objects.create(
            name="Clothing"
        )
        
        # Create test retailers
        self.retailer1 = Retailer.objects.create(
            name="TechStore",
            location=Point(-73.935242, 40.730610),  # NYC coordinates
            contact_info="123 Tech Street, NYC"
        )
        self.retailer2 = Retailer.objects.create(
            name="FashionHub",
            location=Point(-74.006015, 40.712776),  # NYC coordinates
            contact_info="456 Fashion Ave, NYC"
        )
        
        # Create test discounts (using correct field names from Discount model)
        self.discount1 = Discount.objects.create(
            name="iPhone Discount",
            description="20% off iPhone 15",
            discount_value=Decimal("200.00"),
            price_per_unit=Decimal("1000.00"),
            discount_percentage=Decimal("20.00"),
            category=self.electronics_category,
            retailer=self.retailer1,
            is_active=True,
            expiration_date=timezone.now() + timedelta(days=30),
            discount_code="IPHONE20"
        )
        
        self.discount2 = Discount.objects.create(
            name="Samsung TV Deal",
            description="15% off Samsung Smart TV",
            discount_value=Decimal("150.00"),
            price_per_unit=Decimal("1000.00"),
            discount_percentage=Decimal("15.00"),
            category=self.electronics_category,
            retailer=self.retailer1,
            is_active=True,
            expiration_date=timezone.now() + timedelta(days=15),
            discount_code="SAMSUNG15"
        )
        
        self.discount3 = Discount.objects.create(
            name="Summer Dress Sale",
            description="30% off summer dresses",
            discount_value=Decimal("45.00"),
            price_per_unit=Decimal("150.00"),
            discount_percentage=Decimal("30.00"),
            category=self.clothing_category,
            retailer=self.retailer2,
            is_active=True,
            expiration_date=timezone.now() + timedelta(days=7),
            discount_code="DRESS30"
        )

    def test_category_search_basic(self):
        """Test basic category search functionality."""
        url = reverse('geodiscounts:v1:category-discount-search')
        response = self.client.get(url, {'category': 'Electronics'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Check response structure
        self.assertIn('results', data)
        self.assertIn('pagination', data)
        self.assertIn('filters_applied', data)
        self.assertIn('search_metadata', data)
        
        # Check results
        self.assertEqual(len(data['results']), 2)
        self.assertEqual(data['pagination']['total_count'], 2)
        self.assertEqual(data['pagination']['current_page'], 1)
        
        # Verify discount names (using 'name' field instead of 'title')
        discount_names = [discount['name'] for discount in data['results']]
        self.assertIn('iPhone Discount', discount_names)
        self.assertIn('Samsung TV Deal', discount_names)

    def test_category_search_by_id(self):
        """Test category search using category ID."""
        url = reverse('geodiscounts:v1:category-discount-search')
        response = self.client.get(url, {'category': str(self.electronics_category.id)})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(len(data['results']), 2)
        self.assertEqual(data['pagination']['total_count'], 2)

    def test_category_search_pagination(self):
        """Test pagination functionality."""
        # Create more discounts for pagination testing
        for i in range(25):
            Discount.objects.create(
                name=f"Test Discount {i}",
                description=f"Test description {i}",
                discount_value=Decimal("10.00"),
                price_per_unit=Decimal("100.00"),
                discount_percentage=Decimal("10.00"),
                category=self.electronics_category,
                retailer=self.retailer1,
                is_active=True,
                expiration_date=timezone.now() + timedelta(days=30),
                discount_code=f"TEST{i}"
            )
        
        url = reverse('geodiscounts:v1:category-discount-search')
        
        # Test first page
        response = self.client.get(url, {
            'category': 'Electronics',
            'page': 1,
            'page_size': 10
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(len(data['results']), 10)
        self.assertEqual(data['pagination']['current_page'], 1)
        self.assertEqual(data['pagination']['page_size'], 10)
        self.assertEqual(data['pagination']['total_count'], 27)  # 2 original + 25 new
        self.assertTrue(data['pagination']['has_next'])
        self.assertFalse(data['pagination']['has_previous'])
        
        # Test second page
        response = self.client.get(url, {
            'category': 'Electronics',
            'page': 2,
            'page_size': 10
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['pagination']['current_page'], 2)
        self.assertTrue(data['pagination']['has_previous'])
        self.assertTrue(data['pagination']['has_next'])

    def test_category_search_filters(self):
        """Test search with various filters."""
        url = reverse('geodiscounts:v1:category-discount-search')
        
        # Test with minimum discount value filter
        response = self.client.get(url, {
            'category': 'Electronics',
            'min_discount_value': 150
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should only return discounts with value >= 150
        self.assertEqual(len(data['results']), 2)  # Both electronics discounts meet criteria
        
        # Test with maximum discount value filter
        response = self.client.get(url, {
            'category': 'Electronics',
            'max_discount_value': 180
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should only return discount with value <= 180
        self.assertEqual(len(data['results']), 1)  # Only Samsung TV Deal meets criteria

    def test_category_search_sorting(self):
        """Test search with sorting options."""
        url = reverse('geodiscounts:v1:category-discount-search')
        
        # Test sorting by discount value descending
        response = self.client.get(url, {
            'category': 'Electronics',
            'sort_by': 'discount_value',
            'sort_order': 'desc'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should be sorted by discount value descending
        self.assertEqual(data['results'][0]['name'], 'iPhone Discount')  # 200.00
        self.assertEqual(data['results'][1]['name'], 'Samsung TV Deal')   # 150.00

    def test_category_search_invalid_category(self):
        """Test search with invalid category."""
        url = reverse('geodiscounts:v1:category-discount-search')
        response = self.client.get(url, {'category': 'InvalidCategory'})
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.json()
        self.assertIn('error', data)

    def test_category_search_missing_category(self):
        """Test search without category parameter."""
        url = reverse('geodiscounts:v1:category-discount-search')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_category_search_service_methods(self):
        """Test DiscountSearchService methods directly."""
        service = DiscountSearchService()
        
        # Test search by category name
        results = service.search_discounts_by_category('Electronics')
        self.assertEqual(len(results['results']), 2)
        
        # Test search by category ID
        results = service.search_discounts_by_category(str(self.electronics_category.id))
        self.assertEqual(len(results['results']), 2)

    @patch('geodiscounts.v1.services.discount_search_service.cache')
    def test_category_search_caching(self, mock_cache):
        """Test that search results are properly cached."""
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None
        
        service = DiscountSearchService()
        
        # First call should cache the result
        results1 = service.search_discounts_by_category('Electronics')
        
        # Second call should use cached result
        results2 = service.search_discounts_by_category('Electronics')
        
        # Verify cache was called
        mock_cache.get.assert_called()
        mock_cache.set.assert_called()


class SearchFiltersTestCase(TestCase):
    """Test case for SearchFilters dataclass."""
    
    databases = {'default', 'geodiscounts_db'}

    def test_search_filters_defaults(self):
        """Test SearchFilters default values."""
        filters = SearchFilters()
        
        self.assertEqual(filters.page, 1)
        self.assertEqual(filters.page_size, 20)
        self.assertIsNone(filters.min_discount_value)
        self.assertIsNone(filters.max_discount_value)
        self.assertIsNone(filters.brand)
        self.assertIsNone(filters.retailer_id)
        self.assertFalse(filters.include_expired)
        self.assertIsNone(filters.latitude)
        self.assertIsNone(filters.longitude)
        self.assertEqual(filters.radius_km, 50.0)
        self.assertEqual(filters.sort_by, 'created_at')
        self.assertEqual(filters.sort_order, 'desc')

    def test_search_filters_custom_values(self):
        """Test SearchFilters with custom values."""
        filters = SearchFilters(
            page=2,
            page_size=10,
            min_discount_value=100.0,
            max_discount_value=500.0,
            brand="Apple",
            retailer_id=1,
            include_expired=True,
            latitude=40.730610,
            longitude=-73.935242,
            radius_km=25.0,
            sort_by="discount_value",
            sort_order="asc"
        )
        
        self.assertEqual(filters.page, 2)
        self.assertEqual(filters.page_size, 10)
        self.assertEqual(filters.min_discount_value, 100.0)
        self.assertEqual(filters.max_discount_value, 500.0)
        self.assertEqual(filters.brand, "Apple")
        self.assertEqual(filters.retailer_id, 1)
        self.assertTrue(filters.include_expired)
        self.assertEqual(filters.latitude, 40.730610)
        self.assertEqual(filters.longitude, -73.935242)
        self.assertEqual(filters.radius_km, 25.0)
        self.assertEqual(filters.sort_by, "discount_value")
        self.assertEqual(filters.sort_order, "asc")


class DiscountSearchServiceTestCase(TestCase):
    """Test case for DiscountSearchService."""
    
    databases = {'default', 'geodiscounts_db'}

    def setUp(self):
        """Set up test data."""
        self.category = Category.objects.create(name="Test Category")
        self.retailer = Retailer.objects.create(
            name="Test Retailer",
            location=Point(-73.935242, 40.730610)
        )
        
        # Create test discounts
        for i in range(5):
            Discount.objects.create(
                name=f"Test Discount {i}",
                description=f"Test description {i}",
                discount_value=Decimal(f"{10 + i * 10}.00"),
                price_per_unit=Decimal("100.00"),
                discount_percentage=Decimal(f"{10 + i * 10}.00"),
                category=self.category,
                retailer=self.retailer,
                is_active=True,
                expiration_date=timezone.now() + timedelta(days=30),
                discount_code=f"TEST{i}"
            )

    def test_search_discounts_by_category(self):
        """Test search_discounts_by_category method."""
        service = DiscountSearchService()
        
        # Test search by category name
        results = service.search_discounts_by_category("Test Category")
        
        self.assertIn('results', results)
        self.assertIn('pagination', results)
        self.assertIn('filters_applied', results)
        self.assertIn('search_metadata', results)
        
        self.assertEqual(len(results['results']), 5)
        self.assertEqual(results['pagination']['total_count'], 5)
        self.assertEqual(results['pagination']['current_page'], 1)

    def test_get_category_suggestions(self):
        """Test get_category_suggestions method."""
        service = DiscountSearchService()
        
        suggestions = service.get_category_suggestions("test", 5)
        
        self.assertIsInstance(suggestions, list)
        self.assertLessEqual(len(suggestions), 5)
        
        # Should include our test category
        category_names = [s['name'] for s in suggestions]
        self.assertIn("Test Category", category_names)

    def test_get_search_statistics(self):
        """Test get_search_statistics method."""
        service = DiscountSearchService()
        
        stats = service.get_search_statistics("Test Category")
        
        self.assertIn('category_id', stats)
        self.assertIn('category_name', stats)
        self.assertIn('total_discounts', stats)
        self.assertIn('active_discounts', stats)
        self.assertIn('expired_discounts', stats)
        
        self.assertEqual(stats['category_name'], "Test Category")
        self.assertEqual(stats['total_discounts'], 5)
        self.assertEqual(stats['active_discounts'], 5)

    def test_category_search_service_basic(self):
        """Test basic category search functionality using service directly."""
        service = DiscountSearchService()
        
        results = service.search_discounts_by_category("Test Category")
        
        self.assertEqual(len(results['results']), 5)
        self.assertEqual(results['pagination']['total_count'], 5)
        self.assertEqual(results['pagination']['current_page'], 1)
        
        # Verify discount names
        discount_names = [discount['name'] for discount in results['results']]
        for i in range(5):
            self.assertIn(f"Test Discount {i}", discount_names)

    def test_category_search_service_by_id(self):
        """Test category search using category ID."""
        service = DiscountSearchService()
        
        results = service.search_discounts_by_category(str(self.category.id))
        
        self.assertEqual(len(results['results']), 5)
        self.assertEqual(results['pagination']['total_count'], 5)

    def test_category_search_service_pagination(self):
        """Test pagination functionality."""
        service = DiscountSearchService()
        
        # Test first page
        results = service.search_discounts_by_category(
            "Test Category",
            filters=SearchFilters(page=1, page_size=3)
        )
        
        self.assertEqual(len(results['results']), 3)
        self.assertEqual(results['pagination']['current_page'], 1)
        self.assertEqual(results['pagination']['page_size'], 3)
        self.assertEqual(results['pagination']['total_count'], 5)
        self.assertTrue(results['pagination']['has_next'])
        self.assertFalse(results['pagination']['has_previous'])
        
        # Test second page
        results = service.search_discounts_by_category(
            "Test Category",
            filters=SearchFilters(page=2, page_size=3)
        )
        
        self.assertEqual(len(results['results']), 2)
        self.assertEqual(results['pagination']['current_page'], 2)
        self.assertTrue(results['pagination']['has_previous'])
        self.assertFalse(results['pagination']['has_next'])

    def test_category_search_service_filters(self):
        """Test search with various filters."""
        service = DiscountSearchService()
        
        # Test with minimum discount value filter
        results = service.search_discounts_by_category(
            "Test Category",
            filters=SearchFilters(min_discount_value=30.0)
        )
        
        # Should only return discounts with value >= 30
        self.assertEqual(len(results['results']), 3)  # Discounts 2, 3, 4
        
        # Test with maximum discount value filter
        results = service.search_discounts_by_category(
            "Test Category",
            filters=SearchFilters(max_discount_value=30.0)
        )
        
        # Should only return discounts with value <= 30
        self.assertEqual(len(results['results']), 3)  # Discounts 0, 1, 2

    def test_category_search_service_sorting(self):
        """Test search with sorting options."""
        service = DiscountSearchService()
        
        # Test sorting by discount value descending
        results = service.search_discounts_by_category(
            "Test Category",
            filters=SearchFilters(sort_by="discount_value", sort_order="desc")
        )
        
        # Should be sorted by discount value descending
        discount_values = [discount['discount_value'] for discount in results['results']]
        self.assertEqual(discount_values, [50.0, 40.0, 30.0, 20.0, 10.0])

    def test_category_search_service_invalid_category(self):
        """Test search with invalid category."""
        service = DiscountSearchService()
        
        results = service.search_discounts_by_category("InvalidCategory")
        
        self.assertIn('error', results)
        self.assertEqual(results['error'], "Category not found")

    def test_category_search_service_methods(self):
        """Test DiscountSearchService methods directly."""
        service = DiscountSearchService()
        
        # Test search by category name
        results = service.search_discounts_by_category("Test Category")
        self.assertEqual(len(results['results']), 5)
        
        # Test search by category ID
        results = service.search_discounts_by_category(str(self.category.id))
        self.assertEqual(len(results['results']), 5)

    @patch('geodiscounts.v1.services.discount_search_service.cache')
    def test_category_search_service_caching(self, mock_cache):
        """Test that search results are properly cached."""
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None
        
        service = DiscountSearchService()
        
        # First call should cache the result
        results1 = service.search_discounts_by_category("Test Category")
        
        # Second call should use cached result
        results2 = service.search_discounts_by_category("Test Category")
        
        # Verify cache was called
        mock_cache.get.assert_called()
        mock_cache.set.assert_called()

    def test_search_filters_dataclass(self):
        """Test SearchFilters dataclass functionality."""
        # Test default values
        filters = SearchFilters()
        self.assertEqual(filters.page, 1)
        self.assertEqual(filters.page_size, 20)
        self.assertIsNone(filters.min_discount_value)
        self.assertIsNone(filters.max_discount_value)
        self.assertIsNone(filters.brand)
        self.assertIsNone(filters.retailer_id)
        self.assertFalse(filters.include_expired)
        self.assertIsNone(filters.latitude)
        self.assertIsNone(filters.longitude)
        self.assertEqual(filters.radius_km, 50.0)
        self.assertEqual(filters.sort_by, 'created_at')
        self.assertEqual(filters.sort_order, 'desc')
        
        # Test custom values
        custom_filters = SearchFilters(
            page=2,
            page_size=10,
            min_discount_value=100.0,
            max_discount_value=500.0,
            brand="Apple",
            retailer_id=1,
            include_expired=True,
            latitude=40.730610,
            longitude=-73.935242,
            radius_km=25.0,
            sort_by="discount_value",
            sort_order="asc"
        )
        
        self.assertEqual(custom_filters.page, 2)
        self.assertEqual(custom_filters.page_size, 10)
        self.assertEqual(custom_filters.min_discount_value, 100.0)
        self.assertEqual(custom_filters.max_discount_value, 500.0)
        self.assertEqual(custom_filters.brand, "Apple")
        self.assertEqual(custom_filters.retailer_id, 1)
        self.assertTrue(custom_filters.include_expired)
        self.assertEqual(custom_filters.latitude, 40.730610)
        self.assertEqual(custom_filters.longitude, -73.935242)
        self.assertEqual(custom_filters.radius_km, 25.0)
        self.assertEqual(custom_filters.sort_by, "discount_value")
        self.assertEqual(custom_filters.sort_order, "asc") 