"""
URL patterns for the Authentication app.

This module defines the URL endpoints for authentication-related operations,
including login, registration, guest token generation, token refresh,
user profile management, and user registration.

Endpoints:
- LoginView: Authenticates users and returns JWT tokens.
- RegisterView: Handles admin user registration.
- GuestTokenView: Generates tokens for guest users.
- TokenRefreshView: Refreshes JWT access tokens.
- UserInfoView: Retrieves metadata for the authenticated user.
- UserProfileView: Manages user profile operations (retrieve and update).
- UserRegistrationView: Handles registration for guest and new users.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from authentication.v1.views.admin_views import (LoginView, RegisterView,
                                                 UserInfoView)
from authentication.v1.views.guest_views import GuestTokenView
from authentication.v1.views.userprofile_views import (UserProfileView,
                                                       UserRegistrationView)

urlpatterns = [
    path("v1/login/", LoginView.as_view(), name="login"),
    path("v1/register/", RegisterView.as_view(), name="register"),
    path("v1/guest-token/", GuestTokenView.as_view(), name="guest-token"),
    path("v1/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("v1/user-info/", UserInfoView.as_view(), name="user-info"),
    path("v1/user-profile/", UserProfileView.as_view(), name="user-profile"),
    path(
        "v1/user-registration/",
        UserRegistrationView.as_view(),
        name="user-registration",
    ),
]
