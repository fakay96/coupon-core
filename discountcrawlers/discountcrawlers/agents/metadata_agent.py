"""Metadata agent for processing discount metadata."""

import logging
from typing import Dict, Any, List
from datetime import datetime
from django.utils import timezone

LOGGER: logging.Logger = logging.getLogger(__name__)

class MetadataAgent:
    """Agent for processing and storing discount metadata.
    
    This agent is responsible for collecting and processing metadata
    about discounts, including statistics and performance metrics.
    
    Attributes:
        stats: Dictionary containing processing statistics
        processed_items: List of processed metadata items
    """
    
    def __init__(self) -> None:
        """Initialize the metadata agent."""
        self.stats: Dict[str, int] = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0
        }
        self.processed_items: List[Dict[str, Any]] = []
        
    def start(self) -> None:
        """Start the metadata agent."""
        LOGGER.info("Metadata agent started")
        
    def process_metadata(self, metadata: Dict[str, Any]) -> None:
        """Process a metadata item.
        
        Args:
            metadata: Dictionary containing metadata information
            
        Raises:
            ValueError: If metadata is invalid
        """
        if not isinstance(metadata, dict):
            raise ValueError("Invalid metadata format")
            
        self.stats['total_processed'] += 1
        
        try:
            # Validate required fields
            required_fields = ['source_url', 'name']
            for field in required_fields:
                if field not in metadata:
                    raise ValueError(f"Missing required field: {field}")
                    
            # Add timestamp
            metadata['processed_at'] = timezone.now()
            
            # Store processed item
            self.processed_items.append(metadata)
            self.stats['successful'] += 1
            
        except Exception as e:
            self.stats['failed'] += 1
            LOGGER.error(f"Failed to process metadata: {str(e)}")
            raise
            
    def get_stats(self) -> Dict[str, int]:
        """Get current processing statistics.
        
        Returns:
            Dictionary containing processing statistics
        """
        return self.stats.copy()
        
    def get_recent_items(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently processed items.
        
        Args:
            limit: Maximum number of items to return
            
        Returns:
            List of recently processed metadata items
        """
        return self.processed_items[-limit:] 