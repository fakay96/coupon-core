"""
Preference service for managing user preferences and recommendations.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Union
from django.utils import timezone

from geodiscounts.models import UserPreference, Discount, Category, Retailer
from geodiscounts.v1.utils.understand_context import GeminiEmbeddingClient
from ..search.extractors import EmbeddingBasedPreferenceExtractor

logger = logging.getLogger(__name__)

class PreferenceService:
    """Service for managing user preferences and recommendations."""
    
    def __init__(self):
        self.gemini = GeminiEmbeddingClient()
        self.preference_extractor = EmbeddingBasedPreferenceExtractor(self.gemini)
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences."""
        try:
            preferences = UserPreference.objects.using('geodiscounts_db').filter(
                user_id=user_id
            ).first()
            
            if not preferences:
                return self._get_default_preferences()
            
            return {
                'brand_preferences': preferences.brand_preferences or [],
                'category_preferences': preferences.category_preferences or [],
                'price_range': preferences.price_range,
                'location': preferences.location,
                'radius': preferences.radius,
                'last_updated': preferences.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(
                "Error getting user preferences",
                extra={
                    'error': str(e),
                    'user_id': user_id
                }
            )
            return self._get_default_preferences()
    
    def update_preferences(self, user_id: str, text: str) -> Dict[str, Any]:
        """Update user preferences based on text analysis."""
        try:
            # Extract preferences from text
            extracted_preferences = self.preference_extractor.extract_preferences(text)
            
            # Get existing preferences
            preferences = UserPreference.objects.using('geodiscounts_db').filter(
                user_id=user_id
            ).first()
            
            if not preferences:
                preferences = UserPreference(user_id=user_id)
            
            # Update preferences
            if extracted_preferences['brand_preferences']:
                preferences.brand_preferences = extracted_preferences['brand_preferences']
            
            if extracted_preferences['price_preferences']:
                preferences.price_range = extracted_preferences['price_preferences']
            
            if extracted_preferences['location_preferences']:
                preferences.location = extracted_preferences['location_preferences']['location']
                preferences.radius = extracted_preferences['location_preferences']['radius']
            
            preferences.updated_at = timezone.now()
            preferences.save(using='geodiscounts_db')
            
            logger.info(
                "Updated user preferences",
                extra={
                    'user_id': user_id,
                    'preferences': extracted_preferences
                }
            )
            
            return self.get_user_preferences(user_id)
            
        except Exception as e:
            logger.error(
                "Error updating preferences",
                extra={
                    'error': str(e),
                    'user_id': user_id,
                    'text': text
                }
            )
            return self.get_user_preferences(user_id)
    
    def get_recommendations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get personalized recommendations based on user preferences."""
        try:
            # Get user preferences
            preferences = self.get_user_preferences(user_id)
            
            # Build recommendation query
            query = Discount.objects.using('geodiscounts_db').filter(
                valid_until__gte=timezone.now()
            ).select_related('retailer', 'category')
            
            # Add preference filters
            if preferences['brand_preferences']:
                query = query.filter(retailer__name__in=preferences['brand_preferences'])
            
            if preferences['category_preferences']:
                query = query.filter(category__name__in=preferences['category_preferences'])
            
            if preferences['price_range']:
                min_price = preferences['price_range'].get('min')
                max_price = preferences['price_range'].get('max')
                if min_price is not None:
                    query = query.filter(price_per_unit__gte=min_price)
                if max_price is not None:
                    query = query.filter(price_per_unit__lte=max_price)
            
            # Get results
            results = list(query[:limit])
            
            # Calculate relevance scores
            scored_results = []
            for result in results:
                score = self._calculate_relevance_score(result, preferences)
                scored_results.append((result, score))
            
            # Sort by relevance
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            # Serialize results
            return [
                self._serialize_discount(result)
                for result, _ in scored_results
            ]
            
        except Exception as e:
            logger.error(
                "Error getting recommendations",
                extra={
                    'error': str(e),
                    'user_id': user_id
                }
            )
            return []
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default preferences."""
        return {
            'brand_preferences': [],
            'category_preferences': [],
            'price_range': None,
            'location': None,
            'radius': None,
            'last_updated': timezone.now().isoformat()
        }
    
    def _calculate_relevance_score(self, discount: Discount, preferences: Dict[str, Any]) -> float:
        """Calculate relevance score for a discount based on user preferences."""
        score = 0.0
        
        # Brand preference score
        if preferences['brand_preferences'] and discount.retailer:
            if discount.retailer.name in preferences['brand_preferences']:
                score += 0.4
        
        # Category preference score
        if preferences['category_preferences'] and discount.category:
            if discount.category.name in preferences['category_preferences']:
                score += 0.3
        
        # Price range score
        if preferences['price_range'] and discount.price_per_unit:
            min_price = preferences['price_range'].get('min')
            max_price = preferences['price_range'].get('max')
            if min_price is not None and max_price is not None:
                if min_price <= discount.price_per_unit <= max_price:
                    score += 0.3
        
        return score
    
    def _serialize_discount(self, discount: Discount) -> Dict[str, Any]:
        """Serialize a discount object."""
        return {
            'id': str(discount.id),
            'name': discount.name,
            'description': discount.description,
            'retailer_name': discount.retailer.name if discount.retailer else None,
            'category': discount.category.name if discount.category else None,
            'price': float(discount.price_per_unit) if discount.price_per_unit else None,
            'discount_value': float(discount.discount_value) if discount.discount_value else None,
            'discount_percentage': float(discount.discount_percentage) if discount.discount_percentage else None,
            'brand': discount.brand,
            'valid_until': discount.valid_until.isoformat() if discount.valid_until else None,
            'store_name': discount.store_name,
            'product_url': discount.product_url,
            'image': discount.image.url if discount.image else None
        }
    
    def extract_preferences(self, text: str) -> Dict[str, Any]:
        """Extract preferences from text using the preference extractor.
        
        Args:
            text: The text to extract preferences from.
            
        Returns:
            Dictionary containing extracted preferences.
            
        Raises:
            Exception: If there's an error extracting preferences.
        """
        try:
            # Extract preferences using the preference extractor
            preferences = self.preference_extractor.extract_preferences(text)
            
            logger.info(
                "Extracted preferences from text",
                extra={
                    'text': text,
                    'preferences': preferences
                }
            )
            
            return preferences
            
        except Exception as e:
            logger.error(
                "Error extracting preferences",
                extra={
                    'error': str(e),
                    'text': text
                }
            )
            return {
                'brand_preferences': [],
                'price_preferences': None,
                'location_preferences': None
            } 