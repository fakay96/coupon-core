"""Serializers for WebSocket discount requests."""

from rest_framework import serializers
from geodiscounts.models import WebSocketDiscountRequest, Category
from django.contrib.gis.geos import Point

class WebSocketDiscountRequestSerializer(serializers.ModelSerializer):
    """Serializer for WebSocket discount requests."""
    
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = WebSocketDiscountRequest
        fields = [
            'request_id',
            'user',
            'location',
            'radius',
            'category',
            'status',
            'results',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['request_id', 'user', 'status', 'results', 'created_at', 'updated_at']
    
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
    
    def create(self, validated_data):
        """Create a new WebSocket discount request."""
        request = WebSocketDiscountRequest.objects.create(
            user=self.context['request'].user,
            **validated_data
        )
        return request 