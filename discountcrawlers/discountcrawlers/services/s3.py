"""S3 service for handling S3 operations."""

import logging
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.utils import timezone

LOGGER = logging.getLogger(__name__)

class S3Service:
    """S3 service for handling file uploads and downloads."""
    
    def __init__(self):
        """Initialize the S3 service."""
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        
    def upload_file(self, file_path: str, object_name: str) -> str:
        """Upload a file to S3.
        
        Args:
            file_path: Path to the file to upload
            object_name: Name of the object in S3
            
        Returns:
            str: URL of the uploaded file
            
        Raises:
            ClientError: If the upload fails
        """
        try:
            self.client.upload_file(file_path, self.bucket_name, object_name)
            
            # Generate URL
            url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{object_name}"
            
            return url
            
        except ClientError as e:
            LOGGER.error(f"Failed to upload file to S3: {str(e)}")
            raise
            
    def download_file(self, object_name: str, file_path: str) -> None:
        """Download a file from S3.
        
        Args:
            object_name: Name of the object in S3
            file_path: Path to save the file to
            
        Raises:
            ClientError: If the download fails
        """
        try:
            self.client.download_file(self.bucket_name, object_name, file_path)
            
        except ClientError as e:
            LOGGER.error(f"Failed to download file from S3: {str(e)}")
            raise
            
    def delete_file(self, object_name: str) -> None:
        """Delete a file from S3.
        
        Args:
            object_name: Name of the object in S3
            
        Raises:
            ClientError: If the deletion fails
        """
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_name)
            
        except ClientError as e:
            LOGGER.error(f"Failed to delete file from S3: {str(e)}")
            raise
            
    def generate_presigned_url(self, object_name: str, expiration: int = 3600) -> str:
        """Generate a presigned URL for a file.
        
        Args:
            object_name: Name of the object in S3
            expiration: Expiration time in seconds
            
        Returns:
            str: Presigned URL
            
        Raises:
            ClientError: If the URL generation fails
        """
        try:
            response = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_name
                },
                ExpiresIn=expiration
            )
            
            return response
            
        except ClientError as e:
            LOGGER.error(f"Failed to generate presigned URL: {str(e)}")
            raise 