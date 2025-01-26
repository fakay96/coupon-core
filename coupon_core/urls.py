"""
URL configuration for the coupon_core project.

The `urlpatterns` list routes URLs to views. This file manages the inclusion of URLs
from various apps and organizes them under a unified structure with the `api/` prefix.

Features:
- All app-specific URLs are included under the `api/` prefix for consistency.
- Static and media file handling is configured for development environments.
- Environment-specific configurations are dynamically loaded.

For more information, see:
- https://docs.djangoproject.com/en/5.1/topics/http/urls/

Routes:
- `/admin/`: Admin site for managing the project.
- `/api/authentication/`: Routes for authentication-related operations.
- `/api/geodiscounts/`: Routes for geodiscounts-related operations.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base URL patterns
urlpatterns = [
    path("admin/", admin.site.urls),  # Admin panel
]

# Mapping of applications to their URL configurations
app_urls = {
    "authentication": "authentication.v1.urls",
    "geodiscounts": "geodiscounts.v1.urls",
}

# Dynamically include all app-specific URLs under the `api/` prefix
for app_name, app_url in app_urls.items():
    urlpatterns += [
        path(f"api/{app_name}/", include(app_url)),  # Add `api/` prefix
    ]

# Static and media file handling for development
if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )  # Serve static files
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )  # Serve media files
