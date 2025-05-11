"""Storage utilities for uploading data to S3 (or any S3-compatible service)."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional, Dict

from dotenv import load_dotenv
from scrapy import Spider
from twisted.internet import defer, threads

from discountcrawlers.config.settings import (
    AWS_ACCESS_KEY_ID,
    AWS_S3_ENDPOINT_URL,
    AWS_SECRET_ACCESS_KEY,
    AWS_STORAGE_BUCKET_NAME,
)
from discountcrawlers.services.s3 import S3Service
from discountcrawlers.utils.redis_utils import RedisUtils

load_dotenv()
LOGGER = logging.getLogger(__name__)


class StorageService:
    """Handles file uploads to S3."""

    def __init__(self, spider: Optional[Spider] = None) -> None:
        self.spider = spider
        self.s3_service = S3Service(
            endpoint_url=AWS_S3_ENDPOINT_URL,
            access_key_id=AWS_ACCESS_KEY_ID,
            secret_access_key=AWS_SECRET_ACCESS_KEY,
            bucket_name=AWS_STORAGE_BUCKET_NAME,
        )
        self.redis_utils = RedisUtils()

    def _store_metadata(self, url: str, key: str, data: Dict[str, Any]) -> None:
        """Store metadata in Redis for processing."""
        metadata = {
            'url': url,
            'key': key,
            'timestamp': int(time.time()),
            'spider': self.spider.name if self.spider else None,
            'type': 'json',
            'item_count': len(data.get('items', [])) if isinstance(data, dict) else 0,
            'request_id': data.get('request_id'),  # For tracking the WebSocketDiscountRequest
            'status': 'pending',  # Initial status before Celery task processes it
            'data': json.dumps(data)  # Store the full data for processing
        }
        self.redis_utils.store_processed_url(url=url, metadata=metadata)
        LOGGER.info(f"Stored metadata in Redis for {url}")

    def upload_file(self, file_path: Path, key: str) -> str:
        """Upload a file to S3 synchronously."""
        try:
            url = self.s3_service.upload_file(
                file_path=str(file_path),
                object_name=key,
                extra_args={
                    "ACL": "public-read",
                    "CacheControl": "max-age=86400",
                },
            )
            
            # Store metadata in Redis
            metadata = {
                'url': url,
                'key': key,
                'timestamp': int(time.time()),
                'spider': self.spider.name if self.spider else None,
                'type': 'file'
            }
            self.redis_utils.store_processed_url(url=url, metadata=metadata)
            
            return url
        except Exception as e:
            LOGGER.error(f"Failed to upload {file_path} to S3: {e}")
            raise

    def upload_json(self, data: Any, key: str) -> str:
        """Upload JSON data to S3 synchronously."""
        temp_file = Path(f"/tmp/{key}")
        try:
            temp_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file.write_text(json.dumps(data), encoding="utf-8")

            url = self.s3_service.upload_file(
                file_path=str(temp_file),
                object_name=key,
                extra_args={
                    "ContentType": "application/json",
                    "ACL": "public-read",
                    "CacheControl": "max-age=86400",
                },
            )
            
            # Store metadata in Redis for Celery task processing
            self._store_metadata(url=url, key=key, data=data)
            
            return url
        except Exception as e:
            LOGGER.error(f"Failed to upload JSON to S3: {e}")
            raise
        finally:
            if temp_file.exists():
                temp_file.unlink()


@defer.inlineCallbacks
def upload_to_spaces(data: str, key: str) -> defer.Deferred:
    """Upload data to S3/DigitalOcean Spaces using Twisted's deferred pattern."""
    try:
        storage = StorageService()
        # Run the upload in a thread to avoid blocking
        url = yield threads.deferToThread(storage.upload_json, json.loads(data), key)
        defer.returnValue(url)
    except Exception as e:
        LOGGER.error(f"Failed to upload data to S3: {e}")
        defer.returnValue(None)
