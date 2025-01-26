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

    def get(self, request: Any) -> Response:
        """
        Retrieve the profile of the authenticated user.

        Returns:
            - 200: Successfully retrieved profile details.
            - 404: Profile not found.
            - 500: Internal server error.
        """
        try:
            profile = request.user.profile  # Assuming a One-to-One relationship
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
            profile = request.user.profile  # Fetch the authenticated user's profile
            serializer = UserProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()  # Save the updated profile data
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
            # Check if the user is authenticated
            if request.user.is_authenticated:
                # Check if the user is a guest user
                if request.user.is_guest:
                    # Fetch the password and confirm password
                    password = request.data.get("password")
                    confirm_password = request.data.get("confirm_password")

                    # Validate the password inputs
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

                    # Upgrade the guest user to a regular user
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

            # For new user registration
            email = request.data.get("email")
            password = request.data.get("password")
            confirm_password = request.data.get("confirm_password")

            # Validate input
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

            # Use the serializer to validate and create the user
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
