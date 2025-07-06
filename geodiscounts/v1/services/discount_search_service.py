"""
Discount Search Service

This module provides business logic for discount search operations,
including category-based filtering, geospatial queries, and result optimization.
"""

from typing import Dict, List, Optional, Any, Tuple
from django.db.models import Q, F, Count, Prefetch
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from django.db import connection
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from geodiscounts.models import Discount, Category, Retailer
from coupon_core.utils.logging import geo_logger, geo_structured_logger

logger = logging.getLogger(__name__)


@dataclass
class SearchFilters:
    """Data class for search filter parameters."""
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    min_discount_value: Optional[float] = None
    max_discount_value: Optional[float] = None
    brand: Optional[str] = None
    retailer_id: Optional[int] = None
    is_active_only: bool = True
    include_expired: bool = False
    location: Optional[Dict[str, float]] = None
    radius_km: Optional[float] = None
    sort_by: str = 'created_at'
    sort_order: str = 'desc'


class DiscountSearchService:
    """
    Service for handling discount search operations with advanced filtering
    and optimization capabilities.
    """
    
    def __init__(self):
        self.cache_timeout = 300  # 5 minutes
        self.max_results = 1000
    
    def search_discounts_by_category(
        self, 
        category_query: str,
        filters: SearchFilters,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Search discounts by category with comprehensive filtering and pagination.
        
        Args:
            category_query: Category name or ID to search for
            filters: Search filter parameters
            page: Page number for pagination
            page_size: Number of items per page
            
        Returns:
            Dictionary containing paginated results and metadata
        """
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(category_query, filters, page, page_size)
            
            # Try to get from cache first
            cached_result = cache.get(cache_key)
            if cached_result:
                geo_structured_logger.info(
                    geo_logger,
                    "Cache hit for discount search",
                    "discount_search_cache_hit",
                    {
                        'category_query': category_query,
                        'page': page,
                        'page_size': page_size
                    }
                )
                return cached_result
            
            # Build queryset
            queryset = self._build_search_queryset(category_query, filters)
            
            # Apply pagination
            total_count = queryset.count()
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            
            # Get paginated results
            discounts = list(queryset[start_index:end_index])
            
            # Calculate pagination metadata
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_previous = page > 1
            
            # Prepare response
            result = {
                'results': discounts,
                'pagination': {
                    'current_page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': has_next,
                    'has_previous': has_previous,
                    'next_page': page + 1 if has_next else None,
                    'previous_page': page - 1 if has_previous else None,
                },
                'filters_applied': self._serialize_filters(filters),
                'search_metadata': {
                    'category_query': category_query,
                    'search_timestamp': timezone.now().isoformat(),
                    'results_count': len(discounts),
                }
            }
            
            # Cache the result
            cache.set(cache_key, result, self.cache_timeout)
            
            geo_structured_logger.info(
                geo_logger,
                "Discount search completed successfully",
                "discount_search_success",
                {
                    'category_query': category_query,
                    'total_count': total_count,
                    'page': page,
                    'page_size': page_size,
                    'cache_key': cache_key
                }
            )
            
            return result
            
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Error in discount search",
                "discount_search_error",
                e,
                {
                    'category_query': category_query,
                    'page': page,
                    'page_size': page_size
                }
            )
            raise
    
    def _build_search_queryset(self, category_query: str, filters: SearchFilters):
        """
        Build optimized queryset for discount search.
        
        Args:
            category_query: Category query string
            filters: Search filters
            
        Returns:
            Optimized queryset
        """
        # Start with base queryset
        queryset = Discount.objects.select_related(
            'retailer', 'category'
        ).prefetch_related(
            Prefetch('retailer', queryset=Retailer.objects.only('id', 'name', 'location'))
        )
        
        # Apply category filter
        queryset = self._apply_category_filter(queryset, category_query)
        
        # Apply other filters
        queryset = self._apply_filters(queryset, filters)
        
        # Apply sorting
        queryset = self._apply_sorting(queryset, filters.sort_by, filters.sort_order)
        
        return queryset
    
    def _apply_category_filter(self, queryset, category_query: str):
        """Apply category-based filtering."""
        try:
            # Try to parse as category ID first
            category_id = int(category_query)
            return queryset.filter(category_id=category_id)
        except (ValueError, TypeError):
            # If not an ID, search by name
            return queryset.filter(
                Q(category__name__icontains=category_query) |
                Q(category__name__iexact=category_query)
            )
    
    def _apply_filters(self, queryset, filters: SearchFilters):
        """Apply all search filters to the queryset."""
        # Active discounts filter
        if filters.is_active_only:
            queryset = queryset.filter(is_active=True)
        
        # Expiration filter
        if not filters.include_expired:
            queryset = queryset.filter(expiration_date__gt=timezone.now())
        
        # Discount value range
        if filters.min_discount_value is not None:
            queryset = queryset.filter(discount_value__gte=filters.min_discount_value)
        
        if filters.max_discount_value is not None:
            queryset = queryset.filter(discount_value__lte=filters.max_discount_value)
        
        # Brand filter
        if filters.brand:
            queryset = queryset.filter(brand__icontains=filters.brand)
        
        # Retailer filter
        if filters.retailer_id:
            queryset = queryset.filter(retailer_id=filters.retailer_id)
        
        # Geospatial filter
        if filters.location and filters.radius_km:
            user_point = Point(filters.location['longitude'], filters.location['latitude'])
            queryset = queryset.filter(
                location__distance_lte=(user_point, Distance(km=filters.radius_km))
            ).annotate(
                distance=Distance('location', user_point)
            )
        
        return queryset
    
    def _apply_sorting(self, queryset, sort_by: str, sort_order: str):
        """Apply sorting to the queryset."""
        # Validate sort field
        valid_sort_fields = {
            'created_at', 'updated_at', 'discount_value', 'expiration_date',
            'retailer__name', 'category__name', 'brand'
        }
        
        if sort_by not in valid_sort_fields:
            sort_by = 'created_at'
        
        # Apply sort order
        if sort_order.lower() == 'desc':
            sort_by = f'-{sort_by}'
        
        # Handle geospatial sorting
        if hasattr(queryset, 'annotate') and 'distance' in queryset.query.annotations:
            if sort_by == 'distance':
                return queryset.order_by('distance')
            elif sort_by == '-distance':
                return queryset.order_by('-distance')
        
        return queryset.order_by(sort_by)
    
    def _generate_cache_key(self, category_query: str, filters: SearchFilters, page: int, page_size: int) -> str:
        """Generate cache key for search results."""
        filter_hash = hash(str(filters.__dict__))
        return f"discount_search:{category_query}:{filter_hash}:{page}:{page_size}"
    
    def _serialize_filters(self, filters: SearchFilters) -> Dict[str, Any]:
        """Serialize filters for response metadata."""
        return {
            'category_id': filters.category_id,
            'category_name': filters.category_name,
            'min_discount_value': filters.min_discount_value,
            'max_discount_value': filters.max_discount_value,
            'brand': filters.brand,
            'retailer_id': filters.retailer_id,
            'is_active_only': filters.is_active_only,
            'include_expired': filters.include_expired,
            'has_location_filter': filters.location is not None,
            'radius_km': filters.radius_km,
            'sort_by': filters.sort_by,
            'sort_order': filters.sort_order,
        }
    
    def get_category_suggestions(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get category suggestions based on user query.
        
        Args:
            query: User query string
            limit: Maximum number of suggestions
            
        Returns:
            List of category suggestions
        """
        cache_key = f"category_suggestions:{query}:{limit}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        categories = Category.objects.filter(
            name__icontains=query
        ).values('id', 'name')[:limit]
        
        suggestions = [
            {
                'id': cat['id'],
                'name': cat['name'],
                'type': 'category'
            }
            for cat in categories
        ]
        
        # Cache for 10 minutes
        cache.set(cache_key, suggestions, 600)
        
        return suggestions
    
    def get_search_statistics(self, category_query: str) -> Dict[str, Any]:
        """
        Get search statistics for a category.
        
        Args:
            category_query: Category query string
            
        Returns:
            Dictionary with search statistics
        """
        cache_key = f"search_stats:{category_query}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        # Get category
        try:
            category_id = int(category_query)
            category = Category.objects.get(id=category_id)
        except (ValueError, TypeError, Category.DoesNotExist):
            category = Category.objects.filter(name__icontains=category_query).first()
        
        if not category:
            return {'error': 'Category not found'}
        
        # Calculate statistics
        total_discounts = Discount.objects.filter(category=category).count()
        active_discounts = Discount.objects.filter(
            category=category, 
            is_active=True, 
            expiration_date__gt=timezone.now()
        ).count()
        
        avg_discount_value = Discount.objects.filter(
            category=category,
            is_active=True,
            expiration_date__gt=timezone.now()
        ).aggregate(avg_value=F('discount_value'))['avg_value'] or 0
        
        stats = {
            'category_id': category.id,
            'category_name': category.name,
            'total_discounts': total_discounts,
            'active_discounts': active_discounts,
            'expired_discounts': total_discounts - active_discounts,
            'average_discount_value': float(avg_discount_value),
            'last_updated': timezone.now().isoformat(),
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, stats, 300)
        
        return stats


# Global service instance
discount_search_service = DiscountSearchService() 