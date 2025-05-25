from urllib.parse import urlparse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import logging
from geodiscounts.v1.tasks import import_discounts_task
from drf_yasg.utils import swagger_auto_schema


logger = logging.getLogger(__name__)


class CustomAPIKeyPermission(BasePermission):
    """
    Custom permission class to validate API key from X-API-KEY header.
    """
    def has_permission(self, request, view):
        api_key = request.headers.get('X-API-KEY')
        expected_key = getattr(settings, 'EXTERNAL_API_KEY', None)
        
        if not expected_key:
            logger.error("EXTERNAL_API_KEY not configured in settings")
            return False
            
        return api_key and api_key == expected_key


@method_decorator(csrf_exempt, name='dispatch')
class ImportDiscountsAPIView(APIView):
    """
    API endpoint to trigger discount import for a given DigitalOcean Spaces URL.
    
    Authentication: Custom header X-API-KEY must match settings.EXTERNAL_API_KEY.
    
    Expected payload:
    {
        "file_url": "https://your-space.region.digitaloceanspaces.com/path/to/file.json"
    }
    """
    permission_classes = [CustomAPIKeyPermission]
    @swagger_auto_schema(exclude=True)
    def post(self, request):
        """
        Schedule a discount import task from a DigitalOcean Spaces JSON file.
        
        Returns:
            202: Import task scheduled successfully
            400: Invalid request data or file URL format
            401: Invalid or missing API key
            500: Internal server error
        """
        try:
            # Extract and validate file_url
            file_url = request.data.get('file_url')
            if not file_url:
                return Response(
                    {'error': 'file_url is required.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate file_url format
            validation_error = self._validate_file_url(file_url)
            if validation_error:
                return Response(
                    {'error': validation_error}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Import and enqueue Celery task
            try:
                task_result = import_discounts_task.delay(file_url)
                
                logger.info(f"Import task scheduled with ID: {task_result.id} for URL: {file_url}")
                
                return Response({
                    'message': 'Import scheduled successfully.',
                    'task_id': task_result.id,
                    'file_url': file_url
                }, status=status.HTTP_202_ACCEPTED)
                
            except ImportError as e:
                logger.error(f"Failed to import Celery task: {e}")
                return Response(
                    {'error': 'Task scheduling service unavailable.'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            except Exception as e:
                logger.error(f"Failed to schedule import task: {e}")
                return Response(
                    {'error': 'Failed to schedule import task.'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Unexpected error in ImportDiscountsAPIView: {e}")
            return Response(
                {'error': 'An unexpected error occurred.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _validate_file_url(self, file_url):
        """
        Validate the format of the provided file URL.
        
        Args:
            file_url (str): The URL to validate
            
        Returns:
            str or None: Error message if validation fails, None if valid
        """
        try:
            parsed_url = urlparse(file_url)
        except Exception:
            return 'Invalid URL format.'
        
        # Check URL scheme
        if parsed_url.scheme not in ('http', 'https'):
            return 'URL must use http or https protocol.'
        
        # Check if it's a DigitalOcean Spaces URL
        if not parsed_url.netloc.endswith('digitaloceanspaces.com'):
            return 'URL must be from DigitalOcean Spaces (*.digitaloceanspaces.com).'
        
        # Check file extension
        if not parsed_url.path.endswith('.json'):
            return 'File must be a JSON file (.json extension required).'
        
        # Check if path is not empty (beyond just the extension)
        if len(parsed_url.path.rstrip('/')) <= 5:  # ".json" is 5 characters
            return 'URL must include a valid file path.'
        
        return None
    
    def get(self, request):
        """
        Return API documentation and status.
        """
        return Response({
            'message': 'Import Discounts API',
            'description': 'POST to this endpoint with a file_url to schedule a discount import task.',
            'required_headers': {
                'X-API-KEY': 'Your API key',
                'Content-Type': 'application/json'
            },
            'required_payload': {
                'file_url': 'https://your-space.region.digitaloceanspaces.com/path/to/file.json'
            },
            'supported_methods': ['GET', 'POST']
        }, status=status.HTTP_200_OK)