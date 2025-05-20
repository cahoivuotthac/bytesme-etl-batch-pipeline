#!/bin/bash

# Load environment variables from .env file
set -o allexport
source .env
set +o allexport

export PGPASSWORD=$POSTGRES_DB_PASSWORD

SCHEMA_FILE="database/bytesme_psql_schema.sql"

psql -U $POSTGRES_DB_USER -d $POSTGRES_DB_NAME -f $SCHEMA_FILE

echo "Schema has been applied successfully from $SCHEMA_FILE"
