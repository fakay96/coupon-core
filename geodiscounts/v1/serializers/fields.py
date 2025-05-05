"""
Custom serializer fields for the geodiscounts app.

This module provides custom serializer fields for handling geographic data,
including point fields and distance calculations.
"""

from typing import Any, Dict, Optional
from rest_framework import serializers
from django.contrib.gis.geos import Point
from coupon_core.utils.logging import geo_logger, geo_structured_logger

class PointField(serializers.Field):
    """
    Custom field for handling geographic points.
    
    This field handles serialization and deserialization of geographic points,
    including validation of coordinates and proper error handling.
    """
    
    def to_representation(self, value: Point) -> Dict[str, float]:
        """
        Convert a Point object to a dictionary representation.
        
        Args:
            value: The Point object to convert
            
        Returns:
            A dictionary containing latitude and longitude
            
        Raises:
            serializers.ValidationError: If the point is invalid
        """
        if not isinstance(value, Point):
            geo_structured_logger.warning(
                geo_logger,
                "Invalid point type",
                "point_field_to_representation",
                {'value_type': type(value).__name__}
            )
            raise serializers.ValidationError("Invalid point type")
        
        return {
            'latitude': value.y,
            'longitude': value.x
        }

    def to_internal_value(self, data: Dict[str, float]) -> Point:
        """
        Convert a dictionary to a Point object.
        
        Args:
            data: The dictionary containing latitude and longitude
            
        Returns:
            A Point object
            
        Raises:
            serializers.ValidationError: If the data is invalid
        """
        if not isinstance(data, dict):
            geo_structured_logger.warning(
                geo_logger,
                "Invalid point data type",
                "point_field_to_internal_value",
                {'data_type': type(data).__name__}
            )
            raise serializers.ValidationError("Point data must be a dictionary")

        try:
            latitude = float(data.get('latitude', 0))
            longitude = float(data.get('longitude', 0))
        except (TypeError, ValueError) as e:
            geo_structured_logger.warning(
                geo_logger,
                "Invalid point coordinates",
                "point_field_to_internal_value",
                {'data': data}
            )
            raise serializers.ValidationError("Invalid coordinates") from e

        if not (-90 <= latitude <= 90):
            geo_structured_logger.warning(
                geo_logger,
                "Invalid latitude value",
                "point_field_to_internal_value",
                {'latitude': latitude}
            )
            raise serializers.ValidationError("Latitude must be between -90 and 90")

        if not (-180 <= longitude <= 180):
            geo_structured_logger.warning(
                geo_logger,
                "Invalid longitude value",
                "point_field_to_internal_value",
                {'longitude': longitude}
            )
            raise serializers.ValidationError("Longitude must be between -180 and 180")

        return Point(longitude, latitude)

class DistanceField(serializers.FloatField):
    """
    Custom field for handling distance values.
    
    This field handles serialization and deserialization of distance values,
    including validation of units and proper error handling.
    """
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the distance field.
        
        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        self.unit = kwargs.pop('unit', 'km')
        super().__init__(*args, **kwargs)

    def to_representation(self, value: float) -> Dict[str, Any]:
        """
        Convert a distance value to a dictionary representation.
        
        Args:
            value: The distance value to convert
            
        Returns:
            A dictionary containing the distance value and unit
            
        Raises:
            serializers.ValidationError: If the value is invalid
        """
        if not isinstance(value, (int, float)):
            geo_structured_logger.warning(
                geo_logger,
                "Invalid distance type",
                "distance_field_to_representation",
                {'value_type': type(value).__name__}
            )
            raise serializers.ValidationError("Invalid distance type")

        return {
            'value': float(value),
            'unit': self.unit
        }

    def to_internal_value(self, data: Any) -> float:
        """
        Convert a value to a distance.
        
        Args:
            data: The value to convert
            
        Returns:
            A float representing the distance
            
        Raises:
            serializers.ValidationError: If the data is invalid
        """
        try:
            if isinstance(data, dict):
                value = float(data.get('value', 0))
                unit = data.get('unit', self.unit)
                if unit != self.unit:
                    geo_structured_logger.warning(
                        geo_logger,
                        "Invalid distance unit",
                        "distance_field_to_internal_value",
                        {'unit': unit, 'expected_unit': self.unit}
                    )
                    raise serializers.ValidationError(f"Distance must be in {self.unit}")
            else:
                value = float(data)
        except (TypeError, ValueError) as e:
            geo_structured_logger.warning(
                geo_logger,
                "Invalid distance value",
                "distance_field_to_internal_value",
                {'data': data}
            )
            raise serializers.ValidationError("Invalid distance value") from e

        if value < 0:
            geo_structured_logger.warning(
                geo_logger,
                "Negative distance value",
                "distance_field_to_internal_value",
                {'value': value}
            )
            raise serializers.ValidationError("Distance cannot be negative")

        return value 