"""
Services for Conversational Discount Discovery System - Enhanced with Embedding-Based Logic
=========================================================================================

Business logic layer that handles:
- Conversation management and context tracking
- Geospatial discount search with semantic & multilingual ranking
- User preference extraction and learning
- Search request processing with timeout handling
"""
from __future__ import annotations

import time
import json
import re
from decimal import Decimal
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple, Union

import numpy as np
from rapidfuzz import fuzz, process
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
from django.db import transaction
from django.db.models import Q, F, Count
from django.utils import timezone
from django.conf import settings
from coupon_core.utils.logging import geo_logger, geo_structured_logger
from geodiscounts.models import (
    Conversation, ConversationMessage, ConversationContext,
    SearchRequest, UserPreference, Discount, Retailer, Category
)
from geodiscounts.v1.utils.understand_context import GeminiEmbeddingClient
from django.core.cache import cache

# Initialize shared client with proper configuration
client = GeminiEmbeddingClient(
)


class EmbeddingBasedCategoryService:
    """
    Embedding-based classification of user queries into categories.
    """
    def __init__(self, gemini_client: GeminiEmbeddingClient):
        self.gemini = gemini_client
        self._category_embeddings: Dict[str, np.ndarray] = {}
        self._initialize_category_embeddings()

    def _initialize_category_embeddings(self):
        base_categories = [
            'electronics', 'clothing', 'furniture', 'groceries', 'food',
            'shopping', 'entertainment', 'health', 'automotive', 'beauty',
            'sports', 'home', 'books', 'travel', 'services'
        ]
        for category in base_categories:
            emb = self.gemini.get_embedding(category)
            if emb is not None:
                self._category_embeddings[category] = emb

    def classify_category(self, query: str, threshold: float = 0.6) -> Tuple[str, float]:
        emb = self.gemini.get_embedding(query)
        if emb is None:
            return 'other', 0.0
        best, score = 'other', 0.0
        for cat, cemb in self._category_embeddings.items():
            sim = float(np.dot(emb, cemb) / (np.linalg.norm(emb)*np.linalg.norm(cemb)+1e-8))
            if sim >= threshold and sim > score:
                best, score = cat, sim
        return best, score

    def get_related_categories(self, category: str, top_k: int = 3) -> List[Tuple[str, float]]:
        if category not in self._category_embeddings:
            return []
        emb = self._category_embeddings[category]
        scores: List[Tuple[str, float]] = []
        for other, oemb in self._category_embeddings.items():
            if other == category: continue
            sim = float(np.dot(emb, oemb)/(np.linalg.norm(emb)*np.linalg.norm(oemb)+1e-8))
            scores.append((other, sim))
        return sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]


