#!/bin/bash
set -e  # Exit on error

echo "Running service type: $SERVICE_TYPE"

if [ "$SERVICE_TYPE" = "backend" ]; then
    exec /app/entryfile_backend.sh
elif [ "$SERVICE_TYPE" = "celery" ]; then
    exec /app/entryfile_celery.sh
else
    echo " ERROR: Unknown service type '$SERVICE_TYPE'. Use 'backend' or 'celery'."
    exit 1
fi
