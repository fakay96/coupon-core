#!/bin/bash

# Define log directory and file
LOG_DIR="/var/log/celery"
LOG_FILE="$LOG_DIR/celery_worker.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Start Celery Worker with a fixed concurrency of 2 and log output to a file
echo "🚀 Starting Celery worker..."
celery -A "$CELERY_APP_NAME" worker \
    --loglevel="${CELERY_LOG_LEVEL:-info}" \
    --concurrency=2 \
    --logfile="$LOG_FILE" 2>&1 | tee -a "$LOG_FILE"
