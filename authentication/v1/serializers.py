"""
Serializers for authentication-related operations.

This module includes serializers for user login, registration, and guest token generation.
"""

from typing import Any, Dict

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from authentication.models import CustomUser


class LoginSerializer(serializers.Serializer):
    """Serializer for admin login."""

    username: str = serializers.CharField(max_length=150, required=True)
    password: str = serializers.CharField(write_only=True, required=True)

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the username and password combination.

        Args:
            data (Dict[str, Any]): The input data containing 'username' and 'password'.

        Returns:
            Dict[str, Any]: The validated data with the user instance.

        Raises:
            serializers.ValidationError: If credentials are invalid or user is a guest.
        """
        username: str = data.get("username")
        password: str = data.get("password")

        user = authenticate(username=username, password=password)

        if user is None:
            raise serializers.ValidationError(_("Invalid username or password."))

        if user.is_guest:
            raise serializers.ValidationError(
                _("Guest accounts are not allowed to log in.")
            )

        data["user"] = user
        return data


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for admin registration."""

    class Meta:
        """Meta options for the RegisterSerializer."""

        model = CustomUser
        fields = ["username", "password", "email"]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def validate_email(self, value: str) -> str:
        """
        Ensure the email address is not already in use.

        Args:
            value (str): The email to validate.

        Returns:
            str: The validated email.

        Raises:
            serializers.ValidationError: If the email is already in use.
        """
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError(_("Email is already in use."))
        return value

    def validate_username(self, value: str) -> str:
        """
        Ensure the username is not already in use.

        Args:
            value (str): The username to validate.

        Returns:
            str: The validated username.

        Raises:
            serializers.ValidationError: If the username is already taken.
        """
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError(_("Username is already taken."))
        return value

    def create(self, validated_data: dict) -> CustomUser:
        """
        Create a new admin user with a hashed password.

        Args:
            validated_data (dict): The validated data containing username, password, and email.

        Returns:
            CustomUser: The newly created user instance.
        """
        validated_data["password"] = make_password(validated_data["password"])
        return super().create(validated_data)


class GuestTokenSerializer(serializers.Serializer):
    """Serializer for generating guest tokens."""

    email: str = serializers.EmailField(required=True)

    def validate_email(self, value: str) -> str:
        """
        Ensure the email address is valid or create a new guest user if it doesn't exist.

        Args:
            value (str): The email to validate.

        Returns:
            str: The validated email after ensuring a guest user exists.

        Side Effects:
            - Creates a new guest user if one does not already exist.
        """
        user, created = CustomUser.objects.get_or_create(
            email=value,
            defaults={
                "username": value.split("@")[
                    0
                ],  # Use the email's prefix as the username
                "is_guest": True,  # Mark this user as a guest
            },
        )
        if created:
            user.set_unusable_password()  # Disable login for guest accounts
            user.save()
        return value

    def get_abstract_user(self, email: str) -> CustomUser:
        """
        Retrieve a guest user based on their email.

        Args:
            email (str): The email of the guest user to retrieve.

        Returns:
            CustomUser: The `CustomUser` instance if found.

        Raises:
            serializers.ValidationError: If the email does not belong to any user.
        """
        try:
            return CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError(
                _("No user found with the provided email.")
            )
