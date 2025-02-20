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

# 3a) Create default DB (still needed for Django, even if we don't run migrations on it)
create_database_if_missing "$DB_NAME"

# 3b) Create each shard / specialized DB
create_database_if_missing "$AUTHENTICATION_SHARD_DB_NAME"
create_database_if_missing "$GEODISCOUNTS_DB_NAME"
create_database_if_missing "$VECTOR_DB_NAME"

################################################
# 4) (Excluded) Run Migrations on the Default Database
################################################
# We are excluding the default database migrations because our router
# routes all required apps (e.g. admin, auth, sessions, etc.) to a shard.
# The following lines are commented out.
#
# log_and_print "🛠️ Running makemigrations (all apps) on default..."
# python manage.py makemigrations 2>&1 | tee -a "$LOG_FILE"
#
# log_and_print "🛠️ Applying migrations on default DB..."
# python manage.py migrate --database=default 2>&1 | tee -a "$LOG_FILE"

################################################
# 5) Run Migrations for Apps on Their Shards   #
################################################
# Mapping: (App Name) -> (Django DB Alias)
declare -A APP_TO_ALIAS=(
  ["authentication"]="authentication_shard"
  ["geodiscounts"]="geodiscounts_db"
)

run_migrations() {
  local app_name="$1"
  local db_alias="$2"
  log_and_print "🛠️ Running migrate for app: $app_name on DB alias: $db_alias..."
  python manage.py migrate "$app_name" --database="$db_alias" 2>&1 | tee -a "$LOG_FILE"
}

for app in "${!APP_TO_ALIAS[@]}"; do
  db_alias="${APP_TO_ALIAS[$app]}"
  log_and_print "🚀 App '$app' => alias '$db_alias'"
  run_migrations "$app" "$db_alias"
done

log_and_print "✅ All migrations complete."

################################
# 6) Collect Static Files      #
################################
log_and_print "📦 Collecting static files..."
python manage.py collectstatic --noinput 2>&1 | tee -a "$LOG_FILE"

########################################
# 7) Start the Django App (Gunicorn)   #
########################################
log_and_print "🚀 Starting Gunicorn server..."
gunicorn coupon_core.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --threads 1 \
  --timeout 120
