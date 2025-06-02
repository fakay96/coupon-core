"""
Enhanced search service with improved context analysis and error handling.
"""
from __future__ import annotations

import time
import logging
import json
from typing import Dict, List, Optional, Any, Union
from django.utils import timezone
from django.db.models import Q

from geodiscounts.models import Discount, Retailer, SearchRequest
from geodiscounts.v1.utils.understand_context import GeminiEmbeddingClient
from .context import SearchContext, SearchContextManager
from .strategies import (
    SearchStrategy, BasicTextSearchStrategy, SemanticSearchStrategy,
    CategorySearchStrategy, OptimizedSearchStrategy, RetailerSearchStrategy
)
from .extractors import EmbeddingBasedCategoryService, EmbeddingBasedPreferenceExtractor

logger = logging.getLogger(__name__)

class EnhancedSearchService:
    """Enhanced search service with improved context analysis and error handling."""
    
    def __init__(self):
        self.gemini = GeminiEmbeddingClient()
        self.context_manager = SearchContextManager(self.gemini)
        self.preference_extractor = EmbeddingBasedPreferenceExtractor(self.gemini)
        self.retailers = list(Retailer.objects.using('geodiscounts_db').values_list('name', flat=True))
        self._initialize_strategies()
    
    def _initialize_strategies(self):
        """Initialize search strategies."""
        self.strategies = {
            'optimized': OptimizedSearchStrategy(self),
            'basic_text': BasicTextSearchStrategy(self),
            'semantic': SemanticSearchStrategy(self),
            'category': CategorySearchStrategy(self),
            'retailer': RetailerSearchStrategy(self)
        }
    
    def search(self, query: str) -> Dict[str, Any]:
        """Execute search using appropriate strategies."""
        try:
            # Analyze search context
            context = self._analyze_search_context(query)
            
            # For retailer-specific queries, prioritize basic search
            is_retailer_query = bool(context.product_signals.get('retailer'))
            
            # Try basic text search first for simple or retailer queries
            if len(query.split()) <= 3 or is_retailer_query:
                strategy = self.strategies['basic_text']
                results = strategy.search(query, context)
                if results:
                    # Use LLM to rank and filter results
                    ranked_results = self._rank_results_with_llm(results, query, context)
                    if ranked_results:
                        return {
                            'status': 'success',
                            'results': ranked_results,
                            'context': context.__dict__,
                            'strategy_used': 'basic_text'
                        }
            
            # Try optimized strategy if we have good context
            if (context.brand_preferences or context.category != 'other' or 
                context.product_signals or context.price_range):
                strategy = self.strategies['optimized']
                results = strategy.search(query, context)
                if results:
                    # Use LLM to rank and filter results
                    ranked_results = self._rank_results_with_llm(results, query, context)
                    if ranked_results:
                        return {
                            'status': 'success',
                            'results': ranked_results,
                            'context': context.__dict__,
                            'strategy_used': 'optimized'
                        }
            
            # Fall back to other strategies if needed
            for strategy_name in context.fallback_strategies:
                if strategy_name != 'optimized':
                    strategy = self.strategies.get(strategy_name)
                    if strategy:
                        results = strategy.search(query, context)
                        if results:
                            # Use LLM to rank and filter results
                            ranked_results = self._rank_results_with_llm(results, query, context)
                            if ranked_results:
                                return {
                                    'status': 'success',
                                    'results': ranked_results,
                                    'context': context.__dict__,
                                    'strategy_used': strategy_name
                                }
            
            # If no results found, try a very basic search
            if len(query.split()) <= 3 or is_retailer_query:
                basic_results = self._try_basic_search(query)
                if basic_results:
                    # Use LLM to rank and filter results
                    ranked_results = self._rank_results_with_llm(basic_results, query, context)
                    if ranked_results:
                        return {
                            'status': 'success',
                            'results': ranked_results,
                            'context': context.__dict__,
                            'strategy_used': 'basic'
                        }
            
            return {
                'status': 'no_results',
                'results': [],
                'context': context.__dict__,
                'message': "No results found that match your query."
            }
            
        except Exception as e:
            return self._handle_search_error(SearchRequest(query=query), e)

    def _analyze_search_context(self, query: str) -> SearchContext:
        """Analyze search query using LLM for context understanding."""
        try:
            # Clean and normalize query
            query = query.lower().strip()
            
            # Extract basic context from query
            context = SearchContext(
                query=query,
                search_type='general',
                category='other',
                brand_preferences=[],
                price_range=None,
                product_signals={},
                is_ambiguous=False,
                fallback_strategies=['basic_text', 'semantic', 'category']
            )
            
            # Use LLM to analyze the query with a more structured prompt
            prompt = f"""You are a shopping query analyzer. Analyze this query: "{query}"

            Rules:
            1. Return ONLY a valid JSON object
            2. Use lowercase for all values
            3. Keep responses concise
            4. Set fields to null if not found
            5. Only extract category if explicitly mentioned
            6. Distinguish between retailers and brands
            
            Required JSON structure:
            {{
                "search_type": "store|category|product|general",
                "category": "product category or null",
                "retailer": "store name or null",
                "price_range": {{"min": number, "max": number}} or null,
                "product_signals": {{"key": "value"}} or {{}},
                "is_ambiguous": boolean
            }}
            
            Example input: "Find Zalando Fashion Deals"
            Example output: {{
                "search_type": "store",
                "category": "fashion",
                "retailer": "zalando",
                "price_range": null,
                "product_signals": {{"type": "deals"}},
                "is_ambiguous": false
            }}
            
            Your response for "{query}":"""
            
            response = self.gemini.generate_content(prompt)
            if response and response.text:
                # Clean the response text to ensure valid JSON
                response_text = response.text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                response_text = response_text.strip()
                
                try:
                    analysis = json.loads(response_text)
                    
                    # Update context with LLM analysis
                    context.search_type = analysis.get('search_type', 'general')
                    context.category = analysis.get('category', 'other')
                    context.price_range = analysis.get('price_range')
                    context.product_signals = analysis.get('product_signals', {})
                    context.is_ambiguous = analysis.get('is_ambiguous', True)
                    
                    # Handle retailer separately
                    retailer = analysis.get('retailer')
                    if retailer:
                        context.product_signals['retailer'] = retailer
                    
                    # Set appropriate fallback strategies based on analysis
                    if retailer or context.category != 'other':
                        context.fallback_strategies = ['optimized', 'basic_text', 'semantic']
                    
                except json.JSONDecodeError as e:
                    logger.warning(
                        "Failed to parse LLM analysis as JSON",
                        extra={
                            'query': query,
                            'response': response_text,
                            'error': str(e)
                        }
                    )
            
            return context
            
        except Exception as e:
            logger.error(
                "Error analyzing search context",
                extra={
                    'error': str(e),
                    'query': query
                }
            )
            # Return a basic context as fallback
            return SearchContext(
                query=query,
                search_type='general',
                category='other',
                brand_preferences=[],
                price_range=None,
                product_signals={},
                is_ambiguous=True,
                fallback_strategies=['basic_text', 'semantic', 'category']
            )
            
    def _extract_query_parts(self, query: str) -> Dict[str, str]:
        """Extract meaningful parts from a natural language query using LLM."""
        try:
            # Use LLM to extract query parts with a more structured prompt
            prompt = f"""You are a shopping query analyzer. Extract key information from this query: "{query}"

            Rules:
            1. Return ONLY a valid JSON object
            2. Use lowercase for all values
            3. Set fields to null if not found
            4. Keep responses concise
            
            Required JSON structure:
            {{
                "store": "store name or null",
                "category": "product category or null",
                "product": "specific product or null"
            }}
            
            Example input: "Find Zalando Fashion Deals"
            Example output: {{"store": "zalando", "category": "fashion", "product": "deals"}}
            
            Your response for "{query}":"""
            
            response = self.gemini.generate_content(prompt)
            if not response or not response.text:
                logger.warning(
                    "Empty response from LLM for query parts extraction",
                    extra={'query': query}
                )
                return {'store': None, 'product': None, 'category': None}
            
            # Clean the response text to ensure valid JSON
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse the response
            try:
                parts = json.loads(response_text)
                return {
                    'store': parts.get('store'),
                    'category': parts.get('category'),
                    'product': parts.get('product')
                }
            except json.JSONDecodeError as e:
                logger.warning(
                    "Failed to parse LLM response as JSON",
                    extra={
                        'query': query,
                        'response': response_text,
                        'error': str(e)
                    }
                )
                return {'store': None, 'product': None, 'category': None}
                
        except Exception as e:
            logger.error(
                "Error extracting query parts with LLM",
                extra={
                    'error': str(e),
                    'query': query
                }
            )
            return {'store': None, 'product': None, 'category': None}
            
    def _handle_search_error(self, req: SearchRequest, error: Exception) -> Dict[str, Any]:
        """Enhanced error handling with multiple fallback strategies."""
        error_type = type(error).__name__
        error_msg = str(error)
        
        logger.error(
            "Search error occurred",
            extra={
                'error_type': error_type,
                'error_message': error_msg,
                'request_id': req.id,
                'query': req.query,
                'location': req.location,
                'radius': req.radius
            }
        )
        
        # Track fallback errors
        fallback_errors = []
        
        # Get search context for better fallback handling
        context = self._analyze_search_context(req.query)
        
        # Try each fallback strategy in order
        for strategy in context.fallback_strategies:
            try:
                strategy_instance = self.strategies.get(strategy)
                if strategy_instance:
                    results = strategy_instance.search(req.query, context)
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
                "Specify a category",
                "Try a different search term"
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

    def _serialize(self, discount: Discount) -> Dict[str, Any]:
        """Serialize a discount object with its embedding."""
        try:
            # First check if discount is valid
            if not discount or not discount.id:
                logger.warning("Invalid discount object received for serialization")
                return {}

            # Create base data structure with safe gets and type conversion
            data = {}
            
            # Required fields with type conversion
            try:
                data['id'] = str(discount.id)
            except Exception as e:
                logger.error(f"Error converting discount ID: {str(e)}")
                return {}

            # Optional fields with safe gets and defaults
            data.update({
                'name': str(discount.name) if discount.name else '',
                'description': str(discount.description) if discount.description else '',
                'retailer_name': str(discount.retailer.name) if discount.retailer and discount.retailer.name else None,
                'category': str(discount.category.name) if discount.category and discount.category.name else None,
                'brand': str(discount.brand) if discount.brand else '',
                'store_name': str(discount.store_name) if discount.store_name else '',
                'product_url': str(discount.product_url) if discount.product_url else '',
            })

            # Numeric fields with safe conversion
            try:
                if discount.price_per_unit is not None:
                    data['price'] = float(discount.price_per_unit)
                if discount.discount_value is not None:
                    data['discount_value'] = float(discount.discount_value)
                if discount.discount_percentage is not None:
                    data['discount_percentage'] = float(discount.discount_percentage)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error converting numeric fields: {str(e)}")
                # Continue with other fields

            # Date fields with safe conversion
            try:
                if discount.valid_until:
                    data['valid_until'] = discount.valid_until.isoformat()
            except Exception as e:
                logger.warning(f"Error converting date field: {str(e)}")

            # Image field with safe access
            try:
                if discount.image and hasattr(discount.image, 'url'):
                    data['image'] = discount.image.url
            except Exception as e:
                logger.warning(f"Error accessing image URL: {str(e)}")

            # Log successful serialization
            logger.info(
                "Successfully serialized discount",
                extra={
                    'discount_id': data['id'],
                    'retailer': data.get('retailer_name'),
                    'category': data.get('category')
                }
            )
            
            return data
            
        except Exception as e:
            # Log detailed error information
            logger.error(
                "Error serializing discount",
                extra={
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'discount_id': str(discount.id) if discount and hasattr(discount, 'id') else None,
                    'discount_fields': {
                        'id': getattr(discount, 'id', None),
                        'name': getattr(discount, 'name', None),
                        'retailer': getattr(discount, 'retailer', None),
                        'category': getattr(discount, 'category', None)
                    } if discount else None
                }
            )
            # Return minimal valid data
            return {
                'id': str(discount.id) if discount and hasattr(discount, 'id') else None,
                'name': str(getattr(discount, 'name', '')) if discount else '',
                'retailer_name': str(getattr(discount.retailer, 'name', '')) if discount and hasattr(discount, 'retailer') and discount.retailer else None,
                'category': str(getattr(discount.category, 'name', '')) if discount and hasattr(discount, 'category') and discount.category else None
            }

    def _try_basic_search(self, query: str) -> List[Dict[str, Any]]:
        """Try a very basic search for simple queries."""
        try:
            # Clean and normalize query
            query = query.lower().strip()
            
            # Extract query parts
            query_parts = self._extract_query_parts(query)
            
            # Build query conditions
            conditions = Q()
            
            # If retailer is specified, prioritize finding all items from that retailer
            if query_parts.get('store'):
                retailer_conditions = Q(retailer__name__icontains=query_parts['store']) | Q(store_name__icontains=query_parts['store'])
                
                # If we have category, use it to filter within retailer results
                if query_parts.get('category'):
                    conditions = retailer_conditions & Q(category__name__icontains=query_parts['category'])
                else:
                    # If only retailer is specified, return all their items
                    conditions = retailer_conditions
            else:
                # No retailer specified, use category if available
                if query_parts.get('category'):
                    conditions = Q(category__name__icontains=query_parts['category'])
                else:
                    # If no specific parts found, try the whole query
                    conditions |= Q(retailer__name__icontains=query)
                    conditions |= Q(store_name__icontains=query)
                    conditions |= Q(name__icontains=query)
                    conditions |= Q(title__icontains=query)
                    conditions |= Q(description__icontains=query)
            
            # Single optimized query with proper indexing
            discounts = Discount.objects.using('geodiscounts_db').select_related(
                'category', 'retailer'
            ).filter(
                conditions,
                is_active=True
            ).order_by(
                '-discount_percentage',
                '-created_at'
            )[:50]  # Increased limit to get more results
            
            if not discounts:
                return []
                
            # Serialize results with error handling
            results = []
            for discount in discounts:
                try:
                    result = self._serialize(discount)
                    if result and result.get('id'):  # Only add if we have at least an ID
                        # Add relevance score
                        result['relevance_score'] = self._calculate_relevance_score(discount, query_parts)
                        results.append(result)
                except Exception as e:
                    logger.warning(
                        "Error processing discount",
                        extra={
                            'error': str(e),
                            'discount_id': str(discount.id) if discount and hasattr(discount, 'id') else None
                        }
                    )
                    continue
            
            # Sort by relevance score
            results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            return results[:20]  # Return top 20 most relevant results
            
        except Exception as e:
            logger.error(
                "Error in basic search",
                extra={
                    'error': str(e),
                    'query': query
                }
            )
            return []
            
    def _calculate_relevance_score(self, discount: Discount, query_parts: Dict[str, str]) -> float:
        """Calculate relevance score for a discount based on query parts."""
        score = 0.0
        
        # Highest priority: Retailer match
        if query_parts.get('store'):
            if (discount.retailer and discount.retailer.name and 
                query_parts['store'].lower() in discount.retailer.name.lower()):
                score += 3.0
            elif (discount.store_name and 
                  query_parts['store'].lower() in discount.store_name.lower()):
                score += 2.5
        
        # Second priority: Category match
        if query_parts.get('category'):
            if (discount.category and discount.category.name and 
                query_parts['category'].lower() in discount.category.name.lower()):
                score += 2.0
        
        # Third priority: Product match
        if query_parts.get('product'):
            if (discount.name and 
                query_parts['product'].lower() in discount.name.lower()):
                score += 1.5
            elif (discount.description and 
                  query_parts['product'].lower() in discount.description.lower()):
                score += 1.0
        
        # Bonus for active discounts
        if discount.is_active:
            score += 0.5
        
        # Bonus for higher discount percentages
        if discount.discount_percentage:
            score += min(discount.discount_percentage / 100, 1.0)
        
        return score

    def _rank_results_with_llm(self, results: List[Dict[str, Any]], query: str, context: SearchContext) -> List[Dict[str, Any]]:
        """Use LLM to intelligently rank and filter search results."""
        try:
            if not results:
                return []
                
            # Prepare results for LLM analysis
            results_for_llm = []
            for result in results:
                # Only include fields that are guaranteed to be present
                result_info = {
                    'id': result.get('id'),
                    'name': result.get('name', ''),
                    'description': result.get('description', ''),
                    'retailer_name': result.get('retailer_name'),
                    'category': result.get('category'),
                    'price': result.get('price'),
                    'discount_value': result.get('discount_value'),
                    'discount_percentage': result.get('discount_percentage'),
                    'brand': result.get('brand', ''),
                    'store_name': result.get('store_name', '')
                }
                results_for_llm.append(result_info)
            
            # Create prompt for LLM
            prompt = f"""You are a shopping search result ranker. Rank these results for the query: "{query}"

            Context:
            - Search type: {context.search_type}
            - Category: {context.category}
            - Retailer: {context.product_signals.get('retailer')}
            - Brand preferences: {context.brand_preferences}
            - Product signals: {context.product_signals}

            Rules:
            1. Return ONLY a valid JSON array of result IDs in order of relevance
            2. Include only IDs of results that are relevant to the query
            3. Consider retailer matches as highest priority
            4. Consider category matches as second priority
            5. Consider product matches as third priority
            6. Consider discount value as a tiebreaker

            Results to rank:
            {json.dumps(results_for_llm, indent=2)}

            Your response should be a JSON array of relevant result IDs in order of relevance:"""
            
            # Get LLM ranking
            response = self.gemini.generate_content(prompt)
            if not response or not response.text:
                logger.warning(
                    "Empty response from LLM for result ranking",
                    extra={'query': query}
                )
                return results[:20]  # Fallback to first 20 results
            
            # Clean and parse response
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            try:
                ranked_ids = json.loads(response_text)
                if not isinstance(ranked_ids, list):
                    return results[:20]
                
                # Create lookup for results
                result_lookup = {str(r['id']): r for r in results}
                
                # Return ranked results
                ranked_results = []
                for result_id in ranked_ids:
                    if str(result_id) in result_lookup:
                        ranked_results.append(result_lookup[str(result_id)])
                
                return ranked_results[:20]  # Return top 20 ranked results
                
            except json.JSONDecodeError as e:
                logger.warning(
                    "Failed to parse LLM ranking as JSON",
                    extra={
                        'query': query,
                        'response': response_text,
                        'error': str(e)
                    }
                )
                return results[:20]  # Fallback to first 20 results
                
        except Exception as e:
            logger.error(
                "Error ranking results with LLM",
                extra={
                    'error': str(e),
                    'query': query
                }
            )
            return results[:20]  # Fallback to first 20 results 