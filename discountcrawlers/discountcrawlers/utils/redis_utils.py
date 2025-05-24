"""Redis utilities for asynchronous message processing.

This module provides a RedisUtils class for interacting with Redis as a message broker
for asynchronous processing of discount data as well as URL-level jobs.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis
from dotenv import load_dotenv

load_dotenv()

LOGGER: logging.Logger = logging.getLogger(__name__)


class RedisUtils:

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")

    SEARCH_QUEUE: str = "discount_search_queue"
    RESULTS_QUEUE: str = "discount_results_queue"

    PROCESSED_URLS: str = "processed_urls_set"
    PENDING_URLS: str = "pending_urls_set"
    PROCESSING_URLS: str = "processing_urls_set"
    FAILED_URLS: str = "failed_urls_set"

    PENDING_URL_QUEUE: str = "pending_urls_queue"

    def __init__(self) -> None:
        self.client: Optional[redis.Redis] = self._get_redis_client()

    def _get_redis_client(self) -> Optional[redis.Redis]:
        try:
            client = redis.Redis(
                host=self.REDIS_HOST,
                port=self.REDIS_PORT,
                db=self.REDIS_DB,
                password=self.REDIS_PASSWORD,
                decode_responses=True,
            )
            client.ping()
            return client
        except Exception as exc:
            LOGGER.error("Failed to initialise Redis client: %s", exc)
            return None

    def queue_search_request(
        self,
        search_terms: List[str],
        categories: List[str],
        price_range: Dict[str, Optional[float]],
        filters: List[str],
        request_id: str,
    ) -> bool:
        if not self.client:
            return False
        try:
            payload = {
                "request_id": request_id,
                "search_terms": search_terms,
                "categories": categories,
                "price_range": price_range,
                "filters": filters,
                "timestamp": datetime.now().isoformat(),
            }
            self.client.lpush(self.SEARCH_QUEUE, json.dumps(payload))
            LOGGER.info("Queued search request %s", request_id)
            return True
        except Exception as exc:
            LOGGER.error("Failed to queue search request: %s", exc)
            return False

    def get_search_result(self, request_id: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None
        try:
            start = time.monotonic()
            while time.monotonic() - start < timeout:
                for item in self.client.lrange(self.RESULTS_QUEUE, 0, -1):
                    data: Dict[str, Any] = json.loads(item)
                    if data.get("request_id") == request_id:
                        self.client.lrem(self.RESULTS_QUEUE, 1, item)
                        return data
                time.sleep(0.5)
            return None
        except Exception as exc:
            LOGGER.error("Failed to fetch search result: %s", exc)
            return None

    def store_search_result(self, request_id: str, results: Dict[str, Any]) -> bool:
        if not self.client:
            return False
        try:
            envelope = {
                "request_id": request_id,
                "results": results,
                "timestamp": datetime.now().isoformat(),
            }
            self.client.lpush(self.RESULTS_QUEUE, json.dumps(envelope))
            LOGGER.info("Stored search results for %s", request_id)
            return True
        except Exception as exc:
            LOGGER.error("Failed to store search results: %s", exc)
            return False

    def store_processed_url(self, url: str, metadata: Dict[str, Any]) -> bool:
        if not self.client:
            return False
        try:
            metadata = {**metadata, "status": "pending"}
            self.client.setex(f"processed_url:{url}", 86_400, json.dumps(metadata))
            self.client.sadd(self.PENDING_URLS, url)
            queue_item = {
                "url": url,
                "metadata": metadata,
                "queued_at": datetime.now().isoformat(),
            }
            self.client.lpush(self.PENDING_URL_QUEUE, json.dumps(queue_item))
            LOGGER.info("Stored & queued URL for processing: %s", url)
            return True
        except Exception as exc:
            LOGGER.error("Failed to store & queue URL: %s", exc)
            return False

    def dequeue_pending_url(self) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None
        try:
            item = self.client.rpop(self.PENDING_URL_QUEUE)
            return json.loads(item) if item else None
        except Exception as exc:
            LOGGER.error("Failed to dequeue pending URL: %s", exc)
            return None

    def get_pending_urls(self) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        try:
            pending: List[Dict[str, Any]] = []
            for url in self.client.smembers(self.PENDING_URLS):
                raw = self.client.get(f"processed_url:{url}")
                if raw:
                    meta = json.loads(raw)
                    if meta.get("status") == "pending":
                        pending.append({"url": url, "metadata": meta})
            return pending
        except Exception as exc:
            LOGGER.error("Failed to list pending URLs: %s", exc)
            return []

    def update_url_status(self, url: str, status: str) -> bool:
        if not self.client:
            return False
        try:
            raw = self.client.get(f"processed_url:{url}")
            if not raw:
                return False
            meta: Dict[str, Any] = json.loads(raw)
            meta["status"] = status
            self.client.setex(f"processed_url:{url}", 86_400, json.dumps(meta))
            self.client.srem(self.PENDING_URLS, url)
            self.client.srem(self.PROCESSING_URLS, url)
            self.client.srem(self.FAILED_URLS, url)
            if status == "pending":
                self.client.sadd(self.PENDING_URLS, url)
            elif status == "processing":
                self.client.sadd(self.PROCESSING_URLS, url)
            elif status == "failed":
                self.client.sadd(self.FAILED_URLS, url)
            LOGGER.info("Updated URL %s → %s", url, status)
            return True
        except Exception as exc:
            LOGGER.error("Failed to update URL status: %s", exc)
            return False

    def get_url_status(self, url: str) -> Optional[str]:
        try:
            raw = self.client.get(f"processed_url:{url}")
            return json.loads(raw).get("status") if raw else None
        except Exception as exc:
            LOGGER.error("Failed to get URL status: %s", exc)
            return None

    def is_url_processed(self, url: str) -> bool:
        try:
            return bool(self.client.exists(f"processed_url:{url}"))
        except Exception as exc:
            LOGGER.error("Failed to check URL existence: %s", exc)
            return False

    def get_url_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            raw = self.client.get(f"processed_url:{url}")
            return json.loads(raw) if raw else None
        except Exception as exc:
            LOGGER.error("Failed to get URL metadata: %s", exc)
            return None

    def store_batch(self, batch_id: str, items: List[Dict[str, Any]]) -> bool:
        if not self.client:
            return False
        try:
            self.client.setex(f"batch:{batch_id}", 86_400, json.dumps(items))
            return True
        except Exception as exc:
            LOGGER.error("Failed to store batch: %s", exc)
            return False

    def get_batch(self, batch_id: str) -> Optional[List[Dict[str, Any]]]:
        if not self.client:
            return None
        try:
            raw = self.client.get(f"batch:{batch_id}")
            return json.loads(raw) if raw else None
        except Exception as exc:
            LOGGER.error("Failed to fetch batch: %s", exc)
            return None
