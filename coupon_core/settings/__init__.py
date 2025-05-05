import os
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# Only load environment variables if not in test mode
if os.getenv("DJANGO_SETTINGS_MODULE") != "coupon_core.settings.test":
    load_dotenv()
    # Determine environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
    print(f"ENVIRONMENT: {ENVIRONMENT}")
    # Import environment-specific settings
    from .base import *
    if ENVIRONMENT == "production":
        from .prod import *
    elif ENVIRONMENT == "staging":
        from .staging import *
    else:
        from .dev import *
    
    # Configure Sentry (applies to all environments except test)
    SENTRY_DSN = os.getenv("SENTRY_DSN", "")
    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            traces_sample_rate=1.0 if ENVIRONMENT == "production" else 0.5,  # Adjust sampling
            send_default_pii=True,  # Capture user context in production
            environment=ENVIRONMENT,  # Assign correct environment in Sentry logs
        )
else:
    # In test mode, only import base settings
    # Test settings will be loaded directly by manage.py
    from .base import *
