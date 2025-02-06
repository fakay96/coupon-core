"""
Development settings for the coupon_core project.

This module includes configurations for development environments, such as local
database settings, Redis caching, Celery, and S3 storage via LocalStack.

Environment variables are used where applicable to allow for flexibility and
customization during development.

For more details, see:
https://docs.djangoproject.com/en/5.1/topics/settings/
"""

import os
from datetime import timedelta

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent

# Debug
DEBUG = True

# Allowed Hosts
ALLOWED_HOSTS = ["*"]


# Secret Key
SECRET_KEY = "django-insecure-%x0jerw1u3b91t_$!f22v@lh4=he(*t$&wf+y%%7w@ub+s68^c"

# LocalStack S3 Configuration
AWS_S3_ENDPOINT_URL = os.getenv("LOCALSTACK_S3_ENDPOINT_EXTERNAL")
AWS_S3_ENDPOINT_URL_INTERNAL = os.getenv("LOCALSTACK_S3_ENDPOINT")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "test")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "test")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "election-system-dev")
AWS_S3_CUSTOM_DOMAIN = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}"

# Static files storage (S3 via LocalStack)
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]  # Optional: additional static directories
STATIC_ROOT = BASE_DIR / "staticfiles"

# PostgreSQL Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "default_db"),
        "USER": os.getenv("DB_USER", "user"),
        "PASSWORD": os.getenv("DB_PASSWORD", "password"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    },
    "authentication_shard": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": "authentication_shard",
        "USER": os.getenv("DB_USER", "user"),
        "PASSWORD": os.getenv("DB_PASSWORD", "password"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    },
    "geodiscounts_db": {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        "NAME": os.getenv("GEODISCOUNTS_DB_NAME", "geodiscounts_db"),
        "USER": os.getenv("DB_USER", "user"),
        "PASSWORD": os.getenv("DB_PASSWORD", "password"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    },
}

# Credentials for Redis service
REDIS_HOST = os.getenv("DEV_REDIS_HOST", "localhost")
REDIS_PASSWORD = os.getenv("DEV_REDIS_PASS", "redis_password")
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

# Email backend (console for development)
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

# Database Routers


# CORS Configuration
# CORS_ALLOWED_ORIGINS = [
#     "http://localhost:3000",
#     "http://user.localhost",
#     "http://admin.localhost",
#     "http://localhost:3001",
# ]

CORS_ALLOW_ALL_ORIGINS = True
