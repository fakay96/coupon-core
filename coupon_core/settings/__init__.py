import os
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# Load environment variables from a .env file
load_dotenv()

# Determine the current environment (defaults to 'development')
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

# Import base settings
from .base import *

# Import environment-specific settings
if ENVIRONMENT == "production":
    from .prod import *
elif ENVIRONMENT == "staging":
    from .staging import *
else:
    from .dev import *

# Configure Sentry (applies to all environments)
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0 if ENVIRONMENT == "production" else 0.5,  # Adjust sampling
        send_default_pii=True,  # Capture user context in production
        environment=ENVIRONMENT,  # Assign correct environment in Sentry logs
    )
