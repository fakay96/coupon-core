"""
Tests for the discount-related API views.

These tests validate the functionality of endpoints for retrieving discounts,
including listing all discounts and fetching nearby discounts based on user location.

Author: Your Name
Date: YYYY-MM-DD
"""

from unittest.mock import patch

from django.contrib.gis.geos import Point
from rest_framework.test import APITestCase

from geodiscounts.models import Discount, Retailer


class DiscountAPITestCase(APITestCase):
    """
    Tests for the discount-related API views.
    """

    def setUp(self):
        """
        Sets up test data for the API tests, including a retailer and associated discounts.
        """
        self.retailer = Retailer.objects.create(
            name="Test Retailer", location=Point(12.4924, 41.8902)  # Rome
        )
        self.discount = Discount.objects.create(
            retailer=self.retailer,
            description="20% off",
            discount_code="SAVE20",
            expiration_date="2025-12-31",
            location=Point(12.4924, 41.8902),
        )

    def test_discount_list(self):
        """
        Test case for retrieving a list of all available discounts.

        Expected Behavior:
        - Returns HTTP 200 with a list of discounts.
        """
        response = self.client.get("/api/geodiscount/v1/discounts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    @patch("geodiscounts.v1.utils.ip_geolocation.get_location_from_ip")
    def test_nearby_discounts(self, mock_geolocation):
        """
        Test case for retrieving discounts near the user's location.

        Expected Behavior:
        - Returns HTTP 200 with a list of nearby discounts.
        """
        mock_geolocation.return_value = {
            "latitude": 41.8902,
            "longitude": 12.4924,
        }
        response = self.client.get("/api/geodiscount/v1/discounts/nearby/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
