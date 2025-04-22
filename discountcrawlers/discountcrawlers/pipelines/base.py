"""Base pipeline classes for all discount crawlers."""

from typing import Dict, Any, Optional, List
import logging
from scrapy import signals
from scrapy.exceptions import DropItem
from itemadapter import ItemAdapter

LOGGER = logging.getLogger(__name__)

class BasePipeline:
    """Base pipeline class for all discount crawlers.
    
    This class provides common functionality and configuration for all discount pipelines.
    """
    
    def __init__(self, crawler):
        """Initialize the pipeline.
        
        Args:
            crawler: The crawler instance
        """
        self.crawler = crawler
        self.settings = crawler.settings
        
    @classmethod
    def from_crawler(cls, crawler):
        """Create a pipeline instance from a crawler.
        
        Args:
            crawler: The crawler instance
            
        Returns:
            BasePipeline: Pipeline instance
        """
        pipeline = cls(crawler)
        crawler.signals.connect(pipeline.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(pipeline.spider_closed, signal=signals.spider_closed)
        return pipeline
        
    def process_item(self, item: Dict[str, Any], spider) -> Optional[Dict[str, Any]]:
        """Process a discount item.
        
        Args:
            item: The item to process
            spider: The spider that yielded the item
            
        Returns:
            Optional[Dict[str, Any]]: The processed item or None if the item should be dropped
            
        Raises:
            DropItem: If the item should be dropped
        """
        try:
            # Convert to dictionary if not already
            adapter = ItemAdapter(item)
            item_dict = dict(adapter)
            
            # Process the item
            processed_item = self._process_item(item_dict, spider)
            if processed_item is None:
                raise DropItem("Item processing failed")
                
            return processed_item
            
        except Exception as e:
            LOGGER.error(f"Error processing item: {str(e)}")
            raise DropItem(f"Error processing item: {str(e)}")
            
    def _process_item(self, item: Dict[str, Any], spider) -> Optional[Dict[str, Any]]:
        """Process a discount item.
        
        This method should be overridden by subclasses to implement specific processing logic.
        
        Args:
            item: The item to process
            spider: The spider that yielded the item
            
        Returns:
            Optional[Dict[str, Any]]: The processed item or None if processing failed
        """
        raise NotImplementedError("Subclasses must implement _process_item method")
        
    def spider_opened(self, spider):
        """Handle spider opened signal.
        
        Args:
            spider: The spider instance that was opened
        """
        LOGGER.info(f"Spider {spider.name} opened")
        
    def spider_closed(self, spider):
        """Handle spider closed signal.
        
        Args:
            spider: The spider instance that was closed
        """
        LOGGER.info(f"Spider {spider.name} closed")

class BatchProcessingPipeline(BasePipeline):
    """Base class for pipelines that process items in batches."""
    
    def __init__(self, crawler, batch_size: int = 30):
        """Initialize the pipeline.
        
        Args:
            crawler: The crawler instance
            batch_size: Number of items to process in each batch
        """
        super().__init__(crawler)
        self.items: List[Dict[str, Any]] = []
        self.batch_size = batch_size
        
    def process_item(self, item: Dict[str, Any], spider) -> Dict[str, Any]:
        """Process an item by adding it to the current batch.
        
        Args:
            item: The item to process
            spider: The spider that scraped the item
            
        Returns:
            The processed item
        """
        # Convert item to dictionary
        adapter = ItemAdapter(item)
        item_dict = dict(adapter)
        
        # Add to batch
        self.items.append(item_dict)
        
        # Process batch if size reached
        if len(self.items) >= self.batch_size:
            try:
                self._process_batch(self.items, spider)
                self.items = []  # Clear processed items
            except Exception as e:
                LOGGER.error(f"Failed to process batch: {e}")
                
        return item
        
    def _process_batch(self, items: List[Dict[str, Any]], spider) -> None:
        """Process a batch of items.
        
        This method should be overridden by subclasses to implement specific batch processing logic.
        
        Args:
            items: List of items to process
            spider: The spider that scraped the items
        """
        raise NotImplementedError("Subclasses must implement _process_batch method")
        
    def close_spider(self, spider):
        """Process any remaining items when the spider closes.
        
        Args:
            spider: The spider that is closing
        """
        if self.items:
            try:
                self._process_batch(self.items, spider)
            except Exception as e:
                LOGGER.error(f"Failed to process final batch: {e}") 