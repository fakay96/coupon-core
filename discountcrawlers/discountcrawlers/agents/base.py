"""Base agent class for all discount crawler agents."""

from typing import Dict, Any, Optional, List
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
import numpy as np
from redis import Redis
import json

LOGGER = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base agent class for all discount crawler agents.
    
    This class provides common functionality and configuration for all agents.
    """
    
    def __init__(self, redis_client: Redis):
        """Initialize the agent.
        
        Args:
            redis_client: Redis client instance
        """
        self.redis_client = redis_client
        self.processing_stats: Dict[str, Any] = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'last_error': None,
            'start_time': timezone.now().isoformat()
        }
        
    @abstractmethod
    def start(self) -> None:
        """Start the agent.
        
        This method should be implemented by subclasses to start the agent's main processing loop.
        """
        raise NotImplementedError("Subclasses must implement start method")
        
    def _process_batch(self, batch: List[Dict[str, Any]]) -> None:
        """Process a batch of items.
        
        Args:
            batch: List of items to process
        """
        if not batch:
            return
            
        try:
            with transaction.atomic():
                for item in batch:
                    self._process_item(item)
                    
                # Update stats
                self.processing_stats['total_processed'] += len(batch)
                self.processing_stats['successful'] += len(batch)
                
        except Exception as e:
            LOGGER.error(f"Failed to process batch: {str(e)}")
            self.processing_stats['failed'] += len(batch)
            self.processing_stats['last_error'] = str(e)
            
            # Retry failed items
            self._retry_failed_items(batch)
            
    @abstractmethod
    def _process_item(self, item: Dict[str, Any]) -> None:
        """Process a single item.
        
        This method should be implemented by subclasses to process a single item.
        
        Args:
            item: Item to process
        """
        raise NotImplementedError("Subclasses must implement _process_item method")
        
    def _retry_failed_items(self, failed_items: List[Dict[str, Any]]) -> None:
        """Retry processing failed items.
        
        Args:
            failed_items: List of failed items to retry
        """
        retry_batch = failed_items.copy()
        
        for item in retry_batch:
            try:
                self._process_item(item)
            except Exception as e:
                LOGGER.error(f"Failed to retry item: {str(e)}")
                # Add to batch for next retry
                self._add_to_retry_queue(item)
                
    def _add_to_retry_queue(self, item: Dict[str, Any]) -> None:
        """Add an item to the retry queue.
        
        Args:
            item: Item to add to retry queue
        """
        try:
            self.redis_client.lpush('retry_queue', json.dumps(item))
        except Exception as e:
            LOGGER.error(f"Failed to add item to retry queue: {str(e)}")
            
    def get_stats(self) -> Dict[str, Any]:
        """Get current processing statistics.
        
        Returns:
            Dictionary containing processing statistics
        """
        return {
            **self.processing_stats,
            'uptime': (timezone.now() - datetime.fromisoformat(self.processing_stats['start_time'])).total_seconds()
        } 