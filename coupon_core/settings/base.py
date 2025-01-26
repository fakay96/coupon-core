"""
Base settings for the coupon_core project.

This module defines the base configuration for the Django project, including
installed apps, middleware, database settings, REST framework configuration,
and storage settings. For environment-specific settings, override these in
settings/dev.py, settings/prod.py, or other environment-specific files.

For more details, see:
https://docs.djangoproject.com/en/5.1/topics/settings/
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

import os
from pathlib import Path

from storages.backends.s3boto3 import S3Boto3Storage

BASE_DIR = Path(__file__).resolve().parent.parent


class S3MediaStorage(S3Boto3Storage):
    """
    Custom S3 storage class for managing media files.

    Media files are stored in a private S3 bucket with no overwrites.
    """

    location = "media"
    default_acl = "private"
    file_overwrite = False


class S3StaticStorage(S3Boto3Storage):
    """
    Custom S3 storage class for managing static files.

    Static files are stored in a public-read S3 bucket with overwrites enabled.
    """

    location = "static"
    default_acl = "public-read"
    file_overwrite = True


STORAGES = {
    "default": {
        "BACKEND": "coupon_core.settings.S3MediaStorage",
    },
    "staticfiles": {
        "BACKEND": "coupon_core.settings.S3StaticStorage",
    },
}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "storages",
    "rest_framework.authtoken",
    "authentication",
    "corsheaders",
    "geodiscounts",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "coupon_core.custom_middlewares.userlocation_middleware.ClientIPMiddleware",
]

ROOT_URLCONF = "coupon_core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "coupon_core.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.MinimumLengthValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.CommonPasswordValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.NumericPasswordValidator"),
    },
]

LANGUAGE_CODE = "en-uk"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL")

AUTH_USER_MODEL = "authentication.CustomUser"

PUBLIC_ENDPOINTS = ["/authentication/api/v1/guest-token/"]


VECTOR_DB = {
    "NAME": os.getenv("PICONE_DBNAME"),
    "DIMENSION": 512,
    "API_KEY": os.getenv("PINECONE_API_KEY", "your-pinecone-api-key"),
    "ENVIRONMENT": os.getenv("PINECONE_ENV", "us-west1-gcp"),
}
