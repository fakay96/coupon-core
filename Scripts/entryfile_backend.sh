#!/usr/bin/env bash
set -e  # Exit on any error

LOG_FILE="/app/migration_errors.log"
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(50))')
export SECRET_KEY

########################
# 1) Logging Function  #
########################
log_and_print() {
  echo "$1" | tee -a "$LOG_FILE"
}

########################
# 2) Wait for Database #
########################
echo "=== Waiting for the database to be ready on $DB_HOST:$DB_PORT ==="
until nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done
log_and_print "✅ Database is ready."

# Export password so psql won't prompt
export PGPASSWORD="$DB_PASSWORD"

######################################
# 3) Create Databases if Necessary   #
######################################
# Actual PostgreSQL database names come from environment variables

create_database_if_missing() {
  local db_name="$1"

  log_and_print "🔍 Checking if database '$db_name' exists..."
  if ! psql "host=$DB_HOST port=$DB_PORT dbname=postgres user=$DB_USER sslmode=require" \
      -tAc "SELECT 1 FROM pg_database WHERE datname = '$db_name'" | grep -q 1; then
    log_and_print "🛠️ Creating database '$db_name'..."
    psql "host=$DB_HOST port=$DB_PORT dbname=postgres user=$DB_USER sslmode=require" \
      -c "CREATE DATABASE $db_name;"
    log_and_print "✅ Created database '$db_name'."
  else
    log_and_print "✅ Database '$db_name' already exists."
  fi
}

# Create each physical DB (actual name in Postgres) if needed
# Even though we don't migrate "vectors", we still create the DB if it's required.
create_database_if_missing "$AUTHENTICATION_SHARD_DB_NAME"
create_database_if_missing "$GEODISCOUNTS_DB_NAME"
create_database_if_missing "$VECTOR_DB_NAME"

################################################
# 4) Run Migrations for Apps that Need Them    #
################################################

# Mapping: (App Name) -> (Django DB Alias)
# We DO NOT include 'vectors' here, because it's not a real Django app.
declare -A APP_TO_ALIAS=(
  ["authentication"]="authentication_shard"
  ["geodiscounts"]="geodiscounts_db"
)

run_migrations() {
  local app_name="$1"
  local db_alias="$2"

  # 4a) Generate migrations for this specific app
  log_and_print "🛠️ Running makemigrations for app: $app_name..."
  python manage.py makemigrations "$app_name" 2>&1 | tee -a "$LOG_FILE"
  
  # 4b) Apply migrations using the DB alias
  log_and_print "🛠️ Running migrations for app: $app_name on database alias: $db_alias..."
  python manage.py migrate "$app_name" --database="$db_alias" 2>&1 | tee -a "$LOG_FILE"
}

# Only run migrations for the apps in the APP_TO_ALIAS dictionary
for app in "${!APP_TO_ALIAS[@]}"; do
  alias="${APP_TO_ALIAS[$app]}"
  log_and_print "🚀 Running migrations for app: '$app' on alias: '$alias'"
  run_migrations "$app" "$alias"
done

log_and_print "✅ All shard migrations complete."

################################
# 5) Collect Static Files       #
################################
log_and_print "📦 Collecting static files..."
python manage.py collectstatic --noinput 2>&1 | tee -a "$LOG_FILE"

########################################
# 6) Start the Django App (Gunicorn)   #
########################################
log_and_print "🚀 Starting Gunicorn server..."
gunicorn coupon_core.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --threads 1 \
  --timeout 120


