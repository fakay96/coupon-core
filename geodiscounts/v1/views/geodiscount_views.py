"""
API Views for the Discount Discovery System.

This module contains API endpoints for:
- Fetching all available discount categories (cached for 30 minutes).
- Fetching all available discounts.
- Finding nearby discounts based on user IP.
- Searching for discounts using vector embeddings.

Each endpoint is documented and uses Django Rest Framework (DRF) for serialization.
Caching is enabled where applicable to optimize performance.

Author: Your Name
Date: YYYY-MM-DD
"""

import re
import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from django.core.cache import cache
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_202_ACCEPTED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_504_GATEWAY_TIMEOUT,
)
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny

from geodiscounts.models import Discount, Category
from geodiscounts.v1.serializers.discount_serializers import DiscountSerializer, CategorySerializer

from geodiscounts.models import (
    Conversation, ConversationMessage, SearchRequest, 
)
from spellchecker import SpellChecker
from geodiscounts.v1.services.conversation_service import ConversationService, EnhancedSearchService
from geodiscounts.v1.utils.understand_context import GeminiEmbeddingClient
from geodiscounts.v1.serializers import ConversationSerializer

from coupon_core.utils.logging import geo_logger, geo_structured_logger, log_execution

# drf-yasg imports for OpenAPI documentation
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from rest_framework.request import Request
from django.utils import timezone
import logging
from django.db.models import Prefetch

# Greeting patterns
GREETING_PATTERNS = re.compile(r'^(hi|hello|hey|greetings)$', re.IGNORECASE)
MAX_DISTANCE_PARAM = 10
spell = SpellChecker()
learning_logger = logging.getLogger("search.learning")

def correct_spelling(text: str) -> str:
    """Correct common typos in user input."""
    words = text.split()
    corrected = [spell.correction(w) or w for w in words]
    return " ".join(corrected)

class CategoryView(APIView):
    """
    API endpoint to retrieve all available discount categories.

    - Categories are cached for 30 minutes to optimize performance and reduce database load.
    - Uses atomic caching to reduce redundant queries.
    """
    # Removed serializer_class to prevent automatic inclusion in the Swagger spec.
    permission_classes = [AllowAny]  # Public access

    @swagger_auto_schema(
        operation_description="Fetches all discount categories. Caches results for 30 minutes.",
        responses={
            HTTP_200_OK: openapi.Response(
                description="Success.",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "name": openapi.Schema(type=openapi.TYPE_STRING),
                            "image": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                        },
                    ),
                ),
            ),
            HTTP_404_NOT_FOUND: openapi.Response(
                description="No categories found.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal server error.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(type=openapi.TYPE_STRING),
                        "details": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
        },
    )
    @log_execution(geo_logger, 'category_list')
    def get(self, request) -> Response:
        """Get all available discount categories."""
        cache_key = "categories_list"
        try:
            categories = cache.get(cache_key)
            if categories is None:
                category_queryset = Category.objects.only("id", "name", "image")
                if not category_queryset.exists():
                    geo_structured_logger.info(
                        geo_logger,
                        "No categories found",
                        "category_list",
                        {'user_id': getattr(request.user, 'id', None)}
                    )
                    return Response(
                        {"message": "No categories available."},
                        status=HTTP_404_NOT_FOUND,
                    )
                serializer = CategorySerializer(category_queryset, many=True)
                categories = serializer.data
                cache.set(cache_key, categories, timeout=1800)
                
            geo_structured_logger.info(
                geo_logger,
                "Categories retrieved successfully",
                "category_list",
                {
                    'user_id': getattr(request.user, 'id', None),
                    'count': len(categories)
                }
            )
            return Response(categories, status=HTTP_200_OK)
            
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error retrieving categories",
                "category_list",
                e,
                {'user_id': getattr(request.user, 'id', None)}
            )
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=HTTP_500_INTERNAL_SERVER_ERROR,
            )

