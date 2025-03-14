"""
Development settings for the coupon_core project.

This module includes configurations for development environments, such as local
database settings, Redis caching, Celery, and S3 storage via DigitalOcean Spaces.

Environment variables are used where applicable to allow for flexibility and
customization during development.

For more details, see:
https://docs.djangoproject.com/en/5.1/topics/settings/
"""

import os
import logging
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Debug
DEBUG = True

# Allowed Hosts (Allow all for development)
ALLOWED_HOSTS = ["*"]

# Secret Key (For development only)
SECRET_KEY = "django-insecure-%x0jerw1u3b91t_$!f22v@lh4=he(*t$&wf+y%%7w@ub+s68^c"

# -----------------------------------------------
# Static Files Configuration
# -----------------------------------------------
# Local path for collectstatic to gather files before uploading

# -----------------------------------------------
# S3 Storage (DigitalOcean Spaces) - Development
# -----------------------------------------------
# Core AWS/DigitalOcean Spaces settings
AWS_S3_ENDPOINT_URL = "https://fra1.digitaloceanspaces.com"  # Use the regional endpoint
AWS_S3_REGION_NAME = "fra1"  # Match the region of your Space
AWS_ACCESS_KEY_ID = os.getenv("DO_SPACES_ACCESS_KEY_ID", "test")  # Your access key
AWS_SECRET_ACCESS_KEY = os.getenv("DO_SPACES_SECRET_ACCESS_KEY", "test")  # Your secret key
AWS_STORAGE_BUCKET_NAME = "dishpal-data"  # Your bucket name

# Proper domain format without https:// prefix
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.fra1.digitaloceanspaces.com"

# Define the `dev/` folder for development assets and media files
DEV_FOLDER = "dev"
STATIC_LOCATION = f"{DEV_FOLDER}/static"
MEDIA_LOCATION = f"{DEV_FOLDER}/media"

# URL patterns (with https:// explicitly added)
STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{STATIC_LOCATION}/"
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{MEDIA_LOCATION}/"

# Storage backends - use custom storage classes
STATICFILES_STORAGE = "custom_storages.StaticStorage"
DEFAULT_FILE_STORAGE = "custom_storages.MediaStorage"

# Cache control and object parameters
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
}

# Enable boto3 logging for debugging (comment out in production)
logging.basicConfig(level=logging.INFO)

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
    "vector_db": {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        "NAME": os.getenv("VECTOR_DBNAME", "vector_db"),
        "USER": os.getenv("DB_USER", "user"),
        "PASSWORD": os.getenv("DB_PASSWORD", "password"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    },
}

# -----------------------------------------------
# Redis Configuration
# -----------------------------------------------
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

# -----------------------------------------------
# Celery Configuration (RabbitMQ)
# -----------------------------------------------
CELERY_BROKER_URL = (
    f"amqp://{os.getenv('DEV_RABBITMQ_USER', 'guest')}:" 
    f"{os.getenv('DEV_RABBITMQ_PASSWORD', 'guest')}@"
    f"{os.getenv('DEV_RABBITMQ_HOST', 'localhost')}:5672/"
)

# -----------------------------------------------
# Email Backend (Console for Development)
# -----------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# -----------------------------------------------
# SimpleJWT Authentication Configuration
# -----------------------------------------------
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

# -----------------------------------------------
# CORS Configuration
# -----------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True