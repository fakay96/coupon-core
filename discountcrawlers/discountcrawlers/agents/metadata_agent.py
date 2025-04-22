"""Metadata agent for processing discount metadata."""

import json
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from redis import Redis

LOGGER = logging.getLogger(__name__)

@dataclass
class DiscountMetadata:
    """Data class for discount metadata."""
    source_url: str
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    original_price: Optional[float] = None
    sale_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    price_per_unit: Optional[float] = None
    size: Optional[str] = None
    stock_info: Optional[str] = None
    validity_dates: Optional[str] = None
    embedding: Optional[List[float]] = None
    timestamp: int = int(time.time())

class MetadataAgent:
    """Agent for processing and storing discount metadata."""
    
    def __init__(self, redis_client: Redis, batch_size: int = 30):
        """Initialize the metadata agent.
        
        Args:
            redis_client: Redis client instance
            batch_size: Number of items to process in each batch
        """
        self.redis = redis_client
        self.batch_size = batch_size
        self.current_batch: List[Dict[str, Any]] = []
        
    def start(self) -> None:
        """Start the metadata agent."""
        LOGGER.info("Starting metadata agent...")
        self._listen_for_messages()
        
    def _listen_for_messages(self) -> None:
        """Listen for messages on the metadata channel."""
        pubsub = self.redis.pubsub()
        pubsub.subscribe('discount_metadata')
        
        LOGGER.info("Listening for messages on 'discount_metadata' channel...")
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    self._process_message(data)
                except json.JSONDecodeError as e:
                    LOGGER.error(f"Failed to decode message: {e}")
                except Exception as e:
                    LOGGER.error(f"Error processing message: {e}")
                    
    def _process_message(self, data: Dict[str, Any]) -> None:
        """Process a single message.
        
        Args:
            data: Message data dictionary
        """
        try:
            # Create metadata object
            metadata = DiscountMetadata(
                source_url=data['source_url'],
                name=data['name'],
                brand=data.get('brand'),
                category=data.get('category'),
                original_price=data.get('original_price'),
                sale_price=data.get('sale_price'),
                discount_percentage=data.get('discount_percentage'),
                price_per_unit=data.get('price_per_unit'),
                size=data.get('size'),
                stock_info=data.get('stock_info'),
                validity_dates=data.get('validity_dates'),
                embedding=data.get('embedding')
            )
            
            # Add to current batch
            self.current_batch.append(asdict(metadata))
            
            # Process batch if size reached
            if len(self.current_batch) >= self.batch_size:
                self._process_batch()
                
        except KeyError as e:
            LOGGER.error(f"Missing required field in message: {e}")
        except Exception as e:
            LOGGER.error(f"Error processing message: {e}")
            
    def _process_batch(self) -> None:
        """Process the current batch of items."""
        if not self.current_batch:
            return
            
        try:
            # Store batch in Redis
            timestamp = int(time.time())
            batch_key = f"metadata:batch:{timestamp}"
            
            # Store each item
            for item in self.current_batch:
                item_key = f"metadata:item:{item['source_url']}"
                self.redis.set(item_key, json.dumps(item))
                
            # Store batch reference
            self.redis.set(batch_key, json.dumps({
                'timestamp': timestamp,
                'items': [item['source_url'] for item in self.current_batch]
            }))
            
            LOGGER.info(f"Processed batch of {len(self.current_batch)} items")
            
        except Exception as e:
            LOGGER.error(f"Failed to process batch: {e}")
            
        finally:
            # Clear current batch
            self.current_batch = [] 