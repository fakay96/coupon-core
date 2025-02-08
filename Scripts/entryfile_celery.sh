#!/bin/bash

# Simplified Celery initialization script with RabbitMQ as the broker
# All configurations are provided through environment variables.

# Load environment variables (optional: if using a .env file)
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Configuration from environment variables
APP_NAME=${CELERY_APP_NAME:-"my_celery_app"}  # Default to "my_celery_app" if not set
BROKER_URL=${CELERY_BROKER_URL:-"amqp://guest:guest@localhost:5672//"}  # Default RabbitMQ URL
CONCURRENCY=${CELERY_CONCURRENCY:-2}  # Default to 2 workers if not set
LOG_LEVEL=${CELERY_LOG_LEVEL:-"info"}  # Default log level is "info"
LOG_DIR=${CELERY_LOG_DIR:-"./logs"}  # Directory for logs
LOG_FILE="$LOG_DIR/celery.log"  # Log file path

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Check if RabbitMQ broker is running
BROKER_HOST=$(echo "$BROKER_URL" | sed -n 's|.*://.*@\(.*\):.*|\1|p')  
BROKER_PORT=$(echo "$BROKER_URL" | sed -n 's|.*://.*:\(.*\)/.*|\1|p') 

echo "Checking RabbitMQ broker at $BROKER_HOST:$BROKER_PORT..."
if ! nc -z "$BROKER_HOST" "$BROKER_PORT"; then
    echo "Error: RabbitMQ broker is not running or unreachable at $BROKER_HOST:$BROKER_PORT."
    echo "Please start RabbitMQ and try again."
    exit 1
fi

echo "RabbitMQ broker is running. Starting Celery worker..."

# Start Celery worker
celery -A $APP_NAME worker \
    --loglevel=$LOG_LEVEL \
    --concurrency=$CONCURRENCY \
    --logfile=$LOG_FILE &

# Check if Celery started successfully
if [ $? -eq 0 ]; then
    echo "Celery worker started successfully with $CONCURRENCY workers."
    echo "Logs are being written to $LOG_FILE"
else
    echo "Failed to start Celery worker."
    exit 1
fi
