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

GDAL_LIBRARY_PATH = os.getenv("GDAL_LIBRARY_PATH", "/usr/lib/libgdal.so")


BASE_DIR = Path(__file__).resolve().parent.parent






INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "rest_framework",
    "storages",
    "rest_framework.authtoken",
    "authentication",
    "corsheaders",
    "geodiscounts",
    "drf_yasg",
    # Social authentication apps
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.apple",
    "allauth.socialaccount.providers.twitter",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    
    #celery apps
    "django_celery_results"
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "allauth.account.middleware.AccountMiddleware",  
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "coupon_core.custom_middlewares.userlocation_middleware.UserLocationMiddleware",
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
    "NAME": os.getenv("MILVUS_COLLECTION_NAME", "default_vector_collection"),
    "DIMENSION": int(os.getenv("VECTOR_DIMENSION", 512)),
    "HOST": os.getenv("MILVUS_HOST", "localhost"),
    "PORT": os.getenv("MILVUS_PORT", "19530"),
}
DATABASE_ROUTERS = [
    "authentication.routers.AuthenticationRouter",
    "geodiscounts.routers.GeoDiscountsRouter"
]


SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
         'Bearer': {
             'type': 'apiKey',
             'name': 'Authorization',
             'in': 'header'
         }
    },
}

# Social authentication settings
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "key": "",
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
    },
    "apple": {
        "APP": {
            "client_id": os.getenv("APPLE_CLIENT_ID"),
            "secret": os.getenv("APPLE_CLIENT_SECRET"),
            "key": os.getenv("APPLE_KEY_ID"),
            "team_id": os.getenv("APPLE_TEAM_ID"),
        },
        "SCOPE": ["email", "name"],
    },
    "twitter": {
        "APP": {
            "client_id": os.getenv("TWITTER_CLIENT_ID"),
            "secret": os.getenv("TWITTER_CLIENT_SECRET"),
        },
        "SCOPE": ["email", "profile"],
    },
}

# Rest auth settings
REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_COOKIE": "jwt-auth",
    "JWT_AUTH_REFRESH_COOKIE": "jwt-refresh-auth",
    "SESSION_LOGIN": False,
}

STORAGES={
    'default': {
        'BACKEND': 'coupon_core.settings.custom_storages.S3MediaStorage',
    },
    'staticfiles': {
        'BACKEND': 'coupon_core.settings.custom_storages.StaticStorage',
        },
}

BASE_DOMAIN=os.getenv("BASE_DOMAIN")


EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("DISHPAL_EMAIL")
EMAIL_HOST_PASSWORD = os.getenv("DISHPAL_EMAIL_PASSWORD")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Redis Configuration
REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', 6379)),
    'db': int(os.getenv('REDIS_DB', 0)),
    'password': os.getenv('REDIS_PASSWORD', None),
    'channel_prefix': os.getenv('REDIS_CHANNEL_PREFIX', 'discount_request_'),
    'request_channel': os.getenv('REDIS_REQUEST_CHANNEL', 'discount_crawler_requests'),
}

# Caching (Redis)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://:{REDIS_CONFIG['password']}@{REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}/{REDIS_CONFIG['db']}",
    },
    "results": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://:{REDIS_CONFIG['password']}@{REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}/1",
    },
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [f"redis://:{REDIS_CONFIG['password']}@{REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}/1"],
        },
    },
}