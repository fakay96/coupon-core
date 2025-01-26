import os

from dotenv import load_dotenv

load_dotenv()
# Determine environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

# Import environment-specific settings
if ENVIRONMENT == "production":
    pass
elif ENVIRONMENT == "staging":
    pass

else:
    pass
