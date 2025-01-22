"""
Models for custom user and role-based access control (RBAC).

This module defines a custom user model and a role model to support RBAC in the system.
"""

from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.validators import EmailValidator, MinLengthValidator
from django.db import models


class CustomUser(AbstractUser):
    """
    Custom user model with additional fields for extended functionality.

    This model adds support for guest users and includes timestamps for creation and updates.
    """

    email = models.EmailField(
        unique=True,
        validators=[EmailValidator(message="Enter a valid email address.")],
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
        related_name="customuser_groups",
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="customuser_permissions",
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )

    def __str__(self) -> str:
        """
        Return a string representation of the CustomUser instance.

        Returns:
            str: The username of the user.
        """
        return self.username


class Role(models.Model):
    """
    Role model for role-based access control (RBAC).

    Defines roles that can be assigned to users for managing permissions in the system.
    """

    name = models.CharField(
        max_length=50,
        unique=True,
        validators=[
            MinLengthValidator(
                3, message="Role name must be at least 3 characters.")
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
