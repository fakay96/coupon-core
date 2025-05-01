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
import uuid

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.utils.translation import gettext_lazy as _
from django.contrib.gis.geos import Point
from rest_framework import serializers
from django.utils import timezone

from authentication.models import CustomUser, UserProfile, PasswordResetRequest

def raise_validation_error(message: str) -> None:
    """
    Helper function to raise a ValidationError.

    Args:
        message (str): Error message.

    Raises:
        serializers.ValidationError: Always.
    """
    raise serializers.ValidationError(_(message))

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
        allow_blank=False,
        help_text="A valid email address used to identify the user.",
        error_messages={
            'required': 'Please enter your email address.',
            'blank': 'Please enter your email address.',
            'invalid': 'Please enter a valid email address.'
        }
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        allow_blank=False,
        help_text="The user's password (not returned in the response).",
        error_messages={
            'required': 'Please enter your password.',
            'blank': 'Please enter your password.'
        }
    )

    def validate_email(self, value: str) -> str:
        """
        Validate email format and normalize to lowercase.

        Args:
            value (str): Email to validate.

        Returns:
            str: Normalized email address.

        Raises:
            serializers.ValidationError: If email format is invalid.
        """
        try:
            local_part, domain = value.split('@')
            if not local_part or not domain:
                raise serializers.ValidationError(_("Please enter a valid email address."))
            
            if '.' not in domain:
                raise serializers.ValidationError(_("Please enter a valid email address."))
        except ValueError:
            raise serializers.ValidationError(_("Please enter a valid email address."))

        return value.lower()

    def validate_password(self, value: str) -> str:
        """
        Validate password complexity.

        Args:
            value (str): Password to validate.

        Returns:
            str: Validated password.

        Raises:
            serializers.ValidationError: If password doesn't meet complexity requirements.
        """
        if len(value) < 8:
            raise serializers.ValidationError(_("Password must be at least 8 characters long."))
        
        if not any(c.isupper() for c in value):
            raise serializers.ValidationError(_("Password must contain at least one uppercase letter."))
        
        if not any(c.islower() for c in value):
            raise serializers.ValidationError(_("Password must contain at least one lowercase letter."))
        
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError(_("Password must contain at least one number."))
        
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in value):
            raise serializers.ValidationError(_("Password must contain at least one special character."))
        
        return value

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
        email: str = data.get("email", "").lower()  # Normalize email to lowercase
        password: str = data.get("password", "")

        # If either field is empty, raise non_field_errors
        if not email or not password:
            raise serializers.ValidationError({
                'non_field_errors': [_("Invalid email or password.")]
            })

        # Validate password complexity
        try:
            self.validate_password(password)
        except serializers.ValidationError as e:
            raise serializers.ValidationError({
                'non_field_errors': [_("Invalid email or password.")]
            })

        user: Optional[CustomUser] = authenticate(email=email, password=password)

        if user is None:
            raise serializers.ValidationError({
                'non_field_errors': [_("Invalid email or password.")]
            })

        if getattr(user, "is_guest", False):
            raise serializers.ValidationError({
                'non_field_errors': [_("Guest accounts are not allowed to log in.")]
            })

        data["user"] = user
        return data

