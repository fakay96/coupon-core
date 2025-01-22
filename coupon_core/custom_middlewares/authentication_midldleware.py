"""
Custom middleware for token validation.

Handles the validation of tokens for authenticated requests, supports both guest
and regular user tokens, and fetches user metadata as needed.
"""

import logging

import requests
from django.conf import settings
from django.http import JsonResponse
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)


class TokenValidationMiddleware:
    """
    Middleware to validate JWT tokens for incoming requests.

    This middleware checks for the presence of a Bearer token in the Authorization header,
    validates it, and attaches metadata to the request for both guest and regular users.
    """

    def __init__(self, get_response):
        """
        Initialize the middleware.

        Args:
            get_response: The next middleware or view to handle the request.
        """
        self.get_response = get_response
        self.auth_service_url = settings.AUTH_SERVICE_URL

    def __call__(self, request):
        """
        Process the request to validate tokens and attach user metadata.

        Args:
            request: The incoming HTTP request.

        Returns:
            JsonResponse: If validation fails, returns an error response.
            Otherwise, passes the request to the next middleware or view.
        """
        if self._is_public_endpoint(request.path):
            return self.get_response(request)

        token = self._extract_token(request)
        if not token:
            return JsonResponse(
                {"error": "Authentication credentials were not provided."},
                status=401,
            )

        try:
            decoded_token = self._validate_token(token)

            # Check if it's a guest token
            if "is_guest" in decoded_token:
                request.is_guest = True
                request.guest_metadata = decoded_token
            else:
                # It's a regular user token
                user_metadata = self._fetch_user_metadata(token)
                request.user_metadata = user_metadata

        except (InvalidToken, TokenError) as token_error:
            logger.error(f"Token validation failed: {str(token_error)}")
            return JsonResponse(
                {"error": "Invalid or expired token"}, status=401)
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {str(e)}")
            return JsonResponse(
                {"error": "An error occurred during authentication"}, status=500
            )

        return self.get_response(request)

    def _is_public_endpoint(self, path: str) -> bool:
        """
        Check if the request path matches a public endpoint.

        Args:
            path (str): The request path.

        Returns:
            bool: True if the path matches a public endpoint, False otherwise.
        """
        public_endpoints = settings.PUBLIC_ENDPOINTS or ["/public/"]
        return any(path.startswith(endpoint) for endpoint in public_endpoints)

    def _extract_token(self, request) -> str | None:
        """
        Extract the Bearer token from the Authorization header.

        Args:
            request: The HTTP request.

        Returns:
            str | None: The extracted token, or None if not present.
        """
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header.split(" ")[1]
        return None

    def _validate_token(self, token: str) -> dict:
        """
        Validate the JWT token.

        Args:
            token (str): The JWT token.

        Returns:
            dict: The decoded token payload.

        Raises:
            InvalidToken: If the token is invalid.
        """
        return AccessToken(token)

    def _fetch_user_metadata(self, token: str) -> dict:
        """
        Fetch user metadata from the authentication service.

        Args:
            token (str): The JWT token.

        Returns:
            dict: The user metadata.

        Raises:
            ValueError: If the authentication service fails to return metadata.
        """
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{self.auth_service_url}/api/v1/user-info/", headers=headers
        )

        if response.status_code != 200:
            raise ValueError(
                "Failed to fetch user metadata from authentication service."
            )

        return response.json()
