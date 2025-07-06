"""
Performance Optimization Module for Conversation Service

This module provides performance monitoring, caching strategies, and optimization
utilities for the conversation service.
"""

import time
import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from dataclasses import dataclass
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from django.db import connection, reset_queries
from django.db.models import QuerySet

from coupon_core.utils.logging import geo_logger, geo_structured_logger

@dataclass
class PerformanceMetrics:
    """Performance metrics data class."""
    operation: str
    duration_ms: float
    cache_hits: int = 0
    cache_misses: int = 0
    db_queries: int = 0
    memory_usage_mb: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class PerformanceMonitor:
    """Performance monitoring utility."""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.enabled = getattr(settings, 'PERFORMANCE_MONITORING_ENABLED', True)
    
    def record_metric(self, metric: PerformanceMetrics):
        """Record a performance metric."""
        if self.enabled:
            self.metrics.append(metric)
            geo_structured_logger.info(
                geo_logger,
                "Performance metric recorded",
                "performance_metric",
                {
                    'operation': metric.operation,
                    'duration_ms': metric.duration_ms,
                    'cache_hits': metric.cache_hits,
                    'cache_misses': metric.cache_misses,
                    'db_queries': metric.db_queries
                }
            )
    
    def get_average_metrics(self, operation: str, hours: int = 24) -> Optional[PerformanceMetrics]:
        """Get average metrics for an operation over the last N hours."""
        if not self.enabled:
            return None
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        relevant_metrics = [
            m for m in self.metrics 
            if m.operation == operation and m.timestamp > cutoff_time
        ]
        
        if not relevant_metrics:
            return None
        
        avg_duration = sum(m.duration_ms for m in relevant_metrics) / len(relevant_metrics)
        avg_cache_hits = sum(m.cache_hits for m in relevant_metrics) / len(relevant_metrics)
        avg_cache_misses = sum(m.cache_misses for m in relevant_metrics) / len(relevant_metrics)
        avg_db_queries = sum(m.db_queries for m in relevant_metrics) / len(relevant_metrics)
        
        return PerformanceMetrics(
            operation=operation,
            duration_ms=avg_duration,
            cache_hits=avg_cache_hits,
            cache_misses=avg_cache_misses,
            db_queries=avg_db_queries
        )

# Global performance monitor
performance_monitor = PerformanceMonitor()

def performance_tracker(operation_name: str):
    """Decorator to track performance of functions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not performance_monitor.enabled:
                return await func(*args, **kwargs)
            
            start_time = time.time()
            initial_queries = len(connection.queries)
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                final_queries = len(connection.queries)
                
                metric = PerformanceMetrics(
                    operation=operation_name,
                    duration_ms=duration_ms,
                    db_queries=final_queries - initial_queries
                )
                performance_monitor.record_metric(metric)
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                metric = PerformanceMetrics(
                    operation=f"{operation_name}_error",
                    duration_ms=duration_ms
                )
                performance_monitor.record_metric(metric)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not performance_monitor.enabled:
                return func(*args, **kwargs)
            
            start_time = time.time()
            initial_queries = len(connection.queries)
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                final_queries = len(connection.queries)
                
                metric = PerformanceMetrics(
                    operation=operation_name,
                    duration_ms=duration_ms,
                    db_queries=final_queries - initial_queries
                )
                performance_monitor.record_metric(metric)
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                metric = PerformanceMetrics(
                    operation=f"{operation_name}_error",
                    duration_ms=duration_ms
                )
                performance_monitor.record_metric(metric)
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

class CacheManager:
    """Advanced cache management utility."""
    
    @staticmethod
    def get_or_set(key: str, getter_func: Callable, ttl: int = 3600, **kwargs) -> Any:
        """Get from cache or set using getter function."""
        cached_value = cache.get(key)
        if cached_value is not None:
            performance_monitor.record_metric(PerformanceMetrics(
                operation="cache_hit",
                duration_ms=0,
                cache_hits=1
            ))
            return cached_value
        
        performance_monitor.record_metric(PerformanceMetrics(
            operation="cache_miss",
            duration_ms=0,
            cache_misses=1
        ))
        
        value = getter_func(**kwargs)
        cache.set(key, value, ttl)
        return value
    
    @staticmethod
    async def async_get_or_set(key: str, getter_func: Callable, ttl: int = 3600, **kwargs) -> Any:
        """Async version of get_or_set."""
        cached_value = cache.get(key)
        if cached_value is not None:
            performance_monitor.record_metric(PerformanceMetrics(
                operation="cache_hit",
                duration_ms=0,
                cache_hits=1
            ))
            return cached_value
        
        performance_monitor.record_metric(PerformanceMetrics(
            operation="cache_miss",
            duration_ms=0,
            cache_misses=1
        ))
        
        value = await getter_func(**kwargs)
        cache.set(key, value, ttl)
        return value
    
    @staticmethod
    def batch_get(keys: List[str]) -> Dict[str, Any]:
        """Batch get multiple cache keys."""
        results = {}
        cache_hits = 0
        cache_misses = 0
        
        for key in keys:
            value = cache.get(key)
            if value is not None:
                results[key] = value
                cache_hits += 1
            else:
                cache_misses += 1
        
        performance_monitor.record_metric(PerformanceMetrics(
            operation="batch_cache_get",
            duration_ms=0,
            cache_hits=cache_hits,
            cache_misses=cache_misses
        ))
        
        return results
    
    @staticmethod
    def batch_set(key_value_pairs: Dict[str, Any], ttl: int = 3600):
        """Batch set multiple cache keys."""
        for key, value in key_value_pairs.items():
            cache.set(key, value, ttl)

class QueryOptimizer:
    """Database query optimization utilities."""
    
    @staticmethod
    def optimize_queryset(queryset: QuerySet, select_related: List[str] = None, 
                         prefetch_related: List[str] = None) -> QuerySet:
        """Optimize queryset with select_related and prefetch_related."""
        if select_related:
            queryset = queryset.select_related(*select_related)
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)
        return queryset
    
    @staticmethod
    def count_queries(func: Callable) -> Callable:
        """Decorator to count database queries."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            initial_count = len(connection.queries)
            result = func(*args, **kwargs)
            final_count = len(connection.queries)
            
            query_count = final_count - initial_count
            geo_structured_logger.info(
                geo_logger,
                "Database queries executed",
                "query_count",
                {
                    'function': func.__name__,
                    'query_count': query_count,
                    'queries': connection.queries[initial_count:final_count]
                }
            )
            
            return result
        return wrapper

