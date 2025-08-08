"""S3 service for uploads, downloads, and presigned URLs to AWS or any
S3-compatible storage (DigitalOcean Spaces, MinIO, Wasabi, …)."""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError
from django.conf import settings

LOGGER = logging.getLogger(__name__)


def _infer_region_from_endpoint(endpoint_url: str | None) -> str | None:
    if not endpoint_url:
        return None
    host = urlparse(endpoint_url).netloc
    parts = host.split(".")
    if host.endswith("digitaloceanspaces.com"):
        return parts[0]
    if host.endswith("amazonaws.com"):
        parts = [p for p in parts if p != "dualstack"]
        if len(parts) >= 3 and parts[0] == "s3":
            return parts[1]
    return None


class S3Service:
    def __init__(
        self,
        *,
        endpoint_url: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        region_name: Optional[str] = None,
    ) -> None:
        self.endpoint_url = endpoint_url or getattr(settings, "AWS_S3_ENDPOINT_URL", None)
        self.bucket_name = bucket_name or getattr(settings, "AWS_STORAGE_BUCKET_NAME")
        self.region_name = (
            region_name
            or getattr(settings, "AWS_S3_REGION_NAME", None)
            or _infer_region_from_endpoint(self.endpoint_url)
        )
        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=access_key_id or getattr(settings, "AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=secret_access_key
            or getattr(settings, "AWS_SECRET_ACCESS_KEY"),
            region_name=self.region_name,
        )

    def upload_file(
        self,
        file_path: str,
        object_name: str,
        extra_args: Optional[dict] = None,
    ) -> str:
        try:
            self.client.upload_file(
                Filename=file_path,
                Bucket=self.bucket_name,
                Key=object_name,
                ExtraArgs=extra_args or {},
            )
        except ClientError as exc:
            LOGGER.error("Failed to upload file to S3: %s", exc)
            raise
        if self.endpoint_url:
            return f"{self.endpoint_url.rstrip('/')}/{self.bucket_name}/{object_name}"
        region = self.region_name or "us-east-1"
        return f"https://{self.bucket_name}.s3.{region}.amazonaws.com/{object_name}"

    def download_file(self, object_name: str, file_path: str) -> None:
        try:
            self.client.download_file(self.bucket_name, object_name, file_path)
        except ClientError as exc:
            LOGGER.error("Failed to download file from S3: %s", exc)
            raise

    def delete_file(self, object_name: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_name)
        except ClientError as exc:
            LOGGER.error("Failed to delete file from S3: %s", exc)
            raise

    def generate_presigned_url(
        self, object_name: str, expiration: int = 3600
    ) -> str:
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_name},
                ExpiresIn=expiration,
            )
        except ClientError as exc:
            LOGGER.error("Failed to generate presigned URL: %s", exc)
            raise
