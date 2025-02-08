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

from django.contrib.auth.hashers import make_password
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import CustomUser, UserProfile
from authentication.v1.serializers import RegisterSerializer, UserProfileSerializer

# drf-yasg imports for OpenAPI documentation
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

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
                {"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
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
                {"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
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
                if request.user.is_guest:
                    # Fetch the password and confirm password.
                    password = request.data.get("password")
                    confirm_password = request.data.get("confirm_password")

                    # Validate the password inputs.
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

            # Validate input.
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
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