class EmbeddingBasedPreferenceExtractor:
    """
    Embedding-based extraction of user preferences from messages.
    """
    def __init__(self, gemini_client: GeminiEmbeddingClient):
        self.gemini = gemini_client
        self._indicators: Dict[str, np.ndarray] = {}
        self._initialize_indicators()

    def _initialize_indicators(self):
        mapping = {
            'price_sensitive': ['cheap','budget','affordable','discount','sale','deal'],
            'premium': ['expensive','premium','luxury','exclusive'],
            'location': ['nearby','local','walking distance','around here'],
            'quality': ['best','top rated','high quality','reliable']
        }
        for key, words in mapping.items():
            embs = [self.gemini.get_embedding(w) for w in words]
            embs = [e for e in embs if e is not None]
            if embs:
                self._indicators[key] = np.mean(embs, axis=0)

    def extract_preferences(self, message: ConversationMessage) -> List[UserPreference]:
        prefs: List[UserPreference] = []
        try:
            text = message.content
            emb = self.gemini.get_embedding(text)
            if emb is None:
                return []
            for key, iemb in self._indicators.items():
                sim = float(np.dot(emb, iemb)/(np.linalg.norm(emb)*np.linalg.norm(iemb)+1e-8))
                if sim > 0.6:
                    ptype = self._map_type(key)
                    try:
                        pref = UserPreference.objects.using('geodiscounts_db').get(
                            user=message.conversation.user,
                            preference_type=ptype,
                            key=key
                        )
                        # Update existing preference
                        pref.value = key
                        pref.confidence = sim
                        pref.extracted_from_message = message
                        pref.save(using='geodiscounts_db')
                    except UserPreference.DoesNotExist:
                        # Create new preference
                        pref = UserPreference.objects.using('geodiscounts_db').create(
                            user=message.conversation.user,
                            conversation=message.conversation,
                            preference_type=ptype,
                            key=key,
                            value=key,
                            confidence=sim,
                            extracted_from_message=message
                        )
                        prefs.append(pref)

            struct = self.gemini.extract_structured_signals(text)
            for brand in struct.get('brand',[]):
                try:
                    pref = UserPreference.objects.using('geodiscounts_db').get(
                        user=message.conversation.user,
                        preference_type=UserPreference.PreferenceType.BRAND,
                        key='brand'
                    )
                    # Update existing preference
                    pref.value = brand
                    pref.confidence = 0.8
                    pref.extracted_from_message = message
                    pref.save(using='geodiscounts_db')
                except UserPreference.DoesNotExist:
                    # Create new preference
                    pref = UserPreference.objects.using('geodiscounts_db').create(
                        user=message.conversation.user,
                        conversation=message.conversation,
                        preference_type=UserPreference.PreferenceType.BRAND,
                        key='brand',
                        value=brand,
                        confidence=0.8,
                        extracted_from_message=message
                    )
                    prefs.append(pref)

            for prod in struct.get('product_name',[]):
                try:
                    pref = UserPreference.objects.using('geodiscounts_db').get(
                        user=message.conversation.user,
                        preference_type=UserPreference.PreferenceType.CATEGORY,
                        key='product'
                    )
                    # Update existing preference
                    pref.value = prod
                    pref.confidence = 0.7
                    pref.extracted_from_message = message
                    pref.save(using='geodiscounts_db')
                except UserPreference.DoesNotExist:
                    # Create new preference
                    pref = UserPreference.objects.using('geodiscounts_db').create(
                        user=message.conversation.user,
                        conversation=message.conversation,
                        preference_type=UserPreference.PreferenceType.CATEGORY,
                        key='product',
                        value=prod,
                        confidence=0.7,
                        extracted_from_message=message
                    )
                    prefs.append(pref)

        except Exception as e:
            geo_structured_logger.error(geo_logger, "Pref extraction error", "pref_extractor", e)
        return prefs

    def _map_type(self, key: str) -> str:
        return {
            'price_sensitive': UserPreference.PreferenceType.PRICE_RANGE,
            'premium': UserPreference.PreferenceType.PRICE_RANGE,
            'location': UserPreference.PreferenceType.LOCATION,
            'quality': UserPreference.PreferenceType.QUALITY
        }.get(key, UserPreference.PreferenceType.OTHER)


class ConversationService:
    """
    Manages conversation lifecycle and context tracking.
    """
    def __init__(self):
        self.pref_extractor = EmbeddingBasedPreferenceExtractor(client)
        self.search_service = EnhancedSearchService()

    def get_or_create(self, user, conv_id: Optional[str] = None) -> Conversation:
        try:
            if conv_id:
                conv = Conversation.objects.using('geodiscounts_db').get(
                    id=conv_id, user=user, status=Conversation.ConversationStatus.ACTIVE)
                conv.updated_at = timezone.now()
                conv.save(update_fields=['updated_at'], using='geodiscounts_db')
                return conv
            conv = Conversation.objects.using('geodiscounts_db').create(user=user)
            ConversationContext.objects.using('geodiscounts_db').create(conversation=conv)
            geo_structured_logger.info(geo_logger, "New conversation", "conversation_service", {'id': str(conv.id)})
            return conv
        except Conversation.DoesNotExist:
            return self.get_or_create(user, None)
        except Exception as e:
            geo_structured_logger.error(geo_logger, "Conv create error", "conversation_service", e)
            raise

    def _format_alternative_suggestions(self, results: List[Dict]) -> str:
        """Format alternative suggestions into a natural language response."""
        if not results:
            return "I couldn't find any alternatives at the moment."
            
        alternatives = []
        for r in results:
            if r.get('alternative_type') == 'related_category':
                alt = f"Similar {r.get('category', 'items')} from {r.get('retailer_name', 'nearby stores')}"
            elif r.get('alternative_type') == 'expanded_radius':
                alt = f"Options from {r.get('retailer_name', 'stores')} a bit further away"
            else:
                alt = f"Similar {r.get('name', 'items')} from {r.get('retailer_name', 'nearby stores')}"
            alternatives.append(alt)
            
        if len(alternatives) == 1:
            return f"Here's an alternative: {alternatives[0]}"
        else:
            return "Here are some alternatives:\n" + "\n".join(f"- {alt}" for alt in alternatives[:3])

    def handle_search_response(self, message: ConversationMessage, search_results: Dict[str, Any]) -> str:
        """Handle search results and format appropriate response."""
        if search_results['status'] == 'failed':
            error_type = search_results.get('error_type', 'UnknownError')
            suggestions = search_results.get('suggestions', [])
            
            response = "I encountered an issue while searching. "
            if error_type == 'TimeoutError':
                response += "The search took too long to complete. "
            elif error_type == 'IntegrityError':
                response += "There was a problem with the search parameters. "
            else:
                response += "Let me know what you're looking for and I'll try again. "
                
            if suggestions:
                response += "\n\nYou can try:\n" + "\n".join(f"- {s}" for s in suggestions)
            
            return response
            
        results = search_results.get('results', [])
        if not results:
            return "I couldn't find any matches. Would you like to try a different search?"
            
        # Get context from search results
        context = search_results.get('context', {})
        
        # Group results by match type
        exact_matches = [r for r in results if r.get('match_type') == 'exact']
        category_matches = [r for r in results if r.get('match_type') == 'category']
        related_matches = [r for r in results if r.get('match_type') == 'related_category']
        
        response = ""
        
        # If we have exact matches, show those first
        if exact_matches:
            response += "Here are the best matches I found:\n"
            for r in exact_matches[:3]:
                response += f"- {r.get('name', 'Item')} from {r.get('retailer_name', 'nearby store')}"
                if r.get('price_per_unit'):
                    response += f" (${r['price_per_unit']})"
                if r.get('discount_percentage'):
                    response += f" - {r['discount_percentage']}% off"
                if r.get('valid_until'):
                    response += f" (valid until {r['valid_until']})"
                response += "\n"
            response += "\n"
        
        # If we have category matches, show those as alternatives
        if category_matches:
            response += "Here are some other items in this category:\n"
            for r in category_matches[:5]:
                response += f"- {r.get('name', 'Item')} from {r.get('retailer_name', 'nearby store')}"
                if r.get('price_per_unit'):
                    response += f" (${r['price_per_unit']})"
                if r.get('discount_percentage'):
                    response += f" - {r['discount_percentage']}% off"
                if r.get('valid_until'):
                    response += f" (valid until {r['valid_until']})"
                response += "\n"
            response += "\n"
        
        # If we have related category matches, show those as well
        if related_matches:
            response += "You might also be interested in these related items:\n"
            for r in related_matches[:3]:
                response += f"- {r.get('name', 'Item')} from {r.get('retailer_name', 'nearby store')}"
                if r.get('price_per_unit'):
                    response += f" (${r['price_per_unit']})"
                if r.get('discount_percentage'):
                    response += f" - {r['discount_percentage']}% off"
                if r.get('valid_until'):
                    response += f" (valid until {r['valid_until']})"
                response += "\n"
        
        return response

    def update_context(self, conv: Conversation) -> None:
        try:
            ctx, _ = ConversationContext.objects.using('geodiscounts_db').get_or_create(conversation=conv)
            texts = [m.content for m in conv.messages.order_by('-created_at')[:5]]
            if texts:
                combined = " ".join(texts)
                struct = client.extract_structured_signals(combined)
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
            geo_structured_logger.error(geo_logger, "Context update error", "conversation_service", e)

    def _infer(self, analysis: Dict[str, Any]) -> str:
        if analysis.get('product_name') or analysis.get('brand'):
            return 'product_search'
        if any('price' in a.lower() for a in analysis.get('attributes', [])):
            return 'price_comparison'
        if any('near' in a.lower() for a in analysis.get('attributes', [])):
            return 'location_inquiry'
        return 'general_inquiry'

    def extract_preferences(self, message: ConversationMessage) -> List[UserPreference]:
        return self.pref_extractor.extract_preferences(message)

    def get_context(self, conv: Conversation) -> Dict[str, Any]:
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
            geo_structured_logger.error(geo_logger, "Get context error", "conversation_service", e)
            return {}

    def get_or_create_conversation(self, user, conversation_id: Optional[str] = None) -> Conversation:
        """Legacy alias for get_or_create"""
        return self.get_or_create(user, conv_id=conversation_id)

    def update_conversation_context(self, conv: Conversation) -> None:
        """Legacy alias for update_context"""
        return self.update_context(conv)

    def extract_user_preferences(self, message: ConversationMessage) -> List[UserPreference]:
        """Legacy alias for extract_preferences"""
        return self.extract_preferences(message)

    def get_conversation_context(self, conv: Conversation) -> Dict[str, Any]:
        """Legacy alias for get_context"""
        return self.get_context(conv)


