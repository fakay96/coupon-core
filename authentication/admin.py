"""
Admin configuration for the authentication app.

This module customizes the Django admin interface for managing:
- Custom users (`CustomUser`)
- Role-based access control (`Role`)
- User profiles (`UserProfile`)
- Groups and permissions

It provides an enhanced user management experience, including:
- Search and filtering capabilities
- Custom user and permission management
- GIS integration for user locations
"""

from typing import Optional, Tuple, Type

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.gis.admin import OSMGeoAdmin
from django.contrib.auth.models import Group, Permission
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import CustomUser, Role, UserProfile


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Admin panel customization for CustomUser.

    Enhancements include:
    - Search by username and email
    - Filters for active, staff, and guest users
    - Read-only timestamps for auditing
    - Group and permission management for access control
    """

    model = CustomUser
    list_display = ("username", "email", "is_active", "is_staff", "is_superuser", "is_guest", "created_at")
    list_filter = ("is_active", "is_staff", "is_superuser", "is_guest", "created_at")
    search_fields = ("username", "email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets: Tuple[Tuple[Optional[str], dict], ...] = (
        ("Basic Information", {"fields": ("username", "email", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "is_guest")}),
        ("Groups & Permissions", {"fields": ("groups", "user_permissions")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    add_fieldsets: Tuple[Tuple[Optional[str], dict], ...] = (
        ("Create User", {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2", "is_guest", "is_active", "is_staff", "is_superuser"),
        }),
    )

    filter_horizontal = ("groups", "user_permissions")

    def get_queryset(self, request: HttpRequest) -> QuerySet[CustomUser]:
        """
        Return a queryset for all CustomUser objects.

        Args:
            request (HttpRequest): The incoming admin request.

        Returns:
            QuerySet[CustomUser]: Queryset of all CustomUser instances.
        """
        return super().get_queryset(request)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """
    Admin panel customization for Role model.

    - Provides filtering and search options
    - Ensures timestamps are read-only
    - Allows administrators to manage role-based access control
    """

    list_display = ("name", "description", "created_at", "updated_at")
    search_fields = ("name",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    list_filter = ("created_at",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Role]:
        """
        Return a queryset for all Role objects.

        Args:
            request (HttpRequest): The incoming admin request.

        Returns:
            QuerySet[Role]: Queryset of all Role instances.
        """
        return super().get_queryset(request)


@admin.register(UserProfile)
class UserProfileAdmin(OSMGeoAdmin):
    """
    Admin panel customization for UserProfile model.

    - Integrates GIS features for managing user locations
    - Allows administrators to view and edit user preferences
    - Provides search and filtering for efficient user management
    """

    list_display = ("user", "preferences", "location", "created_at")
    search_fields = ("user__username", "user__email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    list_filter = ("created_at",)

    # GIS Admin default map settings
    default_lon = 0  # Default longitude for GIS map
    default_lat = 0  # Default latitude for GIS map
    default_zoom = 4  # Adjust as needed

    def get_queryset(self, request: HttpRequest) -> QuerySet[UserProfile]:
        """
        Return a queryset for all UserProfile objects.

        Args:
            request (HttpRequest): The incoming admin request.

        Returns:
            QuerySet[UserProfile]: Queryset of all UserProfile instances.
        """
        return super().get_queryset(request)


# Ensure groups and permissions are manageable in Django admin
admin.site.unregister(Group)  # Unregister default Group


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """
    Custom admin panel for managing Django groups.

    - Enables search by group name
    - Allows management of permissions within groups
    - Improves default Django admin experience for role-based access
    """

    search_fields = ("name",)
    ordering = ("name",)
    filter_horizontal = ("permissions",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Group]:
        """
        Return a queryset for all Group objects.

        Args:
            request (HttpRequest): The incoming admin request.

        Returns:
            QuerySet[Group]: Queryset of all Group instances.
        """
        return super().get_queryset(request)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """
    Admin panel for managing individual permissions.

    - Enables search by permission name and codename
    - Provides an ordered list of permissions
    - Allows efficient management of user access controls
    """

    search_fields = ("name", "codename")
    ordering = ("name",)
    list_display = ("name", "codename", "content_type")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Permission]:
        """
        Return a queryset for all Permission objects.

        Args:
            request (HttpRequest): The incoming admin request.

        Returns:
            QuerySet[Permission]: Queryset of all Permission instances.
        """
        return super().get_queryset(request)


# Customizing the Django admin interface
admin.site.site_header = "Coupon Core Admin"
admin.site.site_title = "Coupon Core Admin Panel"
admin.site.index_title = "Welcome to Coupon Core Admin"
