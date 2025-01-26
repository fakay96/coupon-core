"""
Serializers for authentication and user-related operations.

This module provides serializers for:
1. User login validation.
2. Admin registration.
3. Guest token generation.
4. User profile management.

Author: Your Name
Date: YYYY-MM-DD
"""

from typing import Any, Dict, Optional

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from authentication.models import CustomUser, UserProfile


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login validation.

    Validates username and password, ensuring the user is not a guest.
    """

    username: serializers.CharField = serializers.CharField(
        max_length=150, required=True
    )
    password: serializers.CharField = serializers.CharField(
        write_only=True, required=True
    )

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the provided username and password.

        Args:
            data (Dict[str, Any]): Input containing 'username' and 'password'.

        Returns:
            Dict[str, Any]: The validated data with the authenticated user instance.

        Raises:
            serializers.ValidationError: If the credentials are invalid or the user is a guest.
        """
        username: str = data.get("username")
        password: str = data.get("password")

        user: Optional[CustomUser] = authenticate(username=username, password=password)

        if user is None:
            raise serializers.ValidationError(_("Invalid username or password."))

        if user.is_guest:
            raise serializers.ValidationError(
                _("Guest accounts are not allowed to log in.")
            )

        data["user"] = user
        return data


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.

    Handles validation of email and username, and creation of new users.
    """

    class Meta:
        model: type = CustomUser
        fields: list[str] = ["username", "password", "email"]
        extra_kwargs: Dict[str, Dict[str, Any]] = {"password": {"write_only": True}}

    def validate_email(self, value: str) -> str:
        """
        Ensure the email address is unique.

        Args:
            value (str): Email to validate.

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
        Ensure the username is unique.

        Args:
            value (str): Username to validate.

        Returns:
            str: The validated username.

        Raises:
            serializers.ValidationError: If the username is already taken.
        """
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError(_("Username is already taken."))
        return value

    def create(self, validated_data: Dict[str, Any]) -> CustomUser:
        """
        Create a new user with hashed password.

        Args:
            validated_data (Dict[str, Any]): Validated user data.

        Returns:
            CustomUser: Newly created user instance.
        """
        validated_data["password"] = make_password(validated_data["password"])
        return super().create(validated_data)


class GuestTokenSerializer(serializers.Serializer):
    """
    Serializer for generating and managing guest tokens.

    Ensures the email is valid and retrieves or creates a guest user.
    """

    email: serializers.EmailField = serializers.EmailField(required=True)

    def validate_email(self, value: str) -> str:
        """
        Validate or create a guest user associated with the provided email.

        Args:
            value (str): Email to validate.

        Returns:
            str: Validated email after ensuring a guest user exists.

        Side Effects:
            - Creates a guest user if one doesn't exist.
        """
        user, created = CustomUser.objects.get_or_create(
            email=value,
            defaults={
                "username": value.split("@")[0],  # Use email prefix as username
                "is_guest": True,  # Mark user as a guest
            },
        )
        if created:
            user.set_unusable_password()  # Prevent guest users from logging in
            user.save()
        return value

    def get_abstract_user(self, email: str) -> CustomUser:
        """
        Retrieve a guest user based on their email.

        Args:
            email (str): Email of the guest user to retrieve.

        Returns:
            CustomUser: Guest user instance.

        Raises:
            serializers.ValidationError: If no user exists with the provided email.
        """
        try:
            return CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError(
                _("No user found with the provided email.")
            )


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the Django CustomUser model.

    Provides basic user details such as username and email.
    """

    class Meta:
        model: type = CustomUser
        fields: list[str] = ["id", "username", "email", "first_name", "last_name"]
        read_only_fields: list[str] = ["id"]


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for managing user profiles.

    Includes fields for user preferences and location.
    """

    user: UserSerializer = UserSerializer(read_only=True)

    class Meta:
        model: type = UserProfile
        fields: list[str] = [
            "id",
            "user",
            "preferences",
            "location",
            "created_at",
            "updated_at",
        ]
        read_only_fields: list[str] = ["id", "created_at", "updated_at"]
