"""
Staging settings for the coupon_core project.

This module includes configurations tailored for the staging environment,
such as connection details for the PostgreSQL database, Redis caching,
RabbitMQ for Celery, and S3 storage via DigitalOcean Spaces.

Environment variables are used to ensure sensitive data and configurations
can be customized per deployment without modifying the source code.

For more details, see:
https://docs.djangoproject.com/en/5.1/topics/settings/
"""

import os
from datetime import timedelta

# Debug
DEBUG = False

# Allowed Hosts
ALLOWED_HOSTS = ["api-staging.dishpal.ai"]

# Secret Key
SECRET_KEY = os.getenv("SECRET_KEY", "staging-secret-key")

# Trust proxy headers to indicate HTTPS.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Optionally enforce HTTPS redirects
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# -----------------------------------------------
# DigitalOcean Spaces Configuration
# -----------------------------------------------
AWS_S3_ENDPOINT_URL = "https://fra1.digitaloceanspaces.com"  # DigitalOcean Spaces endpoint for Frankfurt region
AWS_ACCESS_KEY_ID = os.getenv("DO_SPACES_ACCESS_KEY_ID", "test")  # Your access key
AWS_SECRET_ACCESS_KEY = os.getenv("DO_SPACES_SECRET_ACCESS_KEY", "test")  # Your secret key
AWS_STORAGE_BUCKET_NAME = "dishpal-data"  # DigitalOcean Spaces bucket name

# Define a custom domain for assets
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.fra1.digitaloceanspaces.com"

# Define the `production/` folder for assets and media files
STAGING_FOLDER = "staging"

# Static files storage (for serving CSS, JS, etc.)
STATIC_LOCATION = f"{STAGING_FOLDER}/static"
STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{STATIC_LOCATION}/"
STATICFILES_STORAGE = "custom_storages.StaticStorage"

# Media files storage (for serving uploaded images and other media)
MEDIA_LOCATION = f"{STAGING_FOLDER}/media"
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{MEDIA_LOCATION}/"
DEFAULT_FILE_STORAGE = "custom_storages.MediaStorage"

# Set object ACLs for public access (optional, if required)
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
    "ACL": "public-read",
}

# -----------------------------------------------
# PostgreSQL Database Configuration
# -----------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "default_db"),
        "USER": os.getenv("DB_USER", "user"),
        "PASSWORD": os.getenv("DB_PASSWORD", "password"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "OPTIONS": {
            "sslmode": "require",
        },
    },
    "authentication_shard": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.getenv("AUTHENTICATION_SHARD_DB_NAME"),
        "USER": os.getenv("DB_USER", "user"),
        "PASSWORD": os.getenv("DB_PASSWORD", "password"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "OPTIONS": {
            "sslmode": "require",
        },
    },
    "geodiscounts_db": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.getenv("GEODISCOUNTS_DB_NAME"),
        "USER": os.getenv("DB_USER", "user"),
        "PASSWORD": os.getenv("DB_PASSWORD", "password"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "OPTIONS": {
            "sslmode": "require",
        },
    },
    "vector_db": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.getenv("VECTOR_DB_NAME", "vector_db"),
        "USER": os.getenv("DB_USER", "user"),
        "PASSWORD": os.getenv("DB_PASSWORD", "password"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "OPTIONS": {
            "sslmode": "require",
        },
    },
}

# -----------------------------------------------
# Redis Configuration
# -----------------------------------------------
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "redis_password")
REDIS_PORT = 6379

REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0"

# Caching (Redis)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    },
    "results": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    },
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL




# -----------------------------------------------
# SimpleJWT Authentication Configuration
# -----------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://app-staging.dishpal.ai",
    "https://admin-staging.dishpal.ai",
    "http://0.0.0.0:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http:://192.210.55.154.5173"
]

CELERY_ALWAYS_EAGER=True
FRONTEND_DOMAIN_NAME="https://app-staging.dishpal.ai"

# WebSocket Settings for Staging
WEBSOCKET_PROTOCOL = 'wss'  # Secure WebSocket in staging
WEBSOCKET_DOMAIN = os.getenv('WEBSOCKET_DOMAIN', 'api-staging.dishpal.ai')
WEBSOCKET_PORT = int(os.getenv('WEBSOCKET_PORT', 443))  # Standard HTTPS port
WEBSOCKET_PATH = '/ws/discount-requests/'

# WebSocket Allowed Origins for Staging
WEBSOCKET_ALLOWED_ORIGINS = [
    'https://app-staging.dishpal.ai',
    'https://admin-staging.dishpal.ai',
    'http://0.0.0.0:5173',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://192.210.55.154:5173',
]