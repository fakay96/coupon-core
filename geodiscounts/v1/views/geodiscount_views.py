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
from better_profanity import profanity  

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

from geodiscounts.models import Discount, Category, Retailer
from geodiscounts.v1.serializers.discount_serializers import DiscountSerializer, CategorySerializer

from geodiscounts.models import (
    Conversation, ConversationMessage, SearchRequest, 
)
from spellchecker import SpellChecker
from geodiscounts.v1.services.conversation.service import ConversationService
from geodiscounts.v1.services.search.service import EnhancedSearchService
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


# Module-level singleton for Gemini client
_gemini_client = None

def get_gemini_client() -> GeminiEmbeddingClient:
    """Get or create the singleton Gemini client instance."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiEmbeddingClient()
    return _gemini_client

# Greeting patterns
GREETING_PATTERNS = re.compile(
    r'^(hi|hello|hey|greetings|good\s+(morning|afternoon|evening|day)|morning|afternoon|evening|sup|yo|howdy|hola|hey\s+there|hi\s+there|hello\s+there)$',
    re.IGNORECASE
)
MAX_DISTANCE_PARAM = 10
spell = SpellChecker()
learning_logger = logging.getLogger("search.learning")

# Initialize profanity filter with custom words if needed
profanity.load_censor_words()

def correct_spelling(text: str) -> str:
    """Correct common typos in user input."""
    words = text.split()
    corrected = [spell.correction(w) or w for w in words]
    return " ".join(corrected)

# Search query detection patterns
SEARCH_KEYWORDS = [
    'find', 'search', 'look for', 'discount', 'deal', 'offer',
    'coupon', 'sale', 'cheap', 'near me', 'around here'
]

def is_search_query(text: str) -> bool:
    """Determine if the text contains search-related keywords."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in SEARCH_KEYWORDS)

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
        """Get the singleton Gemini client instance."""
        return get_gemini_client()

    def _safe_service_call(self, service_property, method_name, *args, **kwargs):
        """Safely call a service method with proper error handling."""
        try:
            geo_structured_logger.info(
                geo_logger,
                f"Attempting service call: {service_property}.{method_name}",
                "service_call_start",
                context={
                    'service': service_property,
                    'method': method_name,
                    'args': str(args),
                    'kwargs': str(kwargs)
                }
            )
            
            service = getattr(self, service_property)
            method = getattr(service, method_name)
            
            geo_structured_logger.info(
                geo_logger,
                f"Service and method found, executing call",
                "service_call_execute",
                context={
                    'service_type': type(service).__name__,
                    'method_type': type(method).__name__
                }
            )
            
            result = method(*args, **kwargs)
            
            geo_structured_logger.info(
                geo_logger,
                f"Service call completed successfully",
                "service_call_success",
                context={
                    'service': service_property,
                    'method': method_name,
                    'result_type': type(result).__name__,
                    'result_length': len(result) if hasattr(result, '__len__') else None
                }
            )
            
            return result
            
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                f"Service call failed: {service_property}.{method_name}",
                "service_call_error",
                error=str(e),
                context={
                    'service': service_property,
                    'method': method_name,
                    'args': str(args),
                    'kwargs': str(kwargs),
                    'error_type': type(e).__name__,
                    'error_args': getattr(e, 'args', None)
                }
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

    def _deep_think_about_intent(self, message: str, conversation: Conversation) -> Dict[str, Any]:
        """Perform deep analysis of user intent and context using Gemini.
        
        Args:
            message: The user's message
            conversation: The current conversation
            
        Returns:
            Dictionary containing analyzed intent, context, and suggestions
        """
        try:
            # First check for simple greetings
            message_lower = message.lower().strip()
            if GREETING_PATTERNS.match(message_lower):
                # Check if it's a time-based greeting
                time_based = any(phrase in message_lower for phrase in ['good morning', 'good afternoon', 'good evening', 'good day'])
                return {
                    "primary_intent": "greeting",
                    "confidence": 0.95,
                    "context": {
                        "greeting_type": "time_based" if time_based else "simple",
                        "time_of_day": self._get_time_of_day() if time_based else None
                    },
                    "suggested_queries": [],
                    "explanation": "Matches greeting pattern",
                    "follow_up_questions": []
                }

            # Get recent conversation history for context
            recent_messages = ConversationMessage.objects.filter(
                conversation=conversation
            ).order_by('-created_at')[:5]  # Get last 5 messages
            
            conversation_history = "\n".join([
                f"{'User' if msg.role == ConversationMessage.MessageRole.USER else 'Assistant'}: {msg.content}"
                for msg in reversed(recent_messages)
            ])

            # Get user's search history and preferences
            recent_searches = SearchRequest.objects.filter(
                conversation=conversation
            ).order_by('-created_at')[:3]  # Get last 3 searches
            
            search_history = "\n".join([
                f"Previous search: {search.query}"
                for search in recent_searches
            ])

            # Use Gemini to analyze intent and context
            response = self.gemini_client.generate_content(
                f"""Analyze this user message and conversation context to understand their intent and provide helpful suggestions.

                User Message: {message}
                
                Recent Conversation:
                {conversation_history}
                
                Recent Searches:
                {search_history}
                
                Return a JSON object with:
                {{
                    "primary_intent": "greeting/search/browse/compare/ask/other",
                    "confidence": 0.0 to 1.0,
                    "context": {{
                        "category": "detected category or null",
                        "price_range": {{"min": 0, "max": 1000}} or null,
                        "brand": "detected brand or null",
                        "location": "detected location or null",
                        "time_sensitivity": "high/medium/low",
                        "question_type": "available_discounts/general/specific" or null,
                        "is_general_inquiry": true/false
                    }},
                    "suggested_queries": [
                        "list of suggested search queries based on intent"
                    ],
                    "explanation": "Brief explanation of the analysis",
                    "follow_up_questions": [
                        "list of clarifying questions if needed"
                    ]
                }}
                
                Focus on understanding:
                1. What they're really looking for
                2. Any implicit preferences or constraints
                3. How to help them find what they want
                4. What additional information might be helpful
                
                Important: 
                - If the message is a greeting (hi, hello, hey, good morning, etc.), classify it as "greeting" with high confidence.
                - If the message is asking about available discounts or deals in general (like "what discounts can you find", "show me available deals", etc.), classify it as "ask" with high confidence and set question_type to "available_discounts" and is_general_inquiry to true.
                - For specific discount searches (like "find me shoes on sale"), use "search" intent.
                - For browsing categories or retailers, use "browse" intent.
                - For comparing deals, use "compare" intent.
                """
            )

            # Parse the response
            try:
                analysis = json.loads(response.text)
                
                # If it's a question about available discounts, ensure proper context
                if (analysis["primary_intent"] == "ask" and 
                    analysis["context"].get("question_type") == "available_discounts" and 
                    analysis["context"].get("is_general_inquiry")):
                    analysis["confidence"] = max(analysis["confidence"], 0.9)
                
                return analysis
                
            except json.JSONDecodeError:
                # Fallback to basic analysis
                if GREETING_PATTERNS.match(message_lower):
                    time_based = any(phrase in message_lower for phrase in ['good morning', 'good afternoon', 'good evening', 'good day'])
                    return {
                        "primary_intent": "greeting",
                        "confidence": 0.9,
                        "context": {
                            "greeting_type": "time_based" if time_based else "simple",
                            "time_of_day": self._get_time_of_day() if time_based else None
                        },
                        "suggested_queries": [],
                        "explanation": "Matches greeting pattern",
                        "follow_up_questions": []
                    }
                return {
                    "primary_intent": "search",
                    "confidence": 0.5,
                    "context": {},
                    "suggested_queries": [message],
                    "explanation": "Basic intent analysis",
                    "follow_up_questions": []
                }

        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error in deep thinking analysis",
                "intent_analysis",
                error=str(e)
            )
            return {
                "primary_intent": "search",
                "confidence": 0.0,
                "context": {},
                "suggested_queries": [message],
                "explanation": "Analysis failed",
                "follow_up_questions": []
            }

    def _get_time_of_day(self) -> str:
        """Get the current time of day for greeting context."""
        hour = timezone.now().hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 22:
            return "evening"
        else:
            return "night"

    def _handle_greeting(self, message: ConversationMessage, conversation: Conversation) -> Dict:
        """Handle greeting messages."""
        try:
            # Get greeting context
            greeting_type = message.metadata.get('intent_analysis', {}).get('context', {}).get('greeting_type', 'simple')
            time_of_day = message.metadata.get('intent_analysis', {}).get('context', {}).get('time_of_day')
            
            # Generate appropriate greeting response
            if greeting_type == "time_based" and time_of_day:
                greeting_prompt = f"""Generate a friendly {time_of_day} greeting response to: {message.content}
                Include a brief mention of how I can help find discounts and deals.
                Make it feel natural and time-appropriate."""
            else:
                greeting_prompt = f"""Generate a friendly greeting response to: {message.content}
                Include a brief mention of how I can help find discounts and deals."""

            response = self.gemini_client.generate_content(greeting_prompt)

            # Create assistant message
            assistant_message = ConversationMessage.objects.create(
                conversation=conversation,
                role=ConversationMessage.MessageRole.ASSISTANT,
                content=response.text,
                message_type=ConversationMessage.MessageType.CONVERSATION,
                metadata={
                    "greeting_type": greeting_type,
                    "time_of_day": time_of_day
                }
            )

            return {
                "type": "greeting",
                "message": response.text,
                "message_id": str(assistant_message.id),
                "conversation_id": str(conversation.id)
            }

        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error in greeting handling",
                "greeting_handling",
                error=str(e)
            )
            raise

    def _is_inappropriate_content(self, message: str) -> bool:
        """Check if the message contains inappropriate content.
        
        Args:
            message: The message to check
            
        Returns:
            bool: True if the message contains inappropriate content
        """
        try:
            # Check for profanity
            if profanity.contains_profanity(message):
                return True
            
            # Check for aggressive or threatening language
            aggressive_patterns = [
                r'\b(kill|die|hate|stupid|dumb|idiot|fool)\b',
                r'\b(threat|attack|hurt|harm)\b',
                r'\b(racist|sexist|homophobic)\b',
                r'\b(illegal|criminal|hack|steal)\b'
            ]
            
            message_lower = message.lower()
            for pattern in aggressive_patterns:
                if re.search(pattern, message_lower):
                    return True
                
            return False
            
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error checking inappropriate content",
                "content_check",
                error=str(e)
            )
            # If there's an error in checking, err on the side of caution
            return True

    def _handle_inappropriate_content(self, message: ConversationMessage, conversation: Conversation) -> Dict:
        """Handle messages containing inappropriate content."""
        try:
            # Create a polite but firm response
            response = self.gemini_client.generate_content(
                """Generate a professional response to inappropriate content that:
                1. Maintains a professional tone
                2. Politely but firmly indicates that such content is not acceptable
                3. Redirects the conversation to the purpose of finding discounts and deals
                4. Does not repeat or acknowledge the inappropriate content
                """
            )

            # Create assistant message
            assistant_message = ConversationMessage.objects.create(
                conversation=conversation,
                role=ConversationMessage.MessageRole.ASSISTANT,
                content=response.text,
                message_type=ConversationMessage.MessageType.CONVERSATION,
                metadata={
                    "is_inappropriate": True,
                    "handled_at": timezone.now().isoformat()
                }
            )

            return {
                "type": "conversation",
                "message": response.text,
                "message_id": str(assistant_message.id),
                "conversation_id": str(conversation.id)
            }

        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error handling inappropriate content",
                "inappropriate_handling",
                error=str(e)
            )
            # Fallback response if Gemini fails
            return {
                "type": "conversation",
                "message": "I aim to maintain a professional and respectful environment. I'm here to help you find great deals and discounts. How can I assist you with that?",
                "message_id": str(uuid.uuid4()),
                "conversation_id": str(conversation.id)
            }

    def _process_message(self, request: Request, conversation: Conversation) -> Dict:
        """Process incoming message and return appropriate response."""
        try:
            message = request.data.get('message', '')
            if not message:
                return {"error": "Message is required"}

            # Check for inappropriate content first
            if self._is_inappropriate_content(message):
                # Create user message with inappropriate flag
                user_message = ConversationMessage.objects.create(
                    conversation=conversation,
                    role=ConversationMessage.MessageRole.USER,
                    content=message,
                    message_type=ConversationMessage.MessageType.CONVERSATION,
                    metadata={
                        "is_inappropriate": True,
                        "detected_at": timezone.now().isoformat()
                    }
                )
                return self._handle_inappropriate_content(user_message, conversation)

            # Perform deep thinking analysis
            intent_analysis = self._deep_think_about_intent(message, conversation)
            
            # Create and save user message with intent analysis
            user_message = ConversationMessage.objects.create(
                conversation=conversation,
                role=ConversationMessage.MessageRole.USER,
                content=message,
                message_type=ConversationMessage.MessageType.SEARCH_QUERY if intent_analysis["primary_intent"] == "search" 
                    else ConversationMessage.MessageType.CONVERSATION,
                metadata={
                    "intent_analysis": intent_analysis,
                    "confidence": intent_analysis["confidence"]
                }
            )

            # Extract user preferences
            self._safe_service_call(
                'conversation_service',
                'extract_user_preferences',
                user_message
            )

            # Get conversation context
            context = self._safe_service_call(
                'conversation_service',
                'get_conversation_context',
                conversation
            )

            # Handle based on analyzed intent
            if intent_analysis["primary_intent"] == "greeting":
                return self._handle_greeting(user_message, conversation)
            elif intent_analysis["primary_intent"] == "ask":
                # Check if it's a question about available discounts
                if (intent_analysis["context"].get("question_type") == "available_discounts" and 
                    intent_analysis["context"].get("is_general_inquiry")):
                    return self._handle_question(user_message, conversation)
                # For other types of questions
                return self._handle_question(user_message, conversation)
            elif intent_analysis["primary_intent"] == "search":
                # If confidence is low, ask clarifying questions
                if intent_analysis["confidence"] < 0.6 and intent_analysis["follow_up_questions"]:
                    return self._handle_low_confidence_search(user_message, conversation, intent_analysis)
                return self._handle_search_query(message, conversation.id, intent_analysis)
            elif intent_analysis["primary_intent"] == "browse":
                return self._handle_browse_request(user_message, conversation, intent_analysis)
            elif intent_analysis["primary_intent"] == "compare":
                return self._handle_compare_request(user_message, conversation, intent_analysis)
            else:
                return self._handle_general_conversation(user_message, conversation)

        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error in message processing",
                "message_processing",
                error=str(e)
            )
            raise

    def _handle_low_confidence_search(self, message: ConversationMessage, conversation: Conversation, intent_analysis: Dict) -> Dict:
        """Handle search requests with low confidence by asking clarifying questions."""
        try:
            # Generate clarifying response
            response = self.gemini_client.generate_content(
                f"""Generate a friendly response to help clarify the user's search intent.
                User message: {message.content}
                Analysis: {json.dumps(intent_analysis, indent=2)}
                
                Include:
                1. Acknowledge their request
                2. Ask one of the follow-up questions: {intent_analysis['follow_up_questions']}
                3. Suggest some of the suggested queries: {intent_analysis['suggested_queries']}
                """
            )

            # Create assistant message
            assistant_message = ConversationMessage.objects.create(
                conversation=conversation,
                role=ConversationMessage.MessageRole.ASSISTANT,
                content=response.text,
                message_type=ConversationMessage.MessageType.CONVERSATION,
                metadata={
                    "intent_analysis": intent_analysis,
                    "is_clarifying": True
                }
            )

            return {
                "type": "clarification_needed",
                "message": response.text,
                "message_id": str(assistant_message.id),
                "conversation_id": str(conversation.id),
                "suggested_queries": intent_analysis["suggested_queries"],
                "follow_up_questions": intent_analysis["follow_up_questions"]
            }

        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error in handling low confidence search",
                "low_confidence_handling",
                error=str(e)
            )
            raise

    def _handle_question(self, message: ConversationMessage, conversation: Conversation) -> Dict:
        """Handle question messages."""
        try:
            # Check if the question is about available discounts
            if any(keyword in message.content.lower() for keyword in ['what discounts', 'available discounts', 'what deals', 'available deals']):
                # Query active retailers and their categories
                retailers = Retailer.objects.using('geodiscounts_db').filter(
                    is_active=True
                ).prefetch_related(
                    'discounts__category'  # Use the correct relation through discounts
                ).order_by('name')

                if not retailers.exists():
                    return {
                        "type": "question",
                        "message": "I apologize, but I don't have any active retailers in the system at the moment.",
                        "message_id": str(message.id),
                        "conversation_id": str(conversation.id)
                    }

                # Format retailer information
                retailer_info = []
                for retailer in retailers:
                    # Get unique categories from retailer's discounts
                    categories = set(
                        disc.category.name 
                        for disc in retailer.discounts.all() 
                        if disc.category and disc.is_active and disc.valid_until > timezone.now()
                    )
                    retailer_info.append({
                        'name': retailer.name,
                        'categories': list(categories),
                        'discount_count': retailer.discounts.filter(
                            is_active=True,
                            valid_until__gt=timezone.now()
                        ).count()
                    })

                # Generate response using Gemini
                response = self.gemini_client.generate_content(
                    f"""Based on this retailer information, generate a helpful response about available discounts:
                    {json.dumps(retailer_info, indent=2)}
                    
                    Include:
                    1. Total number of retailers
                    2. Mention some popular categories
                    3. Suggest how the user can search for specific discounts
                    """
                )

                # Create assistant message
                assistant_message = ConversationMessage.objects.create(
                    conversation=conversation,
                    role=ConversationMessage.MessageRole.ASSISTANT,
                    content=response.text,
                    message_type=ConversationMessage.MessageType.CONVERSATION,
                    metadata={
                        'retailer_count': len(retailer_info),
                        'total_discounts': sum(r['discount_count'] for r in retailer_info)
                    }
                )

                return {
                    "type": "question",
                    "message": response.text,
                    "message_id": str(assistant_message.id),
                    "conversation_id": str(conversation.id),
                    "retailers": retailer_info
                }

            # Handle other types of questions
            response = self.gemini_client.generate_content(
                f"""Answer this question about discounts and deals: {message.content}
                If the question is about specific products or discounts, mention that I can search for them."""
            )

            # Create assistant message
            assistant_message = ConversationMessage.objects.create(
                conversation=conversation,
                role=ConversationMessage.MessageRole.ASSISTANT,
                content=response.text,
                message_type=ConversationMessage.MessageType.CONVERSATION
            )

            return {
                "type": "question",
                "message": response.text,
                "message_id": str(assistant_message.id),
                "conversation_id": str(conversation.id)
            }

        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error in question handling",
                "question_handling",
                error=str(e)
            )
            raise

    def _handle_general_conversation(self, message: ConversationMessage, conversation: Conversation) -> Dict:
        """Handle non-search conversation messages."""
        try:
            # Generate response using Gemini
            response = self.gemini_client.generate_content(
                f"User message: {message.content}\nGenerate a helpful response:"
            )

            # Create assistant message
            assistant_message = ConversationMessage.objects.create(
                conversation=conversation,
                role=ConversationMessage.MessageRole.ASSISTANT,
                content=response.text,
                message_type=ConversationMessage.MessageType.CONVERSATION
            )

            return {
                "type": "conversation",
                "message": response.text,
                "message_id": str(assistant_message.id),
                "conversation_id": str(conversation.id)
            }

        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error in general conversation",
                "conversation_handling",
                error=str(e)
            )
            raise

    def _handle_search_query(self, message: str, conversation_id: str, intent_analysis: Dict) -> Dict[str, Any]:
        """Handle a search query message."""
        try:
            geo_structured_logger.info(
                geo_logger,
                "Processing search query",
                "search_query_processing",
                {
                    "query_text": message,
                    "conversation_id": conversation_id
                }
            )
            # Create search request with default location
            search_request = SearchRequest.objects.create(
                query=message,
                conversation_id=conversation_id,
                location=Point(0, 0),  # Default location at origin
                radius=5000,  # Default radius in meters
                status='pending'
            )
            
            # Log search request creation
            geo_structured_logger.info(
                geo_logger,
                "Created search request",
                "search_request_creation",
                {
                    'search_id': str(search_request.id),
                    'query_text': message
                }
            )
            
            # Get search results
            start_time = time.time()
            search_service = EnhancedSearchService()
            results = search_service.search(message)
            processing_time = time.time() - start_time
            
            # Mark search request as completed
            search_request.processing_time = processing_time
            search_request.status = 'completed'
            search_request.save()
            
            # Log search completion
            geo_structured_logger.info(
                geo_logger,
                "Search request completed",
                "search_request_completion",
                {
                    'search_id': str(search_request.id),
                    'processing_time': processing_time,
                    'results_count': len(results.get('results', []))
                }
            )
            
            return {
                'type': 'search_results',
                'results': results.get('results', []),
                'context': results.get('context', {}),
                'message': "Here are the search results I found:",
                'intent_analysis': intent_analysis
            }
            
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error processing search query",
                "search_query_error",
                error=str(e),
                context={
                    "query_text": message,
                    "conversation_id": conversation_id
                }
            )
            return {
                'type': 'error',
                'message': "I encountered an error while searching. Please try again.",
                'intent_analysis': intent_analysis
            }

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

    def _basic_text_search(self, req: SearchRequest) -> List[Dict]:
        """Perform a basic text-based search with bilingual support."""
        try:
            # Detect language of the query
            language = self._detect_language(req.query)
            
            # Create cache key
            cache_key = f"search_{req.query}_{language}"
            cached_results = cache.get(cache_key)
            if cached_results:
                return cached_results

            # Build base query
            base_query = Q(is_active=True, valid_until__gt=timezone.now())
            
            # Build bilingual search query
            text_query = Q()
            words = req.query.lower().split()
            
            for word in words:
                if len(word) > 2:
                    # Search in both English and German fields
                    text_query |= (
                        # English fields
                        Q(name__icontains=word) |
                        Q(description__icontains=word) |
                        Q(brand__icontains=word) |
                        Q(store_name__icontains=word) |
                        # German fields
                        Q(name_de__icontains=word) |
                        Q(description_de__icontains=word) |
                        Q(brand_de__icontains=word) |
                        Q(store_name_de__icontains=word)
                    )

            # Perform search
            results = Discount.objects.using('geodiscounts_db').filter(
                base_query & text_query
            ).select_related(
                'retailer',
                'category'
            ).order_by('-discount_percentage', '-created_at')[:5]

            # Process results with both languages
            processed_results = []
            for result in results:
                result_data = {
                    'id': str(result.id),
                    # English data
                    'name': result.name,
                    'description': result.description,
                    'retailer_name': result.retailer.name,
                    'category': result.category.name,
                    'brand': result.brand,
                    'store_name': result.store_name,
                    # German data
                    'name_de': result.name_de,
                    'description_de': result.description_de,
                    'retailer_name_de': result.retailer.name_de,
                    'category_de': result.category.name_de,
                    'brand_de': result.brand_de,
                    'store_name_de': result.store_name_de,
                    # Common fields
                    'price': float(result.price_per_unit) if result.price_per_unit else None,
                    'discount_value': float(result.discount_value) if result.discount_value else None,
                    'discount_percentage': float(result.discount_percentage) if result.discount_percentage else None,
                    'valid_until': result.valid_until.isoformat() if result.valid_until else None,
                    'product_url': result.product_url,
                    'image': result.image.url if result.image else None,
                    # Add language detection
                    'detected_language': language
                }
                processed_results.append(result_data)

            # Cache results
            cache.set(cache_key, processed_results, timeout=300)
            return processed_results

        except Exception as e:
            geo_structured_logger.error(geo_logger, "Basic text search error", "search_service", e)
            return []

    def _format_search_response(self, results: List[Dict], search_request: SearchRequest, conversation: Conversation, enhanced_query: str) -> Dict:
        """Format search response with bilingual support."""
        try:
            language = self._detect_language(search_request.query)
            
            # Format message in both languages
            if results:
                message_en = f"Found {len(results)} results for your search."
                message_de = f"I habe {len(results)} Ergebnisse für Ihre Suche gefunden."
                
                # Add retailer information if available
                retailers = {r['retailer_name'] for r in results if r['retailer_name']}
                if retailers:
                    message_en += f" Results from: {', '.join(retailers)}."
                    message_de += f" Ergebnisse von: {', '.join(retailers)}."
            else:
                message_en = "I couldn't find any results matching your search. Would you like to try a different search term?"
                message_de = "Ich konnte keine Ergebnisse für Ihre Suche finden. Möchten Sie einen anderen Suchbegriff versuchen?"

            # Create assistant message
            assistant_message = ConversationMessage.objects.create(
                conversation=conversation,
                role=ConversationMessage.MessageRole.ASSISTANT,
                content=message_en,  # Store English as primary
                message_type=ConversationMessage.MessageType.SEARCH_RESULTS,
                metadata={
                    'search_id': str(search_request.id),
                    'message_de': message_de,  # Store German translation
                    'detected_language': language
                },
                search_request=search_request
            )

            return {
                "type": "search_results",
                "message": message_en,
                "message_de": message_de,
                "message_id": str(assistant_message.id),
                "conversation_id": str(conversation.id),
                "results": results,
                "search_id": str(search_request.id),
                "detected_language": language
            }

        except Exception as e:
            geo_structured_logger.error(geo_logger, "Error formatting search response", "response_formatting", e)
            raise

    def _handle_no_results(self, message: ConversationMessage, conversation: Conversation, search_request: SearchRequest, query_analysis: Dict) -> Dict:
        """Handle no results with helpful guidance."""
        try:
            # Get available categories and retailers
            categories = Category.objects.using('geodiscounts_db').filter(
                is_active=True
            ).order_by('name')[:5]  # Get top 5 categories

            retailers = Retailer.objects.using('geodiscounts_db').filter(
                is_active=True
            ).order_by('name')[:5]  # Get top 5 retailers

            # Get popular discounts for suggestions
            popular_discounts = Discount.objects.using('geodiscounts_db').filter(
                is_active=True,
                valid_until__gt=timezone.now()
            ).order_by('-discount_percentage')[:3]

            # Prepare suggestion data
            suggestion_data = {
                'categories': [cat.name for cat in categories],
                'retailers': [ret.name for ret in retailers],
                'popular_discounts': [
                    {
                        'description': disc.description,  # Use description instead of name
                        'retailer': disc.retailer.name,
                        'discount': f"{disc.discount_percentage}% off" if disc.discount_percentage else f"${disc.discount_value} off"
                    }
                    for disc in popular_discounts
                ],
                'query': message.content
            }

            # Generate helpful response using Gemini
            response = self.gemini_client.generate_content(
                f"""The user searched for: {message.content}
                No results were found. Generate a helpful response that:
                1. Acknowledges no results were found
                2. Suggests some available categories: {suggestion_data['categories']}
                3. Mentions some retailers we have: {suggestion_data['retailers']}
                4. Shows some current popular deals: {suggestion_data['popular_discounts']}
                5. Provides guidance on how to refine their search
                
                Make the response friendly and encouraging, suggesting they try searching by:
                - Specific product names
                - Categories
                - Retailers
                - Price ranges
                """
            )

            # Create assistant message
            assistant_message = ConversationMessage.objects.create(
                conversation=conversation,
                role=ConversationMessage.MessageRole.ASSISTANT,
                content=response.text,
                message_type=ConversationMessage.MessageType.SEARCH_RESULTS,
                metadata={
                    'search_id': str(search_request.id),
                    'suggestions': suggestion_data,
                    'is_no_results': True
                },
                search_request=search_request
            )

            return {
                "type": "search_results",
                "message": response.text,
                "message_id": str(assistant_message.id),
                "conversation_id": str(conversation.id),
                "suggestions": {
                    "categories": suggestion_data['categories'],
                    "retailers": suggestion_data['retailers'],
                    "popular_deals": suggestion_data['popular_discounts']
                },
                "search_id": str(search_request.id),
                "is_no_results": True
            }

        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error in handling no results",
                "no_results_handling",
                error=str(e)
            )
            raise

    @swagger_auto_schema(
        operation_description="Refine search based on conversation context",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['conversation_id', 'query'],
            properties={
                'conversation_id': openapi.Schema(type=openapi.TYPE_STRING, description='ID of the conversation to refine'),
                'query': openapi.Schema(type=openapi.TYPE_STRING, description='New search query'),
                'context': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'previous_queries': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description='List of previous queries in the conversation'
                        ),
                        'filters': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'price_range': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'min': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'max': openapi.Schema(type=openapi.TYPE_NUMBER)
                                    }
                                ),
                                'categories': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_STRING)
                                ),
                                'distance': openapi.Schema(type=openapi.TYPE_NUMBER)
                            }
                        )
                    }
                )
            }
        ),
        responses={
            200: openapi.Response(
                description="Search results with conversation context",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'results': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        ),
                        'conversation_id': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            404: "Conversation not found",
            400: "Invalid request parameters"
        }
    )
    def refine_search(self, request):
        """Refine search based on conversation context."""
        try:
            # Validate required parameters
            conversation_id = request.data.get('conversation_id')
            query = request.data.get('query')
            if not conversation_id or not query:
                return Response(
                    {'error': 'conversation_id and query are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get conversation using conversation service
            conversation = self._safe_service_call(
                'conversation_service',
                'get_conversation',
                conversation_id=conversation_id,
                user=request.user
            )
            if not conversation:
                return Response(
                    {'error': 'Conversation not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Create user message and extract preferences
            user_message = ConversationMessage.objects.create(
                conversation=conversation,
                role=ConversationMessage.MessageRole.USER,
                content=query,
                message_type=ConversationMessage.MessageType.SEARCH_QUERY
            )
            self._safe_service_call(
                'conversation_service',
                'extract_user_preferences',
                user_message
            )

            # Get enhanced context
            enhanced_context = self._safe_service_call(
                'conversation_service',
                'get_conversation_context',
                conversation
            )
            if request.data.get('context'):
                enhanced_context.update(request.data['context'])

            # Create and process search request
            search_request = SearchRequest.objects.create(
                query=query,
                conversation=conversation,
                user=request.user,
                location=Point(0, 0),
                radius=5000,
                status='pending'
            )

            # Perform search using search service
            search_results = self._safe_service_call(
                'search_service',
                'search',
                query=query,
                context=enhanced_context,
                search_request=search_request
            )

            # Create assistant message
            assistant_message = ConversationMessage.objects.create(
                conversation=conversation,
                role=ConversationMessage.MessageRole.ASSISTANT,
                content=search_results.get('message', 'Here are the results I found:'),
                message_type=ConversationMessage.MessageType.SEARCH_RESULTS,
                metadata={
                    'search_id': str(search_request.id),
                    'results_count': len(search_results.get('results', []))
                },
                search_request=search_request
            )

            # Update search request status
            search_request.status = 'completed'
            search_request.save()

            return Response({
                'results': search_results.get('results', []),
                'conversation_id': str(conversation.id),
                'message': search_results.get('message', 'Here are the results I found:'),
                'message_id': str(assistant_message.id)
            })

        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error in refine_search",
                "search_refinement",
                error=str(e),
                context={
                    'conversation_id': request.data.get('conversation_id'),
                    'query': request.data.get('query')
                }
            )
            return Response(
                {'error': 'An error occurred while processing your request'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )