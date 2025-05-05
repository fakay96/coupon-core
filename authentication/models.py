"""
Models for custom user and role-based access control (RBAC).

This module defines a custom user model and a role model to support RBAC in the system.
"""

from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.gis.db.models import PointField
from django.core.validators import EmailValidator, MinLengthValidator, RegexValidator
from django.db import models

import uuid
from django.utils import timezone
import logging
from datetime import datetime
from typing import Any
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.html import format_html
from django import forms
from django.contrib import admin
from django.http import HttpRequest
from django.conf import settings
logger = logging.getLogger(__name__)

class CustomUser(AbstractUser):
    """
    Custom user model with additional fields for extended functionality.

    This model adds support for guest users and includes timestamps for creation and updates.
    """
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    email = models.EmailField(
        unique=True,
        validators=[EmailValidator(message="Enter a valid email address.")],
    )
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r"^\+?[1-9]\d{1,14}$",
                message="Enter a valid phone number in international format (e.g., +123456789).",
            )
        ],
        help_text="User's phone number in international format.",
    )
    is_guest = models.BooleanField(
        default=False, help_text="Indicates if the user is a guest."
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the user was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when the user was last updated."
    )

    groups = models.ManyToManyField(
        Group,
        related_name="custom_users",
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_users",
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )
    activated_profile = models.BooleanField(
        null=True, 
        blank=True, 
        default=None, 
        help_text="Indicates if the user has activated their profile."
        )

    def __str__(self) -> str:
        """
        Return a string representation of the CustomUser instance.

        Returns:
            str: The username of the user.
        """
        return self.username
    
    def send_password_reset_email(self) -> None:
        """
        Create a new PasswordResetRequest with a fresh token and enqueue a task to send the password reset email asynchronously.
        """
        from authentication.v1.tasks.verification_task import send_password_reset_email_task
        from django.utils import timezone
        from uuid import uuid4
        from authentication.models import PasswordResetRequest

        # Create a new password reset request with a fresh token and expiration
        reset_request = PasswordResetRequest.objects.create(
            user=self,
            token=uuid4(),
            created_at=timezone.now(),
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
            used=False,
        )
        if settings.CELERY_ALWAYS_EAGER:
            send_password_reset_email_task(self.email, str(reset_request.token))
        else:
            send_password_reset_email_task.delay(self.email, str(reset_request.token))
        


class Role(models.Model):
    """
    Role model for role-based access control (RBAC).

    Defines roles that can be assigned to users for managing permissions in the system.
    """

    name = models.CharField(
        max_length=50,
        unique=True,
        validators=[
            MinLengthValidator(3, message="Role name must be at least 3 characters.")
        ],
        help_text="Name of the role.",
    )
    description = models.TextField(
        blank=True, null=True, help_text="Description of the role."
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the role was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when the role was last updated."
    )

    def __str__(self) -> str:
        """
        Return a string representation of the Role instance.

        Returns:
            str: The name of the role.
        """
        return self.name


class PasswordResetRequest(models.Model):
    """
    Model to record password reset requests and tokens.

    Attributes:
        user (CustomUser): The user who requested the password reset.
        token (UUID): Unique token for password reset.
        created_at (datetime): Timestamp when the request was created.
        expires_at (datetime): Timestamp when the token expires.
        used (bool): Whether the token has been used.
    """

    user = models.ForeignKey(
        "CustomUser",
        on_delete=models.CASCADE,
        related_name="password_reset_requests",
        help_text="The user who requested the password reset.",
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        help_text="Unique token for password reset.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the request was created.",
    )
    expires_at = models.DateTimeField(
        help_text="Timestamp when the token expires.",
    )
    used = models.BooleanField(
        default=False,
        help_text="Indicates whether the token has been used.",
    )

    def save(self, *args, **kwargs) -> None:
        """
        Ensure expires_at is set to 10 minutes from creation if not provided.
        """
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_expired(self) -> bool:
        """
        Check if the token is expired.

        Returns:
            bool: True if expired, False otherwise.
        """
        return timezone.now() > self.expires_at

    def mark_as_used(self) -> None:
        """
        Mark the token as used.
        """
        if not self.used:
            self.used = True
            self.save(update_fields=["used"])

    def __str__(self) -> str:
        return f"Password reset request for {self.user.email} - {'Used' if self.used else 'Pending'}"


class UserProfile(models.Model):
    """
    UserProfile model for managing extended user information.

    This model is linked to the CustomUser model via a One-to-One relationship and includes
    additional fields such as user preferences and geographic location.
    """

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="profile",
        help_text="The user associated with this profile.",
    )
    preferences = models.JSONField(
        blank=True,
        null=True,
        help_text="User preferences stored as a JSON object (e.g., categories of interest).",
    )
    location = PointField(
        blank=True,
        null=True,
        help_text="Geographic location of the user (latitude and longitude).",
    )
    profile_image = models.ImageField(
        upload_to='profile_images/',
        blank=True,
        null=True,
        help_text="Profile image for the user.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the profile was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when the profile was last updated."
    )


    def __str__(self) -> str:
        """
        Return a string representation of the UserProfile instance.

        Returns:
            str: The username of the associated user.
        """
        return f"Profile of {self.user.username}"

    class Meta:
        """
        Meta options for the UserProfile model.
        """

        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ["-created_at"]