class ConversationalDiscountView(APIView):
    """
    Structured conversational AI view for discount search.

    Handles:
    - Conversation management and context tracking
    - Context-aware message processing
    - Search request tracking
    - User preference learning
    """
    permission_classes = [IsAuthenticated]

    @property
    def conversation_service(self):
        """Lazy initialization of conversation service."""
        try:
            if not hasattr(self, '_conversation_service'):
                self._conversation_service = ConversationService()
            return self._conversation_service
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Failed to initialize conversation service",
                "service_initialization",
                error=str(e)
            )
            raise

    @property
    def search_service(self):
        """Lazy initialization of search service."""
        try:
            if not hasattr(self, '_search_service'):
                self._search_service = EnhancedSearchService()
            return self._search_service
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Failed to initialize search service",
                "service_initialization",
                error=str(e)
            )
            raise

    @property
    def gemini_client(self):
        """Lazy initialization of Gemini client."""
        try:
            if not hasattr(self, '_gemini_client'):
                self._gemini_client = GeminiEmbeddingClient()
            return self._gemini_client
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Failed to initialize Gemini client",
                "service_initialization",
                error=str(e)
            )
            raise

    def _safe_service_call(self, service_property, method_name, *args, **kwargs):
        """Safely call a service method with proper error handling."""
        try:
            service = getattr(self, service_property)
            method = getattr(service, method_name)
            return method(*args, **kwargs)
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                f"Service call failed: {service_property}.{method_name}",
                "service_call",
                error=str(e),
                args=args,
                kwargs=kwargs
            )
            raise

    @swagger_auto_schema(
        operation_description="Send a message in conversational discount search",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={'message': openapi.Schema(type=openapi.TYPE_STRING)},
            required=['message']
        ),
        responses={HTTP_200_OK: openapi.Response(
            description="Conversation response",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message_id': openapi.Schema(type=openapi.TYPE_STRING),
                    'conversation_id': openapi.Schema(type=openapi.TYPE_STRING),
                    'response': openapi.Schema(type=openapi.TYPE_STRING),
                    'message_type': openapi.Schema(type=openapi.TYPE_STRING,
                                                 enum=['greeting','conversation','search_results','searching','error']),
                    'results': openapi.Schema(type=openapi.TYPE_ARRAY,items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    'suggestions': openapi.Schema(type=openapi.TYPE_ARRAY,items=openapi.Schema(type=openapi.TYPE_STRING)),
                    'context': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'search_id': openapi.Schema(type=openapi.TYPE_STRING)
                }
            ))}
    )
    def post(self, request: Request, *args, **kwargs) -> Response:
        """Handle incoming messages and return appropriate responses."""
        try:
            # Get conversation ID from query params or create new
            conv_id = request.query_params.get('conversation_id')
            if not conv_id:
                conv_id = str(uuid.uuid4())

            # Get or create conversation
            conversation = self._safe_service_call(
                'conversation_service',
                'get_or_create_conversation',
                user=request.user,
                conversation_id=conv_id
            )

            # Process message and get response
            response = self._process_message(request, conversation)

            return Response(response)

        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error processing message",
                "message_processing",
                error=str(e)
            )
            return Response(
                {"error": "Failed to process message"},
                status=HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _process_message(self, request: Request, conversation: Conversation) -> Dict:
        """Process incoming message and return appropriate response."""
        try:
            message = request.data.get('message', '')
            if not message:
                return {"error": "Message is required"}

            # Get conversation context
            context = self._safe_service_call(
                'conversation_service',
                'get_conversation_context',
                conversation
            )

            # Handle general conversation
            if not self._is_search_query(message):
                return self._handle_general_conversation(message, conversation)

            # Handle search query
            return self._handle_search_query(message, conversation, context)

        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error in message processing",
                "message_processing",
                error=str(e)
            )
            raise

    def _handle_general_conversation(self, message: str, conversation: Conversation) -> Dict:
        """Handle non-search conversation messages."""
        try:
            # Extract user preferences
            self._safe_service_call(
                'conversation_service',
                'extract_user_preferences',
                message
            )

            # Generate response using Gemini
            response = self.gemini_client.generate_content(
                f"User message: {message}\nGenerate a helpful response:"
            )

            return {
                "type": "conversation",
                "message": response.text,
                "conversation_id": conversation.id
            }

        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error in general conversation",
                "conversation_handling",
                error=str(e)
            )
            raise

    def _handle_search_query(self, message: str, conversation: Conversation, context: Dict) -> Dict:
        """Handle search-related queries."""
        try:
            # Enhance search query
            enhanced = self.gemini_client.generate_content(
                f"Enhance this search query: {message}"
            )

            # Create search request
            search_request = SearchRequest(
                query=enhanced.text,
                context=context
            )

            # Perform search
            search_results = self._safe_service_call(
                'search_service',
                'find_discounts',
                req=search_request,
                timeout=30
            )

            return {
                "type": "search_results",
                "results": search_results,
                "conversation_id": conversation.id
            }

        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error in search query handling",
                "search_handling",
                error=str(e)
            )
            raise

    def get(self, request: Request, conversation_id: str = None) -> Response:
        """Get conversation details or list user's conversations."""
        try:
            if conversation_id:
                # Get specific conversation
                conversation = Conversation.objects.get(
                    id=conversation_id,
                    user=request.user
                )
                serializer = ConversationSerializer(conversation)
                return Response(serializer.data)
            
            else:
                # Get user's recent conversations
                conversations = Conversation.objects.filter(
                    user=request.user,
                    status=Conversation.ConversationStatus.ACTIVE
                ).prefetch_related('messages')[:10]
                
                serializer = ConversationSerializer(conversations, many=True)
                return Response({
                    'conversations': serializer.data,
                    'total_count': conversations.count()
                })
                
        except Conversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found"},
                status=HTTP_404_NOT_FOUND
            )
    
    @swagger_auto_schema(
        operation_description="Archive or delete a conversation",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'action': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['archive', 'delete']
                )
            }
        )
    )
    def patch(self, request: Request, conversation_id: str) -> Response:
        """Update conversation status."""
        try:
            conversation = Conversation.objects.get(
                id=conversation_id,
                user=request.user
            )
            
            action = request.data.get('action')
            if action == 'archive':
                conversation.status = Conversation.ConversationStatus.ARCHIVED
            elif action == 'delete':
                conversation.status = Conversation.ConversationStatus.DELETED
            else:
                return Response(
                    {"error": "Invalid action. Use 'archive' or 'delete'"},
                    status=HTTP_400_BAD_REQUEST
                )
            
            conversation.save()
            return Response({"status": "updated"})
            
        except Conversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found"},
                status=HTTP_404_NOT_FOUND
            )