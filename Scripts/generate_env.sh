#!/bin/bash

# Set the output .env file path
ENV_FILE="/app/.env"

# Create the .env file and write environment variables with VITE_ prefix
echo "# Auto-generated VITE_ environment variables" > $ENV_FILE
printenv | grep '^VITE_' >> $ENV_FILE

# Ensure proper permissions
chmod 644 $ENV_FILE

echo "VITE_ environment variables written to $ENV_FILE"