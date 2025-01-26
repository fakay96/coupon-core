"""
Custom permission classes for the election system.

This module includes permissions to check if a user has guest access or is authenticated.
"""

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import View
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class IsGuest(BasePermission):
    """
    Custom permission to check if the user has guest access based on the JWT token.

    This permission extracts the token from the Authorization header, validates it,
    and checks if the `is_guest` claim is present and set to True.
    """

    def has_permission(self, request: Request, view: View) -> bool:
        """
        Determine if the request should be permitted based on guest access.

        Args:
            request (Request): The current HTTP request.
            view (View): The view being accessed.

        Returns:
            bool: True if the user is identified as a guest via the token, False otherwise.
        """
        auth = JWTAuthentication()
        try:
            auth_header: str = request.headers.get("Authorization", "")

            if not auth_header.startswith("Bearer "):
                return False

            token: str = auth_header.split(" ")[1]
            validated_token: Any = auth.get_validated_token(token)

            # Check if the user is identified as a guest
            if validated_token.get("is_guest", False):
                return True

        except (InvalidToken, TokenError, IndexError):
            return False

        return False


class IsAuthenticatedOrGuest(BasePermission):
    """
    Custom permission to check if the user is authenticated or has guest access based on the token.
    """

    def has_permission(self, request: Request, view: View) -> bool:
        """
        Determine if the request should be permitted.

        Args:
            request (Request): The current HTTP request.
            view (View): The view being accessed.

        Returns:
            bool: True if the user is authenticated or identified as a guest via the token,
            False otherwise.
        """
        auth = JWTAuthentication()
        try:
            auth_header: str = request.headers.get("Authorization", "")

            if not auth_header.startswith("Bearer "):
                return False

            token: str = auth_header.split(" ")[1]
            validated_token: Any = auth.get_validated_token(token)

            # Allow if the user is authenticated or has guest access
            if validated_token.get("is_guest", False) or request.user.is_authenticated:
                return True

        except (InvalidToken, TokenError, IndexError):
            return False

        return False
