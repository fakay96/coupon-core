"""
This module provides endpoints for social authentication using Google, Apple, and Twitter OAuth2 protocols.
It also includes an endpoint for listing available social authentication providers.

Endpoints:
    - GoogleLogin: Handles authentication via Google OAuth2.
    - AppleLogin: Handles authentication via Apple Sign In.
    - TwitterLogin: Handles authentication via Twitter OAuth2.
    - SocialAuthProviders: Returns a list of available social authentication providers.

Error Handling:
    All endpoints catch exceptions during processing and return a JSON response containing an error message.
    This ensures that unexpected errors are handled gracefully.

Usage:
    Include these views in your URL configuration according to Django Rest Framework conventions.
"""

from typing import Dict, Any

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.apple.views import AppleOAuth2Adapter
from allauth.socialaccount.providers.twitter.views import TwitterOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class GoogleLogin(SocialLoginView):
    """
    API endpoint for Google OAuth2 login.

    This endpoint allows users to authenticate via Google OAuth2.

    Attributes:
        adapter_class (GoogleOAuth2Adapter): Adapter for Google authentication.
        client_class (OAuth2Client): OAuth2 client for handling the authentication flow.

    Methods:
        post(request, *args, **kwargs):
            Processes POST requests for Google OAuth2 authentication.
            Returns an authentication response or an error message if authentication fails.
    """
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client

    @swagger_auto_schema(
        operation_description="Authenticate using Google OAuth2",
        request_body=None,
        manual_parameters=[
            openapi.Parameter(
                "code", openapi.IN_QUERY,
                description="Authorization code from Google",
                type=openapi.TYPE_STRING, required=True
            ),
            openapi.Parameter(
                "redirect_uri", openapi.IN_QUERY,
                description="Redirect URI registered with Google",
                type=openapi.TYPE_STRING, required=True
            ),
        ],
        responses={
            200: "Authentication successful",
            400: "Invalid input or authentication failed"
        },
    )
    def post(self, request, *args, **kwargs):
        """
        Handle Google OAuth2 authentication.

        Args:
            request (Request): The HTTP request containing OAuth2 parameters.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: A JSON response with authentication details if successful, or an error message with status 400 if authentication fails.

        Error Handling:
            Catches any exceptions that occur during processing and returns a 400 Bad Request response with an error message.
        """
        try:
            return super().post(request, *args, **kwargs)
        except Exception as e:
            # Log the error as needed.
            return Response(
                {"error": f"Google authentication failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


class AppleLogin(SocialLoginView):
    """
    API endpoint for Apple Sign In.

    This endpoint allows users to authenticate via Apple Sign In.

    Attributes:
        adapter_class (AppleOAuth2Adapter): Adapter for Apple authentication.
        client_class (OAuth2Client): OAuth2 client for handling the authentication flow.

    Methods:
        post(request, *args, **kwargs):
            Processes POST requests for Apple Sign In authentication.
            Returns an authentication response or an error message if authentication fails.
    """
    adapter_class = AppleOAuth2Adapter
    client_class = OAuth2Client

    @swagger_auto_schema(
        operation_description="Authenticate using Apple Sign In",
        request_body=None,
        manual_parameters=[
            openapi.Parameter(
                "code", openapi.IN_QUERY,
                description="Authorization code from Apple",
                type=openapi.TYPE_STRING, required=True
            ),
            openapi.Parameter(
                "id_token", openapi.IN_QUERY,
                description="ID token from Apple",
                type=openapi.TYPE_STRING, required=True
            ),
        ],
        responses={
            200: "Authentication successful",
            400: "Invalid input or authentication failed"
        },
    )
    def post(self, request, *args, **kwargs):
        """
        Handle Apple Sign In authentication.

        Args:
            request (Request): The HTTP request containing OAuth2 parameters.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: A JSON response with authentication details if successful, or an error message with status 400 if authentication fails.

        Error Handling:
            Catches any exceptions that occur during processing and returns a 400 Bad Request response with an error message.
        """
        try:
            return super().post(request, *args, **kwargs)
        except Exception as e:
            # Log the error as needed.
            return Response(
                {"error": f"Apple authentication failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


class TwitterLogin(SocialLoginView):
    """
    API endpoint for Twitter OAuth2 login.

    This endpoint allows users to authenticate via Twitter OAuth2.

    Attributes:
        adapter_class (TwitterOAuth2Adapter): Adapter for Twitter authentication.
        client_class (OAuth2Client): OAuth2 client for handling the authentication flow.

    Methods:
        post(request, *args, **kwargs):
            Processes POST requests for Twitter OAuth2 authentication.
            Returns an authentication response or an error message if authentication fails.
    """
    adapter_class = TwitterOAuth2Adapter
    client_class = OAuth2Client

    @swagger_auto_schema(
        operation_description="Authenticate using Twitter OAuth2",
        request_body=None,
        manual_parameters=[
            openapi.Parameter(
                "oauth_token", openapi.IN_QUERY,
                description="OAuth token from Twitter",
                type=openapi.TYPE_STRING, required=True
            ),
            openapi.Parameter(
                "oauth_verifier", openapi.IN_QUERY,
                description="OAuth verifier from Twitter",
                type=openapi.TYPE_STRING, required=True
            ),
        ],
        responses={
            200: "Authentication successful",
            400: "Invalid input or authentication failed"
        },
    )
    def post(self, request, *args, **kwargs):
        """
        Handle Twitter OAuth2 authentication.

        Args:
            request (Request): The HTTP request containing OAuth2 parameters.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: A JSON response with authentication details if successful, or an error message with status 400 if authentication fails.

        Error Handling:
            Catches any exceptions that occur during processing and returns a 400 Bad Request response with an error message.
        """
        try:
            return super().post(request, *args, **kwargs)
        except Exception as e:
            # Log the error as needed.
            return Response(
                {"error": f"Twitter authentication failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


class SocialAuthProviders(APIView):
    """
    API endpoint to list available social authentication providers.

    This endpoint returns a JSON response containing the available social authentication providers,
    including their client IDs and redirect URIs.

    Methods:
        get(request, *args, **kwargs):
            Processes GET requests and returns the list of supported authentication providers.
    """

    @swagger_auto_schema(
        operation_description="List available social authentication providers",
        responses={
            200: openapi.Response(
                description="Available social auth providers",
                examples={
                    "application/json": {
                        "google": {"client_id": "YOUR_GOOGLE_CLIENT_ID", "redirect_uri": "YOUR_REDIRECT_URI"},
                        "apple": {"client_id": "YOUR_APPLE_CLIENT_ID", "redirect_uri": "YOUR_REDIRECT_URI"},
                        "twitter": {"client_id": "YOUR_TWITTER_CLIENT_ID", "redirect_uri": "YOUR_REDIRECT_URI"},
                    }
                },
            )
        },
    )
    def get(self, request, *args, **kwargs):
        """
        Retrieve a list of available social authentication providers.

        Args:
            request (Request): The HTTP request.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: A JSON response containing a dictionary of supported social authentication providers with their respective client IDs and redirect URIs.

        Error Handling:
            Catches any exceptions during processing and returns a 500 Internal Server Error response with an error message.
        """
        try:
            providers: Dict[str, Any] = {
                "google": {"client_id": "YOUR_GOOGLE_CLIENT_ID", "redirect_uri": "YOUR_REDIRECT_URI"},
                "apple": {"client_id": "YOUR_APPLE_CLIENT_ID", "redirect_uri": "YOUR_REDIRECT_URI"},
                "twitter": {"client_id": "YOUR_TWITTER_CLIENT_ID", "redirect_uri": "YOUR_REDIRECT_URI"},
            }
            return Response(providers, status=status.HTTP_200_OK)
        except Exception as e:
            # Log the error as needed.
            return Response(
                {"error": f"Failed to retrieve social auth providers: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
