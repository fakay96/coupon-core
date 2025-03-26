#!/bin/bash

AUTH_APPS=("contenttypes" "auth" "admin" "authtoken" "authentication" "sessions" "socialaccount" "account")
GEODISCOUNTS_APPS=("geodiscounts")
LOG_FILE="migration.log"

log_and_print() {
    echo "$1"
    echo "$1" >> "$LOG_FILE"
}
log_and_print "🛠️ Running migrations on authentication_shard..."
migration_errors=0

for APP in "${AUTH_APPS[@]}"
do
    log_and_print "🚀 Migrating $APP on authentication_shard..."
    if ! poetry run python3 manage.py migrate "$APP" --database=authentication_shard 2>&1 | tee -a "$LOG_FILE"; then
        log_and_print "❌ ERROR: Migration failed for $APP. Exiting..."
        migration_errors=$((migration_errors + 1))
    fi
done

if [ "$migration_errors" -gt 0 ]; then
  log_and_print "❌ Some authentication migrations failed. Check $LOG_FILE for details."
  exit 1
fi

log_and_print "✅ Authentication shard migrations completed successfully!"

log_and_print "🛠️ Running migrations on geodiscounts_db..."
migration_errors=0

for APP in "${GEODISCOUNTS_APPS[@]}"
do
    log_and_print "🚀 Migrating $APP on geodiscounts_db..."
    if ! poetry run python3 manage.py migrate "$APP" --database=geodiscounts_db 2>&1 | tee -a "$LOG_FILE"; then
        log_and_print "❌ ERROR: Migration failed for $APP. Exiting..."
        migration_errors=$((migration_errors + 1))
    fi
done

if [ "$migration_errors" -gt 0 ]; then
  log_and_print "❌ Some geodiscounts migrations failed. Check $LOG_FILE for details."
  exit 1
fi

log_and_print "✅ Geodiscounts DB migrations completed successfully!"

