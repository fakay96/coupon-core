"""Script to run the discount crawlers service."""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from redis import Redis

# Load environment variables
load_dotenv()

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('crawler.log')
        ]
    )

def main():
    """Main entry point for the discount crawlers service."""
    # Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize Redis client
        redis_client = Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            password=os.getenv('REDIS_PASSWORD')
        )
        
        # Initialize and start metadata agent
        from discountcrawlers.agents.metadata_agent import MetadataAgent
        metadata_agent = MetadataAgent(redis_client)
        logger.info("Starting metadata agent...")
        metadata_agent.start()
        
    except Exception as e:
        logger.error(f"Error starting service: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 