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

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "module": "%(module)s", "process": "%(process)d", "thread": "%(thread)d"}',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['require_debug_true'],
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'coupon_core.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'error.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'json_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'json.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'json',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
            'filters': ['require_debug_false'],
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'error_file', 'mail_admins'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'authentication': {
            'handlers': ['console', 'file', 'error_file', 'json_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'geodiscounts': {
            'handlers': ['console', 'file', 'error_file', 'json_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# WebSocket Settings
WEBSOCKET_PROTOCOL = 'ws'  # Default to ws, will be overridden in prod/staging
WEBSOCKET_DOMAIN = 'localhost'  # Default to localhost, will be overridden in prod/staging
WEBSOCKET_PORT = 8000  # Default port, will be overridden in prod/staging
WEBSOCKET_PATH = '/ws/discount-requests/'  # Default path for WebSocket connections

# WebSocket Allowed Origins
WEBSOCKET_ALLOWED_ORIGINS = []  # Will be overridden in prod/staging

# WebSocket Connection Settings
WEBSOCKET_HEARTBEAT_INTERVAL = 30  # Seconds between heartbeat messages
WEBSOCKET_MAX_MESSAGE_SIZE = 1024 * 1024  # 1MB default max message size

