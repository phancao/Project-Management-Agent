#!/usr/bin/env bash
set -euo pipefail

# Restore a SQL dump into the embedded PostgreSQL inside the OpenProject v13 app container
#
# Usage:
#   scripts/restore_op13_embedded.sh /path/to/openproject.sql
#
# Notes:
# - This targets the embedded DB inside the app container (not the external DB container)
# - It will terminate active connections, drop and recreate the openproject DB, restore the dump,
#   and print basic verification counts.

DUMP_FILE="${1:-}"
APP_CONTAINER="${APP_CONTAINER:-project-management-agent-openproject_v13-1}"

if [[ -z "${DUMP_FILE}" || ! -f "${DUMP_FILE}" ]]; then
  echo "Usage: $0 /absolute/path/to/openproject.sql"
  echo "Error: dump file not found: '${DUMP_FILE}'"
  exit 1
fi

echo "App container: ${APP_CONTAINER}"
echo "Dump file: ${DUMP_FILE}"
echo ""

echo "1) Copy dump into app container..."
docker cp "${DUMP_FILE}" "${APP_CONTAINER}:/var/tmp/openproject.sql"

echo "1b) Preprocess dump to clean incompatible statements..."
# Create a cleaned dump inside the container to minimize restore noise/errors
# - Drop psql meta-commands: \restrict / \unrestrict
# - Remove transaction_timeout SET lines not supported
# - Map pg_database_owner to postgres
# - Normalize OWNER TO to postgres
docker exec "${APP_CONTAINER}" sh -lc "\
  awk 'BEGIN{IGNORECASE=1} \
    !/^\\\\restrict/ && !/^\\\\unrestrict/ && \
    !/^SET[[:space:]]+.*transaction_timeout/ { print }' \
  /var/tmp/openproject.sql | \
  sed -E -e 's/OWNER TO [^;]+;/OWNER TO postgres;/Ig' \
         -e 's/TO pg_database_owner/TO postgres/Ig' \
  > /var/tmp/openproject.cleaned.sql"

echo "2) Terminate active connections..."
docker exec "${APP_CONTAINER}" bash -lc "\
  su - postgres -c \"psql -d postgres -v ON_ERROR_STOP=1 -c \\\"UPDATE pg_database SET datallowconn=false WHERE datname='openproject'\\\"\" >/dev/null; \
  for i in {1..10}; do \
    su - postgres -c \"psql -d postgres -c \\\"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='openproject' AND pid <> pg_backend_pid()\\\"\" >/dev/null; \
    sleep 1; \
  done"

echo "3) Drop and recreate database..."
docker exec "${APP_CONTAINER}" sh -lc "\
  su - postgres -c 'dropdb --if-exists openproject' || true; \
  su - postgres -c 'createdb openproject'; \
  su - postgres -c \"psql -d postgres -c \\\"UPDATE pg_database SET datallowconn = true WHERE datname = 'openproject'\\\"\" >/dev/null"

echo "3b) Reset public schema to avoid duplicate schema warnings..."
docker exec "${APP_CONTAINER}" sh -lc "su - postgres -c \"psql -d openproject -v ON_ERROR_STOP=1 -c 'DROP SCHEMA IF EXISTS public CASCADE;' -c 'CREATE SCHEMA public AUTHORIZATION postgres;' -c 'GRANT ALL ON SCHEMA public TO postgres;' -c 'GRANT ALL ON SCHEMA public TO public;'\""

echo "4) Restore dump into embedded DB (this may take a few minutes)..."
docker exec "${APP_CONTAINER}" sh -lc "su - postgres -c 'psql -v ON_ERROR_STOP=0 -d openproject -f /var/tmp/openproject.cleaned.sql' >/dev/null"

echo "5) Verify basic counts:"
docker exec "${APP_CONTAINER}" sh -lc "su - postgres -c \"psql -d openproject -t -A -c 'SELECT count(*) FROM projects;'\""
docker exec "${APP_CONTAINER}" sh -lc "su - postgres -c \"psql -d openproject -t -A -c 'SELECT count(*) FROM users;'\""

echo "✅ Embedded database restore completed."

echo ""
echo "6) Validate/fix users table for token auth (PK and admin uniqueness)..."
# Determine admin user's current id (by login), then move any non-User duplicate that shares that id
ADMIN_ID=$(docker exec "${APP_CONTAINER}" sh -lc "su - postgres -c \"psql -d openproject -t -A -c 'SELECT id FROM users WHERE login='\\''admin'\\'' ORDER BY created_at ASC LIMIT 1;'\"" | tail -n 1)
if [ -z "${ADMIN_ID}" ]; then
  echo "⚠ Could not find admin user id by login; skipping duplicate fix"
else
  echo "   Admin user id detected: ${ADMIN_ID}"
  docker exec "${APP_CONTAINER}" sh -lc "su - postgres <<'EOSQL'
psql -d openproject -v ON_ERROR_STOP=1 <<SQL
BEGIN;
WITH mx AS (SELECT COALESCE(MAX(id),0) AS max_id FROM users),
     dupe AS (
       SELECT ctid FROM users 
       WHERE id=${ADMIN_ID} AND (type <> 'User' OR login IS NULL OR login = '')
       ORDER BY created_at DESC NULLS LAST LIMIT 1
     )
UPDATE users SET id = (SELECT max_id+1 FROM mx) WHERE ctid IN (SELECT ctid FROM dupe);
COMMIT;
SQL
EOSQL"
fi
# Ensure primary key exists
docker exec "${APP_CONTAINER}" sh -lc "su - postgres <<'EOSQL'
psql -d openproject <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c 
    JOIN pg_class t ON c.conrelid=t.oid
    WHERE t.relname='users' AND c.conname='users_pkey'
  ) THEN
    EXECUTE 'ALTER TABLE users ADD PRIMARY KEY (id)';
  END IF;
END$$;
SQL
EOSQL"

echo "7) Wait for API to be ready..."
READY=0
# Shorter wait: up to ~30 seconds total
for i in {1..30}; do
  if curl -s -f http://localhost:8081/api/v3/status >/dev/null 2>&1; then
    READY=1; break;
  fi
  sleep 1
done
if [ "${READY}" != "1" ]; then
  echo "⚠ API status not ready after short wait; continuing to token generation"
fi

echo "8) Generate fresh admin API token (v13) and save for importer..."
# Generate a new API token for admin and capture plain value on host
NEW_TOKEN=$(docker exec "${APP_CONTAINER}" bash -lc "export RAILS_ENV=production && cd /app && ./bin/rails runner \"u=User.find_by(login: 'admin'); t=::Token::API.create!(user: u); puts t.plain_value\"" | tail -n 1)
if [ -z "${NEW_TOKEN}" ]; then
  echo "⚠ Failed to generate token via Rails."
  exit 1
fi
printf %s "${NEW_TOKEN}" > /tmp/op13_token.txt
# Quick test against API (retry once if needed)
B64=$(printf 'apikey:%s' "${NEW_TOKEN}" | base64)
STATUS=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Basic ${B64}" -H 'Accept: application/json' http://localhost:8081/api/v3/users/me || true)
if [ "${STATUS}" != "200" ]; then
  sleep 2
  STATUS=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Basic ${B64}" -H 'Accept: application/json' http://localhost:8081/api/v3/users/me || true)
fi
if [ "${STATUS}" = "200" ]; then
  echo "✓ Token verified (HTTP 200). Saved to /tmp/op13_token.txt"
else
  echo "⚠ Token test failed (HTTP ${STATUS}). Token still saved to /tmp/op13_token.txt"
fi


