#!/bin/sh

echo "Waiting for the database..."
while ! nc -z $DB_HOST 5432; do
  sleep 1
done
echo "Database is ready."


# Execute the original command
exec "$@"
