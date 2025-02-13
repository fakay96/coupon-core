#!/bin/bash

# Wait for the database to be ready
echo "Waiting for the database..."
while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done
echo "Database is ready."

# Export the database password for PostgreSQL
export PGPASSWORD="$DB_PASSWORD"

# Function to create a database shard
create_database_shard() {
  local shard_name=$1

  echo "Checking if database shard '$shard_name' exists..."
  psql "postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/postgres?sslmode=require" -tAc "SELECT 1 FROM pg_database WHERE datname = '$shard_name'" | grep -q 1
  if [ $? -ne 0 ]; then
    echo "Database shard '$shard_name' does not exist. Creating..."
    psql "postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/postgres?sslmode=require" -c "CREATE DATABASE $shard_name;"
    if [ $? -eq 0 ]; then
      echo "Database shard '$shard_name' created successfully."
    else
      echo "Failed to create database shard '$shard_name'. Exiting."
      exit 1
    fi
  else
    echo "Database shard '$shard_name' already exists."
  fi
}

# Function to run migrations for an app on a specific shard
run_migrations() {
  local app_name=$1
  local shard_name=$2

  echo "Running makemigrations for app: $app_name..."
  python manage.py makemigrations "$app_name"
  if [ $? -ne 0 ]; then
    echo "Failed to run makemigrations for app: $app_name. Exiting."
    exit 1
  fi

  echo "Running migrations for app: $app_name on database: $shard_name..."
  python manage.py migrate "$app_name" --database="$shard_name"
  if [ $? -ne 0 ]; then
    echo "Failed to run migrations for app: $app_name on database: $shard_name. Exiting."
    exit 1
  fi
}

# List of apps and their corresponding database shards
declare -A APPS_SHARDS=(
  ["authentication"]="authentication_shard"
  ["geodiscounts"]="geodiscounts_db"
)

# Ensure all shards are created before running migrations
for shard in "${APPS_SHARDS[@]}"; do
  echo "Ensuring database shard exists for: $shard..."
  create_database_shard "$shard"
done

# Run migrations for each app
for app in "${!APPS_SHARDS[@]}"; do
  shard=${APPS_SHARDS[$app]}
  echo "Starting migrations for app: $app on database: $shard..."
  run_migrations "$app" "$shard"
done

echo "Shard creation and migrations complete."

# If in development environment, collect static files
if [ "$ENVIRONMENT" = "development" ]; then
  echo "Environment is development. Collecting static files..."
  python manage.py collectstatic --noinput
else
  echo "Environment is not development. Skipping collectstatic."
fi

exec gunicorn coupon_core.wsgi:application \
    --bind=0.0.0.0:8000 \
    --workers=3 \
    --timeout=120 \
    --log-level=info \
    --access-logfile=- \
    --error-logfile=-
