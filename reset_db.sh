#!/bin/bash

# Set error handling
set -e
trap 'echo "❌ Database reset failed. Check reset_db.log for details."; exit 1' ERR

# Load environment variables
source .env

# Log file
LOG_FILE="reset_db.log"

# Function to log messages with current timestamp
log_and_print() {
    local TIMESTAMP
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

# Function to drop a database using SQL commands with superuser privileges
drop_database() {
    local db_name=$1
    local db_password=$2
    local db_host=$3
    local db_port=$4

    log_and_print "🗑️ Dropping database $db_name..."
    # Terminate any active connections to the database
    PGPASSWORD=$db_password psql -h $db_host -p $db_port -U $(whoami) -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$db_name' AND pid <> pg_backend_pid();" || true

    # Quote the name if it's "default" to avoid reserved-word issues.
    if [ "$db_name" = "default" ]; then
        DROP_CMD="DROP DATABASE IF EXISTS \"default\" WITH (FORCE);"
    else
        DROP_CMD="DROP DATABASE IF EXISTS $db_name;"
    fi

    PGPASSWORD=$db_password psql -h $db_host -p $db_port -U $(whoami) -d postgres -c "$DROP_CMD" || true
}

# Function to create a database and add extensions if needed
create_database() {
    local db_name=$1
    local db_user=$2
    local db_password=$3
    local db_host=$4
    local db_port=$5
    local needs_postgis=$6

    log_and_print "✨ Creating database $db_name..."
    if [ "$db_name" = "default" ]; then
        # Use proper quoting for the reserved word "default"
        PGPASSWORD=$db_password psql -h $db_host -p $db_port -U $db_user -d postgres -c "CREATE DATABASE \"default\";"
    else
        PGPASSWORD=$db_password createdb -h $db_host -p $db_port -U $db_user $db_name
    fi

    # If PostGIS is required, add the extension
    if [ "$needs_postgis" = "true" ]; then
        log_and_print "🔧 Adding PostGIS extension to $db_name..."
        # For the extension, also quote the database name if necessary.
        if [ "$db_name" = "default" ]; then
            TARGET_DB="\"default\""
        else
            TARGET_DB=$db_name
        fi
        PGPASSWORD=$db_password psql -h $db_host -p $db_port -U $(whoami) -d $TARGET_DB -c "CREATE EXTENSION IF NOT EXISTS postgis;"
    fi

    log_and_print "✅ Database $db_name created successfully"
}

# Function to check database connection via Django
check_db_connection() {
    local db=$1
    log_and_print "🔍 Checking connection to $db..."
    if ! python manage.py check --database="$db" 2>/dev/null; then
        log_and_print "❌ ERROR: Cannot connect to $db"
        return 1
    fi
    return 0
}

# Function to wait for a database to be ready

# Start database reset process
log_and_print "🔄 Starting database reset process..."

# Drop existing databases (including the default)

log_and_print "🗑️ Dropping existing databases..."
drop_database "default" "$DB_PASSWORD" "$DB_HOST" "$DB_PORT"
drop_database "authentication_shard" "$DB_PASSWORD" "$DB_HOST" "$DB_PORT"
drop_database "geodiscounts_db" "$DB_PASSWORD" "$DB_HOST" "$DB_PORT"
drop_database "vector_db" "$DB_PASSWORD" "$DB_HOST" "$DB_PORT"

# Create new databases with extensions as needed
log_and_print "✨ Creating new databases..."
create_database "default" "$DB_USER" "$DB_PASSWORD" "$DB_HOST" "$DB_PORT" "false"
create_database "authentication_shard" "$DB_USER" "$DB_PASSWORD" "$DB_HOST" "$DB_PORT" "true"
create_database "geodiscounts_db" "$DB_USER" "$DB_PASSWORD" "$DB_HOST" "$DB_PORT" "true"
create_database "vector_db" "$DB_USER" "$DB_PASSWORD" "$DB_HOST" "$DB_PORT" "false"

# Wait for all databases to be ready before proceeding

log_and_print "✅ Database reset and migration complete!"
