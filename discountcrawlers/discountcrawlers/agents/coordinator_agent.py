"""Coordinator agent for managing search requests."""

from __future__ import annotations
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..models import SearchRequest, SearchResponse
from ..utils.redis_utils import get_redis_client

LOGGER: logging.Logger = logging.getLogger(__name__)

class CoordinatorAgent:
    """Agent for coordinating search requests."""
    
    def __init__(self) -> None:
        """Initialize the coordinator agent."""
        self.redis_client = get_redis_client()
        self.active_requests: Dict[str, datetime] = {}
        
    async def start(self) -> None:
        """Start the coordinator agent."""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe('search_requests')
        
        LOGGER.info("Coordinator agent started")
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    request_data = message['data']
                    request = SearchRequest.parse_raw(request_data)
                    await self.process_request(request)
                except Exception as e:
                    LOGGER.error(f"Error processing request: {str(e)}")
                    
    async def process_request(self, request: SearchRequest) -> None:
        """Process a search request.
        
        Args:
            request: Search request to process
        """
        try:
            # Track active request
            self.active_requests[request.id] = datetime.now()
            
            # Forward request to search agent
            self.redis_client.publish(
                'search_requests',
                request.json()
            )
            
            # Wait for response
            response = await self._wait_for_response(request.id)
            
            # Clean up
            del self.active_requests[request.id]
            
            # Publish response
            self.redis_client.publish(
                f'search_response_{request.id}',
                response.json()
            )
            
        except Exception as e:
            LOGGER.error(f"Error processing request {request.id}: {str(e)}")
            # Send error response
            error_response = SearchResponse(
                request_id=request.id,
                results=[],
                total_results=0,
                processing_time=0.0
            )
            self.redis_client.publish(
                f'search_response_{request.id}',
                error_response.json()
            )
            
    async def _wait_for_response(
        self,
        request_id: str,
        timeout: int = 30
    ) -> SearchResponse:
        """Wait for a search response.
        
        Args:
            request_id: ID of the request to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            SearchResponse: Response from search agent
            
        Raises:
            TimeoutError: If no response is received within timeout
        """
        start_time = time.time()
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(f'search_response_{request_id}')
        
        while time.time() - start_time < timeout:
            message = await pubsub.get_message()
            if message and message['type'] == 'message':
                return SearchResponse.parse_raw(message['data'])
                
        raise TimeoutError(f"No response received for request {request_id}") 