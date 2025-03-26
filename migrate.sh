#!/bin/bash

# Set error handling
set -e
trap 'echo "❌ Migration failed. Check migration.log for details."; exit 1' ERR

# Core Django apps that need to be migrated first
CORE_APPS=("contenttypes" "auth" "admin" "sessions")

# Authentication-related apps
AUTH_APPS=("authtoken" "authentication" "socialaccount" "account")

# Geodiscounts apps
GEODISCOUNTS_APPS=("geodiscounts")

# Available databases from settings
DATABASES=("default" "authentication_shard" "geodiscounts_db" "vector_db")

# Log file
LOG_FILE="migration.log"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# Function to log messages
log_and_print() {
    echo "[$TIMESTAMP] $1"
    echo "[$TIMESTAMP] $1" >> "$LOG_FILE"
}

# Function to check database connection
check_db_connection() {
    local db=$1
    log_and_print "🔍 Checking connection to $db..."
    if ! python manage.py check --database="$db" 2>/dev/null; then
        log_and_print "❌ ERROR: Cannot connect to $db"
        return 1
    fi
    return 0
}

# Function to run migrations for a list of apps
run_migrations() {
    local db=$1
    shift
    local apps=("$@")
    local migration_errors=0

    for APP in "${apps[@]}"
    do
        log_and_print "🚀 Migrating $APP on $db..."
        if ! python manage.py migrate "$APP" --database="$db" 2>&1 | tee -a "$LOG_FILE"; then
            log_and_print "❌ ERROR: Migration failed for $APP"
            migration_errors=$((migration_errors + 1))
        else
            log_and_print "✅ Successfully migrated $APP"
        fi
    done

    if [ "$migration_errors" -gt 0 ]; then
        log_and_print "❌ Some migrations failed on $db. Check $LOG_FILE for details."
        return 1
    fi
    return 0
}

# Function to show migration status
show_migration_status() {
    local db=$1
    log_and_print "📊 Migration status for $db:"
    python manage.py showmigrations --database="$db" 2>&1 | tee -a "$LOG_FILE"
}

# Start migration process
log_and_print "🔄 Starting migration process..."

# Run core migrations on all databases first
for DB in "${DATABASES[@]}"; do
    log_and_print "🛠️ Running core migrations on $DB..."
    if ! run_migrations "$DB" "${CORE_APPS[@]}"; then
        exit 1
    fi
done

# Run authentication migrations on all databases
for DB in "${DATABASES[@]}"; do
    log_and_print "🛠️ Running authentication migrations on $DB..."
    if ! run_migrations "$DB" "${AUTH_APPS[@]}"; then
        exit 1
    fi
done

# Run geodiscounts migrations only on geodiscounts_db
log_and_print "🛠️ Running geodiscounts migrations on geodiscounts_db..."
if ! run_migrations "geodiscounts_db" "${GEODISCOUNTS_APPS[@]}"; then
    exit 1
fi

# Show final migration status
for DB in "${DATABASES[@]}"; do
    show_migration_status "$DB"
done

log_and_print "✅ All migrations completed successfully!"