class EmbeddingBasedQueryParser:
    """
    Parses user queries into structured fields via embeddings.
    """
    def __init__(self, gemini_client: GeminiEmbeddingClient):
        self.gemini = gemini_client

    def parse(self, query: str) -> Dict[str,Any]:
        try:
            struct = self.gemini.extract_structured_signals(query)
            price = self._extract_price(query)
            return {
                'brands': struct.get('brand',[]),
                'products': struct.get('product_name',[]),
                'attributes': struct.get('attributes',[]),
                'price_range': price,
                'keywords': self._keywords(query)
            }
        except Exception as e:
            geo_structured_logger.error(geo_logger, "Query parse error", "query_parser", e)
            return {'brands':[], 'products':[], 'attributes':[], 'price_range':None, 'keywords':query.split()}

    def _extract_price(self, q: str) -> Optional[Dict[str,int]]:
        patt=[(r'under \$?(\d+)', 'max'),(r'more than \$?(\d+)', 'min'),(r'between \$?(\d+) and \$?(\d+)', 'range')]
        low=q.lower()
        for p,k in patt:
            m=re.search(p, low)
            if m:
                if k=='range': return {'min':int(m.group(1)),'max':int(m.group(2))}
                return {k: int(m.group(1))}
        return None

    def _keywords(self, q: str) -> List[str]:
        words=re.findall(r'\b\w+\b', q.lower())
        stop={'the','a','an','and','or','in','on','for','of','with','by','is'}
        return [w for w in words if w not in stop and len(w)>2][:10]


@dataclass
class ProductSignal:
    text: str
    confidence: float
    signal_type: str
    embedding: Optional[np.ndarray] = None


@dataclass
class SearchContext:
    """Enhanced search context with more detailed information."""
    original_query: str
    category: str
    query_embedding: np.ndarray
    category_embedding: np.ndarray
    product_signals: List[ProductSignal]
    confidence_score: float
    is_ambiguous: bool
    price_range: Optional[Dict[str, float]] = None
    location_required: bool = False
    search_radius: Optional[float] = None
    brand_preferences: List[str] = None
    attributes: List[str] = None
    search_type: str = "general"  # general, specific, category, location
    fallback_strategies: List[str] = None


class EnhancedProductExtractor:
    def __init__(self, gemini_client: GeminiEmbeddingClient):
        self.gemini = gemini_client
        self.ambiguity_threshold = 0.3

    def extract_signals(self, query: str) -> List[ProductSignal]:
        prompt = f"""
        Extract JSON: {{"brand":[],"product_name":[],"attributes":[]}}
        Query: "{query}"
        """
        try:
            raw = self.gemini.generate_content(
                prompt,
                generation_config={"temperature": 0.0, "max_output_tokens": 150}
            ).text
            data = json.loads(raw.strip())
        except Exception:
            return []
            
        signals: List[ProductSignal] = []
        for key in ("brand","product_name","attributes"):
            for txt in data.get(key,[]):
                emb = self.gemini.get_embedding(txt)
                conf = 0.9 if key=="brand" else 0.8 if key=="product_name" else 0.6
                signals.append(ProductSignal(txt,conf,key,emb))
        return signals

    def compute_confidence(self, query: str, signals: List[ProductSignal]) -> float:
        if not signals:
            return 0.0
        return np.mean([s.confidence for s in signals])


class MultilingualMatcher:
    def __init__(self):
        self.maps={
            'banane':['banana','bananen'], 'apfel':['apple','pomme'],
            'milch':['milk','lait'], 'schuhe':['shoes','scarpe']
        }
        self.threshold=80

    def normalize(self, txt: str) -> List[str]:
        lo=txt.lower().strip()
        vals=[lo]
        for k,v in self.maps.items():
            if lo==k or lo in v:
                vals+=[k]+v
        return list(set(vals))

    def fuzzy_match(self, signals: List[ProductSignal], names: List[str]) -> Dict[str,float]:
        out: Dict[str,float]={}
        for s in signals:
            for var in self.normalize(s.text):
                for match,score in process.extract(var,names,scorer=fuzz.WRatio,limit=5,score_cutoff=self.threshold):
                    combined=score/100*s.confidence
                    out[match]=max(out.get(match,0), combined)
        return out


class EnhancedSearchService:
    """Enhanced search service with improved context analysis and error handling."""
    
    def __init__(self):
        self.gemini = client
        self.category_service = EmbeddingBasedCategoryService(self.gemini)
        self.preference_extractor = EmbeddingBasedPreferenceExtractor(self.gemini)
        self.product_extractor = EnhancedProductExtractor(self.gemini)
        self.multilingual_matcher = MultilingualMatcher()
        
    def _analyze_search_context(self, query: str) -> Dict[str, Any]:
        """
        Analyze search query using Gemini to extract detailed context.
        
        Returns a dictionary with:
        - location_required: bool
        - category: str
        - price_range: Dict[str, float]
        - brand_preferences: List[str]
        - search_type: str
        - search_radius: float
        - attributes: List[str]
        """
        try:
            # Use structured response schema for better reliability
            response = self.gemini.generate_content(
                prompt=f"""
                Analyze this search query and extract key information:
                Query: "{query}"
                
                Return a JSON object with:
                - location_required: boolean (whether location is needed)
                - category: string (main category)
                - price_range: {{"min": float, "max": float}} or null
                - brand_preferences: string[] (brand names)
                - search_type: string (general/specific/category/location)
                - search_radius: float (in km) or null
                - attributes: string[] (features like color, size)
                """,
                response_schema={
                    'type': 'OBJECT',
                    'properties': {
                        'location_required': {'type': 'BOOLEAN'},
                        'category': {'type': 'STRING'},
                        'price_range': {
                            'type': ['OBJECT', 'NULL'],
                            'properties': {
                                'min': {'type': 'NUMBER'},
                                'max': {'type': 'NUMBER'}
                            }
                        },
                        'brand_preferences': {
                            'type': 'ARRAY',
                            'items': {'type': 'STRING'}
                        },
                        'search_type': {
                            'type': 'STRING',
                            'enum': ['general', 'specific', 'category', 'location']
                        },
                        'search_radius': {
                            'type': ['NUMBER', 'NULL']
                        },
                        'attributes': {
                            'type': 'ARRAY',
                            'items': {'type': 'STRING'}
                        }
                    },
                    'required': ['location_required', 'category', 'search_type']
                }
            )
            
            if not response or not response.text:
                raise ValueError("Empty response from Gemini API")
                
            context = json.loads(response.text.strip())
            
            # Extract product signals for better matching
            signals = self.product_extractor.extract_signals(query)
            confidence = self.product_extractor.compute_confidence(query, signals)
            
            # Get category embeddings
            category_emb = self.gemini.get_embedding(context['category'])
            query_emb = self.gemini.get_embedding(query)
            
            if category_emb is None or query_emb is None:
                raise ValueError("Failed to generate embeddings")
            
            return SearchContext(
                original_query=query,
                category=context['category'],
                query_embedding=query_emb,
                category_embedding=category_emb,
                product_signals=signals,
                confidence_score=confidence,
                is_ambiguous=confidence < 0.7,
                price_range=context.get('price_range'),
                location_required=context['location_required'],
                search_radius=context.get('search_radius'),
                brand_preferences=context.get('brand_preferences', []),
                attributes=context.get('attributes', []),
                search_type=context['search_type'],
                fallback_strategies=self._determine_fallback_strategies(context)
            )
            
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Search context analysis failed",
                "search_context",
                error=str(e),
                query=query
            )
            # Return basic context as fallback
            return SearchContext(
                original_query=query,
                category="other",
                query_embedding=np.zeros(768, dtype=np.float32),
                category_embedding=np.zeros(768, dtype=np.float32),
                product_signals=[],
                confidence_score=0.0,
                is_ambiguous=True,
                fallback_strategies=['basic_text', 'category_only']
            )

    def _determine_fallback_strategies(self, context: Dict[str, Any]) -> List[str]:
        """Determine appropriate fallback strategies based on context."""
        strategies = []
        
        if context['search_type'] == 'general':
            strategies.extend(['basic_text', 'category_only'])
        elif context['search_type'] == 'specific':
            strategies.extend(['semantic_search', 'basic_text'])
        elif context['search_type'] == 'category':
            strategies.extend(['category_only', 'related_categories'])
        elif context['search_type'] == 'location':
            strategies.extend(['location_only', 'basic_text'])
            
        if context.get('brand_preferences'):
            strategies.append('brand_filter')
        if context.get('price_range'):
            strategies.append('price_filter')
            
        return strategies

    def _handle_search_error(self, req: SearchRequest, error: Exception) -> Dict[str, Any]:
        """Enhanced error handling with multiple fallback strategies."""
        error_type = type(error).__name__
        error_msg = str(error)
        
        geo_structured_logger.error(
            geo_logger,
            "Search error occurred",
            "search_error",
            error_type=error_type,
            error_message=error_msg,
            request_id=req.id,
            query=req.query,
            location=req.location,
            radius=req.radius
        )
        
        # Track fallback errors
        fallback_errors = []
        
        # Get search context for better fallback handling
        context = self._analyze_search_context(req.query)
        
        # Try each fallback strategy in order
        for strategy in context.fallback_strategies:
            try:
                if strategy == 'basic_text':
                    results = self._basic_text_search(req)
                elif strategy == 'category_only':
                    results = self._category_only_search(req)
                elif strategy == 'location_only' and req.location:
                    results = self._location_only_search(req)
                elif strategy == 'semantic_search':
                    results = self._find_similar_by_embedding(req.query, [], threshold=0.6)
                elif strategy == 'related_categories':
                    results = self._search_related_categories(context.category)
                elif strategy == 'brand_filter' and context.brand_preferences:
                    results = self._filter_by_brands(req, context.brand_preferences)
                elif strategy == 'price_filter' and context.price_range:
                    results = self._filter_by_price(req, context.price_range)
                else:
                    continue
                    
                if results:
                    return {
                        'status': 'success',
                        'results': results,
                        'fallback_used': strategy,
                        'message': f"Found results using {strategy} search"
                    }
                    
            except Exception as e:
                fallback_errors.append({
                    'strategy': strategy,
                    'error': str(e)
                })
                continue
        
        # If all fallbacks fail, return error with context-aware suggestions
        suggestions = self._generate_error_suggestions(error_type, context)
        
        return {
            'status': 'error',
            'message': "I encountered an issue while searching. Let me know what you're looking for and I'll try again.",
            'suggestions': suggestions[:5],  # Limit to 5 most relevant suggestions
            'error_type': error_type,
            'fallback_errors': fallback_errors,
            'context': {
                'search_type': context.search_type,
                'category': context.category,
                'is_ambiguous': context.is_ambiguous
            }
        }

    def _generate_error_suggestions(self, error_type: str, context: SearchContext) -> List[str]:
        """Generate context-aware suggestions based on error type and search context."""
        suggestions = []
        
        if error_type == 'TimeoutError':
            suggestions.extend([
                "Try a more specific search",
                "Narrow down your location",
                "Specify a category"
            ])
        elif error_type == 'LocationError':
            suggestions.extend([
                "Please provide your location",
                "Try searching without location",
                "Specify a smaller search radius"
            ])
        elif error_type == 'CategoryError':
            suggestions.extend([
                f"Try searching in {context.category}",
                "Be more specific about what you're looking for",
                "Try a different category"
            ])
        else:
            suggestions.extend([
                "Try rephrasing your search",
                "Be more specific",
                "Try a different category"
            ])
            
        # Add context-specific suggestions
        if context.is_ambiguous:
            suggestions.append("Your search is a bit vague. Could you be more specific?")
        if context.search_type == 'general':
            suggestions.append("Try adding more details to your search")
        if context.brand_preferences:
            suggestions.append(f"Try searching specifically for {', '.join(context.brand_preferences)}")
            
        return suggestions

    def _basic_text_search(self, req: SearchRequest) -> List[Dict]:
        """Perform a basic text-based search."""
        try:
            words = req.query.lower().split()
            base_query = Q(is_active=True, valid_until__gt=timezone.now())
            
            # Build text search query
            text_query = Q()
            for word in words:
                if len(word) > 2:  # Ignore very short words
                    text_query |= (
                        Q(name__icontains=word) |
                        Q(description__icontains=word) |
                        Q(brand__icontains=word) |
                        Q(store_name__icontains=word)
                    )
            
            qs = Discount.objects.using('geodiscounts_db').filter(
                base_query & text_query
            ).order_by('-created_at')
            
            return [self._serialize(d) for d in qs[:5]]
        except Exception as e:
            geo_structured_logger.error(geo_logger, "Basic text search error", "search_service", e)
            return []

    def _category_only_search(self, req: SearchRequest) -> List[Dict]:
        """Search only by category."""
        try:
            cat, _ = self.category_service.classify_category(req.query)
            if cat == 'other':
                return []
                
            qs = Discount.objects.using('geodiscounts_db').filter(
                is_active=True,
                valid_until__gt=timezone.now(),
                category__name__iexact=cat
            ).order_by('-discount_percentage', '-created_at')
            
            return [self._serialize(d) for d in qs[:5]]
        except Exception as e:
            geo_structured_logger.error(geo_logger, "Category search error", "search_service", e)
            return []

    def _location_only_search(self, req: SearchRequest) -> List[Dict]:
        """Search only by location."""
        try:
            qs = Discount.objects.using('geodiscounts_db').filter(
                is_active=True,
                valid_until__gt=timezone.now(),
                location__distance_lte=(req.location, Distance(m=req.radius))
            ).order_by('-created_at')
            
            return [self._serialize(d) for d in qs[:5]]
        except Exception as e:
            geo_structured_logger.error(geo_logger, "Location search error", "search_service", e)
            return []

    def _find_similar_by_embedding(self, query: str, results: List[Dict], threshold: float = 0.7) -> List[Dict]:
        """Find similar discounts using embedding similarity."""
        try:
            query_emb = self.gemini.get_embedding(query)
            if query_emb is None:
                return []
                
            similar_results = []
            for result in results:
                if 'embedding' in result and result['embedding'] is not None:
                    # Calculate cosine similarity
                    similarity = float(np.dot(query_emb, result['embedding']) / 
                                    (np.linalg.norm(query_emb) * np.linalg.norm(result['embedding']) + 1e-8))
                    
                    if similarity >= threshold:
                        result['semantic_similarity'] = similarity
                        result['match_type'] = 'semantic'
                        similar_results.append(result)
            
            return sorted(similar_results, key=lambda x: x['semantic_similarity'], reverse=True)
        except Exception as e:
            geo_structured_logger.error(geo_logger, "Embedding similarity error", "search_service", e)
            return []

    def _serialize(self, discount: Discount) -> Dict[str, Any]:
        """Serialize a discount object with its embedding."""
        data = {
            'id': str(discount.id),
            'name': discount.name,
            'description': discount.description,
            'retailer_name': discount.retailer.name if discount.retailer else None,
            'category': discount.category.name if discount.category else None,
            'price': float(discount.price_per_unit) if discount.price_per_unit else None,
            'discount_value': float(discount.discount_value) if discount.discount_value else None,
            'discount_percentage': float(discount.discount_percentage) if discount.discount_percentage else None,
            'embedding': discount.embedding,
            'location': {
                'lat': discount.location.y,
                'lng': discount.location.x
            } if discount.location else None,
            'brand': discount.brand,
            'valid_until': discount.valid_until.isoformat() if discount.valid_until else None,
            'store_name': discount.store_name,
            'product_url': discount.product_url,
            'image': discount.image.url if discount.image else None
        }
        return data