class ProfileVerification(models.Model):
    """
    Model for verifying user profiles via a token-based mechanism.

    This model stores verification tokens with expiration times and ensures they can only be used once.

    Attributes:
        user (CustomUser): The user associated with this verification record.
        token (UUID): Unique verification token for the user.
        created_at (datetime): Timestamp when the verification token was created.
        expires_at (datetime): Timestamp when the verification token expires.
        used (bool): Indicates whether the verification token has been used.
    """

    user: CustomUser = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="verification",
        help_text="The user associated with this verification record."
    )
    token: uuid.UUID = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        help_text="Unique verification token for the user."
    )
    created_at: datetime = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the verification token was created."
    )
    expires_at: datetime = models.DateTimeField(
        help_text="Timestamp when the verification token expires."
    )
    used: bool = models.BooleanField(
        default=False,
        help_text="Indicates whether the verification token has been used."
    )

    def save(self, *args, **kwargs) -> None:
        """
        Ensure `expires_at` is always set correctly when saving.

        If `expires_at` is not already set, it will be assigned a value of 10 minutes from the current time.
        """
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_expired(self) -> bool:
        """
        Check whether the verification token has expired.

        Returns:
            bool: True if the token has expired, False otherwise.
        """
        return timezone.now() > self.expires_at if self.expires_at else True

    def mark_as_used(self) -> None:
        """
        Mark the verification token as used to prevent reuse.

        If the token is not already marked as used, it updates the `used` field and saves the instance.
        """
        if not self.used:
            self.used = True
            self.save(update_fields=["used"])

    def resend_new_token(self, force_resend: bool = False) -> None:
        """
        Resend a new verification token.

        If `force_resend` is True, a new token is generated regardless of expiration status.
        Otherwise, a new token is only generated if the current token is expired and unused.

        Args:
            force_resend (bool, optional): Whether to forcefully resend a new token. Defaults to False.

        Logs:
            - If the token is resent, logs success.
            - If force resend is blocked due to an already used token, logs a warning.
            - If no action is needed, logs that the token is still valid.

        """
        if force_resend or (self.is_expired() and not self.used):
            new_token: uuid.UUID = uuid.uuid4()

            # Avoid unnecessary updates if the token is already new
            if self.token != new_token:
                self.token = new_token
                self.created_at = timezone.now()
                self.expires_at = self.created_at + timezone.timedelta(minutes=10)
                self.used = False
                self.save(update_fields=["token", "created_at", "expires_at", "used"])
            else:
                logger.info(f"Token for user {self.user.email} was already updated recently.")
        
        else:
            if self.used:
                logger.warning(f"Token for user {self.user.email} has already been used. Resend blocked.")
            else:
                logger.info(f"Token for user {self.user.email} is still valid. No need to resend.")     
    def __str__(self) -> str:
        """
        Return a string representation of the `ProfileVerification` instance.

        Returns:
            str: A message indicating the verification status.
        """
        status: str = "Used" if self.used else "Pending"
        return f"Verification for {self.user.username} - {status}"



class PasswordResetRequestForm(forms.ModelForm):
    """
    Sophisticated form for managing PasswordResetRequest instances.
    Includes validation to ensure token integrity.
    """

    class Meta:
        model = PasswordResetRequest
        fields = "__all__"
        widgets = {
            "expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def clean(self) -> dict[str, Any]:
        """
        Validate the form before saving.
        """
        cleaned_data = super().clean()
        expires_at = cleaned_data.get("expires_at")
        used = cleaned_data.get("used")

        if expires_at and expires_at < timezone.now() and not used:
            raise forms.ValidationError(
                "You cannot leave a token unused if it has already expired."
            )

        return cleaned_data

    def clean_user(self) -> Any:
        """
        Prevent changing the user field after creation.
        """
        if self.instance.pk:
            return self.instance.user
        return self.cleaned_data.get("user")

    def clean_token(self) -> Any:
        """
        Prevent changing the token field after creation.
        """
        if self.instance.pk:
            return self.instance.token
        return self.cleaned_data.get("token")


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    """
    Advanced admin configuration for PasswordResetRequest.
    Provides rich UX and strong data protection.
    """

    form = PasswordResetRequestForm

    list_display: tuple[str, ...] = (
        "user",
        "short_token",
        "created_at",
        "expires_at",
        "used",
        "status_display",
    )
    list_filter: tuple[str, ...] = ("used", "created_at", "expires_at")
    search_fields: tuple[str, ...] = ("user__email", "user__username", "token")
    ordering: tuple[str, ...] = ("-created_at",)
    readonly_fields: tuple[str, ...] = ("created_at", "token", "user", "status_display")
    fieldsets: tuple[tuple[str, dict[str, Any]], ...] = (
        (None, {
            "fields": ("user", "token", "created_at", "expires_at", "used", "status_display")
        }),
    )

    def short_token(self, obj: PasswordResetRequest) -> str:
        """
        Shorten token display for better readability in list view.
        """
        return str(obj.token)[:8] + "..."

    short_token.short_description = "Token"

    def status_display(self, obj: PasswordResetRequest) -> str:
        """
        Visually enhanced status of the token (valid, expired, used).
        """
        if obj.used:
            return format_html('<span style="color: gray;">✅ Used</span>')
        elif obj.is_expired():
            return format_html('<span style="color: red;">❌ Expired</span>')
        else:
            return format_html('<span style="color: green;">✅ Valid</span>')

    status_display.short_description = "Status"

    def get_queryset(self, request: HttpRequest) -> QuerySet[PasswordResetRequest]:
        """
        Use authentication shard for consistency with CustomUser admin.
        """
        return super().get_queryset(request).using("authentication_shard")
