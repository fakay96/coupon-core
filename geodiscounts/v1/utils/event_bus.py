"""Event bus for inter-service communication."""

import json
import logging
from typing import Dict, Any, Callable, List
from redis import Redis
from django.conf import settings

logger = logging.getLogger(__name__)

class EventBus:
    """
    Event bus for handling inter-service communication.
    
    This class provides methods for publishing events to topics and subscribing
    to topics for event handling. It uses Redis as the underlying message broker.
    
    Attributes:
        redis_client: Redis client for pub/sub operations
        subscribers: Dictionary mapping topics to their subscriber callbacks
    """
    
    def __init__(self):
        """Initialize the event bus with Redis connection."""
        self.redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        self.subscribers: Dict[str, List[Callable]] = {}
        
    def publish(self, topic: str, event: Dict[str, Any]) -> None:
        """
        Publish an event to a topic.
        
        Args:
            topic: The topic to publish to
            event: The event data to publish
        """
        try:
            self.redis_client.publish(
                topic,
                json.dumps(event)
            )
            logger.info(f"Published event to topic {topic}")
        except Exception as e:
            logger.error(f"Error publishing event to topic {topic}: {str(e)}")
            raise
            
    def subscribe(self, topic: str, callback: Callable) -> None:
        """
        Subscribe to a topic with a callback function.
        
        Args:
            topic: The topic to subscribe to
            callback: Function to call when an event is received
        """
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)
        
        # Start listening for messages in a separate thread
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(topic)
        
        def message_handler():
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        event = json.loads(message['data'])
                        for callback in self.subscribers[topic]:
                            callback(event)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in message: {message['data']}")
                    except Exception as e:
                        logger.error(f"Error handling message: {str(e)}")
                        
        import threading
        thread = threading.Thread(target=message_handler, daemon=True)
        thread.start()
        
    def unsubscribe(self, topic: str, callback: Callable) -> None:
        """
        Unsubscribe a callback from a topic.
        
        Args:
            topic: The topic to unsubscribe from
            callback: The callback function to remove
        """
        if topic in self.subscribers:
            self.subscribers[topic].remove(callback)
            if not self.subscribers[topic]:
                del self.subscribers[topic] 