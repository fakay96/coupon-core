"""
Search context management for enhanced search functionality.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from django.utils import timezone

from geodiscounts.v1.utils.understand_context import GeminiEmbeddingClient

logger = logging.getLogger(__name__)

@dataclass
class SearchContext:
    """Search context data class for storing search-related information."""
    
    query: str
    search_type: str = 'general'
    category: str = 'other'
    is_ambiguous: bool = False
    brand_preferences: List[str] = field(default_factory=list)
    product_signals: List[str] = field(default_factory=list)
    price_range: Optional[Dict[str, float]] = None
    location: Optional[Dict[str, float]] = None
    radius: Optional[float] = None
    fallback_strategies: List[str] = field(default_factory=lambda: ['optimized', 'semantic', 'basic_text'])
    timestamp: str = field(default_factory=lambda: timezone.now().isoformat())

class SearchContextManager:
    """Manages search context analysis and updates."""
    
    def __init__(self, gemini_client: GeminiEmbeddingClient):
        self.gemini = gemini_client
        self._initialize_categories()
    
    def _initialize_categories(self):
        """Initialize category mappings."""
        self.categories = {
            'groceries': ['food', 'grocery', 'supermarket', 'market'],
            'electronics': ['electronics', 'tech', 'gadgets', 'devices'],
            'clothing': ['clothing', 'fashion', 'apparel', 'wear'],
            'home': ['home', 'furniture', 'decor', 'household'],
            'beauty': ['beauty', 'cosmetics', 'skincare', 'makeup'],
            'sports': ['sports', 'fitness', 'outdoor', 'exercise'],
            'other': []
        }
    
    def analyze_query(self, query: str) -> SearchContext:
        """Analyze search query and create context."""
        try:
            # Create base context
            context = SearchContext(query=query)
            
            # Analyze query using Gemini
            analysis = self.gemini.analyze_query(query)
            
            # Update context with analysis results
            context.search_type = analysis.get('search_type', 'general')
            context.category = self._determine_category(query, analysis)
            context.is_ambiguous = analysis.get('is_ambiguous', False)
            context.brand_preferences = analysis.get('brand_preferences', [])
            context.product_signals = analysis.get('product_signals', [])
            context.price_range = analysis.get('price_range')
            context.location = analysis.get('location')
            context.radius = analysis.get('radius')
            
            # Update fallback strategies based on context
            context.fallback_strategies = self._determine_fallback_strategies(context)
            
            logger.info(
                "Analyzed search query",
                extra={
                    'query': query,
                    'search_type': context.search_type,
                    'category': context.category,
                    'is_ambiguous': context.is_ambiguous
                }
            )
            
            return context
            
        except Exception as e:
            logger.error(
                "Error analyzing query",
                extra={
                    'error': str(e),
                    'query': query
                }
            )
            # Return basic context on error
            return SearchContext(query=query)
    
    def _determine_category(self, query: str, analysis: Dict[str, Any]) -> str:
        """Determine the most likely category for the query."""
        # First check if Gemini provided a category
        if 'category' in analysis and analysis['category'] in self.categories:
            return analysis['category']
        
        # Fall back to keyword matching
        query_lower = query.lower()
        for category, keywords in self.categories.items():
            if any(keyword in query_lower for keyword in keywords):
                return category
        
        return 'other'
    
    def _determine_fallback_strategies(self, context: SearchContext) -> List[str]:
        """Determine appropriate fallback strategies based on context."""
        strategies = ['optimized']
        
        if context.category != 'other':
            strategies.append('category')
        
        if context.brand_preferences:
            strategies.append('retailer')
        
        if not context.is_ambiguous:
            strategies.append('semantic')
        
        strategies.append('basic_text')
        
        return strategies
    
    def update_context(self, context: SearchContext, new_query: str) -> SearchContext:
        """Update existing context with new query information."""
        try:
            # Analyze new query
            new_context = self.analyze_query(new_query)
            
            # Merge contexts
            context.query = new_query
            context.search_type = new_context.search_type
            context.category = new_context.category
            context.is_ambiguous = new_context.is_ambiguous
            context.brand_preferences.extend(new_context.brand_preferences)
            context.product_signals.extend(new_context.product_signals)
            
            # Update price range if new one is more specific
            if new_context.price_range:
                if not context.price_range:
                    context.price_range = new_context.price_range
                else:
                    # Merge price ranges
                    context.price_range = {
                        'min': min(context.price_range.get('min', float('inf')),
                                 new_context.price_range.get('min', float('inf'))),
                        'max': max(context.price_range.get('max', 0),
                                 new_context.price_range.get('max', 0))
                    }
            
            # Update location if provided
            if new_context.location:
                context.location = new_context.location
                context.radius = new_context.radius
            
            # Update fallback strategies
            context.fallback_strategies = self._determine_fallback_strategies(context)
            
            logger.info(
                "Updated search context",
                extra={
                    'old_query': context.query,
                    'new_query': new_query,
                    'category': context.category,
                    'search_type': context.search_type
                }
            )
            
            return context
            
        except Exception as e:
            logger.error(
                "Error updating context",
                extra={
                    'error': str(e),
                    'old_query': context.query,
                    'new_query': new_query
                }
            )
            return context 