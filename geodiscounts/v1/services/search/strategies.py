"""
Search strategy implementations for different search approaches.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from django.db.models import Q
from django.utils import timezone

from geodiscounts.models import Discount, Retailer, Category
from .context import SearchContext
from geodiscounts.v1.utils.understand_context import GeminiEmbeddingClient

logger = logging.getLogger(__name__)

class SearchStrategy(ABC):
    """Abstract base class for search strategies."""
    
    def __init__(self, search_service: Any):
        self.search_service = search_service
        self.gemini = search_service.gemini
    
    @abstractmethod
    def search(self, query: str, context: SearchContext) -> List[Dict[str, Any]]:
        """Execute search using this strategy."""
        pass
    
    def get_confidence(self, results: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for search results."""
        if not results:
            return 0.0
        
        # Base confidence on number of results and their relevance
        base_confidence = min(len(results) / 10, 1.0)  # Cap at 1.0
        
        # Adjust based on result quality
        quality_scores = []
        for result in results:
            score = self._calculate_result_quality(result)
            quality_scores.append(score)
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        return (base_confidence + avg_quality) / 2
    
    def _calculate_result_quality(self, result: Dict[str, Any]) -> float:
        """Calculate quality score for a single result."""
        score = 0.0
        
        # Check for essential fields
        if result.get('name'):
            score += 0.3
        if result.get('price'):
            score += 0.2
        if result.get('retailer_name'):
            score += 0.2
        if result.get('discount_percentage'):
            score += 0.2
        if result.get('valid_until'):
            score += 0.1
        
        return score

class BasicTextSearchStrategy(SearchStrategy):
    """Basic text-based search strategy."""
    
    def search(self, query: str, context: SearchContext) -> List[Dict[str, Any]]:
        """Execute basic text search."""
        try:
            # Create search query
            search_query = Q(name__icontains=query) | Q(description__icontains=query)
            
            # Add category filter if available
            if context.category != 'other':
                search_query &= Q(category__name__iexact=context.category)
            
            # Execute search
            results = Discount.objects.using('geodiscounts_db').filter(
                search_query,
                valid_until__gte=timezone.now()
            ).select_related('retailer', 'category')[:20]
            
            # Serialize results
            return [self.search_service._serialize(result) for result in results]
            
        except Exception as e:
            logger.error(
                "Error in basic text search",
                extra={
                    'error': str(e),
                    'query': query
                }
            )
            return []

class SemanticSearchStrategy(SearchStrategy):
    """Semantic search using embeddings."""
    
    def search(self, query: str, context: SearchContext) -> List[Dict[str, Any]]:
        """Execute semantic search."""
        try:
            # Get query embedding
            query_embedding = self.gemini.get_embedding(query)
            
            # Find similar discounts
            results = Discount.objects.using('geodiscounts_db').filter(
                valid_until__gte=timezone.now()
            ).select_related('retailer', 'category')
            
            # Calculate similarity scores
            scored_results = []
            for result in results:
                if result.embedding:
                    similarity = self.gemini.calculate_similarity(
                        query_embedding,
                        result.embedding
                    )
                    if similarity > 0.7:  # Threshold for relevance
                        scored_results.append((result, similarity))
            
            # Sort by similarity
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            # Return top results
            return [
                self.search_service._serialize(result)
                for result, _ in scored_results[:20]
            ]
            
        except Exception as e:
            logger.error(
                "Error in semantic search",
                extra={
                    'error': str(e),
                    'query': query
                }
            )
            return []

class CategorySearchStrategy(SearchStrategy):
    """Category-based search strategy."""
    
    def search(self, query: str, context: SearchContext) -> List[Dict[str, Any]]:
        """Execute category-based search."""
        try:
            if context.category == 'other':
                return []
            
            # Get category
            category = Category.objects.using('geodiscounts_db').filter(
                name__iexact=context.category
            ).first()
            
            if not category:
                return []
            
            # Search within category
            results = Discount.objects.using('geodiscounts_db').filter(
                category=category,
                valid_until__gte=timezone.now()
            ).select_related('retailer', 'category')
            
            # Add text search within category
            if query:
                results = results.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                )
            
            return [
                self.search_service._serialize(result)
                for result in results[:20]
            ]
            
        except Exception as e:
            logger.error(
                "Error in category search",
                extra={
                    'error': str(e),
                    'query': query,
                    'category': context.category
                }
            )
            return []

