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
ALLOWED_HOSTS = ["api.dishpal.ai"]

# Secret Key
SECRET_KEY = os.getenv("SECRET_KEY", "production-secret-key")

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
AWS_ACCESS_KEY_ID = os.getenv("DO_SPACES_ACCESS_KEY_ID", "DO801XNLGTYEWHUBBEAP")  # Your access key
AWS_SECRET_ACCESS_KEY = os.getenv("DO_SPACES_SECRET_ACCESS_KEY", "B5d9q33jcImk00jtkF3zJCAKCCEgfKEzJeyuya+uaqI")  # Your secret key
AWS_STORAGE_BUCKET_NAME = "dishpal-data"  # DigitalOcean Spaces bucket name

# Define a custom domain for assets
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.fra1.digitaloceanspaces.com"

# Define the `production/` folder for assets and media files
PRODUCTION_FOLDER = "production"

# Static files storage (for serving CSS, JS, etc.)
STATIC_LOCATION = f"{PRODUCTION_FOLDER}/static"
STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{STATIC_LOCATION}/"
STATICFILES_STORAGE = "custom_storages.StaticStorage"

# Media files storage (for serving uploaded images and other media)
MEDIA_LOCATION = f"{PRODUCTION_FOLDER}/media"
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

# Caching (Redis)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:6379/0",
    },
    "results": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:6379/1",
    },
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:6379/1"],
        },
    },
}

# -----------------------------------------------
# Celery Configuration (RabbitMQ)
# -----------------------------------------------
CELERY_BROKER_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:6379/0"
CELERY_RESULT_BACKEND = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:6379/0"
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# -----------------------------------------------
# Email Backend (Console for Staging)
# -----------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

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
CELERY_ALWAYS_EAGER=True