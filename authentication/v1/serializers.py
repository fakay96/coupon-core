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
from django.contrib.gis.geos import Point
from rest_framework import serializers

from authentication.models import CustomUser, UserProfile

class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login validation.

    This serializer handles user authentication using email and password.
    It ensures that:
        - The provided email is in a valid format.
        - The password matches the user account.
        - Guest accounts are not allowed to log in.

    Attributes:
        email (EmailField): The user's email address.
        password (CharField): The user's password (write-only).
    """

    email = serializers.EmailField(
        max_length=150,
        required=True,
        help_text="A valid email address used to identify the user."
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        help_text="The user's password (not returned in the response)."
    )

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates the provided email and password against registered users.

        Args:
            data (Dict[str, Any]): A dictionary containing 'email' and 'password'.

        Returns:
            Dict[str, Any]: The validated data with the authenticated user instance.

        Raises:
            serializers.ValidationError: If authentication fails or the user is a guest.
        """
        email: str = data.get("email")
        password: str = data.get("password")

        user: Optional[CustomUser] = authenticate(email=email, password=password)

        if user is None:
            raise serializers.ValidationError(_("Invalid email or password."))

        if getattr(user, "is_guest", False):
            raise serializers.ValidationError(_("Guest accounts are not allowed to log in."))

        data["user"] = user
        return data

class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.

    Handles validation of email and username, and creation of new users.
    """
    class Meta:
        model = CustomUser
        fields = ["username", "password", "email"]
        extra_kwargs = {"password": {"write_only": True}}

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
    email = serializers.EmailField(required=True)

    def validate_email(self, value: str) -> str:
        """
        Validate or create a guest user associated with the provided email.

        Args:
            value (str): Email to validate.

        Returns:
            str: Validated email after ensuring a guest user exists.

        Side Effects:
            Creates a guest user if one doesn't exist.
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
            raise serializers.ValidationError(_("No user found with the provided email."))
class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for managing user profile updates in a flat structure.

    This serializer flattens the user-related fields (first_name, last_name, phone_number)
    into the top level of the payload rather than nesting them inside a 'user' object.

    It supports:
        - Updating basic user details: first_name, last_name, phone_number.
        - Updating profile-specific fields: preferences, location (write-only), profile_image.
        - Accepting user preferences as a dictionary (e.g., {"dark_mode": true}).
        - Validating and converting the location field into a geographic Point.
        - Serializing data into a flat JSON format for ease of use in front-end clients,
          excluding sensitive fields like location from responses.

    Expected input format:
    {
        "first_name": "Jane",
        "last_name": "Doe",
        "phone_number": "+1234567890",
        "preferences": {
            "dark_mode": true,
            "notifications": false
        },
        "location": [-3.93, 50.74],  # accepted but not serialized
        "profile_image": null
    }

    Notes:
        - The location must be a list with exactly two float values: [longitude, latitude].
        - Fields are optional and only provided fields will be updated.
        - The location is only writeable and not returned in serialized output for privacy.
    """

    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    phone_number = serializers.CharField(source='user.phone_number', required=False)

    preferences = serializers.JSONField(required=False)
    location = serializers.ListField(
        child=serializers.FloatField(),
        required=False,
        min_length=2,
        max_length=2,
        write_only=True,
        help_text="Location coordinates as [longitude, latitude] (write-only)"
    )
    profile_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = UserProfile
        fields = [
            "first_name",
            "last_name",
            "phone_number",
            "preferences",
            "location",  # write-only
            "profile_image"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def to_representation(self, instance: UserProfile) -> Dict[str, Any]:
        """
        Convert the UserProfile instance to a dictionary representation,
        excluding location from the serialized output.
        """
        data = super().to_representation(instance)
        # Do not include location in the output
        return data

    def validate_location(self, value: list) -> Point:
        """
        Validate and convert location coordinates to a Point object.

        Args:
            value (list): [longitude, latitude]

        Returns:
            Point: A valid geographic point.

        Raises:
            serializers.ValidationError: If the input format is invalid.
        """
        try:
            return Point(value[0], value[1])
        except (IndexError, ValueError, TypeError):
            raise serializers.ValidationError(_("Invalid location coordinates."))

    def validate_preferences(self, value: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate user preferences.

        Must be a dictionary (e.g., {"dark_mode": true}).
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError(_("Preferences must be a JSON object."))
        return value

    def update(self, instance: UserProfile, validated_data: Dict[str, Any]) -> UserProfile:
        """
        Update the UserProfile and related User fields using flat input.

        Handles:
        - Updating fields on the associated CustomUser instance.
        - Updating profile-specific fields directly.
        """
        user_data = validated_data.pop("user", {})
        user = instance.user

        for attr in ["first_name", "last_name", "phone_number"]:
            if attr in user_data:
                setattr(user, attr, user_data[attr])
        user.save()

        # Update remaining profile fields
        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.save()
        return instance
