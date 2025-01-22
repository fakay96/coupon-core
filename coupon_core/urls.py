"""
URL configuration for coupon_core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from dotenv import load_dotenv

load_dotenv()

# Base URL patterns
urlpatterns = [
    path("admin/", admin.site.urls),
]

# Mapping of applications to their URL configurations
app_urls = {
    "authentication": "authentication.v1.urls",
}

# Include all app URLs
for app_name, app_url in app_urls.items():
    urlpatterns += [
        path(f"{app_name}/", include(app_url)),
    ]

# Add static and media URL patterns for development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
