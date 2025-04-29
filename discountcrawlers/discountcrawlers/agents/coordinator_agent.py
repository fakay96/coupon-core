"""Coordinator agent for managing search and metadata operations."""

from __future__ import annotations
import logging
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from django.utils import timezone
from django.core.cache import cache

from .search_agent import SearchAgent
from .metadata_agent import MetadataAgent

LOGGER: logging.Logger = logging.getLogger(__name__)

class CoordinatorAgent:
    """Agent for coordinating search and metadata operations.
    
    This agent manages the interaction between search and metadata agents,
    tracks system state, and provides monitoring capabilities.
    
    Attributes:
        search_agent: Agent responsible for search operations
        metadata_agent: Agent responsible for metadata operations
        system_state: Dictionary containing current system state
    """
    
    def __init__(self) -> None:
        """Initialize the coordinator agent."""
        self.search_agent = SearchAgent()
        self.metadata_agent = MetadataAgent()
        self.system_state: Dict[str, Any] = {
            'start_time': timezone.now(),
            'agents': {
                'search': {'status': 'initialized'},
                'metadata': {'status': 'initialized'}
            },
            'errors': [],
            'metrics': {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0
            }
        }
        
    def _start_metadata_agent(self) -> None:
        """Start the metadata agent in a separate thread."""
        thread = threading.Thread(target=self.metadata_agent.start)
        thread.daemon = True
        thread.start()
        
    def process_search_request(self, query: str) -> Dict[str, Any]:
        """Process a search request.
        
        Args:
            query: Search query string
            
        Returns:
            Dict containing search results or error information
        """
        self.system_state['metrics']['total_requests'] += 1
        
        try:
            response = self.search_agent.search(query)
            self.system_state['metrics']['successful_requests'] += 1
            return response
        except Exception as e:
            self._handle_error(e)
            self.system_state['metrics']['failed_requests'] += 1
            return {
                'error': True,
                'message': str(e)
            }
            
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status.
        
        Returns:
            Dict containing system status information
        """
        return {
            'start_time': self.system_state['start_time'],
            'agents': self.system_state['agents'],
            'errors': self.system_state['errors'],
            'metrics': self.system_state['metrics'],
            'metadata_agent_stats': self.metadata_agent.get_stats(),
            'cache_status': {
                'memory_usage': self._get_cache_memory_usage()
            }
        }
        
    def _handle_error(self, error: Exception) -> None:
        """Handle and log system errors.
        
        Args:
            error: Exception that occurred
        """
        error_info = {
            'type': error.__class__.__name__,
            'message': str(error),
            'timestamp': timezone.now()
        }
        self.system_state['errors'].append(error_info)
        LOGGER.error(f"Error occurred: {str(error)}")
        
    def _get_cache_memory_usage(self) -> int:
        """Calculate current cache memory usage.
        
        Returns:
            Total memory usage in bytes
        """
        try:
            if not hasattr(cache, '_cache'):
                return 0
                
            total_size = 0
            for key, value in cache._cache.items():
                total_size += len(str(key)) + len(str(value))
            return total_size
        except Exception:
            return 0 