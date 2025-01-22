"""
URL patterns for the Authentication app.

This module defines the URL endpoints for authentication-related operations,
including login, registration, guest token generation, token refresh, and
retrieval of user information.

Endpoints:
- LoginView: Authenticates users and returns JWT tokens.
- RegisterView: Handles admin user registration.
- GuestTokenView: Generates tokens for guest users.
- TokenRefreshView: Refreshes JWT access tokens.
- UserInfoView: Retrieves metadata for the authenticated user.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from authentication.v1.views.admin_views import LoginView, RegisterView, UserInfoView
from authentication.v1.views.guest_views import GuestTokenView

urlpatterns = [
    path("api/v1/login/", LoginView.as_view(), name="login"),
    path("api/v1/register/", RegisterView.as_view(), name="register"),
    path("api/v1/guest-token/", GuestTokenView.as_view(), name="guest-token"),
    path(
        "api/v1/token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh"),
    path("api/v1/user-info/", UserInfoView.as_view(), name="user-info"),
]
