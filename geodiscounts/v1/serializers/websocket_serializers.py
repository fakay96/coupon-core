"""
Serializers for websocket-related models.

This module provides serializers for converting websocket models to and from JSON,
with proper validation and error handling.
"""

from typing import Dict, Any, Optional
from rest_framework import serializers
from coupon_core.utils.logging import geo_logger, geo_structured_logger
from geodiscounts.models import WebSocketDiscountRequest, Category
from django.contrib.gis.geos import Point

class WebSocketDiscountRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for the WebSocketDiscountRequest model.
    
    Handles serialization and deserialization of websocket discount request data,
    including validation of required fields and proper error handling.
    """
    
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = WebSocketDiscountRequest
        fields = [
            'id', 'user', 'query', 'location', 'max_distance',
            'status', 'results', 'error_message', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_query(self, value: str) -> str:
        """
        Validate the search query.
        
        Args:
            value: The query to validate
            
        Returns:
            The validated query
            
        Raises:
            serializers.ValidationError: If the query is invalid
        """
        if not value or len(value.strip()) < 2:
            geo_structured_logger.warning(
                geo_logger,
                "Invalid search query length",
                "websocket_request_validate_query",
                {'query': value}
            )
            raise serializers.ValidationError("Search query must be at least 2 characters long")
        return value

    def validate_max_distance(self, value: float) -> float:
        """
        Validate the maximum distance.
        
        Args:
            value: The maximum distance to validate
            
        Returns:
            The validated maximum distance
            
        Raises:
            serializers.ValidationError: If the maximum distance is invalid
        """
        if value <= 0:
            geo_structured_logger.warning(
                geo_logger,
                "Invalid maximum distance",
                "websocket_request_validate_max_distance",
                {'max_distance': value}
            )
            raise serializers.ValidationError("Maximum distance must be greater than 0")
        return value

    def validate_status(self, value: str) -> str:
        """
        Validate the request status.
        
        Args:
            value: The status to validate
            
        Returns:
            The validated status
            
        Raises:
            serializers.ValidationError: If the status is invalid
        """
        if value not in dict(WebSocketDiscountRequest.STATUS_CHOICES):
            geo_structured_logger.warning(
                geo_logger,
                "Invalid request status",
                "websocket_request_validate_status",
                {'status': value}
            )
            raise serializers.ValidationError("Invalid status")
        return value

    def validate_location(self, value):
        """Validate the location format."""
        if not isinstance(value, Point):
            try:
                lat = float(value.get('latitude', 0))
                lon = float(value.get('longitude', 0))
                return Point(lon, lat)
            except (TypeError, ValueError, AttributeError):
                raise serializers.ValidationError(
                    "Location must be a valid Point or contain 'latitude' and 'longitude'"
                )
        return value

    def create(self, validated_data: Dict[str, Any]) -> WebSocketDiscountRequest:
        """
        Create a new websocket discount request.
        
        Args:
            validated_data: The validated data for creating the request
            
        Returns:
            The created request instance
        """
        try:
            request = WebSocketDiscountRequest.objects.create(
                user=self.context['request'].user,
                **validated_data
            )
            geo_structured_logger.info(
                geo_logger,
                "WebSocket discount request created successfully",
                "websocket_request_create",
                {
                    'request_id': request.id,
                    'user_id': request.user.id,
                    'query': request.query,
                    'status': request.status
                }
            )
            return request
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error creating websocket discount request",
                "websocket_request_create",
                e,
                {
                    'user_id': validated_data.get('user').id,
                    'query': validated_data.get('query')
                }
            )
            raise

    def update(self, instance: WebSocketDiscountRequest, validated_data: Dict[str, Any]) -> WebSocketDiscountRequest:
        """
        Update an existing websocket discount request.
        
        Args:
            instance: The request instance to update
            validated_data: The validated data for updating the request
            
        Returns:
            The updated request instance
        """
        try:
            request = super().update(instance, validated_data)
            geo_structured_logger.info(
                geo_logger,
                "WebSocket discount request updated successfully",
                "websocket_request_update",
                {
                    'request_id': request.id,
                    'user_id': request.user.id,
                    'status': request.status
                }
            )
            return request
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error updating websocket discount request",
                "websocket_request_update",
                e,
                {
                    'request_id': instance.id,
                    'user_id': instance.user.id,
                    'status': instance.status
                }
            )
            raise 