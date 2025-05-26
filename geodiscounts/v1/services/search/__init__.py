"""
Search module for handling product and discount searches.
"""

from .service import EnhancedSearchService
from .context import SearchContext, SearchContextManager
from .strategies import (
    SearchStrategy,
    BasicTextSearchStrategy,
    SemanticSearchStrategy,
    CategorySearchStrategy,
    OptimizedSearchStrategy,
    RetailerSearchStrategy,
    SearchStrategyFactory
)
from .extractors import (
    EmbeddingBasedCategoryService,
    EnhancedProductExtractor,
    MultilingualMatcher
)

__all__ = [
    'EnhancedSearchService',
    'SearchContext',
    'SearchContextManager',
    'SearchStrategy',
    'BasicTextSearchStrategy',
    'SemanticSearchStrategy',
    'CategorySearchStrategy',
    'OptimizedSearchStrategy',
    'RetailerSearchStrategy',
    'SearchStrategyFactory',
    'EmbeddingBasedCategoryService',
    'EnhancedProductExtractor',
    'MultilingualMatcher'
] 