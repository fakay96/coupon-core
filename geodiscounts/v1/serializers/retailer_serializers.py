"""
Serializers for retailer-related models in the Discount Discovery System.
"""

from rest_framework import serializers
from geodiscounts.models import Retailer, Discount


class RetailerSerializer(serializers.ModelSerializer):
    """
    Serializer for basic retailer information.
    Used for creating, updating, and retrieving retailer details.
    """
    class Meta:
        model = Retailer
        fields = [
            'id', 
            'name', 
            'contact_info', 
            'location', 
            'owner', 
            'analytics_data',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['owner', 'id', 'created_at', 'updated_at']


class NearbyRetailersSerializer(serializers.ModelSerializer):
    """
    Serializer for nearby retailers, including distance information.
    """
    distance = serializers.SerializerMethodField()

    class Meta:
        model = Retailer
        fields = [
            'id', 
            'name', 
            'contact_info', 
            'location', 
            'distance'
        ]
    
    def get_distance(self, obj):
        """
        Calculate and return distance if available in the queryset.
        """
        # Check if distance has been annotated to the queryset
        if hasattr(obj, 'distance'):
            return obj.distance.km
        return None


class RetailerAnalyticsSerializer(serializers.Serializer):
    """
    Serializer for retailer analytics data.
    Provides insights into discount performance and metrics.
    """
    total_discounts = serializers.IntegerField()
    active_discounts = serializers.IntegerField()
    expired_discounts = serializers.IntegerField()
    avg_discount_value = serializers.FloatField()
    total_shared_discounts = serializers.IntegerField()
    active_shared_discounts = serializers.IntegerField()

    class Meta:
        fields = [
            'total_discounts', 
            'active_discounts', 
            'expired_discounts', 
            'avg_discount_value', 
            'total_shared_discounts', 
            'active_shared_discounts'
        ]