"""
Views for admin-related functionality in the authentication app.

Includes endpoints for login, registration, and retrieving user metadata.
"""

import logging
from typing import Any, Dict

from django.db import IntegrityError
from rest_framework import status, serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Import serializers and token manager.
from authentication.v1.serializers import LoginSerializer, RegisterSerializer,PasswordResetSerializer
from authentication.v1.utils.token_manager import TokenManager

# drf-yasg imports for OpenAPI documentation
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from authentication.models import CustomUser,PasswordResetRequest

import traceback
from rest_framework.exceptions import ValidationError
import uuid

logger = logging.getLogger(__name__)



class LoginView(APIView):
    """Handles admin login and token generation."""
    
    permission_classes: list[Any] = [AllowAny]

    # Define the response schema for token generation.
    token_response_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "access_token": openapi.Schema(
                type=openapi.TYPE_STRING, description="JWT access token"
            ),
            "refresh_token": openapi.Schema(
                type=openapi.TYPE_STRING, description="JWT refresh token"
            ),
        }
    )

    @swagger_auto_schema(
        operation_description="Handle POST requests for admin login.",
        request_body=LoginSerializer,
        responses={
            200: openapi.Response(
                "Successfully generated tokens.", schema=token_response_schema
            ),
            400: "Bad request due to validation errors.",
            403: "Account not verified.",
            500: "An unexpected error occurred. Please try again later.",
        },
    )
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
            

            if not user.activated_profile:
                return Response(
                    {"error": "Your account is not verified. Please check your email for verification instructions."},
                    status=status.HTTP_403_FORBIDDEN
                )

            tokens: Dict[str, str] = TokenManager.create_admin_tokens(user)
            return Response(tokens, status=status.HTTP_200_OK)

        except ValidationError as ve:
            logger.error(f"Validation error during login: {str(ve)}")
            # DRF ValidationError has a .detail attribute that often holds more granular info.
            return Response({"error": ve.detail}, status=status.HTTP_400_BAD_REQUEST)

        except KeyError as ke:
            logger.error(f"Missing required field: {str(ke)}")
            return Response(
                {"error": f"Missing required field: {str(ke)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            # Capture the complete traceback for debugging.
            logger.error(f"Unexpected error during login: {traceback.format_exc()}")
            return Response(
                {"error": "An unexpected error occurred. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



class RegisterView(APIView):
    """Handles admin registration."""

    permission_classes = [AllowAny]

    # Define the response schema for a successful registration.
    register_response_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "message": openapi.Schema(
                type=openapi.TYPE_STRING, example="User created successfully"
            ),
        }
    )

    # Define the error response schema.
    error_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "error": openapi.Schema(type=openapi.TYPE_STRING),
            "errors": openapi.Schema(type=openapi.TYPE_OBJECT),
        }
    )

    @swagger_auto_schema(
        operation_description="Handle POST requests for admin registration.",
        request_body=RegisterSerializer,
        responses={
            201: openapi.Response(
                "User created successfully.", schema=register_response_schema
            ),
            400: openapi.Response(
                "Validation error or username/email already exists.", schema=error_schema
            ),
            500: "An unexpected error occurred. Please try again later.",
        },
    )
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
                # Compress error messages into a single string per field.
                compressed_errors = {
                    field: ", ".join(messages)
                    for field, messages in serializer.errors.items()
                }
                return Response(
                    {"errors": compressed_errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer.save()
            return Response(
                {"message": "User created successfully"},
                status=status.HTTP_201_CREATED,
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

    # Define the response schema for user metadata.
    user_info_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "id": openapi.Schema(
                type=openapi.TYPE_INTEGER, example=1, description="User ID"
            ),
            "username": openapi.Schema(
                type=openapi.TYPE_STRING, example="admin_user", description="Username"
            ),
            "email": openapi.Schema(
                type=openapi.TYPE_STRING, format="email", example="admin@example.com", description="User email"
            ),
            "role": openapi.Schema(
                type=openapi.TYPE_STRING, example="Admin", description="User role"
            ),
            "is_staff": openapi.Schema(
                type=openapi.TYPE_BOOLEAN, example=True, description="Is the user a staff member?"
            ),
            "is_active": openapi.Schema(
                type=openapi.TYPE_BOOLEAN, example=True, description="Is the user active?"
            ),
            "date_joined": openapi.Schema(
                type=openapi.TYPE_STRING, format="date-time", example="2025-01-01T12:00:00Z", description="Date joined"
            ),
            "last_login": openapi.Schema(
                type=openapi.TYPE_STRING, format="date-time", example="2025-02-01T08:30:00Z", description="Last login time"
            ),
        }
    )

    @swagger_auto_schema(
        operation_description="Retrieve metadata for the authenticated user.",
        responses={
            200: openapi.Response(
                "User metadata retrieved successfully.", schema=user_info_schema
            ),
            403: "Guest accounts are not allowed to access this resource.",
            500: "An unexpected error occurred.",
        },
    )
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

            # Validate that the user is not a guest.
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

            # Prepare the user metadata.
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
class PasswordResetView(APIView):
    """Handles password reset requests via email."""

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Handle POST requests for password reset.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description="User email"),
                'force_resend': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Force a new reset token even if one already exists",
                    default=False
                ),
            },
        ),
        responses={
            200: openapi.Response("Password reset email sent successfully."),
            400: openapi.Response("Validation error", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={'error': openapi.Schema(type=openapi.TYPE_STRING)}
            )),
            500: openapi.Response("Internal server error"),
        },
    )
    def post(self, request) -> Response:
        """
        Handle POST requests for password reset.

        Expects JSON body:
            - email (str): the user's email
            - force_resend (bool, optional)
        """
        serializer = PasswordResetSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {"message": "Password reset email sent."},
                status=status.HTTP_200_OK,
            )
        except serializers.ValidationError as ve:
            # Return the serializer's own error messages as a 400
            return Response({"error": ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error during password reset: {e}", exc_info=True)
            return Response(
                {"error": "An unexpected error occurred. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    
    @swagger_auto_schema(
        operation_description="Reset password using token.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['token', 'email', 'new_password'],
            properties={
                'token': openapi.Schema(type=openapi.TYPE_STRING, description="Reset token from email"),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description="User email"),
                'new_password': openapi.Schema(type=openapi.TYPE_STRING, description="New password"),
            },
        ),
        responses={
            200: openapi.Response("Password reset successful."),
            400: openapi.Response("Validation error", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={'error': openapi.Schema(type=openapi.TYPE_STRING)}
            )),
            404: openapi.Response("Token not found or invalid"),
            410: openapi.Response("Token expired or already used"),
            500: openapi.Response("Internal server error"),
        },
    )
    def put(self, request) -> Response:
        """
        Reset password using token.

        Expects JSON body:
            - token (str): the reset token from the email
            - email (str): the user's email
            - new_password (str): the new password
        """
        # Extract request data
        token = request.data.get('token')
        email = request.data.get('email')
        new_password = request.data.get('new_password')
        
        # Validate required fields
        if not all([token, email, new_password]):
            return Response(
                {"error": "Token, email, and new password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Convert string token to UUID
            token_uuid = uuid.UUID(token)
            
            # Find the reset request
            try:
                reset_request = PasswordResetRequest.objects.get(
                    token=token_uuid,
                    user__email=email
                )
            except PasswordResetRequest.DoesNotExist:
                return Response(
                    {"error": "Invalid token or email."},
                    status=status.HTTP_404_NOT_FOUND
                )
                
            # Check if token is expired
            if reset_request.is_expired():
                return Response(
                    {"error": "Reset token has expired."},
                    status=status.HTTP_410_GONE
                )
                
            # Check if token is already used
            if reset_request.used:
                return Response(
                    {"error": "Reset token has already been used."},
                    status=status.HTTP_410_GONE
                )
                
            # Update user's password
            user = reset_request.user
            user.set_password(new_password)
            user.save()
            
            # Mark token as used
            reset_request.mark_as_used()
            
            # Invalidate all other reset tokens for this user
            PasswordResetRequest.objects.filter(
                user=user, 
                used=False
            ).update(used=True)
            
            return Response(
                {"message": "Password has been reset successfully."},
                status=status.HTTP_200_OK
            )
            
        except ValueError:
            # Invalid UUID format
            return Response(
                {"error": "Invalid token format."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error during password reset: {e}", exc_info=True)
            return Response(
                {"error": "An unexpected error occurred. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )