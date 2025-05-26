"""
URL configuration for the coupon_core project.

The `urlpatterns` list routes URLs to views. This file manages the inclusion of URLs
from various apps and organizes them under a unified structure with the `api/` prefix.

Features:
- All app-specific URLs are included under the `api/` prefix for consistency.
- Static and media file handling is configured for development environments.
- Environment-specific configurations are dynamically loaded.
- Swagger and Redoc endpoints are added to automatically document the API.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from dotenv import load_dotenv

#from utils.health_check import health_check

# Load environment variables
load_dotenv()

from django.http import HttpResponse

def trigger_error(request):
    division_by_zero = 1 / 0
# Import drf-yasg components
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Set up the schema view for Swagger
schema_view = get_schema_view(
    openapi.Info(
        title="Dishpal Core API",
        default_version='v1',
        description="API documentation for the Dishpal Core project",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="fakay96@gmail.com.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# Base URL patterns
urlpatterns = [
    path("admin/", admin.site.urls),  # Admin panel
    # path("healthz/", health_check, name="health-check"),  # Health check endpoint
    path('sentry-debug/', trigger_error),

]

# Mapping of applications to their URL configurations
app_urls = {
    "authentication": "authentication.v1.urls",
    "geodiscounts": "geodiscounts.v1.urls",
}

# Dynamically include all app-specific URLs under the `api/` prefix
for app_name, app_url in app_urls.items():
    if app_name == "geodiscounts":
        urlpatterns += [
            path(f"api/{app_name}/v1/", include(app_url)),  # Use v1 prefix for geodiscounts
        ]
    else:
        urlpatterns += [
            path(f"api/{app_name}/", include(app_url)),  # Keep original prefix for other apps
        ]

# Add Swagger and Redoc endpoints (typically for development)
urlpatterns += [
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]


