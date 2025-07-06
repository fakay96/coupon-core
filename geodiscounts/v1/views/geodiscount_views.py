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

import asyncio
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
from coupon_core.utils.async_authentication import AsyncJWTAuthentication

# drf-yasg imports for OpenAPI documentation
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from rest_framework.request import Request
from django.utils import timezone
import logging
from django.db.models import Prefetch
from asgiref.sync import sync_to_async, async_to_sync

# Greeting patterns
GREETING_PATTERNS = re.compile(r'^(hi|hello|hey|greetings)$', re.IGNORECASE)
MAX_DISTANCE_PARAM = 10
spell = SpellChecker()
learning_logger = logging.getLogger("search.learning")

def get_gemini_client():
    """Lazily initialize and cache the GeminiEmbeddingClient."""
    if not hasattr(get_gemini_client, '_client'):
        get_gemini_client._client = GeminiEmbeddingClient()
    return get_gemini_client._client

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
        tags=['Categories'],
    )
    @log_execution(geo_logger, 'category_list')
    async def get(self, request) -> Response:
        """Get all available discount categories."""
        cache_key = "categories_list"
        try:
            categories_data = cache.get(cache_key)
            if categories_data is None:
                # Fetching data asynchronously
                category_queryset = Category.objects.only("id", "name", "image")
                if not await category_queryset.aexists():
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
                
                # Convert async queryset to list for serializer (serializers are typically sync)
                categories_list = await asyncio.to_thread(list, category_queryset)
                serializer = CategorySerializer(categories_list, many=True)
                categories_data = serializer.data
                cache.set(cache_key, categories_data, timeout=1800) # Cache operations are thread-safe
                
            geo_structured_logger.info(
                geo_logger,
                "Categories retrieved successfully",
                "category_list",
                {
                    'user_id': getattr(request.user, 'id', None),
                    'count': len(categories_data)
                }
            )
            return Response(categories_data, status=HTTP_200_OK)
            
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
    authentication_classes = [AsyncJWTAuthentication]

    def __init__(self):
        super().__init__()
        # Lazy initialization - don't create services until needed
        self._conversation_service = None
        self._search_service = None
        self._gemini_client = None

    @property
    def conversation_service(self):
        """Lazy load conversation service."""
        if self._conversation_service is None:
            self._conversation_service = ConversationService()
        return self._conversation_service

    @property
    def search_service(self):
        """Lazy load search service."""
        if self._search_service is None:
            self._search_service = EnhancedSearchService()
        return self._search_service

    @property
    def gemini_client(self):
        """Lazy load Gemini client."""
        if self._gemini_client is None:
            self._gemini_client = get_gemini_client()
        return self._gemini_client

    @swagger_auto_schema(
        operation_description="""
        Send a message in conversational discount search.
        
        This endpoint allows users to interact with an AI-powered discount discovery system using natural language.
        The system can understand queries like "Show me fashion discounts near me" or "What grocery deals are available?"
        and will respond with relevant discounts, suggestions, and follow-up questions.
        
        **Features:**
        - Natural language processing for discount queries
        - Location-based search using client coordinates
        - Conversation context maintenance
        - Intelligent suggestions for follow-up queries
        - Real-time discount data retrieval
        
        **Example Queries:**
        - "Show me fashion discounts within 2km"
        - "What grocery deals are available today?"
        - "Find electronics with at least 20% off"
        - "Show me all Penny store discounts"
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'message': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description="Natural language query describing the desired discounts. Examples: 'Show me fashion discounts', 'Find grocery deals near me', 'What electronics are on sale?'",
                    example="Show me fashion discounts within 3km"
                ),
                'conversation_id': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description="Optional conversation ID to continue an existing conversation. If not provided, a new conversation will be created.",
                    example="conv_12345678-1234-1234-1234-123456789abc"
                ),
                'radius': openapi.Schema(
                    type=openapi.TYPE_NUMBER, 
                    description="Search radius in meters. Default is 5000m (5km). Maximum is 50000m (50km).",
                    default=5000,
                    minimum=100,
                    maximum=50000,
                    example=3000
                )
            },
            required=['message'],
            example={
                "message": "Show me fashion discounts within 2km",
                "conversation_id": "conv_12345678-1234-1234-1234-123456789abc",
                "radius": 2000
            }
        ),
        responses={
            HTTP_200_OK: openapi.Response(
                description="Conversation response with discount results and suggestions",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message_id': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Unique identifier for this message response",
                            example="msg_87654321-4321-4321-4321-cba987654321"
                        ),
                        'conversation_id': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Conversation ID for continuing the chat",
                            example="conv_12345678-1234-1234-1234-123456789abc"
                        ),
                        'response': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="AI-generated response to the user's query",
                            example="I found 15 fashion discounts within 2km of your location. Here are the best deals:"
                        ),
                        'message_type': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            enum=['greeting','conversation','search_results','searching','error'],
                            description="Type of message response. 'greeting' for initial interactions, 'conversation' for ongoing chat, 'search_results' when discounts are found, 'searching' when processing, 'error' for issues."
                        ),
                        'results': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER, example=123),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING, example="Nike Air Max Sneakers"),
                                    'store_name': openapi.Schema(type=openapi.TYPE_STRING, example="Penny"),
                                    'original_price': openapi.Schema(type=openapi.TYPE_NUMBER, example=89.99),
                                    'sale_price': openapi.Schema(type=openapi.TYPE_NUMBER, example=59.99),
                                    'discount_percentage': openapi.Schema(type=openapi.TYPE_STRING, example="33%"),
                                    'distance': openapi.Schema(type=openapi.TYPE_NUMBER, example=1.2),
                                    'valid_until': openapi.Schema(type=openapi.TYPE_STRING, example="2024-01-15"),
                                    'category': openapi.Schema(type=openapi.TYPE_STRING, example="fashion")
                                }
                            ),
                            description="Array of discount items matching the search criteria"
                        ),
                        'suggestions': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description="Suggested follow-up queries to help users discover more discounts",
                            example=["Show me grocery deals", "Find electronics discounts", "What's on sale at Penny?"]
                        ),
                        'context': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description="Conversation context for maintaining chat state",
                            properties={
                                'search_history': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                                'preferences': openapi.Schema(type=openapi.TYPE_OBJECT),
                                'last_query': openapi.Schema(type=openapi.TYPE_STRING)
                            }
                        ),
                        'search_id': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Unique identifier for this search operation",
                            example="search_98765432-5432-5432-5432-210987654321"
                        ),
                        'metadata': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description="Additional metadata about the search results",
                            properties={
                                'total_results': openapi.Schema(type=openapi.TYPE_INTEGER, example=15),
                                'search_time_ms': openapi.Schema(type=openapi.TYPE_INTEGER, example=245),
                                'radius_used': openapi.Schema(type=openapi.TYPE_NUMBER, example=2000),
                                'categories_found': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING))
                            }
                        )
                    }
                )
            ),
            HTTP_400_BAD_REQUEST: openapi.Response(
                description="Bad request - Invalid input parameters",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Error message describing what went wrong",
                            example="Message is required"
                        ),
                        'details': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Additional error details if available",
                            example="The message field cannot be empty"
                        )
                    }
                )
            ),
            HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Internal server error - Something went wrong on the server",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Generic error message",
                            example="Internal server error"
                        ),
                        'details': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Technical error details for debugging",
                            example="Failed to process conversation request"
                        )
                    }
                )
            )
        },
        tags=['Discounts'],
    )
    def post(self, request: Request) -> Response:
        """Handle conversational discount search requests."""
        # Use sync_to_async to handle the async operations
        return async_to_sync(self._async_post)(request)
    
    async def _async_post(self, request: Request) -> Response:
        """Async implementation of the post method."""
        try:
            raw = request.data.get('message','').strip()
            if not raw:
                return Response({"error":"Message is required"},status=HTTP_400_BAD_REQUEST)
            message_content = correct_spelling(raw)

            conv_id = request.data.get('conversation_id')
            lat = request.client_latitude
            lon = request.client_longitude
            radius = float(request.data.get('radius',5000))
            loc_data = {"latitude":lat,"longitude":lon}

            # Handle anonymous users by creating a temporary guest user
            user = request.user
            if user.is_anonymous:
                from authentication.models import CustomUser
                # Create a temporary guest user for anonymous requests
                user, created = await sync_to_async(CustomUser.objects.get_or_create)(
                    email="anonymous@temp.com",
                    defaults={
                        "username": "anonymous_user",
                        "is_guest": True,
                    }
                )
                if created:
                    await sync_to_async(user.set_unusable_password)()
                    await sync_to_async(user.save)()

            conversation = await self.conversation_service.async_get_or_create(
                user=user, conv_id=conv_id
            )
            user_msg = await ConversationMessage.objects.acreate(
                conversation=conversation,
                role=ConversationMessage.MessageRole.USER,
                content=message_content,
                message_type=self._determine_message_type(message_content)
            )
            context = await self.conversation_service.async_get_context(conversation)
            history = await self.conversation_service.async_get_recent_messages(conversation)

            if user_msg.message_type == ConversationMessage.MessageType.GREETING:
                response_data = self._process_message(
                    message=user_msg, conversation=conversation,
                    request=request, radius=radius, location_data=loc_data,
                    context=context, history=history
                )
            elif user_msg.message_type == ConversationMessage.MessageType.SEARCH_QUERY:
                response_data = await self._handle_search_query(
                    user_msg, conversation, request, radius, loc_data, context, history
                )
            else:
                response_data = await self._handle_general_conversation(user_msg, context, history)

            assistant_msg = await ConversationMessage.objects.acreate(
                conversation=conversation,
                role=ConversationMessage.MessageRole.ASSISTANT,
                content=response_data['response'],
                message_type=response_data['message_type'],
                metadata=response_data.get('metadata',{}),
                search_request=response_data.get('search_request')
            )
            await self.conversation_service.async_update_context(conversation)
            if 'search_id' in response_data:
                learning_logger.info("Search run",extra={
                    'query':user_msg.content,'search_id':response_data['search_id'],
                    'count':len(response_data.get('results',[])),
                    'suggestions':response_data.get('suggestions',[])
                })
            response_data.update({
                'message_id':str(assistant_msg.id),
                'conversation_id':str(conversation.id)
            })
            return Response(response_data, status=HTTP_200_OK)
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error processing conversational message",
                "conversational_discount",
                e,
                {'user_id': getattr(request.user, 'id', None)}
            )
            return Response(
                {"error": "Internal server error"},
                status=HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _determine_message_type(self, content: str) -> str:
        """Determine the type of user message."""
        content_lower = content.lower()
        
        # Check for greetings
        greeting_patterns = [
            r'^(hi|hello|hey|greetings|good\s(morning|afternoon|evening))$'
        ]
        if any(re.match(pattern, content_lower) for pattern in greeting_patterns):
            return ConversationMessage.MessageType.GREETING
        
        # Check for search queries
        search_keywords = [
            'find', 'search', 'look for', 'discount', 'deal', 'offer',
            'coupon', 'sale', 'cheap', 'near me', 'around here'
        ]
        if any(keyword in content_lower for keyword in search_keywords):
            return ConversationMessage.MessageType.SEARCH_QUERY
        
        return ConversationMessage.MessageType.CONVERSATION # Default
    
    def _process_message(
        self, 
        message: ConversationMessage, 
        conversation: Conversation,
        request: Request, 
        radius: float,
        location_data: dict,
        context: dict,
        history: list
    ) -> dict:
        if message.message_type == ConversationMessage.MessageType.GREETING:
            return self._handle_greeting(context)
        # For other types, should not be called
        return {}
    
    def _handle_greeting(self, context: Dict) -> Dict[str, Any]:
        """Handle greeting messages."""
        stage = context.get('stage', 'initial')
        if stage == 'initial':
            response = "Hello! I'm here to help you find the best discounts and deals. What are you looking for today?"
            suggestions = [
                "Find restaurants near me",
                "Show me clothing deals", 
                "What discounts are available nearby?"
            ]
        else:
            response = "Hi again! How can I continue helping you find great deals?"
            suggestions = [
                "Search for different discounts",
                "Expand my search area",
                "Show me more options"
            ]
        return {
            'response': response,
            'message_type': ConversationMessage.MessageType.GREETING,
            'suggestions': suggestions,
            'context': context,
            'metadata': {'greeting_type': stage}
        }
    
    async def _enhance_search_query(self, query: str, context: Dict, history: List[str]) -> Dict[str, Any]:
        """Enhance search query using fast heuristics instead of expensive LLM calls."""
        try:
            # Use simple keyword-based enhancement for speed
            query_lower = query.lower()
            
            # Simple category detection
            category_keywords = {
                'fashion': ['clothing', 'shoes', 'dress', 'shirt', 'pants', 'fashion', 'style'],
                'grocery': ['food', 'grocery', 'fresh', 'organic', 'produce', 'meat', 'dairy'],
                'electronics': ['phone', 'laptop', 'computer', 'electronics', 'tech', 'gadget'],
                'home': ['furniture', 'home', 'kitchen', 'bedroom', 'living room', 'decor'],
                'beauty': ['makeup', 'beauty', 'cosmetics', 'skincare', 'perfume'],
                'sports': ['sport', 'fitness', 'gym', 'running', 'exercise', 'athletic'],
                'entertainment': ['movie', 'game', 'book', 'music', 'entertainment']
            }
            
            detected_category = 'other'
            category_confidence = 0.5
            
            for category, keywords in category_keywords.items():
                for keyword in keywords:
                    if keyword in query_lower:
                        detected_category = category
                        category_confidence = 0.8
                        break
                if category_confidence > 0.5:
                    break
            
            # Simple search type detection
            search_type = 'general'
            if any(word in query_lower for word in ['near', 'around', 'location', 'distance']):
                search_type = 'location'
            elif any(word in query_lower for word in ['brand', 'specific', 'exact']):
                search_type = 'specific'
            elif detected_category != 'other':
                search_type = 'category'
            
            # Simple price range detection
            price_range = None
            if any(word in query_lower for word in ['cheap', 'budget', 'under', 'less than']):
                price_range = {'max': 50}
            elif any(word in query_lower for word in ['expensive', 'premium', 'luxury']):
                price_range = {'min': 100}
            
            # Simple brand detection
            brand_preferences = []
            common_brands = ['nike', 'adidas', 'apple', 'samsung', 'penny', 'aldi', 'lidl']
            for brand in common_brands:
                if brand in query_lower:
                    brand_preferences.append(brand)
            
            return {
                'query': query,  # Keep original query for now
                'confidence': category_confidence,
                'search_type': search_type,
                'category': {
                    'name': detected_category,
                    'confidence': category_confidence
                },
                'filters': {
                    'price_range': price_range,
                    'brand': brand_preferences[0] if brand_preferences else None
                }
            }
            
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Query enhancement failed",
                "query_enhancement",
                {"error": str(e), "context": {"query": query}}
            )
            # Return default structure on error
            return {
                'query': query,
                'confidence': 0.5,
                'search_type': 'general',
                'category': {
                    'name': 'other',
                    'confidence': 0.5
                },
                'filters': {
                    'price_range': {'min': 0, 'max': float('inf')}
                }
            }

    async def _handle_search_query(
        self,
        message: ConversationMessage,
        conversation: Conversation,
        request: Request,  # Keep request for now, but client_latitude/longitude might need specific handling in async views
        radius: float,
        location_data: Dict,  # Passed from post()
        context: Dict,  # Passed from _process_message
        history: List[str],
    ) -> Dict[str, Any]:  # Now async
        """Handle search query messages (async)."""
        
        # Get user location (remains synchronous as it reads from request attributes)
        try:
            if location_data.get('latitude') and location_data.get('longitude'):
                latitude = float(location_data['latitude'])
                longitude = float(location_data['longitude'])
            else:
                latitude = float(request.client_latitude)
                longitude = float(request.client_longitude)
        except (TypeError, ValueError, AttributeError):
            return {
                'response': "I need your location to search for nearby discounts. Please share your location and try again.",
                'message_type': ConversationMessage.MessageType.ERROR,
                'suggestions': ["Share your location", "Try again"]
            }
        
        # Enhance the query using Gemini (now async)
        query_enhancement = await self._enhance_search_query(message.content, context, history)
        
        # Create search request with enhanced query (now async)
        search_request = await SearchRequest.objects.acreate(
            conversation=conversation,
            query=query_enhancement['query'],
            location=Point(longitude, latitude),
            radius=radius,
            search_context={
                **context,
                'enhanced_query': query_enhancement,
                'original_query': message.content
            }
        )
        
        # Update conversation location (now async)
        conversation.last_location = Point(longitude, latitude) # Point creation is sync
        conversation.last_radius = radius
        await conversation.asave(update_fields=['last_location', 'last_radius'])
        
        # Perform search (now async)
        # This assumes self.search_service.find_discounts will be made async
        try:
            search_results = await self.search_service.find_discounts(
                req=search_request, # search_request is now an async created object
                timeout=30 # Timeout handling might need review in fully async context
            )
            
            if search_results['status'] == 'completed':
                result_count = len(search_results['results'])
                if result_count > 0:
                    if query_enhancement['confidence'] > 0.7:
                        response = f"I found {result_count} great deals matching your search for {query_enhancement['query']}!"
                    else:
                        response = f"I found {result_count} deals that might interest you!"
                else: # No specific results
                    category_deals = await self._get_all_categories() # Now async
                    if category_deals:
                        category_name = query_enhancement.get('category', {}).get('name', '')
                        if category_name and category_name != 'other':
                            response = f"I couldn't find exactly what you're looking for, but here are some great {category_name} deals in your area!"
                        else:
                            response = "I couldn't find exactly what you're looking for, but here are some great deals in your area!"
                    else:
                        response = "I couldn't find any deals matching your search. Would you like to try a different search term?"
                    search_results['results'] = category_deals
                    result_count = len(category_deals)
                
                # Generate suggestions based on the results (now async)
                try:
                    suggestions = await self._generate_search_suggestions(search_results['results'])
                except Exception as e:
                    geo_structured_logger.error(
                        geo_logger,
                        "Failed to generate suggestions (async)",
                        "suggestion_generation",
                        {"error": str(e)}
                    )
                    suggestions = ["Try a different search term", "Browse all categories", "Expand your search area"]
                return {
                    'response': response,
                    'message_type': ConversationMessage.MessageType.SEARCH_RESULTS,
                    'results': search_results['results'],
                    'suggestions': suggestions,
                    'context': {
                        **context,
                        'enhanced_query': query_enhancement
                    },
                    'search_id': str(search_request.id),
                    'metadata': {
                        'result_count': result_count,
                        'search_time': search_results.get('processing_time'), # Assuming this is part of search_results
                        'query_confidence': query_enhancement['confidence']
                    }
                }
            
            elif search_results['status'] == 'timeout':
                category_deals = await self._get_all_categories() # Now async
                return {
                    'response': "I couldn't complete your search in time, but here are some great deals in your area!",
                    'message_type': ConversationMessage.MessageType.SEARCH_RESULTS,
                    'results': category_deals,
                    'suggestions': [
                        "Try a different search term",
                        "Browse all categories",
                        "Expand your search area"
                    ],
                    'search_id': str(search_request.id)
                }
            
            else:  # Failed search status
                category_deals = await self._get_all_categories() # Now async
                search_request.status = SearchRequest.SearchStatus.FAILED
                search_request.error_message = search_results.get('error_message', "Unknown search failure")
                await search_request.asave(update_fields=['status', 'error_message'])
                return {
                    'response': "I couldn't complete your search, but here are some great deals in your area!",
                    'message_type': ConversationMessage.MessageType.SEARCH_RESULTS,
                    'results': category_deals,
                    'suggestions': [
                        "Try a different search term",
                        "Browse all categories",
                        "Expand your search area"
                    ],
                    'search_id': str(search_request.id)
                }
                
        except Exception as e: # Catch-all for other exceptions during the process
            geo_structured_logger.error(
                geo_logger,
                "Error in _handle_search_query (async)",
                "search_handling",
                {"error": str(e), "search_id": str(search_request.id) if 'search_request' in locals() else None}
            )
            category_deals = await self._get_all_categories() # Now async
            if 'search_request' in locals():
                search_request.status = SearchRequest.SearchStatus.FAILED
                search_request.error_message = str(e)
                await search_request.asave(update_fields=['status', 'error_message'])
            return {
                'response': "I encountered an issue with your search, but here are some great deals in your area!",
                'message_type': ConversationMessage.MessageType.SEARCH_RESULTS,
                'results': category_deals,
                'suggestions': [
                    "Try a different search term",
                    "Browse all categories",
                    "Expand your search area"
                ],
                'search_id': str(search_request.id) if 'search_request' in locals() else None
            }

    async def _get_all_categories(self) -> List[Dict]: # Now async
        """Get all available categories and their discounts grouped by retailer (async)."""
        try:
            # Use proper async ORM operations
            categories_qs = Category.objects.filter(discounts__isnull=False).distinct()
            
            results = []
            async for category_item in categories_qs:
                # Get discounts for this category
                discounts_qs = category_item.discounts.select_related('retailer').order_by('retailer__name', '-created_at')
                
                retailer_groups = {}
                async for discount_item in discounts_qs:
                    retailer = discount_item.retailer
                    if retailer:
                        if retailer.id not in retailer_groups:
                            retailer_groups[retailer.id] = {
                                'id': str(retailer.id), 'name': retailer.name, 'type': 'retailer',
                                'image': None, 'description': f"Browse all {retailer.name} deals",
                                'discounts': []
                            }
                        retailer_groups[retailer.id]['discounts'].append({
                            'id': str(discount_item.id), 'title': discount_item.title, 'url': discount_item.url,
                            'type': 'discount', 'category': {'id': str(category_item.id), 'name': category_item.name}
                        })
                
                if retailer_groups:
                    category_data = {
                        'id': str(category_item.id), 'name': category_item.name, 'type': 'category',
                        'image': category_item.image.url if category_item.image else None,
                        'description': f"Browse all {category_item.name} deals",
                        'discount_count': await category_item.discounts.acount(),
                        'retailers': list(retailer_groups.values())
                    }
                    results.append(category_data)
            
            return results
            
        except Exception as e:
            geo_structured_logger.error(geo_logger, "Failed to get all categories (async)", "category_list", {'error': str(e)})
            return []
    
    async def _handle_general_conversation(
        self, message: ConversationMessage, context: Dict, history: List[str]
    ) -> Dict[str, Any]:
        """Handle general conversation messages (async)."""
        
        # Extract preferences from conversation (now async)
        await self.conversation_service.async_extract_preferences(message)
        
        # Generate contextual response using Gemini (now async)
        result = await self._generate_contextual_response(
            message.content, context, history
        )

        suggestions = result.get(
            "suggestions",
            [
                "Search for discounts near me",
                "Find specific deals",
                "What's available in my area?",
            ],
        )

        return {
            "response": result.get("response"),
            "message_type": ConversationMessage.MessageType.CONVERSATION,
            "context": context,
            "suggestions": suggestions,
        }
    
    async def _generate_contextual_response(
        self, content: str, context: Dict, history: List[str]
    ) -> Dict[str, Any]:
        """Generate contextual response using fast heuristics instead of expensive LLM calls."""
        try:
            content_lower = content.lower()
            
            # Simple response generation based on content keywords
            if any(word in content_lower for word in ['thank', 'thanks', 'appreciate']):
                response = "You're welcome! I'm here to help you find the best deals. Is there anything specific you're looking for?"
                suggestions = ["Find discounts near me", "Show me today's deals", "What's on sale?"]
            
            elif any(word in content_lower for word in ['help', 'assist', 'support']):
                response = "I can help you find discounts and deals! Just tell me what you're looking for - like 'fashion deals' or 'grocery discounts near me'."
                suggestions = ["Find fashion deals", "Show me grocery discounts", "What's available nearby?"]
            
            elif any(word in content_lower for word in ['how', 'what', 'where', 'when']):
                response = "I can help you find that! Try asking me something like 'Show me fashion deals near me' or 'Find grocery discounts'."
                suggestions = ["Show me fashion deals", "Find grocery discounts", "What's on sale today?"]
            
            elif any(word in content_lower for word in ['yes', 'yeah', 'sure', 'okay']):
                response = "Great! What would you like to search for? I can help you find deals on fashion, groceries, electronics, and more."
                suggestions = ["Find fashion deals", "Show me grocery discounts", "What electronics are on sale?"]
            
            elif any(word in content_lower for word in ['no', 'not', 'dont', "don't"]):
                response = "No problem! Let me know if you change your mind or if there's anything else I can help you with."
                suggestions = ["Find different deals", "Show me all categories", "What's new today?"]
            
            else:
                # Default response for general conversation
                response = "I understand! I'm here to help you find great deals and discounts. What are you looking for today?"
                suggestions = [
                    "Find fashion deals near me",
                    "Show me grocery discounts", 
                    "What electronics are on sale?",
                    "Find deals under $50"
                ]
            
            return {
                "response": response,
                "suggestions": suggestions,
            }
            
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Response generation failed (async)",
                "response_generation",
                {"error": str(e), "content": content}
            )
            return {
                "response": "I understand. Could you tell me more about what you're looking for?",
                "suggestions": ["Find fashion deals", "Show me grocery discounts", "What's on sale?"],
            }
    
    async def _generate_search_suggestions(self, results: List[Dict]) -> List[str]: # Now async
        """Generate search suggestions using fast heuristics instead of expensive LLM calls."""
        try:
            if not results:
                return ["Try a different search term", "Browse all categories", "Expand your search area"]
            
            # Extract categories and retailers from results for context-aware suggestions
            categories = set()
            retailers = set()
            
            for result in results[:10]:  # Limit to first 10 results for speed
                if result.get('category'):
                    categories.add(result['category'])
                if result.get('retailer_name'):
                    retailers.add(result['retailer_name'])
            
            suggestions = []
            
            # Generate context-aware suggestions without LLM calls
            if categories:
                category_list = list(categories)[:3]  # Limit to 3 categories
                for category in category_list:
                    suggestions.append(f"Show me more {category} deals")
                    suggestions.append(f"Find {category} discounts near me")
            
            if retailers:
                retailer_list = list(retailers)[:2]  # Limit to 2 retailers
                for retailer in retailer_list:
                    suggestions.append(f"What's on sale at {retailer}?")
            
            # Add generic suggestions
            suggestions.extend([
                "Show me deals with bigger discounts",
                "Find items under $50",
                "Show me deals ending soon"
            ])
            
            # Return unique suggestions, limited to 5
            unique_suggestions = []
            seen = set()
            for suggestion in suggestions:
                if suggestion not in seen and len(unique_suggestions) < 5:
                    unique_suggestions.append(suggestion)
                    seen.add(suggestion)
            
            return unique_suggestions
            
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Suggestion generation failed (async)",
                "suggestion_generation",
                {"error": str(e)}
            )
            # Return fallback suggestions without LLM
            return ["Try a different search term", "Browse all categories", "Expand your search area"]
  
    @swagger_auto_schema(
        operation_description="Get conversation details or list user's conversations",
        manual_parameters=[
            openapi.Parameter(
                'conversation_id',
                openapi.IN_PATH,
                description="Optional conversation ID to get specific conversation",
                type=openapi.TYPE_STRING
            )
        ],
        responses={
            HTTP_200_OK: openapi.Response(
                description="Conversation data retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'conversations': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        ),
                        'total_count': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            HTTP_404_NOT_FOUND: openapi.Response(
                description="Conversation not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        },
        tags=['Discounts'],
    )
    def get(self, request: Request, conversation_id: str = None) -> Response:
        """Get conversation details or list user's conversations."""
        return async_to_sync(self._async_get)(request, conversation_id)
    
    async def _async_get(self, request: Request, conversation_id: str = None) -> Response:
        """Async implementation of the get method."""
        try:
            if conversation_id:
                conversation = await Conversation.objects.aget(
                    id=conversation_id,
                    user=request.user
                )
                serializer = ConversationSerializer(conversation)
                return Response(serializer.data)
            else:
                conversations_qs = Conversation.objects.filter(
                    user=request.user,
                    status=Conversation.ConversationStatus.ACTIVE
                ).prefetch_related('messages')[:10]
                conversations_list = []
                async for conv in conversations_qs:
                    conversations_list.append(conv)
                serializer = ConversationSerializer(conversations_list, many=True)
                return Response({
                    'conversations': serializer.data,
                    'total_count': len(conversations_list)
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
        ),
        responses={
            HTTP_200_OK: openapi.Response(
                description="Conversation updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            HTTP_400_BAD_REQUEST: openapi.Response(
                description="Bad request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            HTTP_404_NOT_FOUND: openapi.Response(
                description="Conversation not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        },
        tags=['Discounts'],
    )
    def patch(self, request: Request, conversation_id: str) -> Response:
        """Update conversation status."""
        return async_to_sync(self._async_patch)(request, conversation_id)
    
    async def _async_patch(self, request: Request, conversation_id: str) -> Response:
        """Async implementation of the patch method."""
        try:
            conversation = await Conversation.objects.aget(
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
            await conversation.asave()
            return Response({"status": "updated"})
        except Conversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found"},
                status=HTTP_404_NOT_FOUND
            )