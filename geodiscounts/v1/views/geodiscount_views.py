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

# Initialize shared Gemini client
gemini_client = GeminiEmbeddingClient(
   
)

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

    def __init__(self):
        super().__init__()
        self.conversation_service = ConversationService()
        self.search_service = EnhancedSearchService()
        self.gemini_client = gemini_client  # Use the shared client instance

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
    async def post(self, request: Request) -> Response:
        try:
            raw = request.data.get('message','').strip()
            if not raw:
                return Response({"error":"Message is required"},status=HTTP_400_BAD_REQUEST)
            message_content = correct_spelling(raw) # Assuming correct_spelling is lightweight

            conv_id = request.data.get('conversation_id')
            lat = request.client_latitude # Assuming these are available from an async middleware or sync_to_async if needed
            lon = request.client_longitude
            radius = float(request.data.get('radius',5000))
            loc_data = {"latitude":lat,"longitude":lon}

            # Updated to use async version of conversation service method
            conversation = await self.conversation_service.async_get_or_create(
                user=request.user, conv_id=conv_id
            )
            
            # Updated to use async ORM method
            user_msg = await ConversationMessage.objects.acreate(
                conversation=conversation,
                role=ConversationMessage.MessageRole.USER,
                content=message_content,
                message_type=self._determine_message_type(message_content) # This is sync
            )
            
            # Updated to await async helper method
            response_data = await self._process_message(
                message=user_msg, conversation=conversation,
                request=request, radius=radius, location_data=loc_data
            )
            
            # Updated to use async ORM method
            assistant_msg = await ConversationMessage.objects.acreate(
                conversation=conversation,
                role=ConversationMessage.MessageRole.ASSISTANT,
                content=response_data['response'],
                message_type=response_data['message_type'],
                metadata=response_data.get('metadata',{}),
                search_request=response_data.get('search_request') # Ensure search_request is obtained correctly if it's an ORM object
            )
            
            # Updated to use async version of conversation service method
            await self.conversation_service.async_update_context(conversation)

            # Learning log (remains synchronous for logging)
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
                {'user_id': request.user.id}
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
    
    async def _process_message(
        self, 
        message: ConversationMessage, 
        conversation: Conversation,
        request: Request, 
        radius: float,
        location_data: Dict
    ) -> Dict[str, Any]:
        """Process message and generate appropriate response (async)."""
        
        # Get conversation context and recent message history (now async)
        context = await self.conversation_service.async_get_context(conversation)
        history = await self.conversation_service.async_get_recent_messages(conversation)
        
        # Handle different message types (calling async helpers)
        if message.message_type == ConversationMessage.MessageType.GREETING:
            return await self._handle_greeting(context)
        
        elif message.message_type == ConversationMessage.MessageType.SEARCH_QUERY:
            return await self._handle_search_query(
                message, conversation, request, radius, location_data, context, history
            )
        
        else: # General conversation
            return await self._handle_general_conversation(message, context, history)
    
    async def _handle_greeting(self, context: Dict) -> Dict[str, Any]: # Now async, though no async calls within yet
        """Handle greeting messages (async)."""
        # This method itself doesn't make async calls but is called by an async method.
        # If it were to make LLM calls for personalized greetings, those would be awaited.
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
    
    async def _enhance_search_query(self, query: str, context: Dict, history: List[str]) -> Dict[str, Any]: # Now async
        """Enhance search query using Gemini for better understanding (async)."""
        try:
            # Use Gemini to analyze and enhance the query (now async)
            enhanced_response = await self.gemini_client.async_generate_content(
                prompt=f"""
                Analyze this search query and determine the most relevant category and search terms.
                Query: "{query}"
                Context: {json.dumps(context)}
                History: {json.dumps(history)}
                Recent Searches: {json.dumps(context.get('search_history', []))}
                Last Known Location: {json.dumps(context.get('last_location'))}
                
                Return a JSON object with these exact fields:
                {{
                    "enhanced_query": "improved search query",
                    "search_type": "general/specific/category/location",
                    "confidence": 0.8,
                    "category": {{
                        "name": "exact category name",
                        "confidence": 0.8
                    }},
                    "suggested_filters": {{
                        "price_range": {{
                            "min": 0,
                            "max": 1000
                        }},
                        "brand": "brand name"
                    }}
                }}
                
                IMPORTANT: 
                - The category name must exactly match one of: fashion, grocery, electronics, home, beauty, sports, entertainment, other
                - If unsure about category, use "other"
                - Return ONLY the JSON object, no other text
                """,
                response_schema={
                    'type': 'OBJECT',
                    'properties': {
                        'enhanced_query': {'type': 'STRING'},
                        'search_type': {'type': 'STRING'},
                        'confidence': {'type': 'NUMBER'},
                        'category': {
                            'type': 'OBJECT',
                            'properties': {
                                'name': {'type': 'STRING'},
                                'confidence': {'type': 'NUMBER'}
                            }
                        },
                        'suggested_filters': {
                            'type': 'OBJECT',
                            'properties': {
                                'price_range': {
                                    'type': 'OBJECT',
                                    'properties': {
                                        'min': {'type': 'NUMBER'},
                                        'max': {'type': 'NUMBER'}
                                    }
                                },
                                'brand': {'type': 'STRING'}
                            }
                        }
                    }
                }
            )
            
            if not enhanced_response or not enhanced_response.text:
                # Return default structure when no specific enhancement found
                return {
                    'query': query,
                    'confidence': 0.5,
                    'search_type': 'general',
                    'category': {
                        'name': 'other',
                        'confidence': 0.5
                    },
                    'filters': {
                        'price_range': {'min': 0, 'max': float('inf')} # Ensure this default is sensible
                    }
                }
                
            # Extract JSON from response
            text = enhanced_response.text.strip()
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = text[json_start:json_end]
                try:
                    result = json.loads(json_str)
                except json.JSONDecodeError:
                    geo_structured_logger.error(
                        geo_logger,
                        "Query enhancement JSON decode failed",
                        "query_enhancement",
                        {'response': enhanced_response.text},
                    )
                    result = {}
                
                # Validate category
                valid_categories = ['fashion', 'grocery', 'electronics', 'home', 'beauty', 'sports', 'entertainment', 'other']
                category_name = result.get('category', {}).get('name', '').lower()
                if category_name not in valid_categories:
                    category_name = 'other'
                
                # If confidence is low or no specific category found, return all categories
                if (result.get('confidence', 0) < 0.3 or 
                    result.get('category', {}).get('confidence', 0) < 0.3):
                    return {
                        'query': query,
                        'confidence': 0.5,
                        'search_type': 'general',
                        'category': {
                            'name': category_name,
                            'confidence': 0.5
                        },
                        'filters': {
                            'price_range': {'min': 0, 'max': float('inf')}
                        }
                    }
                
                return {
                    'query': result.get('enhanced_query', query),
                    'search_type': result.get('search_type', 'general'),
                    'confidence': result.get('confidence', 0.5),
                    'category': {
                        'name': category_name,
                        'confidence': result.get('category', {}).get('confidence', 0.5)
                    },
                    'filters': result.get('suggested_filters', {})
                }
            
            # Return all categories if JSON parsing fails
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
            
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Query enhancement failed",
                "query_enhancement",
                {
                    'error': str(e),
                    'context': {'query': query}
                }
            )
            # Return all categories on error
            return {
                'query': query,
                'confidence': 0.5,
                'search_type': 'general',
                'category': {
                    'name': 'other',
                    'confidence': 0.5
                },
                'filters': {
                    'price_range': {'min': 0, 'max': float('inf')} # Default
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
                    suggestions = await self._generate_search_suggestions(
                        search_results['results'], context, history
                    )
                except Exception as e:
                    geo_structured_logger.error(geo_logger, "Failed to generate suggestions (async)", "suggestion_generation", error=str(e))
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
                await search_request.amark_failed(error_message=search_results.get('error_message', "Unknown search failure"))
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
            geo_structured_logger.error(geo_logger, "Error in _handle_search_query (async)", "search_handling", e, search_id=str(search_request.id))
            category_deals = await self._get_all_categories() # Now async
            await search_request.amark_failed(error_message=str(e)) # Ensure amark_failed exists or use asave
            return {
                'response': "I encountered an issue with your search, but here are some great deals in your area!",
                'message_type': ConversationMessage.MessageType.SEARCH_RESULTS,
                'results': category_deals,
                'suggestions': [
                    "Try a different search term",
                    "Browse all categories",
                    "Expand your search area"
                ],
                'search_id': str(search_request.id)
            }

    async def _get_all_categories(self) -> List[Dict]: # Now async
        """Get all available categories and their discounts grouped by retailer (async)."""
        try:
            # The complex prefetch might be hard to do with full async ORM elegantly.
            # Wrapping the synchronous ORM call in to_thread for this part.
            def _fetch_categories_sync():
                categories_qs = Category.objects.filter(discounts__isnull=False).distinct().prefetch_related(
                    Prefetch(
                        'discounts',
                        queryset=Discount.objects.select_related('retailer').order_by('retailer__name', '-created_at')
                    )
                )
                
                results_sync = []
                for category_item in categories_qs: # Iterate over sync queryset
                    sample_discount_sync = category_item.discounts.first() # Sync access
                    
                    if sample_discount_sync:
                        retailer_groups_sync = {}
                        for discount_item in category_item.discounts.all(): # Sync access
                            retailer_sync = discount_item.retailer
                            if retailer_sync:
                                if retailer_sync.id not in retailer_groups_sync:
                                    retailer_groups_sync[retailer_sync.id] = {
                                        'id': str(retailer_sync.id), 'name': retailer_sync.name, 'type': 'retailer',
                                        'image': None, 'description': f"Browse all {retailer_sync.name} deals",
                                        'discounts': []
                                    }
                                retailer_groups_sync[retailer_sync.id]['discounts'].append({
                                    'id': str(discount_item.id), 'title': discount_item.title, 'url': discount_item.url,
                                    'type': 'discount', 'category': {'id': str(category_item.id), 'name': category_item.name}
                                })
                        
                        category_data_sync = {
                            'id': str(category_item.id), 'name': category_item.name, 'type': 'category',
                            'image': category_item.image.url if category_item.image else None,
                            'description': f"Browse all {category_item.name} deals",
                            'discount_count': category_item.discounts.count(), # Sync access
                            'retailers': list(retailer_groups_sync.values())
                        }
                        results_sync.append(category_data_sync)
                return results_sync

            results = await asyncio.to_thread(_fetch_categories_sync)
            
            if not results:
                return []
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
        """Generate contextual response and suggestions using Gemini (async)."""
        try:
            gemini_response_obj = await self.gemini_client.async_generate_content(
                prompt=f"""
                Generate a helpful response for this user message using the provided context.
                Message: "{content}"
                Context: {json.dumps(context)}
                History: {json.dumps(history)}
                Recent Searches: {json.dumps(context.get('search_history', []))}
                Last Known Location: {json.dumps(context.get('last_location'))}

                The response should be:
                - Natural and conversational
                - Relevant to the user's query
                - Include suggestions if appropriate
                - Be concise but informative
                """,
                response_schema={
                    'type': 'OBJECT',
                    'properties': {
                        'response': {'type': 'STRING'},
                        'suggestions': {
                            'type': 'ARRAY',
                            'items': {'type': 'STRING'}
                        }
                    }
                }
            )
            
            if not gemini_response_obj or not gemini_response_obj.text:
                return {
                    "response": "I understand you're looking for deals. Could you tell me more about what you're interested in?",
                    "suggestions": [],
                }

            try:
                result = json.loads(gemini_response_obj.text.strip())
            except json.JSONDecodeError:
                geo_structured_logger.error(
                    geo_logger,
                    "Contextual response JSON decode failed",
                    "response_generation",
                    {'response': gemini_response_obj.text},
                )
                return {"response": gemini_response_obj.text.strip(), "suggestions": []}

            return {
                "response": result.get(
                    "response",
                    "I understand. Could you provide more details on what you're looking for?",
                ),
                "suggestions": result.get("suggestions", []),
            }
            
        except Exception as e:
            geo_structured_logger.error(geo_logger, "Response generation failed (async)", "response_generation", error=str(e), content=content)
            return {
                "response": "I understand. Could you tell me more about what you're looking for?",
                "suggestions": [],
            }
    
    async def _generate_search_suggestions(
        self,
        results: List[Dict],
        context: Dict,
        history: List[str],
    ) -> List[str]:
        """Generate search suggestions using Gemini with additional context."""
        try:
            if not results:
                return [] # No suggestions if no results
                
            gemini_response_obj = await self.gemini_client.async_generate_content(
                prompt=f"""
                Generate helpful search suggestions based on these results.
                Results: {json.dumps(results)}
                Context: {json.dumps(context)}
                History: {json.dumps(history)}

                Return a JSON array of suggestion strings that:
                - Are relevant to the search results
                - Help users refine their search
                - Reference recent conversation history when helpful
                - Are natural and conversational
                - Are specific and actionable
                """,
                response_schema={
                    'type': 'ARRAY',
                    'items': {'type': 'STRING'}
                }
            )
            
            if not gemini_response_obj or not gemini_response_obj.text:
                return [] # No suggestions if Gemini fails
                
            try:
                suggestions = json.loads(gemini_response_obj.text.strip())
            except json.JSONDecodeError:
                geo_structured_logger.error(
                    geo_logger,
                    "Suggestion JSON decode failed",
                    "suggestion_generation",
                    {"response": gemini_response_obj.text},
                )
                return []

            return suggestions[:5]  # Limit to 5 suggestions
            
        except Exception as e:
            geo_structured_logger.error(geo_logger, "Suggestion generation failed (async)", "suggestion_generation", error=str(e))
            return [] # Return empty on error
  
    async def get(self, request: Request, conversation_id: str = None) -> Response: # Now async
        """Get conversation details or list user's conversations (async)."""
        try:
            if conversation_id:
                # Get specific conversation (now async)
                conversation = await Conversation.objects.aget(
                    id=conversation_id,
                    user=request.user
                )
                # Serializers are typically sync. Fetch data then serialize.
                # This might need adjustment if serializer expects a sync object or needs specific async handling.
                # For now, assuming serializer can handle the instance.
                serializer = ConversationSerializer(conversation) 
                return Response(serializer.data)
            
            else:
                # Get user's recent conversations (now async)
                conversations_qs = Conversation.objects.filter(
                    user=request.user,
                    status=Conversation.ConversationStatus.ACTIVE
                ).prefetch_related('messages')[:10] # prefetch_related might need care with async
                
                # Convert to list for serializer and count
                # conversations_list = await sync_to_async(list)(conversations_qs)
                # total_count = await conversations_qs.acount()
                
                # Simpler approach: fetch list and then get its length
                conversations_list = []
                async for conv in conversations_qs:
                    conversations_list.append(conv)
                
                serializer = ConversationSerializer(conversations_list, many=True)
                return Response({
                    'conversations': serializer.data,
                    'total_count': len(conversations_list) # Count after fetching
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
    async def patch(self, request: Request, conversation_id: str) -> Response: # Now async
        """Update conversation status (async)."""
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
            
            await conversation.asave() # Now async
            return Response({"status": "updated"})
            
        except Conversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found"},
                status=HTTP_404_NOT_FOUND
            )