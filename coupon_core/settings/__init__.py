import os

from dotenv import load_dotenv

load_dotenv()
# Determine environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
# Import environment-specific settings
from .base import *
if ENVIRONMENT == "production":
    from .prod import *
elif ENVIRONMENT == "staging":
    from .staging import *
    
else:
   from .dev import *