class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.

    Handles validation of email and username, and creation of new users.
    """
    password_confirmation = serializers.CharField(write_only=True, required=True)
    MAX_GUEST_USERS = 5

    class Meta:
        model = CustomUser
        fields = ["username", "password", "password_confirmation", "email"]
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
        Ensure the username is unique and valid.

        Args:
            value (str): Username to validate.

        Returns:
            str: The validated username.

        Raises:
            serializers.ValidationError: If the username is invalid or already taken.
        """
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError(_("Username is already taken."))
        
        # Username validation rules
        if not value.isalnum() and not all(c.isalnum() or c in '._-' for c in value):
            raise serializers.ValidationError(_("Username can only contain letters, numbers, dots, underscores, and hyphens."))
        
        if len(value) < 3:
            raise serializers.ValidationError(_("Username must be at least 3 characters long."))
        
        if len(value) > 30:
            raise serializers.ValidationError(_("Username must be at most 30 characters long."))
        
        return value

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the registration data.

        Args:
            data (Dict[str, Any]): The registration data.

        Returns:
            Dict[str, Any]: The validated data.

        Raises:
            serializers.ValidationError: If validation fails.
        """
        if data['password'] != data['password_confirmation']:
            raise serializers.ValidationError(_("Passwords do not match."))
        
        # Check guest user limit
        if CustomUser.objects.filter(is_guest=True).count() >= self.MAX_GUEST_USERS:
            raise serializers.ValidationError(_("Maximum number of guest users reached."))
        
        return data

    def create(self, validated_data: Dict[str, Any]) -> CustomUser:
        """
        Create a new user with hashed password.

        Args:
            validated_data (Dict[str, Any]): Validated user data.

        Returns:
            CustomUser: Newly created user instance.
        """
        validated_data.pop('password_confirmation')  # Remove password confirmation
        validated_data["password"] = make_password(validated_data["password"])
        return super().create(validated_data)


class GuestTokenSerializer(serializers.Serializer):
    """
    Serializer for generating and managing guest tokens.

    Ensures the email is valid and retrieves or creates a guest user.
    """
    email = serializers.EmailField(required=True)
    MAX_GUEST_USERS = 5

    def validate_email(self, value: str) -> str:
        """
        Validate or create a guest user associated with the provided email.

        Args:
            value (str): Email to validate.

        Returns:
            str: Validated email after ensuring a guest user exists.

        Side Effects:
            Creates a guest user if one doesn't exist.

        Raises:
            serializers.ValidationError: If maximum number of guest users is reached.
        """
        # Check guest user limit before creating a new one
        if CustomUser.objects.filter(is_guest=True).count() >= self.MAX_GUEST_USERS:
            raise serializers.ValidationError(_("Maximum number of guest users reached."))

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
    Serializer for UserProfile model.

    Handles validation and serialization of user profile data.
    """
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    phone_number = serializers.CharField(source='user.phone_number', required=False)
    location = serializers.ListField(
        child=serializers.FloatField(),
        required=False,
        min_length=2,
        max_length=2,
        write_only=True,
        help_text="Location coordinates as [longitude, latitude] (write-only)"
    )

    class Meta:
        model = UserProfile
        fields = [
            'first_name',
            'last_name',
            'phone_number',
            'preferences',
            'location',
            'profile_image'
        ]

    def validate_preferences(self, value: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate preferences data.

        Args:
            value (Dict[str, Any]): Preferences data to validate.

        Returns:
            Dict[str, Any]: Validated preferences data.

        Raises:
            serializers.ValidationError: If preferences data is invalid.
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError(_("Preferences must be a dictionary."))

        # Validate allowed preference keys and types
        allowed_preferences = {
            'theme': str,
            'notifications': dict,
            'language': str,
            'timezone': str
        }

        for key, val in value.items():
            if key not in allowed_preferences:
                raise serializers.ValidationError(_(f"Invalid preference key: {key}"))
            
            expected_type = allowed_preferences[key]
            if not isinstance(val, expected_type):
                raise serializers.ValidationError(_(f"Invalid type for {key}. Expected {expected_type.__name__}."))

            # Validate nested preferences
            if key == 'notifications':
                self._validate_notification_preferences(val)

        return value

    def _validate_notification_preferences(self, notifications: Dict[str, bool]) -> None:
        """
        Validate notification preferences.

        Args:
            notifications (Dict[str, bool]): Notification settings to validate.

        Raises:
            serializers.ValidationError: If notification settings are invalid.
        """
        allowed_settings = {'email', 'push', 'sms'}
        
        for key, val in notifications.items():
            if key not in allowed_settings:
                raise serializers.ValidationError(_(f"Invalid notification setting: {key}"))
            
            if not isinstance(val, bool):
                raise serializers.ValidationError(_(f"Notification setting {key} must be a boolean."))

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
        if not isinstance(value, list):
            raise serializers.ValidationError(_("Location must be a list of coordinates."))

        if len(value) != 2:
            raise serializers.ValidationError(_("Location must contain exactly two values: [longitude, latitude]."))

        try:
            lng, lat = float(value[0]), float(value[1])
            self._validate_location_coordinates({'lat': lat, 'lng': lng})
            return Point(lng, lat)
        except (IndexError, ValueError, TypeError):
            raise serializers.ValidationError(_("Invalid location coordinates."))

    def _validate_location_coordinates(self, coords: Dict[str, float]) -> None:
        """
        Validate location coordinates.

        Args:
            coords (Dict[str, float]): Dictionary containing lat and lng values.

        Raises:
            serializers.ValidationError: If coordinates are invalid.
        """
        try:
            lat = float(coords.get('lat', 0))
            lng = float(coords.get('lng', 0))

            if not (-90 <= lat <= 90):
                raise serializers.ValidationError(_("Latitude must be between -90 and 90."))
            if not (-180 <= lng <= 180):
                raise serializers.ValidationError(_("Longitude must be between -180 and 180."))
        except (TypeError, ValueError):
            raise serializers.ValidationError(_("Invalid coordinate values."))

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

class PasswordResetSerializer(serializers.Serializer):
    """
    Serializer for password reset requests.

    Handles validation of email and sending a password reset email.
    """
    email = serializers.EmailField(
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'Please enter your email address.',
            'blank': 'Please enter your email address.',
            'invalid': 'Please enter a valid email address.'
        }
    )
    RATE_LIMIT_MINUTES = 10  # Time window for rate limiting in minutes

    def validate_email(self, value: str) -> str:
        """
        Validate the email address and check rate limits.

        Args:
            value (str): Email to validate.

        Returns:
            str: Validated email.

        Raises:
            serializers.ValidationError: If email is invalid or rate limit is exceeded.
        """
        try:
            local_part, domain = value.split('@')
            if not local_part or not domain:
                raise serializers.ValidationError(_("Please enter a valid email address."))
            
            if '.' not in domain:
                raise serializers.ValidationError(_("Please enter a valid email address."))
        except ValueError:
            raise serializers.ValidationError(_("Please enter a valid email address."))

        value = value.lower()

        try:
            user = CustomUser.objects.get(email=value)
            
            # Check if there's a recent password reset request
            recent_request = PasswordResetRequest.objects.filter(
                user=user,
                created_at__gte=timezone.now() - timezone.timedelta(minutes=self.RATE_LIMIT_MINUTES),
                used=False
            ).exists()

            if recent_request:
                raise serializers.ValidationError(_("Please wait before requesting another password reset."))

        except CustomUser.DoesNotExist:
            # Don't reveal user existence
            pass

        return value

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the data and ensure email is present.

        Args:
            data (Dict[str, Any]): The data to validate.

        Returns:
            Dict[str, Any]: The validated data.

        Raises:
            serializers.ValidationError: If validation fails.
        """
        email = data.get('email')
        if not email:
            raise serializers.ValidationError({
                'email': [_("Please enter your email address.")]
            })

        # Validate email format and rate limit
        try:
            email = self.validate_email(email)
        except serializers.ValidationError as e:
            raise serializers.ValidationError({
                'email': e.detail
            })

        data['email'] = email
        return data

    def save(self) -> None:
        """
        Create a password reset request and send the reset email.
        """
        email = self.validated_data["email"]
        try:
            user = CustomUser.objects.get(email=email)
            # Create a new password reset request with a fresh token and expiration
            reset_request = PasswordResetRequest.objects.create(
                user=user,
                token=uuid.uuid4(),
                created_at=timezone.now(),
                expires_at=timezone.now() + timezone.timedelta(minutes=10),
                used=False,
            )
            from authentication.v1.tasks.verification_task import send_password_reset_email_task
            send_password_reset_email_task.delay(email, str(reset_request.token))
        except CustomUser.DoesNotExist:
            # Don't reveal user existence
            pass

