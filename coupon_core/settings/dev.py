"""
Development settings for the coupon_core project.

This module includes configurations for development environments, such as local
database settings, Redis caching, Celery, and S3 storage via LocalStack and DigitalOcean Spaces.

Environment variables are used where applicable to allow for flexibility and
customization during development.

For more details, see:
https://docs.djangoproject.com/en/5.1/topics/settings/
"""

import os
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
# S3 Storage (DigitalOcean Spaces) - Development
# -----------------------------------------------
AWS_S3_ENDPOINT_URL = "https://fra1.digitaloceanspaces.com"  # DigitalOcean Spaces endpoint (Frankfurt)
AWS_ACCESS_KEY_ID = os.getenv("DO_SPACES_ACCESS_KEY_ID", "your-access-key")
AWS_SECRET_ACCESS_KEY = os.getenv("DO_SPACES_SECRET_ACCESS_KEY", "your-secret-key")
AWS_STORAGE_BUCKET_NAME = "dishpal-data"  # DigitalOcean Spaces bucket name

AWS_S3_CUSTOM_DOMAIN = f"https://{AWS_STORAGE_BUCKET_NAME}.fra1.digitaloceanspaces.com"

# Define the `dev/` folder for development assets and media files
DEV_FOLDER = "dev"

# Static files storage (local for development)
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files storage (S3 via DigitalOcean Spaces)
MEDIA_URL = f"{AWS_S3_CUSTOM_DOMAIN}/{DEV_FOLDER}/media/"
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

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
