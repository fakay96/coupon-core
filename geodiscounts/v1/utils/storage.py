## coupon_core/utils/storage.py
"""Storage utilities for downloading data from S3 (or any S3-compatible service)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from scrapy import Spider

from coupon_core.settings import (
    AWS_ACCESS_KEY_ID,
    AWS_S3_ENDPOINT_URL,
    AWS_SECRET_ACCESS_KEY,
    AWS_STORAGE_BUCKET_NAME,
)
from coupon_core.utils.s3 import S3Service

load_dotenv()
LOGGER = logging.getLogger(__name__)


class StorageService:
    """Handles file downloads from S3 synchronously."""

    def __init__(self, spider: Optional[Spider] = None) -> None:
        self.spider = spider
        self.s3_service = S3Service(
            endpoint_url=AWS_S3_ENDPOINT_URL,
            access_key_id=AWS_ACCESS_KEY_ID,
            secret_access_key=AWS_SECRET_ACCESS_KEY,
            bucket_name=AWS_STORAGE_BUCKET_NAME,
        )

    def fetch_file(self, key: str, download_path: Path) -> bool:
        """
        Download a file from the S3 bucket and save it locally.

        Args:
            key (str): The key of the file in the S3 bucket.
            download_path (Path): The local path to save the downloaded file.

        Returns:
            bool: True if download succeeded, False otherwise.
        """
        try:
            # Perform a blocking download
            self.s3_service.download_file(
                object_name=key,
                file_path=str(download_path),
            )
            LOGGER.info(f"Successfully downloaded {key} to {download_path}")
            return True
        except Exception as e:
            LOGGER.error(f"Failed to fetch {key} from S3: {e}")
            return False