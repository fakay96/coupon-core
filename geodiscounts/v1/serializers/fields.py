"""
Custom serializer fields for the Discount Discovery System.
"""

from rest_framework import serializers
from django.contrib.gis.geos import Point


class PointField(serializers.Field):
    """Custom field for handling Point objects."""

    def to_representation(self, value):
        """Convert Point to a dict with lat/lon."""
        if value is None:
            return None
        return {'latitude': value.y, 'longitude': value.x}

    def to_internal_value(self, data):
        """Convert lat/lon dict to Point."""
        if isinstance(data, dict):
            try:
                if 'latitude' in data and 'longitude' in data:
                    return Point(data['longitude'], data['latitude'])
                elif 'lat' in data and 'lon' in data:
                    return Point(data['lon'], data['lat'])
                elif 'y' in data and 'x' in data:
                    return Point(data['x'], data['y'])
                else:
                    raise serializers.ValidationError(
                        "Invalid location format. Expected {'latitude': float, 'longitude': float} or {'lat': float, 'lon': float}"
                    )
            except (TypeError, ValueError) as e:
                raise serializers.ValidationError(f"Invalid location coordinates: {str(e)}")
        elif isinstance(data, Point):
            return data
        raise serializers.ValidationError("Invalid location format") 