#!/bin/bash

echo "Waiting for the database..."
while ! nc -z $DB_HOST 5432; do
  sleep 1
done
echo "Database is ready."

# Export the database password for PostgreSQL
export PGPASSWORD=$DEV_DB_PASSWORD

# Function to create a database shard
create_database_shard() {
  local shard_name=$1

  echo "Checking if database shard '$shard_name' exists..."
  psql -h $DB_HOST -U $DB_USER -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$shard_name'" | grep -q 1
  if [ $? -ne 0 ]; then
    echo "Database shard '$shard_name' does not exist. Creating..."
    psql -h $DB_HOST -U $DB_USER -d postgres -c "CREATE DATABASE $shard_name;"
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
  python manage.py makemigrations $app_name
  if [ $? -ne 0 ]; then
    echo "Failed to run makemigrations for app: $app_name. Exiting."
    exit 1
  fi

  echo "Running migrations for app: $app_name on database: $shard_name..."
  python manage.py migrate $app_name --database=$shard_name
  if [ $? -ne 0 ]; then
    echo "Failed to run migrations for app: $app_name on database: $shard_name. Exiting."
    exit 1
  fi
}

# List of apps and their corresponding database shards
declare -A APPS_SHARDS
APPS_SHARDS=(
  ["authentication"]="authentication_shard"

)

# Ensure all shards are created before running migrations
for SHARD in "${APPS_SHARDS[@]}"; do
  echo "Ensuring database shard exists for: $SHARD..."
  create_database_shard $SHARD
done

# Run migrations for each app
for APP in "${!APPS_SHARDS[@]}"; do
  SHARD=${APPS_SHARDS[$APP]}
  echo "Starting migrations for app: $APP on database: $SHARD..."
  run_migrations $APP $SHARD
done

echo "Shard creation and migrations complete."
exec "$@"
