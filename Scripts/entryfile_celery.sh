#!/bin/bash

# Celery initialization script using Redis as the broker and PostgreSQL as the result backend.
# Configurations are provided through environment variables.

# Load environment variables (if using a .env file)
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Configuration from environment variables
APP_NAME=${CELERY_APP_NAME:-"my_celery_app"}  
REDIS_HOST=${REDIS_HOST:-"localhost"}  
REDIS_PORT=${REDIS_PORT:-6379}  
REDIS_PASSWORD=${REDIS_PASSWORD:-""} 
CELERY_DB=${CELERY_DB:-"test_db"} 
CONCURRENCY=${CELERY_CONCURRENCY:-2} 
LOG_LEVEL=${CELERY_LOG_LEVEL:-"info"}  
LOG_DIR=${CELERY_LOG_DIR:-"./logs"}  
LOG_FILE="$LOG_DIR/celery.log"  

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Dynamically build the Redis Broker URL
if [[ -n "$REDIS_PASSWORD" ]]; then
    BROKER_URL="redis://:$REDIS_PASSWORD@$REDIS_HOST:$REDIS_PORT/0"
else
    BROKER_URL="redis://$REDIS_HOST:$REDIS_PORT/0"
fi

RESULT_BACKEND="django-db"

# Check if Redis is running
echo "🔍 Checking Redis broker at $REDIS_HOST:$REDIS_PORT..."
if ! nc -z "$REDIS_HOST" "$REDIS_PORT"; then
    echo "❌ Error: Redis broker is not running or unreachable at $REDIS_HOST:$REDIS_PORT."
    echo "Please start Redis and try again."
    exit 1
fi
echo "✅ Redis broker is running."

# Ensure PostgreSQL Result Backend is available
echo "🔍 Checking PostgreSQL result backend ($CELERY_DB)..."
DB_HOST=$(echo "$CELERY_DB" | sed -n 's|.*://\([^:/]\+\).*|\1|p')
DB_PORT=$(echo "$CELERY_DB" | sed -n 's|.*:\([0-9]\+\)/.*|\1|p')

if ! nc -z "$DB_HOST" "$DB_PORT"; then
    echo "❌ Error: PostgreSQL backend is not running or unreachable at $DB_HOST:$DB_PORT."
    echo "Please start PostgreSQL and try again."
    exit 1
fi
echo "✅ PostgreSQL backend is running."

# Start Celery worker with Redis as the broker and PostgreSQL as result backend
echo "🚀 Starting Celery worker..."
celery -A $APP_NAME worker \
    --broker="$BROKER_URL" \
    --loglevel=$LOG_LEVEL \
    --concurrency=$CONCURRENCY \
    --logfile=$LOG_FILE &

# Check if Celery started successfully
if [ $? -eq 0 ]; then
    echo "✅ Celery worker started successfully with $CONCURRENCY workers."
    echo "📄 Logs are being written to $LOG_FILE"
else
    echo "❌ Failed to start Celery worker."
    exit 1
fi
