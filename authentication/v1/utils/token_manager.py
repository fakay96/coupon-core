"""
Utility module for handling JWT token generation.

Provides methods to create tokens for guest and admin users, with error handling and logging.
"""

import logging
from typing import Dict

from django.contrib.auth.models import AbstractUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)


class TokenManager:
    """A utility class for handling JWT token generation."""

    @staticmethod
    def create_guest_token(guest_user: AbstractUser) -> str:
        """
        Create a JWT token for guest users.

        Args:
            guest_user (AbstractUser): The guest user instance.

        Returns:
            str: A JWT access token for the guest user.

        Raises:
            ValueError: If token creation fails or the user instance is invalid.
        """
        if guest_user is None:
            logger.error("Guest user instance cannot be None.")
            raise ValueError("Guest user instance cannot be None.")

        try:
            refresh = RefreshToken.for_user(guest_user)
            access_token = str(refresh.access_token)
            logger.info(
                f"Access token created for guest user: {
                    guest_user.username}")
            return access_token
        except TokenError as e:
            logger.error(
                f"Failed to create guest token for user {
                    guest_user.username}: {str(e)}"
            )
            raise ValueError("Unable to generate guest token.") from e

    @staticmethod
    def create_admin_tokens(user: AbstractUser) -> Dict[str, str]:
        """
        Create access and refresh tokens for an admin user.

        Args:
            user (AbstractUser): The user instance for whom tokens are generated.

        Returns:
            Dict[str, str]: A dictionary containing 'access' and 'refresh' tokens.

        Raises:
            ValueError: If token creation fails or the user instance is invalid.
        """
        if user is None:
            logger.error("Admin user instance cannot be None.")
            raise ValueError("Admin user instance cannot be None.")

        try:
            refresh = RefreshToken.for_user(user)

            tokens = {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
            logger.info(
                f"Tokens successfully created for admin user: {
                    user.username}")
            return tokens
        except TokenError as e:
            logger.error(
                f"Failed to create tokens for admin user {
                    user.username}: {str(e)}"
            )
            raise ValueError(
                "Unable to generate tokens for the admin user.") from e
