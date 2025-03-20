"""
Views for managing user profiles and user registration.

This module provides the following endpoints:
1. User Profile Management:
    - GET /api/v1/user-profile/: Retrieve the authenticated user's profile details.
    - PUT /api/v1/user-profile/: Update the authenticated user's profile details.

2. User Registration:
    - POST /api/v1/register/: Register a new user or upgrade a guest user to a regular user.

Error Handling:
    - Handles missing profiles with 404 responses.
    - Handles validation errors with 400 responses.
    - Catches unexpected exceptions with 500 responses.

Author: Your Name
Date: YYYY-MM-DD
"""

from typing import Any
import logging

from django.contrib.auth.hashers import make_password
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.core.validators import validate_email

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from authentication.models import CustomUser, UserProfile, ProfileVerification
from authentication.v1.serializers import RegisterSerializer, UserProfileSerializer

# Configure a logger for this module.
logger = logging.getLogger(__name__)

# Define common response schema for error responses.
error_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "error": openapi.Schema(
            type=openapi.TYPE_STRING,
            description="Error message",
            example="Profile not found."
        ),
        "details": openapi.Schema(
            type=openapi.TYPE_STRING,
            description="Detailed error message",
            example="Field 'email' is required."
        ),
    }
)


class UserProfileView(APIView):
    """
    API endpoint to manage user profiles.

    Permissions:
        - Requires the user to be authenticated.

    Endpoints:
        - GET /api/v1/user-profile/: Retrieve the authenticated user's profile details.
        - PUT /api/v1/user-profile/: Update the authenticated user's profile details.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve the profile of the authenticated user.",
        responses={
            200: openapi.Response(
                description="Successfully retrieved profile details.",
                schema=UserProfileSerializer()
            ),
            404: openapi.Response(
                description="Profile not found.",
                schema=error_response_schema
            ),
            500: openapi.Response(
                description="Internal server error.",
                schema=error_response_schema
            ),
        },
    )
    def get(self, request: Any) -> Response:
        """
        Retrieve the profile of the authenticated user.

        Returns:
            - 200: Successfully retrieved profile details.
            - 404: Profile not found.
            - 500: Internal server error.
        """
        try:
            profile = request.user.profile  # Assuming a One-to-One relationship exists.
            serializer = UserProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error("Error retrieving user profile: %s", str(e), exc_info=True)
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @swagger_auto_schema(
        operation_description="Update the profile of the authenticated user.",
        request_body=UserProfileSerializer,
        responses={
            200: openapi.Response(
                description="Successfully updated profile details.",
                schema=UserProfileSerializer()
            ),
            400: openapi.Response(
                description="Validation errors.",
                schema=error_response_schema
            ),
            404: openapi.Response(
                description="Profile not found.",
                schema=error_response_schema
            ),
            500: openapi.Response(
                description="Internal server error.",
                schema=error_response_schema
            ),
        },
    )
    def put(self, request: Any) -> Response:
        """
        Update the profile of the authenticated user.

        Args:
            request (Any): The HTTP request containing the updated profile data.

        Returns:
            - 200: Successfully updated profile details.
            - 400: Validation errors.
            - 404: Profile not found.
            - 500: Internal server error.
        """
        try:
            profile = request.user.profile  # Fetch the authenticated user's profile.
            serializer = UserProfileSerializer(profile, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()  # Save the updated profile data.
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error("Error updating user profile: %s", str(e), exc_info=True)
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserRegistrationView(APIView):
    """
    API endpoint for user registration.

    Handles:
    - Registration for logged-in guest users, allowing them to set a password.
    - Registration for new users providing email, password, and confirmation password.

    Permissions:
        - Allows both authenticated (guest) and unauthenticated users.
    """

    permission_classes = [AllowAny]

    # Define a response schema for successful registration.
    register_success_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "message": openapi.Schema(
                type=openapi.TYPE_STRING, example="User registered successfully."
            ),
            "user": openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description="Registered user details."
            ),
        },
    )

    @swagger_auto_schema(
        operation_description="Register a new user or upgrade a guest user to a regular user.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING, format="email", description="User email."
                ),
                "password": openapi.Schema(
                    type=openapi.TYPE_STRING, format="password", description="User password."
                ),
                "confirm_password": openapi.Schema(
                    type=openapi.TYPE_STRING, format="password", description="Password confirmation."
                ),
            },
            required=["email", "password", "confirm_password"],
        ),
        responses={
            201: openapi.Response(
                description="User successfully registered or upgraded.",
                schema=register_success_schema,
            ),
            400: openapi.Response(
                description="Validation errors or missing fields.",
                schema=error_response_schema,
            ),
            500: openapi.Response(
                description="Internal server error.",
                schema=error_response_schema,
            ),
        },
    )
    def post(self, request: Any) -> Response:
        """
        Register a new user or upgrade a guest user to a regular user.

        Args:
            request (Any): The HTTP request object containing user data.

        Returns:
            - 201: User successfully registered or upgraded.
            - 400: Validation errors or missing fields.
            - 500: Internal server error.
        """
        try:
            # Check if the user is authenticated.
            if request.user.is_authenticated:
                # Check if the user is a guest user.
                if getattr(request.user, "is_guest", False):
                    password = request.data.get("password")
                    confirm_password = request.data.get("confirm_password")

                    if not password or not confirm_password:
                        return Response(
                            {"error": "Password and confirm password are required."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    if password != confirm_password:
                        return Response(
                            {"error": "Password and confirm password do not match."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    # Upgrade the guest user to a regular user.
                    request.user.is_guest = False
                    request.user.role = "user"
                    request.user.password = make_password(password)
                    request.user.save()

                    return Response(
                        {"message": "Guest user upgraded to a regular user."},
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    return Response(
                        {"error": "You are already registered."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # For new user registration.
            email = request.data.get("email")
            password = request.data.get("password")
            confirm_password = request.data.get("confirm_password")

            if not email or not password or not confirm_password:
                return Response(
                    {"error": "Email, password, and confirm password are required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if password != confirm_password:
                return Response(
                    {"error": "Password and confirm password do not match."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate email format before proceeding.
            try:
                validate_email(email)
            except ValidationError:
                return Response(
                    {"error": "Invalid email format."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Use the serializer to validate and create the user.
            serializer = RegisterSerializer(
                data={
                    "email": email,
                    "password": password,
                    "username": email.split("@")[0],
                }
            )
            if serializer.is_valid():
                user = serializer.save()
                user.role = "user"
                user.save()
                return Response(
                    {
                        "message": "User registered successfully.",
                        "user": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error("Error in user registration: %s", str(e), exc_info=True)
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserDeleteView(APIView):
    """
    API endpoint to allow users to delete their account.

    Permissions:
        - Requires the user to be authenticated.

    Endpoints:
        - DELETE /api/v1/user-profile/: Delete the authenticated user's account.
    
    Responses:
        - 204: Successfully deleted user account.
        - 403: User is not authorized to perform this action.
        - 500: Internal server error.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Delete the authenticated user's account.",
        responses={
            204: openapi.Response(description="User account successfully deleted."),
            403: openapi.Response(
                description="User is not authorized to delete this account.",
                schema=error_response_schema
            ),
            500: openapi.Response(
                description="Internal server error.",
                schema=error_response_schema
            ),
        },
    )
    def delete(self, request: Any) -> Response:
        """
        Delete the authenticated user's account.

        Returns:
            - 204: Successfully deleted user account.
            - 403: User is not authorized to perform this action.
            - 500: Internal server error.
        """
        try:
            user = request.user  # Get authenticated user
            CustomUser.objects.filter(id=user.id).delete()
            # Return 204 No Content without a response body.
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error("Error deleting user account: %s", str(e), exc_info=True)
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TokenVerificationView(APIView):
    """
    API endpoint to verify user tokens and resend new tokens.
    
    Methods:
        - GET: Verify a user token using email and token parameters.
        - PUT: Resend a new token if expired or forced.
    """
    permission_classes: list[Any] = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Verify a user token",
        operation_description="Verify a token associated with a user's email.",
        manual_parameters=[
            openapi.Parameter("email", openapi.IN_QUERY, description="User's email address", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("token", openapi.IN_QUERY, description="Token to verify", type=openapi.TYPE_STRING, required=True),
        ],
        responses={
            200: openapi.Response("Token verified successfully", examples={"application/json": {"message": "Token verified successfully."}}),
            400: openapi.Response("Token expired or already used", examples={"application/json": {"error": "Token has expired."}}),
            404: openapi.Response("Invalid email or token", examples={"application/json": {"error": "Invalid email or token."}}),
        },
    )
    def get(self, request: Any) -> Response:
        """
        Verify a user token.
        """
        try:
            email: str | None = request.query_params.get("email")
            token: str | None = request.query_params.get("token")
            
            if not email or not token:
                return Response(
                    {"error": "Email and token are required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Fetch the verification instance; get_object_or_404 will raise Http404 if not found.
            verification = get_object_or_404(ProfileVerification, user__email=email, token=token)
            
            if verification.used:
                return Response(
                    {"error": "Token has already been used."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if verification.is_expired():
                return Response(
                    {"error": "Token has expired."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            verification.mark_as_used()
            verification.user.activated_profile = True
            verification.user.save()
            return Response(
                {"message": "Token verified successfully."},
                status=status.HTTP_200_OK
            )
        except Http404:
            return Response(
                {"error": "Invalid email or token."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error("Error verifying token: %s", str(e), exc_info=True)
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_summary="Resend a new token",
        operation_description="Resend a new token if expired or forced.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="User's email address"),
                "force_resend": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Force resend a new token", default=False),
            },
            required=["email"]
        ),
        responses={
            200: openapi.Response("New token sent successfully", examples={"application/json": {"message": "New token sent successfully."}}),
            400: openapi.Response("Invalid email format", examples={"application/json": {"error": "Invalid email format."}}),
            404: openapi.Response("User not found", examples={"application/json": {"error": "User with the given email not found."}}),
        },
    )
    def put(self, request: Any) -> Response:
        """
        Resend a new token if expired or forced.

        Args:
            request (Request): The HTTP request containing the email and optional force_resend flag.

        Returns:
            Response: JSON response indicating success or failure.
        """
        try:
            email = request.data.get("email")
            force_resend = request.data.get("force_resend", False)

            if not email:
                return Response(
                    {"error": "Email is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Convert force_resend to boolean (handles "true"/"false" strings)
            force_resend = str(force_resend).lower() in ["true", "1"]

            # Validate email format
            try:
                validate_email(email)
            except ValidationError:
                return Response(
                    {"error": "Invalid email format."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Fetch verification instance
            verification = get_object_or_404(ProfileVerification, user__email=email)

            # Resend token based on force_resend or expiration status
            if force_resend or (verification.is_expired() and not verification.used):
                verification.resend_new_token(force_resend=force_resend)  # ✅ Pass force_resend
                return Response(
                    {"message": "New token sent successfully."},
                    status=status.HTTP_200_OK
                )

            return Response(
                {"message": "Current token is still valid."},
                status=status.HTTP_200_OK
            )

        except Http404:
            return Response(
                {"error": "User with the given email not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error("Unexpected error in token resend: %s", str(e), exc_info=True)
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )






