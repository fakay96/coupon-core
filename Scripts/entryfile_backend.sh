#!/bin/bash



LOG_FILE="/app/migration_errors.log"

SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(50))')
export SECRET_KEY

# Function to log errors and output
log_and_print() {
  echo "$1" | tee -a "$LOG_FILE"
}

echo "=== Waiting for the database to be ready ==="
while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done
log_and_print "✅ Database is ready."

# Export the database password for PostgreSQL
export PGPASSWORD="$DB_PASSWORD"



# === Function to create a database shard ===
create_database_shard() {
  local shard_name=$1

  log_and_print "🔍 Checking if database shard '$shard_name' exists..."
  psql "host=$DB_HOST port=$DB_PORT dbname=postgres user=$DB_USER sslmode=require" -tAc \
    "SELECT 1 FROM pg_database WHERE datname = '$shard_name'" | grep -q 1

  if [ $? -ne 0 ]; then
    log_and_print "🛠️ Creating database shard '$shard_name'..."
    psql "host=$DB_HOST port=$DB_PORT dbname=postgres user=$DB_USER sslmode=require" -c "CREATE DATABASE $shard_name;"
    if [ $? -eq 0 ]; then
      log_and_print "✅ Database shard '$shard_name' created successfully."
    else
      log_and_print "❌ Failed to create database shard '$shard_name'. Exiting."
      exit 1
    fi
  else
    log_and_print "✅ Database shard '$shard_name' already exists."
  fi
}

# === Function to run migrations for an app on a specific shard ===
run_migrations() {
  local app_name=$1
  local shard_name=$2

  log_and_print "🛠️ Running makemigrations for app: $app_name..."
  python manage.py makemigrations "$app_name" 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    log_and_print "❌ Failed to run makemigrations for app: $app_name. Check $LOG_FILE for details."
    exit 1
  fi

  log_and_print "🛠️ Running migrations for app: $app_name on database: $shard_name..."
  python manage.py migrate "$app_name" --database="$shard_name" 2>&1 | tee -a "$LOG_FILE"
  if [ $? -ne 0 ]; then
    log_and_print "❌ Failed to run migrations for app: $app_name on database: $shard_name. Check $LOG_FILE for details."
    exit 1
  fi
}

# === Define app-to-shard mapping ===
declare -A APPS_SHARDS=(
  ["authentication"]=$AUTHENTICATION_SHARD_DB_NAME
  ["geodiscounts"]=$GEODISCOUNTS_DB_NAME
  ["vectors"]=$VECTOR_DB_NAME
)

# === Ensure all shards are created before running migrations ===
for shard in "${APPS_SHARDS[@]}"; do
  log_and_print "🛠️ Ensuring database shard exists for: $shard..."
  create_database_shard "$shard"
done

# === Run migrations for each app ===
for app in "${!APPS_SHARDS[@]}"; do
  shard=${APPS_SHARDS[$app]}
  log_and_print "🚀 Running migrations for app: $app on database: $shard..."
  run_migrations "$app" "$shard"
done

log_and_print "✅ Shard creation and migrations complete."

# === Collect static files (only in production) ===
log_and_print "📦 Collecting static files..."
python manage.py collectstatic --noinput 2>&1 | tee -a "$LOG_FILE"

# === Start the Django application using Gunicorn ===
log_and_print "🚀 Starting Gunicorn server..."
exec gunicorn coupon_core.wsgi:application --bind 0.0.0.0:8000
