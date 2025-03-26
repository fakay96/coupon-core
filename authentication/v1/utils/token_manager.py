"""
Utility module for handling JWT token generation.

Provides methods to create tokens for guest and admin users, with error handling and logging.
"""

import logging
from typing import Dict, Optional
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

logger = logging.getLogger(__name__)


class TokenManager:
    """A utility class for handling JWT token generation."""

    @staticmethod
    def create_access_token(user: AbstractUser, expiration: Optional[int] = None) -> str:
        """
        Create a JWT access token for a user.

        Args:
            user (AbstractUser): The user instance.
            expiration (Optional[int]): Token expiration time in seconds.

        Returns:
            str: A JWT access token for the user.

        Raises:
            ValueError: If token creation fails or the user instance is invalid.
        """
        if user is None:
            logger.error("User instance cannot be None.")
            raise ValueError("User instance cannot be None.")

        try:
            refresh = RefreshToken.for_user(user)
            if expiration:
                refresh.access_token.set_exp(lifetime=timedelta(seconds=expiration))
            access_token = str(refresh.access_token)
            logger.info(f"Access token created for user: {user.username}")
            return access_token
        except TokenError as e:
            logger.error(f"Failed to create access token for user {user.username}: {str(e)}")
            raise ValueError("Unable to generate access token.") from e

    @staticmethod
    def create_refresh_token(user: AbstractUser, expiration: Optional[int] = None) -> str:
        """
        Create a JWT refresh token for a user.

        Args:
            user (AbstractUser): The user instance.
            expiration (Optional[int]): Token expiration time in seconds.

        Returns:
            str: A JWT refresh token for the user.

        Raises:
            ValueError: If token creation fails or the user instance is invalid.
        """
        if user is None:
            logger.error("User instance cannot be None.")
            raise ValueError("User instance cannot be None.")

        try:
            refresh = RefreshToken.for_user(user)
            if expiration:
                refresh.set_exp(lifetime=timedelta(seconds=expiration))
            refresh_token = str(refresh)
            logger.info(f"Refresh token created for user: {user.username}")
            return refresh_token
        except TokenError as e:
            logger.error(f"Failed to create refresh token for user {user.username}: {str(e)}")
            raise ValueError("Unable to generate refresh token.") from e

    @staticmethod
    def create_guest_token(guest_user: AbstractUser | str) -> str:
        """
        Create a JWT token for guest users.

        Args:
            guest_user (AbstractUser | str): The guest user instance or email string.

        Returns:
            str: A JWT access token for the guest user.

        Raises:
            ValueError: If token creation fails or the user instance is invalid.
        """
        if guest_user is None:
            logger.error("Guest user instance cannot be None.")
            raise ValueError("Guest user instance cannot be None.")

        if isinstance(guest_user, str):
            from authentication.models import CustomUser
            guest_user = CustomUser.objects.create_user(
                username=guest_user.split('@')[0],
                email=guest_user,
                is_guest=True
            )

        try:
            refresh = RefreshToken.for_user(guest_user)
            access_token = str(refresh.access_token)
            logger.info(f"Access token created for guest user: {guest_user.username}")
            return access_token
        except TokenError as e:
            logger.error(f"Failed to create guest token for user {guest_user.username}: {str(e)}")
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
                f"Tokens successfully created for admin user: {user.username}"
            )
            return tokens
        except TokenError as e:
            logger.error(
                f"Failed to create tokens for admin user {user.username}: {str(e)}"
            )
            raise ValueError("Unable to generate tokens for the admin user.") from e

    @staticmethod
    def verify_token(token: str) -> Dict:
        """
        Verify a JWT token and return its payload.

        Args:
            token (str): The JWT token to verify.

        Returns:
            Dict: The decoded token payload.

        Raises:
            ValueError: If token verification fails or the token is invalid.
        """
        try:
            # Try to decode as access token first
            access_token = AccessToken(token)
            return access_token.payload
        except TokenError:
            try:
                # If not an access token, try as refresh token
                refresh_token = RefreshToken(token)
                return refresh_token.payload
            except TokenError as e:
                logger.error(f"Failed to verify token: {str(e)}")
                raise ValueError("Invalid or expired token.") from e
