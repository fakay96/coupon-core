"""
Tests for the retailer-related API views.

These tests validate the functionality of endpoints for retrieving retailer data,
including listing all retailers and fetching specific retailer details.

Author: Your Name
Date: YYYY-MM-DD
"""

from django.contrib.gis.geos import Point
from rest_framework.test import APITestCase

from geodiscounts.models import Retailer


class RetailerAPITestCase(APITestCase):
    """
    Tests for the retailer-related API views.
    """

    def setUp(self):
        """
        Sets up test data for the API tests, including a retailer with a geographic location.
        """
        self.retailer = Retailer.objects.create(
            name="Test Retailer", location=Point(12.4924, 41.8902)  # Rome
        )

    def test_retailer_list(self):
        """
        Test case for retrieving a list of all retailers.

        Expected Behavior:
        - Returns HTTP 200 with a list of retailers.
        """
        response = self.client.get("/api/geodiscount/v1/retailers/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_retailer_detail(self):
        """
        Test case for retrieving details of a specific retailer by ID.

        Expected Behavior:
        - Returns HTTP 200 with retailer details if found.
        - Returns HTTP 404 if the retailer is not found.
        """
        response = self.client.get(f"/api/geodiscount/v1/retailers/{self.retailer.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Test Retailer")
