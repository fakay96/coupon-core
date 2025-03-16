#!/bin/bash

# Start Celery Worker with a fixed concurrency of 2
echo "🚀 Starting Celery worker..."
celery -A "$CELERY_APP_NAME" worker --loglevel="${CELERY_LOG_LEVEL:-info}" --concurrency=2
