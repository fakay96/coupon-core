from django.http import JsonResponse, HttpRequest
import logging

# Initialize logger for health check
logger = logging.getLogger(__name__)

def health_check(request: HttpRequest) -> JsonResponse:
    """
    Health check endpoint to verify if the application is ready to serve traffic.
    This endpoint performs a lightweight check to confirm the application is responsive.

    Args:
        request (HttpRequest): The incoming HTTP request object.

    Returns:
        JsonResponse: A JSON response indicating the status of the health check.
    """
    try:
        # Simple health check response
        return JsonResponse({"status": "ok", "message": "Application is healthy"}, status=200)
    except Exception as e:
        # Log the error for debugging purposes
        logger.error("Health check failed", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)