"""Metadata processor for monitoring and processing stored data.

This module provides functionality to listen for and process metadata
from Redis about processed data batches. It can be used to:
- Monitor processing status
- Trigger downstream processing
- Generate statistics
- Clean up old data
"""

from __future__ import annotations
import logging
import json
import time
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta
import threading
from queue import Queue
import redis
from dotenv import load_dotenv
import os

load_dotenv()

LOGGER: logging.Logger = logging.getLogger(__name__)

class MetadataProcessor:
    """Processor for monitoring and handling metadata from Redis."""
    
    def __init__(
        self,
        redis_host: str = os.getenv('REDIS_HOST', 'localhost'),
        redis_port: int = int(os.getenv('REDIS_PORT', 6379)),
        redis_db: int = int(os.getenv('REDIS_DB', 0)),
        redis_password: Optional[str] = os.getenv('REDIS_PASSWORD'),
        key_prefix: str = "processed_data:",
        poll_interval: int = 60,  # seconds
        max_batch_age: int = 7 * 24 * 60 * 60  # 7 days in seconds
    ):
        """Initialize the metadata processor.
        
        Args:
            redis_host: Redis host address
            redis_port: Redis port
            redis_db: Redis database number
            redis_password: Redis password
            key_prefix: Prefix for Redis keys
            poll_interval: How often to check for new data (seconds)
            max_batch_age: Maximum age of batches to process (seconds)
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.key_prefix = key_prefix
        self.poll_interval = poll_interval
        self.max_batch_age = max_batch_age
        self.redis_password = redis_password
        self._stop_event = threading.Event()
        self._processor_thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
    def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get a Redis client instance."""
        try:
            client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password,
                decode_responses=True
            )
            client.ping()
            return client
        except Exception as e:
            LOGGER.error(f"Failed to connect to Redis: {str(e)}")
            return None
            
    def add_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Add a callback function to be called when new metadata is received.
        
        Args:
            callback: Function that takes a metadata dictionary as argument
        """
        self._callbacks.append(callback)
        
    def _process_metadata(self, metadata: Dict[str, Any]) -> None:
        """Process metadata by calling all registered callbacks.
        
        Args:
            metadata: The metadata dictionary to process
        """
        for callback in self._callbacks:
            try:
                callback(metadata)
            except Exception as e:
                LOGGER.error(f"Callback failed: {str(e)}")
                
    def _cleanup_old_data(self, client: redis.Redis) -> None:
        """Clean up old data from Redis.
        
        Args:
            client: Redis client instance
        """
        try:
            # Get all keys
            keys = client.keys(f"{self.key_prefix}*")
            
            # Check each key's TTL
            for key in keys:
                ttl = client.ttl(key)
                if ttl < 0:  # Key has no TTL or doesn't exist
                    client.delete(key)
                    LOGGER.info(f"Deleted expired key: {key}")
                    
        except Exception as e:
            LOGGER.error(f"Failed to clean up old data: {str(e)}")
            
    def _process_new_batches(self, client: redis.Redis) -> None:
        """Process new batches from Redis.
        
        Args:
            client: Redis client instance
        """
        try:
            # Get all keys
            keys = client.keys(f"{self.key_prefix}*")
            
            # Process each key
            for key in keys:
                data = client.get(key)
                if data:
                    metadata = json.loads(data)
                    self._process_metadata(metadata)
                    
        except Exception as e:
            LOGGER.error(f"Failed to process new batches: {str(e)}")
            
    def _processor_loop(self) -> None:
        """Main processing loop."""
        while not self._stop_event.is_set():
            try:
                client = self._get_redis_client()
                if client:
                    self._process_new_batches(client)
                    self._cleanup_old_data(client)
            except Exception as e:
                LOGGER.error(f"Error in processor loop: {str(e)}")
                
            # Wait for next poll
            time.sleep(self.poll_interval)
            
    def start(self) -> None:
        """Start the metadata processor."""
        if self._processor_thread and self._processor_thread.is_alive():
            LOGGER.warning("Processor is already running")
            return
            
        self._stop_event.clear()
        self._processor_thread = threading.Thread(target=self._processor_loop)
        self._processor_thread.daemon = True
        self._processor_thread.start()
        LOGGER.info("Metadata processor started")
        
    def stop(self) -> None:
        """Stop the metadata processor."""
        if not self._processor_thread or not self._processor_thread.is_alive():
            LOGGER.warning("Processor is not running")
            return
            
        self._stop_event.set()
        self._processor_thread.join(timeout=5)
        LOGGER.info("Metadata processor stopped")
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics.
        
        Returns:
            Dictionary containing processing statistics
        """
        try:
            client = self._get_redis_client()
            if not client:
                return {}
                
            keys = client.keys(f"{self.key_prefix}*")
            stats = {
                'total_batches': len(keys),
                'batches_by_source': {},
                'total_items': 0,
                'oldest_batch': None,
                'newest_batch': None
            }
            
            for key in keys:
                data = client.get(key)
                if data:
                    metadata = json.loads(data)
                    source = metadata['metadata']['source']
                    stats['batches_by_source'][source] = stats['batches_by_source'].get(source, 0) + 1
                    stats['total_items'] += metadata['metadata']['items_processed']
                    
                    timestamp = datetime.fromisoformat(metadata['timestamp'])
                    if not stats['oldest_batch'] or timestamp < stats['oldest_batch']:
                        stats['oldest_batch'] = timestamp
                    if not stats['newest_batch'] or timestamp > stats['newest_batch']:
                        stats['newest_batch'] = timestamp
                        
            return stats
            
        except Exception as e:
            LOGGER.error(f"Failed to get statistics: {str(e)}")
            return {} 