class EmbeddingOptimizer:
    """Embedding-specific optimizations."""
    
    @staticmethod
    def batch_embeddings(texts: List[str], batch_size: int = 5) -> List[List[str]]:
        """Split texts into batches for efficient embedding generation."""
        return [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
    
    @staticmethod
    def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
        """Normalize embedding for faster similarity calculations."""
        norm = np.linalg.norm(embedding)
        if norm > 0:
            return embedding / norm
        return embedding
    
    @staticmethod
    def precompute_similarity_matrix(embeddings: Dict[str, np.ndarray]) -> Dict[str, Dict[str, float]]:
        """Precompute similarity matrix for faster lookups."""
        matrix = {}
        normalized_embeddings = {
            key: EmbeddingOptimizer.normalize_embedding(emb) 
            for key, emb in embeddings.items()
        }
        
        for key1, emb1 in normalized_embeddings.items():
            matrix[key1] = {}
            for key2, emb2 in normalized_embeddings.items():
                if key1 != key2:
                    similarity = float(np.dot(emb1, emb2))
                    matrix[key1][key2] = similarity
        
        return matrix

class PerformanceConfig:
    """Performance configuration settings."""
    
    # Cache TTLs
    EMBEDDING_CACHE_TTL = 3600 * 24 * 7  # 7 days
    CATEGORY_CACHE_TTL = 3600 * 24 * 30  # 30 days
    CONVERSATION_CACHE_TTL = 300  # 5 minutes
    PREFERENCE_CACHE_TTL = 3600  # 1 hour
    
    # Batch sizes
    EMBEDDING_BATCH_SIZE = 5
    PREFERENCE_BATCH_SIZE = 10
    DATABASE_BATCH_SIZE = 100
    
    # Timeouts
    EMBEDDING_TIMEOUT = 10  # seconds
    DATABASE_TIMEOUT = 5  # seconds
    
    # Thresholds
    SIMILARITY_THRESHOLD = 0.6
    CONFIDENCE_THRESHOLD = 0.7
    
    @classmethod
    def get_cache_ttl(cls, cache_type: str) -> int:
        """Get cache TTL for a specific type."""
        ttl_map = {
            'embedding': cls.EMBEDDING_CACHE_TTL,
            'category': cls.CATEGORY_CACHE_TTL,
            'conversation': cls.CONVERSATION_CACHE_TTL,
            'preference': cls.PREFERENCE_CACHE_TTL
        }
        return ttl_map.get(cache_type, 3600)

# Performance optimization utilities
def optimize_conversation_service():
    """Apply performance optimizations to conversation service."""
    recommendations = []
    
    # Check cache hit rates
    cache_metrics = performance_monitor.get_average_metrics("cache_hit")
    if cache_metrics and cache_metrics.cache_hits < cache_metrics.cache_misses:
        recommendations.append("Consider increasing cache TTL or improving cache keys")
    
    # Check database query counts
    db_metrics = performance_monitor.get_average_metrics("conversation_get")
    if db_metrics and db_metrics.db_queries > 5:
        recommendations.append("Consider using select_related/prefetch_related to reduce queries")
    
    # Check embedding generation times
    embedding_metrics = performance_monitor.get_average_metrics("embedding_generation")
    if embedding_metrics and embedding_metrics.duration_ms > 1000:
        recommendations.append("Consider implementing embedding caching or batching")
    
    return recommendations

def get_performance_report() -> Dict[str, Any]:
    """Generate a comprehensive performance report."""
    report = {
        'timestamp': datetime.now().isoformat(),
        'cache_performance': {},
        'database_performance': {},
        'embedding_performance': {},
        'recommendations': optimize_conversation_service()
    }
    
    # Cache performance
    cache_hit_metrics = performance_monitor.get_average_metrics("cache_hit")
    cache_miss_metrics = performance_monitor.get_average_metrics("cache_miss")
    
    if cache_hit_metrics and cache_miss_metrics:
        total_requests = cache_hit_metrics.cache_hits + cache_miss_metrics.cache_misses
        hit_rate = (cache_hit_metrics.cache_hits / total_requests) * 100 if total_requests > 0 else 0
        
        report['cache_performance'] = {
            'hit_rate_percent': round(hit_rate, 2),
            'total_requests': total_requests,
            'cache_hits': cache_hit_metrics.cache_hits,
            'cache_misses': cache_miss_metrics.cache_misses
        }
    
    # Database performance
    db_metrics = performance_monitor.get_average_metrics("conversation_get")
    if db_metrics:
        report['database_performance'] = {
            'average_queries': round(db_metrics.db_queries, 2),
            'average_duration_ms': round(db_metrics.duration_ms, 2)
        }
    
    # Embedding performance
    embedding_metrics = performance_monitor.get_average_metrics("embedding_generation")
    if embedding_metrics:
        report['embedding_performance'] = {
            'average_duration_ms': round(embedding_metrics.duration_ms, 2)
        }
    
    return report 