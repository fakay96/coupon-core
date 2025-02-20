"""
URL patterns for the Authentication app.

This module defines the URL endpoints for authentication-related operations,
including login, registration, guest token generation, token refresh,
user profile management, user registration, and social authentication.

Endpoints:
- LoginView: Authenticates users and returns JWT tokens.
- RegisterView: Handles admin user registration.
- GuestTokenView: Generates tokens for guest users.
- TokenRefreshView: Refreshes JWT access tokens.
- UserInfoView: Retrieves metadata for the authenticated user.
- UserProfileView: Manages user profile operations (retrieve and update).
- UserRegistrationView: Handles registration for guest and new users.
- SocialAuth: Google, Apple, and Twitter authentication endpoints.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from authentication.v1.views.admin_views import LoginView, RegisterView, UserInfoView
from authentication.v1.views.guest_views import GuestTokenView
from authentication.v1.views.userprofile_views import (
    UserProfileView,
    UserRegistrationView,
)
from authentication.v1.views.social_auth_views import (
    GoogleLogin,
    AppleLogin,
    TwitterLogin,
    SocialAuthProviders
)

urlpatterns = [
    # Existing routes
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

    # Social authentication routes
    path("v1/auth/google/", GoogleLogin.as_view(), name="google-login"),
    path("v1/auth/apple/", AppleLogin.as_view(), name="apple-login"),
    path("v1/auth/twitter/", TwitterLogin.as_view(), name="twitter-login"),
    path("v1/auth/providers/", SocialAuthProviders.as_view(), name="social-auth-providers"),
]
