"""Search agent for handling discount searches."""

from __future__ import annotations
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..models import Discount, SearchRequest, SearchResponse
from ..utils.redis_utils import get_redis_client

LOGGER: logging.Logger = logging.getLogger(__name__)

class SearchAgent:
    """Agent for handling search requests."""
    
    def __init__(self) -> None:
        """Initialize the search agent."""
        self.redis_client = get_redis_client()
        self.search_results: Dict[str, List[Discount]] = {}
        
    async def start(self) -> None:
        """Start the search agent."""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe('search_requests')
        
        LOGGER.info("Search agent started")
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    request_data = message['data']
                    request = SearchRequest.parse_raw(request_data)
                    response = await self.process_search(request)
                    self.redis_client.publish(
                        f'search_response_{request.id}',
                        response.json()
                    )
                except Exception as e:
                    LOGGER.error(f"Error processing search request: {str(e)}")
                    
    async def process_search(
        self,
        request: SearchRequest
    ) -> SearchResponse:
        """Process a search request.
        
        Args:
            request: Search request to process
            
        Returns:
            SearchResponse: Response containing search results
        """
        start_time = time.time()
        
        try:
            # TODO: Implement actual search logic
            # For now, return mock results
            results = [
                Discount(
                    id=f"discount_{i}",
                    retailer=f"Retailer {i}",
                    category=request.category or "uncategorized",
                    description=f"Sample discount {i}",
                    discount_value=f"{i}% off",
                    is_active=True
                )
                for i in range(min(request.max_results, 5))
            ]
            
            return SearchResponse(
                request_id=request.id,
                results=results,
                total_results=len(results),
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            LOGGER.error(f"Error processing search: {str(e)}")
            return SearchResponse(
                request_id=request.id,
                results=[],
                total_results=0,
                processing_time=time.time() - start_time
            ) 