class PreferenceService:
    """ Manages user preference retrieval and confidence updates. """
    def get_user_preferences(self, user) -> Dict[str,Any]:
        try:
            prefs=UserPreference.objects.using('geodiscounts_db').filter(user=user)
            agg={'categories':[],'price_ranges':[],'locations':[],'brands':[],'search_radius':5000.0}
            for p in prefs:
                # aggregate by type...
                pass
            return agg
        except Exception as e:
            geo_structured_logger.error(geo_logger,"Pref get error","preference_service",e)
            return {'categories':[],'price_ranges':[],'locations':[],'brands':[],'search_radius':5000.0}

    def update_confidence(self, user, ptype:str, key:str, delta:float) -> None:
        try:
            pref=UserPreference.objects.using('geodiscounts_db').get(user=user, preference_type=ptype, key=key)
            pref.confidence=max(0.0,min(1.0,pref.confidence+delta))
            pref.save(update_fields=['confidence','updated_at'],using='geodiscounts_db')
        except UserPreference.DoesNotExist:
            return
        except Exception as e:
            geo_structured_logger.error(geo_logger,"Pref update error","preference_service",e)

# Factory functions

def get_conversation_service() -> ConversationService:
    return ConversationService()

def get_search_service() -> EnhancedSearchService:
    return EnhancedSearchService()

def get_preference_service() -> PreferenceService:
    return PreferenceService()
