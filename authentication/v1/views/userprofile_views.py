"""
Views for managing user profiles and user registration.

This module provides the following endpoints:
1. User Profile Management:
    - GET /authentication/api/v1/user-profile/: Retrieve the authenticated user's profile details.
    - PUT /authentication/api/v1/user-profile/: Update the authenticated user's profile details.
    - PATCH /authentication/api/v1/user-profile/: Partially update the authenticated user's profile details.
    - DELETE /authentication/api/v1/user-profile/: Delete the authenticated user's profile image.

2. User Registration:
    - POST /authentication/api/v1/register/: Register a new user or upgrade a guest user to a regular user.

Error Handling:
    - Handles missing profiles with 404 responses.
    - Handles validation errors with 400 responses.
    - Catches unexpected exceptions with 500 responses.

Author: Your Name
Date: YYYY-MM-DD
"""

import json
import logging
from typing import Any

from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import Http404

from rest_framework import status
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from authentication.models import CustomUser, UserProfile, ProfileVerification
from authentication.v1.serializers import RegisterSerializer, UserProfileSerializer

logger = logging.getLogger(__name__)

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
    """
    parser_classes = [JSONParser, MultiPartParser]
    permission_classes = [IsAuthenticated]

    def _coerce_nested(self, data: dict) -> dict:
        """
        If preferences or location arrive as JSON-encoded strings (e.g. in multipart),
        decode them back into Python objects.
        """
        out = {}
        for k, v in data.items():
            if k in ("preferences", "location") and isinstance(v, str):
                try:
                    out[k] = json.loads(v)
                except json.JSONDecodeError:
                    out[k] = v
            else:
                out[k] = v
        return out

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
        try:
            profile = request.user.profile
            serializer = UserProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
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
        try:
            profile = request.user.profile
            raw = request.data.copy()
            data = self._coerce_nested(raw)

            # Add client geolocation if provided by middleware
            if getattr(request, "client_latitude", None) is not None and getattr(request, "client_longitude", None) is not None:
                data["location"] = [request.client_longitude, request.client_latitude]

            serializer = UserProfileSerializer(profile, data=data, partial=False)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except UserProfile.DoesNotExist:
            return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
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
        try:
            profile = request.user.profile
            raw = request.data.copy()
            data = self._coerce_nested(raw)

            # Handle nested user fields
            if 'first_name' in data or 'last_name' in data:
                user_data = {}
                if 'first_name' in data: user_data['first_name'] = data.pop('first_name')
                if 'last_name' in data: user_data['last_name'] = data.pop('last_name')
                data['user'] = user_data

            # Merge preferences
            if 'preferences' in data:
                if not isinstance(data['preferences'], dict):
                    return Response({"error": "Preferences must be a JSON object."}, status=status.HTTP_400_BAD_REQUEST)
                current = profile.preferences or {}
                current.update(data['preferences'])
                data['preferences'] = current

            serializer = UserProfileSerializer(profile, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except UserProfile.DoesNotExist:
            return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error patching user profile: %s", str(e), exc_info=True)
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @swagger_auto_schema(
        operation_description="Delete the profile image of the authenticated user.",
        responses={
            204: openapi.Response(description="Successfully deleted profile image."),
            404: openapi.Response(description="Profile not found.", schema=error_response_schema),
            500: openapi.Response(description="Internal server error.", schema=error_response_schema),
        },
    )
    def delete(self, request: Any) -> Response:
        try:
            profile = request.user.profile
            if profile.profile_image:
                profile.profile_image.delete()
                profile.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except UserProfile.DoesNotExist:
            return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
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
    parser_classes = [JSONParser, MultiPartParser]
    permission_classes = [AllowAny]

    register_success_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "message": openapi.Schema(type=openapi.TYPE_STRING, example="User registered successfully."),
            "user": openapi.Schema(type=openapi.TYPE_OBJECT, description="Registered user details."),
        },
    )

    @swagger_auto_schema(
        operation_description="Register a new user or upgrade a guest user to a regular user.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
                "confirm_password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
            },
            required=["email", "password", "confirm_password"],
        ),
        responses={
            201: openapi.Response(description="User successfully registered or upgraded.", schema=register_success_schema),
            400: openapi.Response(description="Validation errors or missing fields.", schema=error_response_schema),
            500: openapi.Response(description="Internal server error.", schema=error_response_schema),
        },
    )
    def post(self, request: Any) -> Response:
        try:
            raw = request.data.copy()
            data = self._coerce_nested(raw) if hasattr(self, '_coerce_nested') else raw

            email = data.get("email")
            password = data.get("password")
            confirm = data.get("confirm_password")

            if not all([email, password, confirm]):
                return Response({"error": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                validate_email(email)
            except ValidationError:
                return Response({"error": "Invalid email format."}, status=status.HTTP_400_BAD_REQUEST)

            if password != confirm:
                return Response({"error": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

            if CustomUser.objects.filter(email=email).exists():
                return Response({"error": "Email is already registered."}, status=status.HTTP_400_BAD_REQUEST)

            user = CustomUser.objects.create(
                email=email,
                password=make_password(password),
                is_active=True,
            )
            UserProfile.objects.create(user=user)

            verification = ProfileVerification.objects.create(user=user, email=email)
            verification.send_verification_email()

            serializer = RegisterSerializer(user)
            return Response(
                {"message": "User registered successfully.", "user": serializer.data},
                status=status.HTTP_201_CREATED
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
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Delete the authenticated user's account.",
        responses={
            204: openapi.Response(description="User account successfully deleted."),
            403: openapi.Response(description="Not authorized.", schema=error_response_schema),
            500: openapi.Response(description="Internal server error.", schema=error_response_schema),
        },
    )
    def delete(self, request: Any) -> Response:
        try:
            CustomUser.objects.filter(id=request.user.id).delete()
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
    """
    parser_classes = [JSONParser, MultiPartParser]
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Verify a user token",
        manual_parameters=[
            openapi.Parameter("email", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("token", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True),
        ],
        responses={
            200: openapi.Response("Token verified successfully."),
            400: openapi.Response("Token expired or used."),
            404: openapi.Response("Invalid email or token."),
        },
    )
    def get(self, request: Any) -> Response:
        try:
            email = request.query_params.get("email")
            token = request.query_params.get("token")
            if not email or not token:
                return Response({"error":"Email and token are required."}, status=status.HTTP_400_BAD_REQUEST)

            verification = ProfileVerification.objects.filter(user__email=email, token=token).first()
            if not verification:
                return Response({"error":"Invalid email or token."}, status=status.HTTP_404_NOT_FOUND)
            if verification.used:
                return Response({"error":"Token has already been used."}, status=status.HTTP_400_BAD_REQUEST)
            if verification.is_expired():
                return Response({"error":"Token has expired."}, status=status.HTTP_400_BAD_REQUEST)

            verification.mark_as_used()
            verification.user.activated_profile = True
            verification.user.save()
            return Response({"message":"Token verified successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error("Error verifying token: %s", str(e), exc_info=True)
            return Response({"error":"An unexpected error occurred.","details":str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Resend a new token",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "force_resend": openapi.Schema(type=openapi.TYPE_BOOLEAN, default=False),
            },
            required=["email"]
        ),
        responses={
            200: openapi.Response("New token sent successfully."),
            400: openapi.Response("Invalid email format."),
            404: openapi.Response("User not found."),
        },
    )
    def put(self, request: Any) -> Response:
        try:
            raw = request.data.copy()
            data = self._coerce_nested(raw) if hasattr(self, '_coerce_nested') else raw

            email = data.get("email")
            force = data.get("force_resend", False)

            if not email:
                return Response({"error":"Email is required."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                validate_email(email)
            except ValidationError:
                return Response({"error":"Invalid email format."}, status=status.HTTP_400_BAD_REQUEST)

            verification = ProfileVerification.objects.filter(user__email=email).first()
            if not verification:
                return Response({"error":"User with the given email not found."}, status=status.HTTP_404_NOT_FOUND)

            if force or (verification.is_expired() and not verification.used):
                verification.resend_new_token(force_resend=force)
                return Response({"message":"New token sent successfully."}, status=status.HTTP_200_OK)

            return Response({"message":"Current token is still valid."}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error("Unexpected error in token resend: %s", str(e), exc_info=True)
            return Response({"error":"An unexpected error occurred.","details":str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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






