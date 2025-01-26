"""
Tests for utility functions used in the Discount Discovery API.

These utilities provide reusable logic for geolocation, input validation, and
geospatial calculations. The tests ensure the correctness and robustness of
these functions.


"""

from unittest.mock import patch

from django.test import TestCase

from geodiscounts.v1.utils.ip_geolocation import (
    calculate_distance,
    get_location_from_ip,
    validate_max_distance,
)


class UtilsTest(TestCase):
    """
    Tests for utility functions used across the Discount Discovery API.
    """

    @patch("geodiscounts.v1.utils.requests.get")
    def test_get_location_from_ip_success(self, mock_get):
        """
        Test case for successfully fetching geolocation data from a valid IP address.

        Expected Behavior:
        - The function should return a dictionary containing latitude and longitude.
        """
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "status": "success",
            "lat": 37.7749,
            "lon": -122.4194,
        }
        result = get_location_from_ip("8.8.8.8")
        self.assertEqual(result["latitude"], 37.7749)
        self.assertEqual(result["longitude"], -122.4194)

    def test_validate_max_distance_valid(self):
        """
        Test case for validating a valid `max_distance` parameter.

        Expected Behavior:
        - The function should return the distance as a float.
        """
        result = validate_max_distance("10")
        self.assertEqual(result, 10.0)

    def test_validate_max_distance_invalid(self):
        """
        Test case for handling an invalid `max_distance` parameter.

        Expected Behavior:
        - The function should raise a `ValueError` if the input is not a valid number.
        """
        with self.assertRaises(ValueError):
            validate_max_distance("invalid")

    def test_calculate_distance(self):
        """
        Test case for calculating the geodesic distance between two geographic points.

        Expected Behavior:
        - The function should return the distance in kilometers with reasonable accuracy.
        """
        coord1 = (41.8902, 12.4922)  # Rome
        coord2 = (48.8566, 2.3522)  # Paris
        result = calculate_distance(coord1, coord2)
        self.assertAlmostEqual(result, 1105.5, places=1)
