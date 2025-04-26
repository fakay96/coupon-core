from typing import Optional, Tuple
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpRequest
from django.db.models import QuerySet

from .models import (
    CustomUser,
    UserProfile,
    ProfileVerification,
    Role,
    PasswordResetRequest,
)


class UserProfileInline(admin.StackedInline):
    """
    Inline admin for displaying and editing user profile details
    within the CustomUser admin panel.
    """
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    fk_name = "user"


class ProfileVerificationInline(admin.StackedInline):
    """
    Inline admin for managing profile verification tokens associated
    with the user in the CustomUser admin panel.
    """
    model = ProfileVerification
    can_delete = False
    verbose_name_plural = "Verification"
    fk_name = "user"
    def get_queryset(self, request: HttpRequest) -> QuerySet[ProfileVerification]:
        """
        Force ProfileVerificationInline to use the authentication shard.
        """
        return super().get_queryset(request).using("authentication_shard")

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Admin panel customization for CustomUser.

    Enhancements include:
    - Search by username, email, and phone number
    - Filters for active, staff, superuser, guest, and profile activation
    - Read-only timestamps for auditing
    - Group and permission management for access control
    - Inline display of UserProfile and ProfileVerification models
    """

    model = CustomUser

    # Fields to display in the admin list view
    list_display: Tuple[str, ...] = (
        "username",
        "email",
        "phone_number",
        "is_active",
        "is_staff",
        "is_superuser",
        "is_guest",
        "activated_profile",
        "created_at"
    )

    # Filters available in the right sidebar
    list_filter: Tuple[str, ...] = (
        "is_active",
        "is_staff",
        "is_superuser",
        "is_guest",
        "activated_profile",
        "created_at"
    )

    # Fields searchable from the search bar
    search_fields: Tuple[str, ...] = ("username", "email", "phone_number")

    # Default ordering of the admin list view
    ordering: Tuple[str] = ("-created_at",)

    # Fields marked as read-only
    readonly_fields: Tuple[str, ...] = ("created_at", "updated_at")

    # Inline panels for linked models
    inlines = (UserProfileInline, ProfileVerificationInline)

    # Field layout in the detail view for existing users
    fieldsets: Tuple[Tuple[Optional[str], dict], ...] = (
        ("Basic Information", {
            "fields": ("username", "email", "phone_number", "password")
        }),
        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "is_guest",
                "activated_profile"
            )
        }),
        ("Groups & Permissions", {
            "fields": ("groups", "user_permissions")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )

    # Field layout when adding a new user
    add_fieldsets: Tuple[Tuple[Optional[str], dict], ...] = (
        ("Create User", {
            "classes": ("wide",),
            "fields": (
                "username",
                "email",
                "phone_number",
                "password1",
                "password2",
                "is_guest",
                "is_active",
                "is_staff",
                "is_superuser",
                "activated_profile"
            )
        }),
    )

    # Horizontal filter box for group and permissions
    filter_horizontal: Tuple[str, ...] = ("groups", "user_permissions")

    def get_queryset(self, request: HttpRequest) -> QuerySet[CustomUser]:
        """
        Return a queryset for all CustomUser objects, explicitly using the 'authentication_shard'
        database to avoid cross-database relation issues in the admin panel.

        Args:
            request (HttpRequest): The incoming admin request.

        Returns:
            QuerySet[CustomUser]: Queryset of all CustomUser instances from authentication_shard.
        """
        return super().get_queryset(request).using("authentication_shard")
    def delete_queryset(self, request: HttpRequest, queryset: QuerySet[CustomUser]) -> None:
        """
        Ensure that deletions of CustomUser and related objects use the authentication shard.
        """
        for obj in queryset:
            # Delete related profiles and verifications explicitly if needed
            UserProfile.objects.using("authentication_shard").filter(user=obj).delete()
            ProfileVerification.objects.using("authentication_shard").filter(user=obj).delete()
            obj.delete(using="authentication_shard")




@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """
    Admin panel configuration for the Role model.

    Supports:
    - Search by role name
    - Sorting by creation timestamp
    - Listing name and description
    """
    list_display: Tuple[str, ...] = ("name", "description", "created_at")
    search_fields: Tuple[str, ...] = ("name",)
    ordering: Tuple[str, ...] = ("-created_at",)
