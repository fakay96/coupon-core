"""
discountcrawlers.agents.enhanced_search_agent
============================================

Enhanced search agent that implements advanced semantic search with prompt optimization
and dynamic query enhancement.
"""

from __future__ import annotations
import logging
import time
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from celery import shared_task
from coupon_core.celery.celery import app as celery_app

from ..utils.embedding import get_embedding as get_query_embedding_vector
from ..utils.vector_db import VectorDBClient, DEFAULT_TOP_K as VECTOR_DB_DEFAULT_TOP_K
from ..items import DiscountItem

LOGGER = logging.getLogger(__name__)

# Default search parameters
DEFAULT_SEARCH_TOP_K = 10
DEFAULT_MIN_SIMILARITY = 0.7

@dataclass
class SearchContext:
    """Contextual information for search optimization."""
    user_history: List[str] = None  # Recent user searches
    user_preferences: Dict[str, Any] = None  # User preferences/preferences
    demographic_data: Dict[str, Any] = None  # Optional demographic info
    search_intent: str = None  # Extracted search intent

class EnhancedSearchAgent:
    """
    Enhanced search agent with advanced semantic search capabilities including:
    - Dynamic prompt optimization
    - Context-aware search
    - Query enhancement
    - Advanced filtering
    """
    
    _instance: Optional[EnhancedSearchAgent] = None

    @classmethod
    def get_instance(cls) -> EnhancedSearchAgent:
        """Provides a singleton-like instance for Celery tasks."""
        if cls._instance is None:
            LOGGER.info("Creating new EnhancedSearchAgent instance.")
            cls._instance = EnhancedSearchAgent()
        return cls._instance

    def __init__(self, vector_db_client: Optional[VectorDBClient] = None) -> None:
        """
        Initialize the enhanced search agent.
        
        Args:
            vector_db_client: Optional pre-initialized VectorDBClient instance
        """
        try:
            self.vector_db = vector_db_client if vector_db_client else VectorDBClient()
            LOGGER.info("EnhancedSearchAgent initialized successfully with VectorDBClient.")
        except Exception as e:
            LOGGER.critical(f"EnhancedSearchAgent: Failed to initialize VectorDBClient: {e}")
            self.vector_db = None

    def _optimize_prompt(self, query: str, context: Optional[SearchContext] = None) -> str:
        """
        Optimize the search prompt using context and intent analysis.
        
        Args:
            query: Original search query
            context: Optional search context for optimization
            
        Returns:
            Optimized query string
        """
        # Basic prompt optimization
        optimized = query.strip()
        
        if context:
            # Add contextual information if available
            if context.user_history and len(context.user_history) > 0:
                # Use recent search history to enhance context
                recent_searches = " ".join(context.user_history[-3:])  # Last 3 searches
                optimized = f"{optimized} (context: {recent_searches})"
            
            if context.user_preferences:
                # Add relevant preferences
                if "preferred_categories" in context.user_preferences:
                    categories = context.user_preferences["preferred_categories"]
                    optimized = f"{optimized} (categories: {', '.join(categories)})"
                
                if "price_range" in context.user_preferences:
                    price_range = context.user_preferences["price_range"]
                    optimized = f"{optimized} (price: {price_range['min']}-{price_range['max']})"
            
            if context.search_intent:
                # Add explicit search intent
                optimized = f"{optimized} (intent: {context.search_intent})"
        
        return optimized

    def _extract_search_intent(self, query: str) -> str:
        """
        Extract the primary search intent from the query.
        
        Args:
            query: Search query string
            
        Returns:
            Extracted search intent
        """
        # Basic intent extraction - can be enhanced with ML models
        query_lower = query.lower()
        
        # Common intent patterns
        intent_patterns = {
            "price_focus": ["cheap", "budget", "affordable", "discount", "deal", "sale"],
            "quality_focus": ["best", "quality", "premium", "high-end", "top"],
            "specific_feature": ["wireless", "waterproof", "portable", "compact"],
            "brand_focus": ["brand", "make", "manufacturer"],
            "comparison": ["compare", "versus", "vs", "difference between"],
            "review_focus": ["review", "rating", "recommendation"]
        }
        
        for intent, patterns in intent_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                return intent
                
        return "general_search"  # Default intent

    def _build_search_filters(self, 
                            query: str, 
                            context: Optional[SearchContext] = None,
                            explicit_filters: Optional[Dict[str, Any]] = None) -> str:
        """
        Build RediSearch filter string from query, context, and explicit filters.
        
        Args:
            query: Search query
            context: Optional search context
            explicit_filters: Optional explicit filter parameters
            
        Returns:
            RediSearch filter string
        """
        filter_parts = []
        
        # Add explicit filters if provided
        if explicit_filters:
            for field, value in explicit_filters.items():
                if isinstance(value, (int, float)):
                    filter_parts.append(f"@{field}:[{value} {value}]")
                elif isinstance(value, str):
                    if ' ' in value or any(c in value for c in ['-', '&', '|']):
                        filter_parts.append(f"@{field}:{{{value}}}")
                    else:
                        filter_parts.append(f"@{field}:{value}")
                elif isinstance(value, dict) and 'min' in value and 'max' in value:
                    filter_parts.append(f"@{field}:[{value['min']} {value['max']}]")
        
        # Add context-based filters
        if context and context.user_preferences:
            prefs = context.user_preferences
            if "preferred_stores" in prefs:
                stores = "|".join(prefs["preferred_stores"])
                filter_parts.append(f"@store_name:{{{stores}}}")
            
            if "excluded_categories" in prefs:
                excluded = "|".join(prefs["excluded_categories"])
                filter_parts.append(f"-@category:{{{excluded}}}")
        
        return " ".join(filter_parts) if filter_parts else "*"

    def perform_enhanced_search(
        self,
        query_text: str,
        context: Optional[SearchContext] = None,
        top_k: int = DEFAULT_SEARCH_TOP_K,
        min_similarity: Optional[float] = DEFAULT_MIN_SIMILARITY,
        explicit_filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform an enhanced semantic search with context awareness and prompt optimization.
        
        Args:
            query_text: The user's search query
            context: Optional search context for optimization
            top_k: Maximum number of results to return
            min_similarity: Minimum similarity score threshold
            explicit_filters: Optional explicit filter parameters
            
        Returns:
            Dictionary containing search results and metadata
        """
        start_time = time.monotonic()

        if not self.vector_db:
            raise ConnectionError("SearchAgent is not connected to the vector database.")

        if not query_text or not isinstance(query_text, str) or not query_text.strip():
            raise ValueError("Search query cannot be empty.")

        # 1. Extract search intent
        search_intent = self._extract_search_intent(query_text)
        if context:
            context.search_intent = search_intent

        # 2. Optimize the prompt
        optimized_query = self._optimize_prompt(query_text, context)
        
        # 3. Build search filters
        filter_string = self._build_search_filters(query_text, context, explicit_filters)
        
        LOGGER.info(
            f"Performing enhanced search. Original query: '{query_text}', "
            f"Optimized: '{optimized_query}', Intent: {search_intent}, "
            f"Filters: '{filter_string}'"
        )

        try:
            # 4. Perform vector search
            search_results = self.vector_db.search_similar_items(
                query_text=optimized_query,
                top_k=top_k * 2 if min_similarity is not None else top_k,
                filter_conditions=filter_string
            )

            # 5. Post-process results
            final_results = []
            if min_similarity is not None:
                for result in search_results:
                    if result.get("similarity_score", 0.0) >= min_similarity:
                        final_results.append(result)
            else:
                final_results = search_results

            # Sort by similarity score
            final_results.sort(key=lambda x: x.get("similarity_score", 0.0), reverse=True)
            final_results = final_results[:top_k]

            processing_time = (time.monotonic() - start_time) * 1000
            
            response = {
                'query': query_text,
                'optimized_query': optimized_query,
                'search_intent': search_intent,
                'filters_applied': filter_string,
                'results': final_results,
                'metadata': {
                    'total_candidates': len(search_results),
                    'returned_results': len(final_results),
                    'processing_time_ms': round(processing_time, 2),
                    'context_used': bool(context)
                }
            }
            
            LOGGER.info(
                f"Enhanced search completed. Found {len(search_results)} candidates, "
                f"returned {len(final_results)} results. Time: {processing_time:.2f}ms"
            )
            
            return response

        except Exception as e:
            LOGGER.exception(f"Error during enhanced search: {e}")
            return {
                'query': query_text,
                'optimized_query': optimized_query,
                'search_intent': search_intent,
                'filters_applied': filter_string,
                'results': [],
                'metadata': {
                    'error': str(e),
                    'processing_time_ms': (time.monotonic() - start_time) * 1000
                }
            }

@shared_task(bind=True, 
            name="discountcrawlers.agents.perform_enhanced_search_task",
            autoretry_for=(ConnectionError,),
            retry_kwargs={'max_retries': 3, 'countdown': 5})
def perform_enhanced_search_task(
    self,
    request_id: str,
    query_text: str,
    context: Optional[Dict[str, Any]] = None,
    top_k: int = DEFAULT_SEARCH_TOP_K,
    min_similarity: Optional[float] = DEFAULT_MIN_SIMILARITY,
    explicit_filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Celery task for performing enhanced semantic search asynchronously.
    
    Args:
        request_id: Unique identifier for the search request
        query_text: Search query
        context: Optional search context as dictionary
        top_k: Maximum number of results
        min_similarity: Minimum similarity threshold
        explicit_filters: Optional explicit filters
        
    Returns:
        Search results and metadata
    """
    LOGGER.info(f"[Task {self.request.id}|Request {request_id}] Starting enhanced search for: '{query_text}'")
    
    try:
        # Convert context dict to SearchContext if provided
        search_context = None
        if context:
            search_context = SearchContext(
                user_history=context.get('user_history'),
                user_preferences=context.get('user_preferences'),
                demographic_data=context.get('demographic_data'),
                search_intent=context.get('search_intent')
            )
        
        agent = EnhancedSearchAgent.get_instance()
        if not agent or not agent.vector_db:
            raise ConnectionError("SearchAgent could not connect to VectorDB")

        results = agent.perform_enhanced_search(
            query_text=query_text,
            context=search_context,
            top_k=top_k,
            min_similarity=min_similarity,
            explicit_filters=explicit_filters
        )
        
        results['request_id'] = request_id
        
        # Store results in Redis
        if agent.vector_db and agent.vector_db.client:
            result_key = f"search_results:{request_id}"
            agent.vector_db.client.set(
                result_key,
                json.dumps(results, default=str),
                ex=3600  # Expire after 1 hour
            )
            LOGGER.info(f"Stored search results in Redis at key: {result_key}")
        
        return results

    except Exception as e:
        LOGGER.exception(f"[Task {self.request.id}|Request {request_id}] Search failed: {e}")
        return {
            'request_id': request_id,
            'error': str(e),
            'results': [],
            'metadata': {'error_type': type(e).__name__}
        }

# Example usage
if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Example search context
    context = SearchContext(
        user_history=["wireless headphones", "gaming mouse"],
        user_preferences={
            "preferred_categories": ["Electronics", "Gaming"],
            "preferred_stores": ["Amazon", "BestBuy"],
            "price_range": {"min": 50, "max": 200}
        }
    )
    
    # Example search
    agent = EnhancedSearchAgent()
    results = agent.perform_enhanced_search(
        query_text="wireless gaming mouse with RGB",
        context=context,
        top_k=5,
        min_similarity=0.7,
        explicit_filters={"category": "Gaming", "price": {"min": 30, "max": 150}}
    )
    
    print("\nSearch Results:")
    print(f"Query: {results['query']}")
    print(f"Optimized Query: {results['optimized_query']}")
    print(f"Search Intent: {results['search_intent']}")
    print(f"Filters: {results['filters_applied']}")
    print(f"Found {len(results['results'])} results")
    
    for item in results['results']:
        print(f"\n- {item['name']}")
        print(f"  Price: ${item['price']}")
        print(f"  Store: {item['store_name']}")
        print(f"  Similarity: {item['similarity_score']:.2f}") 