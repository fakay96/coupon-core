"""
Staging settings for the coupon_core project.

This module includes configurations tailored for the staging environment,
such as connection details for the PostgreSQL database, Redis caching,
RabbitMQ for Celery, and S3 storage via LocalStack.

Environment variables are used to ensure sensitive data and configurations
can be customized per deployment without modifying the source code.

For more details, see:
https://docs.djangoproject.com/en/5.1/topics/settings/
"""

import os
from datetime import timedelta

# Debug
DEBUG = True


ALLOWED_HOSTS = ["api-staging.dishpal.ai"]

CORS_ALLOW_ALL_ORIGINS = True

# Secret Key
SECRET_KEY = os.getenv("SECRET_KEY", "staging-secret-key")

# Trust proxy headers to indicate HTTPS.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Optionally enforce HTTPS redirects
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# LocalStack S3 Configuration
AWS_S3_ENDPOINT_URL = os.getenv("LOCALSTACK_S3_ENDPOINT_EXTERNAL")
AWS_S3_ENDPOINT_URL_INTERNAL = os.getenv("LOCALSTACK_S3_ENDPOINT")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "test")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "test")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "election-system-dev")
AWS_S3_CUSTOM_DOMAIN = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}"

# Static files storage (S3 via LocalStack)
STATIC_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/static/"
STATICFILES_STORAGE = "storages.backends.s3boto3.S3StaticStorage"
STATIC_ROOT = f"{AWS_S3_ENDPOINT_URL_INTERNAL}/{AWS_STORAGE_BUCKET_NAME}/static/"

# Media files storage (S3 via LocalStack)
MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/media/"
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

# PostgreSQL Database
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
        "NAME": "authentication_shard",
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
        "NAME": os.getenv("GEODISCOUNTS_DB_NAME", "geodiscounts_db"),
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
        "NAME": os.getenv("VECTOR_DBNAME", "vector_db"),
        "USER": os.getenv("DB_USER", "user"),
        "PASSWORD": os.getenv("DB_PASSWORD", "password"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "OPTIONS": {
            "sslmode": "require",
        },
    },
}

# Credentials for Redis service
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

# Celery settings (RabbitMQ as the broker)
CELERY_BROKER_URL = (
    f"amqp://{os.getenv('DEV_RABBITMQ_USER', 'guest')}:"
    f"{os.getenv('DEV_RABBITMQ_PASSWORD', 'guest')}@"
    f"{os.getenv('DEV_RABBITMQ_HOST', 'localhost')}:5672/"
)

# Email backend (console for staging)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# SimpleJWT Configuration
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
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
