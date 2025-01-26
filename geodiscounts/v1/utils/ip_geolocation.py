"""
API Utilities

This module contains reusable utility functions used across API views to ensure
modularity, readability, and maintainability. These utilities handle tasks like
IP-based geolocation, input validation, and geospatial calculations.

Functions:
    - get_location_from_ip: Fetches geolocation data based on a user's IP address.
    - validate_max_distance: Validates and converts the `max_distance` parameter.
    - calculate_distance: Calculates the geodesic distance between two coordinates.


"""

from typing import Any, Dict, Optional, Tuple

import requests
from geopy.distance import geodesic


def get_location_from_ip(ip: str) -> Optional[Dict[str, Any]]:
    """
    Fetches geolocation data (latitude, longitude) for a given IP address using an external API.

    Args:
        ip (str): The IP address of the user.

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing latitude, longitude, and additional
        location metadata (if successful). Returns None if the API call fails or if the IP address
        cannot be resolved.

    Example:
        >>> get_location_from_ip("8.8.8.8")
        {'latitude': 37.751, 'longitude': -97.822, ...}

    Notes:
        - Uses the free `ip-api.com` service. Consider using a paid service for production
          environments to ensure better accuracy and reliability.

    Raises:
        None: Errors are logged, and None is returned if the API call fails.
    """
    GEOLOCATION_API_URL = "http://ip-api.com/json/"
    try:
        response = requests.get(f"{GEOLOCATION_API_URL}{ip}")
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return {
                    "latitude": data.get("lat"),
                    "longitude": data.get("lon"),
                    "country": data.get("country"),
                    "region": data.get("regionName"),
                    "city": data.get("city"),
                    "zip": data.get("zip"),
                }
        return None
    except requests.RequestException as e:
        print(f"Error fetching geolocation: {e}")
        return None


def validate_max_distance(max_distance: str) -> float:
    """
    Validates and converts the `max_distance` parameter to a float.

    Args:
        max_distance (str): The maximum distance (in kilometers) provided by the user as a string.

    Returns:
        float: The validated and converted maximum distance in kilometers.

    Raises:
        ValueError: If the `max_distance` parameter is not a valid number.

    Example:
        >>> validate_max_distance("10")
        10.0

        >>> validate_max_distance("invalid")
        ValueError: max_distance must be a valid number.
    """
    try:
        return float(max_distance)
    except ValueError:
        raise ValueError("max_distance must be a valid number.")


def calculate_distance(
    coord1: Tuple[float, float], coord2: Tuple[float, float]
) -> float:
    """
    Calculates the geodesic distance (in kilometers) between two geographic coordinates.

    Args:
        coord1 (Tuple[float, float]): Latitude and longitude of the first point.
        coord2 (Tuple[float, float]): Latitude and longitude of the second point.

    Returns:
        float: The geodesic distance between the two points in kilometers.

    Example:
        >>> calculate_distance((41.8902, 12.4922), (48.8566, 2.3522))
        1105.24

    Notes:
        - Uses the `geopy` library for accurate geospatial calculations.
        - The distance is calculated assuming the Earth is an ellipsoid (WGS-84 standard).
    """
    return geodesic(coord1, coord2).kilometers
