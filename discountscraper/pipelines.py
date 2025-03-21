# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface

from itemadapter import ItemAdapter
from datetime import datetime

class DiscountPipeline:
    """Pipeline to clean and standardize discount data"""
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # Clean prices while preserving currency symbol
        price_fields = ['original_price', 'sale_price', 'price_per_unit']
        for field in price_fields:
            value = adapter.get(field)
            if value and isinstance(value, str):
                try:
                    # Keep the € symbol but ensure proper formatting
                    if '€' not in value:
                        value = f"€{value}"
                    adapter[field] = value
                except (ValueError, TypeError):
                    adapter[field] = None
        
        # Clean discount percentage
        discount = adapter.get('discount_percentage')
        if discount:
            try:
                # Store as integer
                adapter['discount_percentage'] = int(str(discount))
            except (ValueError, TypeError):
                adapter['discount_percentage'] = None
        
        # Add timestamp
        adapter['timestamp'] = datetime.now().isoformat()
        
        return item
