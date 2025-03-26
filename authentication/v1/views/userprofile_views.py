"""
Views for managing user profiles and user registration.

This module provides the following endpoints:
1. User Profile Management:
    - GET /api/v1/user-profile/: Retrieve the authenticated user's profile details.
    - PUT /api/v1/user-profile/: Update the authenticated user's profile details.
    - PATCH /api/v1/user-profile/: Partially update the authenticated user's profile details.
    - DELETE /api/v1/user-profile/image/: Delete the authenticated user's profile image.

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
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
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
        - PATCH /api/v1/user-profile/: Partially update the authenticated user's profile details.
        - DELETE /api/v1/user-profile/image/: Delete the authenticated user's profile image.
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
            profile = request.user.profile
            # Handle nested user data by including it in the request data
            data = request.data.copy()
            if 'first_name' in request.data or 'last_name' in request.data:
                user_data = {}
                if 'first_name' in request.data:
                    user_data['first_name'] = request.data['first_name']
                if 'last_name' in request.data:
                    user_data['last_name'] = request.data['last_name']
                data['user'] = user_data

            serializer = UserProfileSerializer(profile, data=data)
            if serializer.is_valid():
                serializer.save()
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

    @swagger_auto_schema(
        operation_description="Partially update the profile of the authenticated user.",
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
    def patch(self, request: Any) -> Response:
        """
        Partially update the profile of the authenticated user.

        Args:
            request (Any): The HTTP request containing the partial profile data.

        Returns:
            - 200: Successfully updated profile details.
            - 400: Validation errors.
            - 404: Profile not found.
            - 500: Internal server error.
        """
        try:
            profile = request.user.profile
            # Handle nested user data by including it in the request data
            data = request.data.copy()
            if 'first_name' in request.data or 'last_name' in request.data:
                user_data = {}
                if 'first_name' in request.data:
                    user_data['first_name'] = request.data['first_name']
                if 'last_name' in request.data:
                    user_data['last_name'] = request.data['last_name']
                data['user'] = user_data

            # Handle preferences update
            if 'preferences' in data:
                if not isinstance(data['preferences'], dict):
                    return Response(
                        {"error": "Preferences must be a JSON object."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                current_preferences = profile.preferences or {}
                current_preferences.update(data['preferences'])
                data['preferences'] = current_preferences

            serializer = UserProfileSerializer(profile, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
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

    @swagger_auto_schema(
        operation_description="Delete the profile image of the authenticated user.",
        responses={
            204: openapi.Response(
                description="Successfully deleted profile image.",
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
    def delete(self, request: Any) -> Response:
        """
        Delete the profile image of the authenticated user.

        Returns:
            - 204: Successfully deleted profile image.
            - 404: Profile not found.
            - 500: Internal server error.
        """
        try:
            profile = request.user.profile
            if profile.profile_image:
                profile.profile_image.delete()
                profile.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error("Error deleting profile image: %s", str(e), exc_info=True)
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
            request (Any): The HTTP request containing registration data.

        Returns:
            - 201: User successfully registered or upgraded.
            - 400: Validation errors or missing fields.
            - 500: Internal server error.
        """
        try:
            # Validate required fields
            email = request.data.get("email")
            password = request.data.get("password")
            confirm_password = request.data.get("confirm_password")

            if not all([email, password, confirm_password]):
                return Response(
                    {"error": "All fields are required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate email format
            try:
                validate_email(email)
            except ValidationError:
                return Response(
                    {"error": "Invalid email format."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if passwords match
            if password != confirm_password:
                return Response(
                    {"error": "Passwords do not match."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if email is already registered
            if CustomUser.objects.filter(email=email).exists():
                return Response(
                    {"error": "Email is already registered."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create user and profile
            user = CustomUser.objects.create(
                email=email,
                password=make_password(password),
                is_active=True,
            )

            profile = UserProfile.objects.create(user=user)

            # Create verification token
            verification = ProfileVerification.objects.create(
                user=user,
                email=email,
            )
            verification.send_verification_email()

            serializer = RegisterSerializer(user)
            return Response(
                {
                    "message": "User registered successfully.",
                    "user": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error("Error during user registration: %s", str(e), exc_info=True)
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


class UserProfileBulkView(APIView):
    """
    API endpoint for bulk operations on user profiles.

    Permissions:
        - Requires the user to be an admin.

    Endpoints:
        - GET /api/v1/user-profiles/bulk/: Retrieve multiple user profiles.
        - PUT /api/v1/user-profiles/bulk/: Update multiple user profiles.
        - DELETE /api/v1/user-profiles/bulk/: Delete multiple user profiles.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    @swagger_auto_schema(
        operation_description="Retrieve multiple user profiles.",
        manual_parameters=[
            openapi.Parameter(
                'user_ids',
                openapi.IN_QUERY,
                description="Comma-separated list of user IDs",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Successfully retrieved profiles.",
                schema=UserProfileSerializer(many=True)
            ),
            400: openapi.Response(
                description="Invalid request parameters.",
                schema=error_response_schema
            ),
            404: openapi.Response(
                description="One or more profiles not found.",
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
        Retrieve multiple user profiles.

        Args:
            request (Any): The HTTP request containing user IDs.

        Returns:
            - 200: Successfully retrieved profiles.
            - 400: Invalid request parameters.
            - 404: One or more profiles not found.
            - 500: Internal server error.
        """
        try:
            user_ids = request.query_params.get('user_ids', '').split(',')
            if not user_ids or not all(user_ids):
                return Response(
                    {"error": "user_ids parameter is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            profiles = UserProfile.objects.filter(user_id__in=user_ids)
            if not profiles.exists():
                return Response(
                    {"error": "No profiles found for the provided user IDs."},
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = UserProfileSerializer(profiles, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Error retrieving user profiles: %s", str(e), exc_info=True)
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @swagger_auto_schema(
        operation_description="Update multiple user profiles.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'profiles': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'data': UserProfileSerializer,
                        },
                    ),
                ),
            },
            required=['profiles'],
        ),
        responses={
            200: openapi.Response(
                description="Successfully updated profiles.",
                schema=UserProfileSerializer(many=True)
            ),
            400: openapi.Response(
                description="Invalid request data.",
                schema=error_response_schema
            ),
            404: openapi.Response(
                description="One or more profiles not found.",
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
        Update multiple user profiles.

        Args:
            request (Any): The HTTP request containing profile updates.

        Returns:
            - 200: Successfully updated profiles.
            - 400: Invalid request data.
            - 404: One or more profiles not found.
            - 500: Internal server error.
        """
        try:
            profiles_data = request.data.get('profiles', [])
            if not profiles_data:
                return Response(
                    {"error": "No profile updates provided."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            updated_profiles = []
            errors = []

            for profile_update in profiles_data:
                try:
                    user_id = profile_update.get('user_id')
                    data = profile_update.get('data', {})

                    if not user_id:
                        errors.append({"error": "user_id is required.", "data": profile_update})
                        continue

                    try:
                        profile = UserProfile.objects.get(user_id=user_id)
                    except UserProfile.DoesNotExist:
                        errors.append({"error": f"Profile not found for user_id {user_id}."})
                        continue

                    serializer = UserProfileSerializer(profile, data=data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        updated_profiles.append(serializer.data)
                    else:
                        errors.append({
                            "user_id": user_id,
                            "errors": serializer.errors
                        })
                except Exception as e:
                    errors.append({
                        "user_id": profile_update.get('user_id'),
                        "error": str(e)
                    })

            response_data = {
                "updated_profiles": updated_profiles,
            }
            if errors:
                response_data["errors"] = errors

            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Error updating user profiles: %s", str(e), exc_info=True)
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @swagger_auto_schema(
        operation_description="Delete multiple user profiles.",
        manual_parameters=[
            openapi.Parameter(
                'user_ids',
                openapi.IN_QUERY,
                description="Comma-separated list of user IDs",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            204: openapi.Response(
                description="Successfully deleted profiles.",
            ),
            400: openapi.Response(
                description="Invalid request parameters.",
                schema=error_response_schema
            ),
            404: openapi.Response(
                description="One or more profiles not found.",
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
        Delete multiple user profiles.

        Args:
            request (Any): The HTTP request containing user IDs.

        Returns:
            - 204: Successfully deleted profiles.
            - 400: Invalid request parameters.
            - 404: One or more profiles not found.
            - 500: Internal server error.
        """
        try:
            user_ids = request.query_params.get('user_ids', '').split(',')
            if not user_ids or not all(user_ids):
                return Response(
                    {"error": "user_ids parameter is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            profiles = UserProfile.objects.filter(user_id__in=user_ids)
            if not profiles.exists():
                return Response(
                    {"error": "No profiles found for the provided user IDs."},
                    status=status.HTTP_404_NOT_FOUND
                )

            profiles.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error("Error deleting user profiles: %s", str(e), exc_info=True)
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )






