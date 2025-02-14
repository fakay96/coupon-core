#!/bin/bash

set -e  # Exit on error

echo "=== Waiting for the database to be ready ==="
while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done
echo "✅ Database is ready."

# Export the database password for PostgreSQL
export PGPASSWORD="$DB_PASSWORD"

# === Find and export the correct GDAL path ===
echo "🔍 Searching for GDAL library..."
GDAL_LIB_PATH=$(find /usr/lib /usr/lib/aarch64-linux-gnu /usr/lib/x86_64-linux-gnu -name "libgdal.so*" 2>/dev/null | head -n 1)

if [ -z "$GDAL_LIB_PATH" ]; then
  echo "❌ GDAL library not found! Exiting."
  exit 1
else
  echo "✅ GDAL found at: $GDAL_LIB_PATH"
  export GDAL_LIBRARY_PATH="$GDAL_LIB_PATH"
  export LD_LIBRARY_PATH="$(dirname "$GDAL_LIB_PATH"):$LD_LIBRARY_PATH"
fi

echo "✅ GDAL_LIBRARY_PATH set to: $GDAL_LIBRARY_PATH"
echo "✅ LD_LIBRARY_PATH set to: $LD_LIBRARY_PATH"

# === Function to create a database shard ===
create_database_shard() {
  local shard_name=$1

  echo "🔍 Checking if database shard '$shard_name' exists..."
  psql "host=$DB_HOST port=$DB_PORT dbname=postgres user=$DB_USER sslmode=require" -tAc \
    "SELECT 1 FROM pg_database WHERE datname = '$shard_name'" | grep -q 1

  if [ $? -ne 0 ]; then
    echo "🛠️ Creating database shard '$shard_name'..."
    psql "host=$DB_HOST port=$DB_PORT dbname=postgres user=$DB_USER sslmode=require" -c "CREATE DATABASE $shard_name;"
    if [ $? -eq 0 ]; then
      echo "✅ Database shard '$shard_name' created successfully."
    else
      echo "❌ Failed to create database shard '$shard_name'. Exiting."
      exit 1
    fi
  else
    echo "✅ Database shard '$shard_name' already exists."
  fi
}

# === Function to run migrations for an app on a specific shard ===
run_migrations() {
  local app_name=$1
  local shard_name=$2

  echo "🛠️ Running makemigrations for app: $app_name..."
  python manage.py makemigrations "$app_name"
  if [ $? -ne 0 ]; then
    echo "❌ Failed to run makemigrations for app: $app_name. Exiting."
    exit 1
  fi

  echo "🛠️ Running migrations for app: $app_name on database: $shard_name..."
  python manage.py migrate "$app_name" --database="$shard_name"
  if [ $? -ne 0 ]; then
    echo "❌ Failed to run migrations for app: $app_name on database: $shard_name. Exiting."
    exit 1
  fi
}

# === Define app-to-shard mapping ===
declare -A APPS_SHARDS=(
  ["authentication"]="authentication_shard"
  ["geodiscounts"]="geodiscounts_db"
)

# === Ensure all shards are created before running migrations ===
for shard in "${APPS_SHARDS[@]}"; do
  echo "🛠️ Ensuring database shard exists for: $shard..."
  create_database_shard "$shard"
done

# === Run migrations for each app ===
for app in "${!APPS_SHARDS[@]}"; do
  shard=${APPS_SHARDS[$app]}
  echo "🚀 Running migrations for app: $app on database: $shard..."
  run_migrations "$app" "$shard"
done

echo "✅ Shard creation and migrations complete."

# === Collect static files (only in production) ===
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

# === Start the Django application using Gunicorn ===
echo "🚀 Starting Gunicorn server..."
exec gunicorn coupon_core.wsgi:application --bind 0.0.0.0:8000
