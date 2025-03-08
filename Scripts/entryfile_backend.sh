#!/usr/bin/env bash
set -e  # Exit on critical errors

LOG_FILE="/app/migration_errors.log"
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(50))')
export SECRET_KEY

########################
# 1) Logging Function  #
########################
log_and_print() {
  local timestamp
  timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo "[$timestamp] $1" | tee -a "$LOG_FILE"
}

########################
# 2) Validate Environment Variables #
########################
REQUIRED_VARS=("DB_HOST" "DB_PORT" "DB_USER" "DB_PASSWORD" "DB_NAME" "AUTHENTICATION_SHARD_DB_NAME" "GEODISCOUNTS_DB_NAME" "VECTOR_DB_NAME")

for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    log_and_print "❌ ERROR: Environment variable $var is not set."
    exit 1
  fi
done

########################
# 3) Wait for Database #
########################
TIMEOUT=60
elapsed=0
log_and_print "=== Waiting for the database to be ready on $DB_HOST:$DB_PORT ==="

while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
  elapsed=$((elapsed + 1))
  if [ "$elapsed" -ge "$TIMEOUT" ]; then
    log_and_print "❌ ERROR: Database did not become ready within $TIMEOUT seconds."
    exit 1
  fi
done
log_and_print "✅ Database is ready."

# Export password so psql won't prompt
export PGPASSWORD="$DB_PASSWORD"

######################################
# 4) Create Databases if Necessary   #
######################################
create_database_if_missing() {
  local db_name="$1"

  log_and_print "🔍 Checking if database '$db_name' exists..."
  if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$db_name'" | grep -q 1; then
    log_and_print "🛠️ Creating database '$db_name'..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE $db_name;"
    log_and_print "✅ Created database '$db_name'."
  else
    log_and_print "✅ Database '$db_name' already exists."
  fi
}

create_database_if_missing "$DB_NAME"
create_database_if_missing "$AUTHENTICATION_SHARD_DB_NAME"
create_database_if_missing "$GEODISCOUNTS_DB_NAME"
create_database_if_missing "$VECTOR_DB_NAME"

################################################
# 5) Run Migrations in Order on Authentication Shard  #
################################################
AUTH_APPS=("contenttypes" "auth" "admin" "authtoken" "authentication" "sessions","socialaccount","account")

log_and_print "🛠️ Running migrations on authentication_shard..."
migration_errors=0

for APP in "${AUTH_APPS[@]}"
do
    log_and_print "🚀 Migrating $APP on authentication_shard..."
    if ! python manage.py migrate "$APP" --database=authentication_shard 2>&1 | tee -a "$LOG_FILE"; then
        log_and_print "❌ ERROR: Migration failed for $APP. Exiting..."
        migration_errors=$((migration_errors + 1))
    fi
done

if [ "$migration_errors" -gt 0 ]; then
  log_and_print "❌ Some authentication migrations failed. Check $LOG_FILE for details."
  exit 1
fi

log_and_print "✅ Authentication shard migrations completed successfully!"

################################################
# 6) Run Migrations for Geodiscounts           #
################################################
GEODISCOUNTS_APPS=("geodiscounts")

log_and_print "🛠️ Running migrations on geodiscounts_db..."
migration_errors=0

for APP in "${GEODISCOUNTS_APPS[@]}"
do
    log_and_print "🚀 Migrating $APP on geodiscounts_db..."
    if ! python manage.py migrate "$APP" --database=geodiscounts_db 2>&1 | tee -a "$LOG_FILE"; then
        log_and_print "❌ ERROR: Migration failed for $APP. Exiting..."
        migration_errors=$((migration_errors + 1))
    fi
done

if [ "$migration_errors" -gt 0 ]; then
  log_and_print "❌ Some geodiscounts migrations failed. Check $LOG_FILE for details."
  exit 1
fi

log_and_print "✅ Geodiscounts migrations completed successfully!"

################################
# 7) Collect Static Files      #
################################
log_and_print "📦 Collecting static files..."
python manage.py collectstatic --noinput 2>&1 | tee -a "$LOG_FILE"

########################################
# 8) Start the Django App (Gunicorn)   #
########################################
log_and_print "🚀 Starting Gunicorn server..."
exec gunicorn coupon_core.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --threads 1 \
  --timeout 120
