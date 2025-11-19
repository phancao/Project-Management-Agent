#!/usr/bin/env bash
set -euo pipefail

# Dump the embedded PostgreSQL database from OpenProject v13 app container
#
# Usage:
#   scripts/utils/dump_op13_database.sh [output_file]
#
# If output_file is not provided, defaults to ~/Downloads/OpenProject_$(date +%Y%m%d_%H%M%S).sql
#
# Notes:
# - This targets the embedded DB inside the app container (not the external DB container)
# - Uses pg_dump to create a SQL dump file

OUTPUT_FILE="${1:-}"
if [[ -z "${OUTPUT_FILE}" ]]; then
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  OUTPUT_FILE="/Users/phancao/Downloads/OpenProject_${TIMESTAMP}.sql"
fi

APP_CONTAINER="${APP_CONTAINER:-project-management-agent-openproject_v13-1}"

# Ensure output directory exists
OUTPUT_DIR=$(dirname "${OUTPUT_FILE}")
mkdir -p "${OUTPUT_DIR}"

echo "App container: ${APP_CONTAINER}"
echo "Output file: ${OUTPUT_FILE}"
echo ""

# Check if container exists
if ! docker ps --format '{{.Names}}' | grep -q "^${APP_CONTAINER}$"; then
  echo "Error: Container '${APP_CONTAINER}' is not running."
  echo "Please start OpenProject v13 first."
  exit 1
fi

echo "1) Dumping database from embedded PostgreSQL..."
# Use pg_dump with the format: PGPASSWORD=password pg_dump -h host -p port -U user -d database -n schema -f file
# Adapted for embedded database inside container (uses postgres user via su, localhost, default port)
docker exec "${APP_CONTAINER}" bash -lc "\
  su - postgres -c 'PGPASSWORD=postgres pg_dump -h localhost -p 5432 -U postgres -d openproject -n public -f /tmp/openproject_dump.sql' 2>/dev/null || \
  su - postgres -c 'pg_dump -h localhost -p 5432 -U postgres -d openproject -n public -f /tmp/openproject_dump.sql' && \
  cat /tmp/openproject_dump.sql && \
  rm -f /tmp/openproject_dump.sql \
" > "${OUTPUT_FILE}"

# Check if dump was successful
if [[ ! -f "${OUTPUT_FILE}" ]] || [[ ! -s "${OUTPUT_FILE}" ]]; then
  echo "Error: Dump file was not created or is empty."
  exit 1
fi

# Get file size
FILE_SIZE=$(du -h "${OUTPUT_FILE}" | cut -f1)
echo ""
echo "✅ Database dump completed successfully!"
echo "   File: ${OUTPUT_FILE}"
echo "   Size: ${FILE_SIZE}"
echo ""

# Verify basic structure
echo "2) Verifying dump file..."
if grep -q "PostgreSQL database dump" "${OUTPUT_FILE}"; then
  echo "   ✓ Dump file appears valid (contains PostgreSQL dump header)"
else
  echo "   ⚠ Warning: Dump file may not be valid (missing expected header)"
fi

# Count tables/objects in dump
TABLE_COUNT=$(grep -c "^CREATE TABLE" "${OUTPUT_FILE}" || echo "0")
echo "   ✓ Found ${TABLE_COUNT} CREATE TABLE statements"

echo ""
echo "✅ Dump completed successfully!"

