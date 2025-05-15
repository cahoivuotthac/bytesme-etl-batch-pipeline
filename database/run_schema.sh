#!/bin/bash

# Load environment variables from .env file
set -o allexport
source .env
set +o allexport

# Export password for PostgreSQL authentication
export PGPASSWORD=$POSTGRES_DB_PASSWORD

# Define the relative path to your schema file (in the database/ folder)
SCHEMA_FILE="database/bytesme_psql_schema.sql"

# Run the .sql file using psql
psql -U $POSTGRES_DB_USER -d $POSTGRES_DB_NAME -f $SCHEMA_FILE

# Confirm success
echo "Schema has been applied successfully from $SCHEMA_FILE"
