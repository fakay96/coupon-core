"""Storage utilities for uploading data to S3.

This module provides functions for uploading data to S3
using the S3Service class.
"""

from __future__ import annotations
import logging
import json
from pathlib import Path
from typing import Optional, Any
from scrapy import Spider
from dotenv import load_dotenv
from twisted.internet import defer
from discountcrawlers.services.s3 import S3Service
from discountcrawlers.config.settings import (
    AWS_S3_ENDPOINT_URL,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_STORAGE_BUCKET_NAME
)

load_dotenv()
LOGGER = logging.getLogger(__name__)

class StorageService:
    """Handles file uploads to S3."""
    
    def __init__(self, spider: Optional[Spider] = None) -> None:
        """Initialize the storage service with S3 client."""
        self.spider = spider
        self.s3_service = S3Service(
            endpoint_url=AWS_S3_ENDPOINT_URL,
            access_key_id=AWS_ACCESS_KEY_ID,
            secret_access_key=AWS_SECRET_ACCESS_KEY,
            bucket_name=AWS_STORAGE_BUCKET_NAME
        )

    async def upload_file(self, file_path: Path, key: str) -> Optional[str]:
        """Upload a file to S3 and return the public URL if successful."""
        try:
            return await self.s3_service.upload_file(
                file_path=str(file_path),
                object_name=key,
                extra_args={
                    'ACL': 'public-read',
                    'CacheControl': 'max-age=86400'
                }
            )
        except Exception as e:
            LOGGER.error(f"Failed to upload {file_path} to S3: {e}")
            return None

    async def upload_json(self, data: Any, key: str) -> Optional[str]:
        """Upload JSON data directly to S3 and return the public URL if successful."""
        try:
            # Create a temporary file to store JSON data
            temp_file = Path(f"/tmp/{key}")
            temp_file.write_text(json.dumps(data))
            
            return await self.s3_service.upload_file(
                file_path=str(temp_file),
                object_name=key,
                extra_args={
                    'ContentType': 'application/json',
                    'ACL': 'public-read',
                    'CacheControl': 'max-age=86400'
                }
            )
        except Exception as e:
            LOGGER.error(f"Failed to upload JSON to S3: {e}")
            return None
        finally:
            # Clean up temporary file
            if temp_file.exists():
                temp_file.unlink()

@defer.inlineCallbacks
def upload_to_spaces(data: str, key: str) -> defer.Deferred:
    """Upload data to S3 using Twisted's deferred pattern.
    
    Args:
        data: The data to upload
        key: The S3 key to store the data under
        
    Returns:
        A deferred that will fire with the URL of the uploaded file
    """
    try:
        storage = StorageService()
        url = yield defer.maybeDeferred(
            storage.upload_json,
            json.loads(data),
            key
        )
        defer.returnValue(url)
    except Exception as e:
        LOGGER.error(f"Failed to upload data to S3: {e}")
        defer.returnValue(None) 