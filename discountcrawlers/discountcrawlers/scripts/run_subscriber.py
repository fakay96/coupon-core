"""Script to run the discount crawlers Redis subscriber."""

import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'discountcrawlers.config.settings')

import django
django.setup()

from django.conf import settings
from redis import Redis
from discountcrawlers.services.redis import RedisSubscriber

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('subscriber.log')
        ]
    )

def main():
    """Main entry point for the Redis subscriber."""
    # Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize Redis client
        redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD
        )
        
        # Initialize and start Redis subscriber
        subscriber = RedisSubscriber(redis_client)
        logger.info("Starting Redis subscriber...")
        subscriber.start()
        
    except Exception as e:
        logger.error(f"Error starting subscriber: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 