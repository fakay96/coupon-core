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

    Validates username and password, ensuring the user is not a guest.
    """
    username = serializers.CharField(max_length=150, required=True)
    password = serializers.CharField(write_only=True, required=True)

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


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the Django CustomUser model.

    Provides basic user details such as username and email.
    """
    class Meta:
        model = CustomUser
        fields = ["id", "username", "email", "first_name", "last_name", "phone_number"]
        read_only_fields = ["id"]


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for managing user profiles.

    This serializer is responsible for serializing and deserializing user profile data.
    It supports:
        - Retrieving profile information, including user details.
        - Updating user preferences and location.
        - Allowing updates to the user's phone number.

    Attributes:
        - user (UserSerializer, read-only): Nested serializer for user details.
        - phone_number (str, optional): Allows updating the phone number of the user.
        - preferences (dict, optional): JSON object storing user preferences.
        - location (PointField, optional): Geographical location of the user.
        - created_at (datetime, read-only): Timestamp when the profile was created.
        - updated_at (datetime, read-only): Timestamp when the profile was last updated.
    """
    user = UserSerializer(read_only=True)
    phone_number = serializers.CharField(
        source="user.phone_number",
        required=False,
        help_text="The phone number of the user in international format (e.g., +1234567890)."
    )
    location = serializers.ListField(
        child=serializers.FloatField(),
        required=False,
        min_length=2,
        max_length=2,
        help_text="Location coordinates as [longitude, latitude]"
    )

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "user",
            "phone_number",
            "preferences",
            "location",
            "profile_image",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def to_representation(self, instance: UserProfile) -> Dict[str, Any]:
        """
        Convert the UserProfile instance to a dictionary representation.

        Args:
            instance (UserProfile): The user profile instance to serialize.

        Returns:
            Dict[str, Any]: The serialized user profile data.
        """
        data = super().to_representation(instance)
        if instance.location:
            data['location'] = [instance.location.x, instance.location.y]
        return data

    def validate_location(self, value: list) -> Point:
        """
        Validate and convert location coordinates to a Point object.

        Args:
            value (list): List containing [longitude, latitude] coordinates.

        Returns:
            Point: A Point object representing the location.

        Raises:
            serializers.ValidationError: If the coordinates are invalid.
        """
        try:
            return Point(value[0], value[1])
        except (IndexError, ValueError, TypeError):
            raise serializers.ValidationError(_("Invalid location coordinates."))

    def validate_preferences(self, value: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate user preferences.

        Args:
            value (Dict[str, Any]): Dictionary containing user preferences.

        Returns:
            Dict[str, Any]: The validated preferences.

        Raises:
            serializers.ValidationError: If the preferences format is invalid.
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError(_("Preferences must be a JSON object."))
        return value

    def update(self, instance: UserProfile, validated_data: Dict[str, Any]) -> UserProfile:
        """
        Update the UserProfile and the associated User model.

        This method ensures that:
        - `phone_number`, `first_name`, and `last_name` updates are applied to the `CustomUser` model.
        - Other profile-related fields (`preferences`, `location`) are updated normally.

        Args:
            instance (UserProfile): The current user profile instance.
            validated_data (dict): The validated data from the request.

        Returns:
            UserProfile: The updated user profile instance.
        """
        # Extract user data from validated data; if not provided, an empty dict is used.
        user_data = validated_data.pop("user", {})

        user = instance.user
        # Update user fields if provided.
        phone_number = user_data.get("phone_number")
        first_name = user_data.get("first_name")
        last_name = user_data.get("last_name")

        if phone_number is not None:
            user.phone_number = phone_number
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name

        user.save()

        # Update profile fields
        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.save()
        return instance
