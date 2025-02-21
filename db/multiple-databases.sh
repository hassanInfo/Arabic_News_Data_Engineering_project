#!/bin/bash

set -e
set -u

function create_database() {
    local database=$1
    echo "Creating database '$database'"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        CREATE DATABASE $database;
EOSQL
}

if [ -n "$POSTGRES_MULTIPLE_DATABASES" ]; then
    echo "Multiple database creation requested: $POSTGRES_MULTIPLE_DATABASES"
    
    IFS=',' read -ra DB_LIST <<< "$POSTGRES_MULTIPLE_DATABASES"
    for db in "${DB_LIST[@]}"; do
        create_database $db
    done
    echo "Multiple databases created"
fi
