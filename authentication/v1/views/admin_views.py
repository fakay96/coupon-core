"""
Views for admin-related functionality in the authentication app.

Includes endpoints for login, registration, and retrieving user metadata.
"""

import logging
from typing import Any, Dict

from django.db import IntegrityError
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.v1.serializers import LoginSerializer, RegisterSerializer
from authentication.v1.utils.token_manager import TokenManager

logger = logging.getLogger(__name__)


class LoginView(APIView):
    """Handles admin login and token generation."""

    permission_classes: list[Any] = [AllowAny]

    def post(self, request: Any) -> Response:
        """
        Handle POST requests for admin login.

        Args:
            request (Any): The HTTP request containing login data.

        Returns:
            Response: A DRF Response with tokens or error messages.
        """
        try:
            serializer: LoginSerializer = LoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user = serializer.validated_data["user"]
            tokens: Dict[str, str] = TokenManager.create_admin_tokens(user)

            return Response(tokens, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}")
            return Response(
                {"error": "An unexpected error occurred. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RegisterView(APIView):
    """Handles admin registration."""

    permission_classes = [AllowAny]

    def post(self, request: Any) -> Response:
        """
        Handle POST requests for admin registration.

        Args:
            request (Any): The HTTP request containing registration data.

        Returns:
            Response: A DRF Response with success or error messages.
        """
        try:
            serializer = RegisterSerializer(data=request.data)
            if not serializer.is_valid():
                compressed_errors = {
                    field: ", ".join(messages)
                    for field, messages in serializer.errors.items()
                }
                return Response(
                    {"errors": compressed_errors}, status=status.HTTP_400_BAD_REQUEST
                )

            serializer.save()
            return Response(
                {"message": "User created successfully"}, status=status.HTTP_201_CREATED
            )

        except IntegrityError as e:
            logger.warning(f"Integrity error during registration: {str(e)}")
            return Response(
                {"error": "Username or email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.error(f"Unexpected error during registration: {str(e)}")
            return Response(
                {"error": "An unexpected error occurred. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserInfoView(APIView):
    """
    Returns user metadata for authenticated requests.

    Guest accounts are not allowed to access this endpoint.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Any) -> Response:
        """
        Handle GET requests to retrieve user metadata.

        Args:
            request (Any): The HTTP request.

        Returns:
            Response: A DRF Response containing user metadata or an error message.
        """
        try:
            user = request.user

            # Validate that the user is not a guest
            if getattr(user, "is_guest", False):
                logger.warning(
                    f"Guest token access attempt by user: {user.id if user.id else 'unknown'}"
                )
                return Response(
                    {
                        "error": "Guest accounts are not allowed to access this resource."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Prepare the user metadata
            user_metadata = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": (
                    user.role.name if hasattr(user, "role") and user.role else "Guest"
                ),
                "is_staff": user.is_staff,
                "is_active": user.is_active,
                "date_joined": user.date_joined,
                "last_login": user.last_login,
            }

            logger.info(f"User metadata retrieved for user ID: {user.id}")
            return Response(user_metadata, status=status.HTTP_200_OK)

        except AttributeError as ae:
            logger.error(f"AttributeError in UserInfoView: {str(ae)}")
            return Response(
                {"error": "User object is missing required attributes."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        except Exception as e:
            logger.error(f"Unexpected error in UserInfoView: {str(e)}")
            return Response(
                {"error": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
