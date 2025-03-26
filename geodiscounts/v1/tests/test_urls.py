"""
Tests for URL patterns in the Geodiscount API.

This module tests:
1. URL pattern resolution
2. URL name resolution
3. URL parameter handling
"""

from django.test import TestCase
from django.urls import reverse, NoReverseMatch

class URLPatternsTest(TestCase):
    """Test URL pattern resolution."""

    def test_discount_list_url(self):
        """Test discount list URL pattern."""
        url = reverse('geodiscounts:discount-list')
        self.assertEqual(url, '/api/v1/discounts/')

    def test_discount_detail_url(self):
        """Test discount detail URL pattern."""
        url = reverse('geodiscounts:discount-detail', args=[1])
        self.assertEqual(url, '/api/v1/discounts/1/')

    def test_nearby_discounts_url(self):
        """Test nearby discounts URL pattern."""
        url = reverse('geodiscounts:discount-nearby')
        self.assertEqual(url, '/api/v1/discounts/nearby/')

    def test_search_discounts_url(self):
        """Test discount search URL pattern."""
        url = reverse('geodiscounts:discount-search')
        self.assertEqual(url, '/api/v1/discounts/search/')

    def test_retailer_list_url(self):
        """Test retailer list URL pattern."""
        url = reverse('geodiscounts:retailer-list')
        self.assertEqual(url, '/api/v1/retailers/')

    def test_retailer_detail_url(self):
        """Test retailer detail URL pattern."""
        url = reverse('geodiscounts:retailer-detail', args=[1])
        self.assertEqual(url, '/api/v1/retailers/1/')

    def test_retailer_detail_url_invalid_id(self):
        """Test retailer detail URL with invalid ID."""
        with self.assertRaises(NoReverseMatch):
            reverse('geodiscounts:retailer-detail', args=['invalid'])

    def test_nearby_retailers_url(self):
        """Test nearby retailers URL pattern."""
        url = reverse('geodiscounts:retailer-nearby')
        self.assertEqual(url, '/api/v1/retailers/nearby/')

    def test_shared_discount_list_url(self):
        """Test shared discount list URL pattern."""
        url = reverse('geodiscounts:shared-discount-list')
        self.assertEqual(url, '/api/v1/shared-discounts/')

    def test_shared_discount_detail_url(self):
        """Test shared discount detail URL pattern."""
        url = reverse('geodiscounts:shared-discount-detail', args=[1])
        self.assertEqual(url, '/api/v1/shared-discounts/1/')

    def test_retailer_analytics_url(self):
        """Test retailer analytics URL pattern."""
        url = reverse('geodiscounts:merchant-analytics', args=[1])
        self.assertEqual(url, '/api/v1/retailers/1/analytics/')