class RetailerSearchStrategy(SearchStrategy):
    """Retailer-based search strategy."""
    
    def search(self, query: str, context: SearchContext) -> List[Dict[str, Any]]:
        """Execute retailer-based search."""
        try:
            if not context.brand_preferences:
                return []
            
            # Get matching retailers
            retailers = Retailer.objects.using('geodiscounts_db').filter(
                name__in=context.brand_preferences
            )
            
            if not retailers:
                return []
            
            # Search within retailers
            results = Discount.objects.using('geodiscounts_db').filter(
                retailer__in=retailers,
                valid_until__gte=timezone.now()
            ).select_related('retailer', 'category')
            
            # Add text search within retailers
            if query:
                results = results.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                )
            
            return [
                self.search_service._serialize(result)
                for result in results[:20]
            ]
            
        except Exception as e:
            logger.error(
                "Error in retailer search",
                extra={
                    'error': str(e),
                    'query': query,
                    'brands': context.brand_preferences
                }
            )
            return []

class OptimizedSearchStrategy(SearchStrategy):
    """Optimized search combining multiple strategies."""
    
    def search(self, query: str, context: SearchContext) -> List[Dict[str, Any]]:
        """Execute optimized search combining multiple strategies."""
        try:
            # Initialize base query
            base_query = Q(valid_until__gte=timezone.now())
            
            # Add category filter
            if context.category != 'other':
                base_query &= Q(category__name__iexact=context.category)
            
            # Add retailer filter
            if context.brand_preferences:
                base_query &= Q(retailer__name__in=context.brand_preferences)
            
            # Add price range filter
            if context.price_range:
                min_price = context.price_range.get('min')
                max_price = context.price_range.get('max')
                if min_price is not None:
                    base_query &= Q(price_per_unit__gte=min_price)
                if max_price is not None:
                    base_query &= Q(price_per_unit__lte=max_price)
            
            # Execute search
            results = Discount.objects.using('geodiscounts_db').filter(
                base_query
            ).select_related('retailer', 'category')
            
            # Add text search
            if query:
                results = results.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                )
            
            # Get initial results
            initial_results = list(results[:50])
            
            if not initial_results:
                return []
            
            # Get query embedding for semantic ranking
            query_embedding = self.gemini.get_embedding(query)
            
            # Score and rank results
            scored_results = []
            for result in initial_results:
                if result.embedding:
                    similarity = self.gemini.calculate_similarity(
                        query_embedding,
                        result.embedding
                    )
                    scored_results.append((result, similarity))
            
            # Sort by similarity
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            # Return top results
            return [
                self.search_service._serialize(result)
                for result, _ in scored_results[:20]
            ]
            
        except Exception as e:
            logger.error(
                "Error in optimized search",
                extra={
                    'error': str(e),
                    'query': query,
                    'context': context.__dict__
                }
            )
            return []

class SearchStrategyFactory:
    """Factory for creating appropriate search strategies based on context."""
    
    def __init__(self, search_service: Any):
        """Initialize the factory with search service."""
        self.search_service = search_service
    
    def get_strategy(self, context: SearchContext) -> SearchStrategy:
        """Get the most appropriate search strategy based on context.
        
        Args:
            context: The search context containing query and preferences.
            
        Returns:
            An instance of SearchStrategy.
        """
        # If we have specific retailer preferences, use retailer strategy
        if context.brand_preferences:
            return RetailerSearchStrategy(self.search_service)
            
        # If we have a specific category, use category strategy
        if context.category and context.category != 'other':
            return CategorySearchStrategy(self.search_service)
            
        # If we have a complex query, use semantic search
        if len(context.query.split()) > 2:
            return SemanticSearchStrategy(self.search_service)
            
        # Default to optimized strategy which combines multiple approaches
        return OptimizedSearchStrategy(self.search_service) 