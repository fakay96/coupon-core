"""
Views for handling guest token creation and retrieval.

Provides functionality for users to obtain a guest token by providing their email address.
If a token already exists for the given email, it is returned. Otherwise, a new token is
generated, stored in Redis with a 1-hour expiration, and returned.
"""

import datetime
import logging
from typing import Any, Optional

from django.db import IntegrityError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import CustomUser
from authentication.v1.serializers import GuestTokenSerializer
from authentication.v1.utils.redis_client import RedisClient
from authentication.v1.utils.token_manager import TokenManager

logger = logging.getLogger(__name__)


class GuestTokenView(APIView):
    """
    API view to handle the creation of guest tokens.

    This view allows users to obtain a guest token by providing their email address.
    If a token already exists for the given email, it returns the existing token.
    Otherwise, it generates a new guest token, stores it in Redis with a 1-hour expiration,
    and returns the newly created token.
    """

    permission_classes = [AllowAny]

    def post(self, request: Any) -> Response:
        """
        Handle POST requests to create or retrieve a guest token.

        This method validates the provided email, checks for an existing guest token in Redis,
        and either returns the existing token or generates a new one. The new token is stored
        in Redis with a 1-hour expiration time.

        Args:
            request (Any): The HTTP request object containing the guest token creation data.

        Returns:
            Response: A Django REST Framework Response object containing the guest token
                      or error messages.

        Raises:
            None: All exceptions are handled within the method.
        """
        try:
            # Initialize and validate the serializer with request data
            serializer: GuestTokenSerializer = GuestTokenSerializer(
                data=request.data)
            serializer.is_valid(raise_exception=True)

            email: str = serializer.validated_data["email"]
            redis_client: RedisClient = RedisClient()

            logger.debug(
                f"Attempting to create/retrieve guest token for email: {email}"
            )

            # Check if a token already exists for the given email
            existing_token: Optional[str] = redis_client.get_token(email)
            if existing_token:
                logger.info(f"Existing guest token found for email: {email}")
                return Response(
                    {"guest_token": existing_token}, status=status.HTTP_200_OK
                )

            # Retrieve or create an abstract user associated with the email
            user: Optional[CustomUser] = serializer.get_abstract_user(email)
            if not user:
                logger.warning(f"No user found or created for email: {email}")
                return Response(
                    {"error": "Unable to create a guest user for the provided email."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Generate a new guest token
            token: str = TokenManager.create_guest_token(user)
            logger.debug(f"Generated new guest token for email: {email}")

            # Store the token in Redis with a 1-hour expiration
            redis_client.set_token(
                email, token, int(datetime.timedelta(hours=1).total_seconds())
            )
            logger.info(f"Guest token stored in Redis for email: {email}")

            return Response({"guest_token": token},
                            status=status.HTTP_201_CREATED)

        except IntegrityError as ie:
            logger.warning(
                f"Integrity error during guest token creation: {ie}")
            return Response(
                {"error": "A user with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except ValidationError as ve:
            logger.warning(
                f"Validation error during guest token creation: {ve}")
            return Response({"errors": ve.detail},
                            status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(
                f"Unexpected error during guest token creation: {e}", exc_info=True
            )
            return Response(
                {"error": "An unexpected error occurred. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
