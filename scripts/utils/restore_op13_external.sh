#!/usr/bin/env bash
set -euo pipefail

DUMP_FILE="${1:-}"
DB_CONTAINER="project-management-agent-openproject_db_v13-1"
DB_USER="openproject"
DB_NAME="openproject"

if [[ -z "${DUMP_FILE}" || ! -f "${DUMP_FILE}" ]]; then
  echo "Usage: $0 /path/to/openproject.sql"
  exit 1
fi

echo "Copying dump to DB container..."
docker cp "${DUMP_FILE}" "${DB_CONTAINER}:/tmp/dump.sql"

echo "Terminating connections..."
docker exec "${DB_CONTAINER}" psql -U "${DB_USER}" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();" || true

echo "Dropping and recreating database..."
docker exec "${DB_CONTAINER}" dropdb -U "${DB_USER}" --if-exists "${DB_NAME}"
docker exec "${DB_CONTAINER}" createdb -U "${DB_USER}" "${DB_NAME}"

echo "Resetting public schema..."
docker exec "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "DROP SCHEMA IF EXISTS public CASCADE;"

echo "Restoring dump..."
# We might need to clean the dump if it has ownership issues, but let's try direct first or use the cleaning logic from the other script if needed.
# The previous script did some cleaning. Let's replicate that cleaning on the host before copying.

cleaned_dump="${DUMP_FILE}.cleaned"
echo "Cleaning dump..."
awk 'BEGIN{IGNORECASE=1} \
    !/^\\restrict/ && !/^\\unrestrict/ && \
    !/^SET[[:space:]]+.*transaction_timeout/ { print }' \
  "${DUMP_FILE}" | \
  sed -E -e 's/OWNER TO [^;]+;/OWNER TO openproject;/Ig' \
         -e 's/TO pg_database_owner/TO openproject/Ig' \
  > "${cleaned_dump}"

echo "Copying cleaned dump..."
docker cp "${cleaned_dump}" "${DB_CONTAINER}:/tmp/dump.sql"

echo "Importing dump (logging to /tmp/restore_error.log)..."
docker exec "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1 -f /tmp/dump.sql > /tmp/restore_output.log 2> /tmp/restore_error.log || {
  echo "Import failed! Checking last few lines of error log:"
  docker exec "${DB_CONTAINER}" tail -n 20 /tmp/restore_error.log
  exit 1
}

echo "Done."
