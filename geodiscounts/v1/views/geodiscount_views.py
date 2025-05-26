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
    def post(self, request: Request) -> Response:
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

            conversation = self.conversation_service.get_or_create_conversation(
                user=request.user,conversation_id=conv_id
            )
            user_msg = ConversationMessage.objects.create(
                conversation=conversation,
                role=ConversationMessage.MessageRole.USER,
                content=message_content,
                message_type=self._determine_message_type(message_content)
            )
            response_data = self._process_message(
                message=user_msg,conversation=conversation,
                request=request,radius=radius,location_data=loc_data
            )
            assistant_msg = ConversationMessage.objects.create(
                conversation=conversation,
                role=ConversationMessage.MessageRole.ASSISTANT,
                content=response_data['response'],
                message_type=response_data['message_type'],
                metadata=response_data.get('metadata',{}),
                search_request=response_data.get('search_request')
            )
            self.conversation_service.update_conversation_context(conversation)

            # Learning log
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
                geo_logger,"Error processing conversational message",
                "conversational_discount",e,{'user_id':request.user.id}
            )
            return Response({"error":"Internal server error"},status=HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error in conversational message processing",
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
        
        return ConversationMessage.MessageType.CONVERSATION
    
    def _process_message(
        self, 
        message: ConversationMessage, 
        conversation: Conversation,
        request: Request, 
        radius: float,
        location_data: Dict
    ) -> Dict[str, Any]:
        """Process message and generate appropriate response."""
        
        # Get conversation context
        context = self.conversation_service.get_conversation_context(conversation)
        
        # Handle different message types
        if message.message_type == ConversationMessage.MessageType.GREETING:
            return self._handle_greeting(context)
        
        elif message.message_type == ConversationMessage.MessageType.SEARCH_QUERY:
            return self._handle_search_query(
                message, conversation, request, radius, location_data, context
            )
        
        else:
            return self._handle_general_conversation(message, context)
    
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
    
    def _enhance_search_query(self, query: str, context: Dict) -> Dict[str, Any]:
        """Enhance search query using Gemini for better understanding."""
        try:
            # Use Gemini to analyze and enhance the query
            enhanced = self.gemini_client.generate_content(
                prompt=f"""
                Analyze this search query and determine the most relevant category and search terms:
                Query: "{query}"
                Context: {json.dumps(context)}
                
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
            
            if not enhanced or not enhanced.text:
                # Return all categories when no specific matches found
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
                
            # Extract JSON from response
            text = enhanced.text.strip()
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = text[json_start:json_end]
                result = json.loads(json_str)
                
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
                    'price_range': {'min': 0, 'max': float('inf')}
                }
            }

    def _handle_search_query(
        self,
        message: ConversationMessage,
        conversation: Conversation,
        request: Request,
        radius: float,
        location_data: Dict,
        context: Dict
    ) -> Dict[str, Any]:
        """Handle search query messages."""
        
        # Get user location
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
        
        # Enhance the query using Gemini
        query_enhancement = self._enhance_search_query(message.content, context)
        
        # Create search request with enhanced query
        search_request = SearchRequest.objects.create(
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
        
        # Update conversation location
        conversation.last_location = Point(longitude, latitude)
        conversation.last_radius = radius
        conversation.save(update_fields=['last_location', 'last_radius'])
        
        # Perform search
        try:
            # Use the correct search method name
            search_results = self.search_service.find_discounts(
                req=search_request,
                timeout=30
            )
            
            if search_results['status'] == 'completed':
                result_count = len(search_results['results'])
                if result_count > 0:
                    # Use enhanced query context for better response
                    if query_enhancement['confidence'] > 0.7:
                        response = f"I found {result_count} great deals matching your search for {query_enhancement['query']}!"
                    else:
                        response = f"I found {result_count} deals that might interest you!"
                else:
                    # When no specific results found, get category deals
                    category_deals = self._get_all_categories()
                    if category_deals:
                        # Get the category from the enhanced query if available
                        category = query_enhancement.get('category', {}).get('name', '')
                        if category and category != 'other':
                            response = f"I couldn't find exactly what you're looking for, but here are some great {category} deals in your area!"
                        else:
                            response = "I couldn't find exactly what you're looking for, but here are some great deals in your area!"
                    else:
                        response = "I couldn't find any deals matching your search. Would you like to try a different search term?"
                    
                    search_results['results'] = category_deals
                    result_count = len(category_deals)
                
                # Generate suggestions based on the results
                try:
                    suggestions = self._generate_search_suggestions(search_results['results'])
                except Exception as e:
                    geo_structured_logger.error(
                        geo_logger,
                        "Failed to generate suggestions",
                        "suggestion_generation",
                        error=str(e)
                    )
                    suggestions = [
                        "Try a different search term",
                        "Browse all categories",
                        "Expand your search area"
                    ]
                
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
                        'search_time': search_results.get('processing_time'),
                        'query_confidence': query_enhancement['confidence']
                    }
                }
            
            elif search_results['status'] == 'timeout':
                # On timeout, return category deals with appropriate message
                category_deals = self._get_all_categories()
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
            
            else:  # failed
                # On failure, return category deals with appropriate message
                category_deals = self._get_all_categories()
                search_request.mark_failed(error_message="")
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
                
        except Exception as e:
            # On any error, return category deals with appropriate message
            category_deals = self._get_all_categories()
            search_request.mark_failed(error_message=str(e))
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

    def _get_all_categories(self) -> List[Dict]:
        """Get all available categories and their discounts grouped by retailer."""
        try:
            # Get only categories that have discounts
            categories = Category.objects.filter(discounts__isnull=False).distinct().prefetch_related(
                Prefetch(
                    'discounts',
                    queryset=Discount.objects.select_related('retailer').order_by('retailer__name', '-created_at')
                )
            )
            
            results = []
            
            for category in categories:
                # Get the first discount for each category as an example
                sample_discount = category.discounts.first()
                
                # Only include category if it has discounts
                if sample_discount:
                    # Group discounts by retailer
                    retailer_groups = {}
                    # Use all() to get the queryset of discounts
                    for discount in category.discounts.all():
                        retailer = discount.retailer
                        if retailer:
                            if retailer.id not in retailer_groups:
                                retailer_groups[retailer.id] = {
                                    'id': str(retailer.id),
                                    'name': retailer.name,
                                    'type': 'retailer',
                                    'image': None,  # Remove image access since Retailer model doesn't have it
                                    'description': f"Browse all {retailer.name} deals",
                                    'discounts': []
                                }
                            
                            retailer_groups[retailer.id]['discounts'].append({
                                'id': str(discount.id),
                                'title': discount.title,
                                'url': discount.url,
                                'type': 'discount',
                                'category': {
                                    'id': str(category.id),
                                    'name': category.name
                                }
                            })
                    
                    # Add category with its retailer groups
                    category_data = {
                        'id': str(category.id),
                        'name': category.name,
                        'type': 'category',
                        'image': category.image.url if category.image else None,
                        'description': f"Browse all {category.name} deals",
                        'discount_count': category.discounts.count(),
                        'retailers': list(retailer_groups.values())
                    }
                    
                    # Add category to results
                    results.append(category_data)
            
            # If no categories with discounts found, return empty list
            if not results:
                return []
                
            return results
            
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Failed to get all categories",
                "category_list",
                {
                    'error': str(e)
                }
            )
            return []
    
    def _handle_general_conversation(self, message: ConversationMessage, context: Dict) -> Dict[str, Any]:
        """Handle general conversation messages."""
        
        # Extract preferences from conversation
        self.conversation_service.extract_user_preferences(message)
        
        # Generate contextual response using Gemini
        response = self._generate_contextual_response(message.content, context)
        
        return {
            'response': response,
            'message_type': ConversationMessage.MessageType.CONVERSATION,
            'context': context,
            'suggestions': [
                "Search for discounts near me",
                "Find specific deals", 
                "What's available in my area?"
            ]
        }
    
    def _generate_contextual_response(self, content: str, context: Dict) -> str:
        """Generate contextual response using Gemini."""
        try:
            response = self.gemini_client.generate_content(
                prompt=f"""
                Generate a helpful response for this user message:
                Message: "{content}"
                Context: {json.dumps(context)}
                
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
            
            if not response or not response.text:
                return "I understand you're looking for deals. Could you tell me more about what you're interested in?"
                
            result = json.loads(response.text.strip())
            return result.get('response', "I understand you're looking for deals. Could you tell me more about what you're interested in?")
            
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Response generation failed",
                "response_generation",
                error=str(e),
                content=content
            )
            return "I understand you're looking for deals. Could you tell me more about what you're interested in?"
    
    def _generate_search_suggestions(self, results: List[Dict]) -> List[str]:
        """Generate search suggestions using Gemini."""
        try:
            if not results:
                return []
                
            response = self.gemini_client.generate_content(
                prompt=f"""
                Generate helpful search suggestions based on these results:
                Results: {json.dumps(results)}
                
                Return a JSON array of suggestion strings that:
                - Are relevant to the search results
                - Help users refine their search
                - Are natural and conversational
                - Are specific and actionable
                """,
                response_schema={
                    'type': 'ARRAY',
                    'items': {'type': 'STRING'}
                }
            )
            
            if not response or not response.text:
                return []
                
            suggestions = json.loads(response.text.strip())
            return suggestions[:5]  # Limit to 5 suggestions
            
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Suggestion generation failed",
                "suggestion_generation",
                error=str(e)
            )
            return []
  
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