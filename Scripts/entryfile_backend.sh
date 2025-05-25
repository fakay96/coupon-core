#!/usr/bin/env bash
set -e  # Exit on critical errors

##################################
# 1) Define Directories & Files  #
##################################
LOG_DIR="/app/logs"
LOG_FILE="$LOG_DIR/migration.log"
ACCESS_LOG="$LOG_DIR/gunicorn_access.log"
ERROR_LOG="$LOG_DIR/gunicorn_error.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Ensure log files exist
touch "$LOG_FILE" "$ACCESS_LOG" "$ERROR_LOG"

##################################
# 2) Logging Function            #
##################################
log_and_print() {
  local timestamp
  timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo "[$timestamp] $1" | tee -a "$LOG_FILE"
}

##################################
# 3) Validate Environment Variables #
##################################
REQUIRED_VARS=("DB_HOST" "DB_PORT" "DB_USER" "DB_PASSWORD" "DB_NAME" 
               "AUTHENTICATION_SHARD_DB_NAME" "GEODISCOUNTS_DB_NAME" 
               "VECTOR_DB_NAME")

for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    log_and_print "❌ ERROR: Environment variable $var is not set."
    exit 1
  fi
done

##################################
# 4) Wait for Database to be Ready #
##################################
TIMEOUT=60
elapsed=0
log_and_print "⏳ Waiting for the database to be ready on $DB_HOST:$DB_PORT..."

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

##################################
# 5) Create Databases if Necessary #
##################################
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

#########################################
# 6) Run Migrations on Authentication Shard #
#########################################
AUTH_APPS=("contenttypes" "auth" "admin" "authtoken" "authentication" "sessions" "socialaccount" "account")

log_and_print "🛠️ Running migrations on authentication_shard..."
migration_errors=0

for APP in "${AUTH_APPS[@]}"; do
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

#########################################
# 7) Run Migrations for Geodiscounts    #
#########################################
GEODISCOUNTS_APPS=("geodiscounts")

log_and_print "🛠️ Running migrations on geodiscounts_db..."
migration_errors=0

for APP in "${GEODISCOUNTS_APPS[@]}"; do
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

############################################
# 8) Run Migrations for Django Celery Results #
############################################
log_and_print "🛠️ Running migrations for django_celery_results..."
if ! python manage.py migrate django_celery_results 2>&1 | tee -a "$LOG_FILE"; then
  log_and_print "❌ ERROR: Migration failed for django_celery_results. Exiting..."
  exit 1
fi
log_and_print "✅ Django Celery Results migrations completed successfully!"

log_and_print "🛠️ Running migrations for django_celery_beat..."
if ! python manage.py migrate django_celery_beat 2>&1 | tee -a "$LOG_FILE"; then
  log_and_print "❌ ERROR: Migration failed for django_celery_beat. Exiting..."
  exit 1
fi
log_and_print "✅ Django Celery Results migrations completed successfully!"
################################
# 9) Collect Static Files      #
################################
log_and_print "📦 Collecting static files..."
python manage.py collectstatic --noinput 2>&1 | tee -a "$LOG_FILE"

########################################
# 10) Start the Django App (Gunicorn)  #
########################################
log_and_print "🚀 Starting Gunicorn server with logging..."

exec gunicorn coupon_core.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --threads 1 \
  --timeout 120 \
  --graceful-timeout 120 \
  --access-logfile "$ACCESS_LOG" \
  --error-logfile "$ERROR_LOG"

