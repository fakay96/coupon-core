"""
Conversation service for managing chat sessions and context.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any
from django.utils import timezone

from geodiscounts.models import (
    Conversation, ConversationMessage, ConversationContext,
    SearchRequest
)
from ..search.service import EnhancedSearchService
from ..preferences.service import PreferenceService
from geodiscounts.v1.utils.understand_context import GeminiEmbeddingClient
from .formatters import SearchResponseFormatter

logger = logging.getLogger(__name__)

class ConversationService:
    """
    Manages conversation lifecycle and context tracking.
    """
    def __init__(self):
        """Initialize the conversation service."""
        self.search_service = EnhancedSearchService()
        self.preference_service = PreferenceService()
        self.gemini = GeminiEmbeddingClient()
        self.response_formatter = SearchResponseFormatter()

    def get_or_create(self, user, conv_id: Optional[str] = None) -> Conversation:
        """Get or create a conversation for a user.
        
        Args:
            user: The user to create/get conversation for.
            conv_id: Optional conversation ID to retrieve.
            
        Returns:
            The conversation object.
        """
        try:
            if conv_id:
                conv = Conversation.objects.using('geodiscounts_db').get(
                    id=conv_id, user=user, status=Conversation.ConversationStatus.ACTIVE)
                conv.updated_at = timezone.now()
                conv.save(update_fields=['updated_at'], using='geodiscounts_db')
                return conv
            conv = Conversation.objects.using('geodiscounts_db').create(user=user)
            ConversationContext.objects.using('geodiscounts_db').create(conversation=conv)
            logger.info("New conversation created", extra={'id': str(conv.id)})
            return conv
        except Conversation.DoesNotExist:
            return self.get_or_create(user, None)
        except Exception as e:
            logger.error("Conversation creation error", extra={'error': str(e)})
            raise

    def handle_search_response(self, message: ConversationMessage, search_results: Dict[str, Any]) -> str:
        """Handle search results and format appropriate response.
        
        Args:
            message: The conversation message.
            search_results: The search results to format.
            
        Returns:
            Formatted response string.
        """
        if search_results['status'] == 'failed':
            return self.response_formatter.format_error_response(
                search_results.get('error_type', 'UnknownError'),
                search_results.get('suggestions', [])
            )
            
        return self.response_formatter.format_search_response(
            search_results.get('results', []),
            search_results.get('context', {})
        )

    def update_context(self, conv: Conversation) -> None:
        """Update conversation context based on recent messages.
        
        Args:
            conv: The conversation to update.
        """
        try:
            ctx, _ = ConversationContext.objects.using('geodiscounts_db').get_or_create(conversation=conv)
            texts = [m.content for m in conv.messages.order_by('-created_at')[:5]]
            if texts:
                combined = " ".join(texts)
                struct = self.gemini.extract_structured_signals(combined)
                ctx.topics_discussed = struct.get('product_name', []) + struct.get('attributes', [])
                ctx.user_intent = self._infer(struct)
                
                # Track search success/failure
                last_search = conv.search_requests.order_by('-created_at').first()
                if last_search:
                    if last_search.status == SearchRequest.SearchStatus.COMPLETED:
                        ctx.successful_searches += 1
                    elif last_search.status in [SearchRequest.SearchStatus.FAILED, SearchRequest.SearchStatus.TIMEOUT]:
                        ctx.failed_searches += 1
                
                ctx.save(using='geodiscounts_db')
                if not conv.title and conv.message_count >= 2:
                    title = ctx.topics_discussed[0] if ctx.topics_discussed else 'Chat'
                    conv.title = f"Search for {title}"[:100]
                    conv.save(update_fields=['title'], using='geodiscounts_db')
        except Exception as e:
            logger.error("Context update error", extra={'error': str(e)})

    def _infer(self, analysis: Dict[str, Any]) -> str:
        """Infer user intent from analysis.
        
        Args:
            analysis: The analysis results.
            
        Returns:
            Inferred intent string.
        """
        if analysis.get('product_name') or analysis.get('brand'):
            return 'product_search'
        if any('price' in a.lower() for a in analysis.get('attributes', [])):
            return 'price_comparison'
        if any('near' in a.lower() for a in analysis.get('attributes', [])):
            return 'location_inquiry'
        return 'general_inquiry'

    def get_context(self, conv: Conversation) -> Dict[str, Any]:
        """Get conversation context.
        
        Args:
            conv: The conversation to get context for.
            
        Returns:
            Dictionary containing context information.
        """
        try:
            ctx = getattr(conv, 'context', None)
            if not ctx:
                ctx = ConversationContext.objects.using('geodiscounts_db').create(conversation=conv)
            return {
                'stage': ctx.stage,
                'topics': ctx.topics_discussed,
                'intent': ctx.user_intent,
                'count': conv.message_count
            }
        except Exception as e:
            logger.error("Get context error", extra={'error': str(e)})
            return {}

    def get_conversation_context(self, conv: Conversation) -> Dict[str, Any]:
        """Get conversation context.
        
        This is an alias for get_context to maintain backward compatibility.
        
        Args:
            conv: The conversation to get context for.
            
        Returns:
            Dictionary containing context information.
        """
        return self.get_context(conv)

    def get_or_create_conversation(self, user, conversation_id: Optional[str] = None) -> Conversation:
        """Get or create a conversation for a user.
        
        Args:
            user: The user to create/get conversation for.
            conversation_id: Optional conversation ID to retrieve.
            
        Returns:
            The conversation object.
            
        Raises:
            Exception: If there's an error creating or retrieving the conversation.
        """
        try:
            if conversation_id:
                conv = Conversation.objects.using('geodiscounts_db').get(
                    id=conversation_id, 
                    user=user, 
                    status=Conversation.ConversationStatus.ACTIVE
                )
                conv.updated_at = timezone.now()
                conv.save(update_fields=['updated_at'], using='geodiscounts_db')
                return conv
                
            # Create new conversation
            conv = Conversation.objects.using('geodiscounts_db').create(
                user=user,
                status=Conversation.ConversationStatus.ACTIVE
            )
            
            # Create associated context
            ConversationContext.objects.using('geodiscounts_db').create(
                conversation=conv
            )
            
            logger.info(
                "New conversation created",
                extra={
                    'conversation_id': str(conv.id),
                    'user_id': str(user.id)
                }
            )
            
            return conv
            
        except Conversation.DoesNotExist:
            # If conversation not found, create new one
            return self.get_or_create_conversation(user, None)
            
        except Exception as e:
            logger.error(
                "Error in get_or_create_conversation",
                extra={
                    'error': str(e),
                    'user_id': str(user.id),
                    'conversation_id': conversation_id
                }
            )
            raise 

    def extract_user_preferences(self, message: ConversationMessage) -> Dict[str, Any]:
        """Extract user preferences from a conversation message.
        
        Args:
            message: The conversation message to analyze.
            
        Returns:
            Dictionary containing extracted preferences.
            
        Raises:
            Exception: If there's an error extracting preferences.
        """
        try:
            # Get message content
            content = message.content
            
            # Extract preferences using preference service
            preferences = self.preference_service.extract_preferences(content)
            
            # Extract product signals
            product_signals = self.gemini.extract_structured_signals(content)
            
            # Combine preferences and signals
            extracted_data = {
                'preferences': preferences,
                'product_signals': product_signals,
                'message_id': str(message.id),
                'conversation_id': str(message.conversation.id)
            }
            
            logger.info(
                "Extracted user preferences",
                extra={
                    'message_id': str(message.id),
                    'preferences': preferences,
                    'product_signals': product_signals
                }
            )
            
            # Update conversation context with new preferences
            self.update_context(message.conversation)
            
            return extracted_data
            
        except Exception as e:
            logger.error(
                "Error extracting user preferences",
                extra={
                    'error': str(e),
                    'message_id': str(message.id)
                }
            )
            raise 