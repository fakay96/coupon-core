from rest_framework import serializers
from django.contrib.auth import get_user_model
from geodiscounts.models import (
    Conversation, ConversationMessage, SearchRequest, 
    UserPreference, ConversationContext
)

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user information for conversations."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']
        read_only_fields = ['id', 'username']


class SearchRequestSerializer(serializers.ModelSerializer):
    """Serializer for search requests within conversations."""
    
    location = serializers.SerializerMethodField()
    
    class Meta:
        model = SearchRequest
        fields = [
            'id', 'query', 'location', 'radius', 'status', 
            'result_count', 'processing_time', 'created_at',
            'completed_at', 'error_message'
        ]
        read_only_fields = [
            'id', 'status', 'result_count', 'processing_time',
            'created_at', 'completed_at', 'error_message'
        ]
    
    def get_location(self, obj):
        """Convert Point to lat/lng dict."""
        if obj.location:
            return {
                'latitude': obj.location.y,
                'longitude': obj.location.x
            }
        return None


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for conversation messages."""
    
    search_request = SearchRequestSerializer(read_only=True)
    
    class Meta:
        model = ConversationMessage
        fields = [
            'id', 'role', 'content', 'message_type', 'metadata',
            'search_request', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at'
        ]
    
    def to_representation(self, instance):
        """Customize the output representation."""
        data = super().to_representation(instance)
        
        # Add human-readable role
        data['role_display'] = instance.get_role_display()
        data['message_type_display'] = instance.get_message_type_display()
        
        # Format timestamps
        if instance.created_at:
            data['timestamp'] = instance.created_at.isoformat()
        
        return data


class ConversationContextSerializer(serializers.ModelSerializer):
    """Serializer for conversation context."""
    
    class Meta:
        model = ConversationContext
        fields = [
            'id', 'stage', 'topics_discussed', 'preferences_mentioned',
            'last_search_query', 'search_history', 'context_data',
            'updated_at'
        ]
        read_only_fields = ['id', 'updated_at']


class ConversationSerializer(serializers.ModelSerializer):
    """Main serializer for conversations."""
    
    user = UserBasicSerializer(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    context = ConversationContextSerializer(read_only=True)
    last_location = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'user', 'title', 'status', 'last_location', 
            'last_radius', 'created_at', 'updated_at', 'last_activity',
            'messages', 'context', 'message_count', 'last_message'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'last_activity'
        ]
    
    def get_last_location(self, obj):
        """Convert Point to lat/lng dict."""
        if obj.last_location:
            return {
                'latitude': obj.last_location.y,
                'longitude': obj.last_location.x
            }
        return None
    
    def get_message_count(self, obj):
        """Get total message count."""
        return obj.messages.count()
    
    def get_last_message(self, obj):
        """Get the most recent message."""
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return {
                'id': str(last_msg.id),
                'content': last_msg.content[:100] + '...' if len(last_msg.content) > 100 else last_msg.content,
                'role': last_msg.role,
                'message_type': last_msg.message_type,
                'created_at': last_msg.created_at.isoformat()
            }
        return None
    
    def to_representation(self, instance):
        """Customize the output representation."""
        data = super().to_representation(instance)
        
        # Add human-readable status
        data['status_display'] = instance.get_status_display()
        
        # Format timestamps
        for field in ['created_at', 'updated_at', 'last_activity']:
            if data.get(field):
                data[field] = instance.__dict__[field].isoformat()
        
        return data


class ConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for conversation lists."""
    
    last_location = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    last_message_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'status', 'last_location', 'last_radius',
            'created_at', 'updated_at', 'last_activity', 
            'message_count', 'last_message_preview'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'last_activity'
        ]
    
    def get_last_location(self, obj):
        """Convert Point to lat/lng dict."""
        if obj.last_location:
            return {
                'latitude': obj.last_location.y,
                'longitude': obj.last_location.x
            }
        return None
    
    def get_message_count(self, obj):
        """Get total message count."""
        return obj.messages.count()
    
    def get_last_message_preview(self, obj):
        """Get a preview of the last message."""
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            preview = last_msg.content[:50] + '...' if len(last_msg.content) > 50 else last_msg.content
            return {
                'preview': preview,
                'role': last_msg.role,
                'created_at': last_msg.created_at.isoformat()
            }
        return None


class UserPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for user preferences learned from conversations."""
    
    class Meta:
        model = UserPreference
        fields = [
            'id', 'preference_type', 'preference_key', 'preference_value',
            'confidence_score', 'source', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at'
        ]


# Specialized serializers for API responses

class ConversationResponseSerializer(serializers.Serializer):
    """Serializer for conversation API responses."""
    
    message_id = serializers.UUIDField()
    conversation_id = serializers.UUIDField()
    response = serializers.CharField()
    message_type = serializers.ChoiceField(choices=[
        ('greeting', 'Greeting'),
        ('conversation', 'Conversation'),  
        ('search_results', 'Search Results'),
        ('searching', 'Searching'),
        ('error', 'Error')
    ])
    results = serializers.ListField(child=serializers.DictField(), required=False)
    suggestions = serializers.ListField(child=serializers.CharField(), required=False)
    context = serializers.DictField(required=False)
    search_id = serializers.UUIDField(required=False)
    metadata = serializers.DictField(required=False)


class ConversationCreateSerializer(serializers.Serializer):
    """Serializer for creating new conversation messages."""
    
    message = serializers.CharField(max_length=2000, help_text="User message/query")
    conversation_id = serializers.UUIDField(required=False, help_text="UUID of existing conversation")
    radius = serializers.FloatField(default=5000, min_value=100, max_value=50000, 
                                   help_text="Search radius in meters")
    location = serializers.DictField(required=False, help_text="User location override")
    
    def validate_location(self, value):
        """Validate location data."""
        if value:
            if 'latitude' not in value or 'longitude' not in value:
                raise serializers.ValidationError("Location must include both latitude and longitude")
            
            try:
                lat = float(value['latitude'])
                lng = float(value['longitude'])
                
                if not (-90 <= lat <= 90):
                    raise serializers.ValidationError("Latitude must be between -90 and 90")
                if not (-180 <= lng <= 180):
                    raise serializers.ValidationError("Longitude must be between -180 and 180")
                    
            except (ValueError, TypeError):
                raise serializers.ValidationError("Latitude and longitude must be valid numbers")
        
        return value


class ConversationUpdateSerializer(serializers.Serializer):
    """Serializer for updating conversations."""
    
    action = serializers.ChoiceField(choices=['archive', 'delete'], 
                                   help_text="Action to perform on conversation")
    title = serializers.CharField(max_length=200, required=False,
                                 help_text="Update conversation title")


# Nested serializers for complex responses

class ConversationDetailSerializer(ConversationSerializer):
    """Detailed serializer with full message history."""
    
    messages = MessageSerializer(many=True, read_only=True)
    user_preferences = UserPreferenceSerializer(source='user.userpreference_set', 
                                               many=True, read_only=True)
    
    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ['user_preferences']


class MessageWithContextSerializer(MessageSerializer):
    """Message serializer with conversation context."""
    
    conversation = ConversationListSerializer(read_only=True)
    
    class Meta(MessageSerializer.Meta):
        fields = MessageSerializer.Meta.fields + ['conversation']