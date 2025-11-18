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

echo "3) Drop and recreate database (deleting ALL current data)..."
# Completely remove the database to ensure no current data remains
docker exec "${APP_CONTAINER}" sh -lc "\
  su - postgres -c 'dropdb --if-exists openproject' || true; \
  su - postgres -c 'createdb openproject'; \
  su - postgres -c \"psql -d postgres -c \\\"UPDATE pg_database SET datallowconn = true WHERE datname = 'openproject'\\\"\" >/dev/null"

echo "3b) Reset public schema to ensure clean state..."
docker exec "${APP_CONTAINER}" sh -lc "su - postgres -c \"psql -d openproject -v ON_ERROR_STOP=1 -c 'DROP SCHEMA IF EXISTS public CASCADE;' -c 'CREATE SCHEMA public AUTHORIZATION postgres;' -c 'GRANT ALL ON SCHEMA public TO postgres;' -c 'GRANT ALL ON SCHEMA public TO public;'\""

echo "4) Restore dump into embedded DB (this may take a few minutes)..."
docker exec "${APP_CONTAINER}" sh -lc "su - postgres -c 'psql -v ON_ERROR_STOP=0 -d openproject -f /var/tmp/openproject.cleaned.sql' >/dev/null"

echo "5) Verify basic counts:"
docker exec "${APP_CONTAINER}" sh -lc "su - postgres -c \"psql -d openproject -t -A -c 'SELECT count(*) FROM projects;'\""
docker exec "${APP_CONTAINER}" sh -lc "su - postgres -c \"psql -d openproject -t -A -c 'SELECT count(*) FROM users;'\""

echo "✅ Embedded database restore completed."

echo ""
echo "6) Validate/fix users table for token auth (PK and ALL duplicate IDs)..."
# Fix ALL duplicate user IDs, not just admin
# Priority: Keep regular Users, move special principals (SystemUser, AnonymousUser) to new IDs
docker exec "${APP_CONTAINER}" sh -lc "su - postgres <<'EOSQL'
psql -d openproject -v ON_ERROR_STOP=1 <<'SQL'
DO \$\$
DECLARE
  dup_id INTEGER;
  max_id INTEGER;
  dupe_ctid TID;
  dupe_type TEXT;
BEGIN
  -- Get max user ID to assign new IDs above it
  SELECT COALESCE(MAX(id), 0) INTO max_id FROM users;
  
  -- Find and fix all duplicate IDs
  FOR dup_id IN 
    SELECT id FROM users GROUP BY id HAVING COUNT(*) > 1
  LOOP
    -- Keep one entry (prefer User type, then oldest), move all others
    -- Process all duplicates except the first one (which we keep)
    FOR dupe_ctid, dupe_type IN
      SELECT ctid, type
      FROM users
      WHERE id = dup_id
      ORDER BY 
        CASE WHEN type = 'User' THEN 1 ELSE 2 END,  -- Prefer to keep Users
        created_at ASC NULLS FIRST  -- Keep oldest
      OFFSET 1  -- Skip the first one (keep it)
    LOOP
      max_id := max_id + 1;
      UPDATE users SET id = max_id WHERE ctid = dupe_ctid;
      RAISE NOTICE 'Moved duplicate user (id=%, type=%) to new id=%', dup_id, dupe_type, max_id;
    END LOOP;
  END LOOP;
END \$\$;
SQL
EOSQL"
# Determine admin user's current id for logging
ADMIN_ID=$(docker exec "${APP_CONTAINER}" sh -lc "su - postgres -c \"psql -d openproject -t -A -c 'SELECT id FROM users WHERE login='\\''admin'\\'' ORDER BY created_at ASC LIMIT 1;'\"" | tail -n 1)
if [ -n "${ADMIN_ID}" ]; then
  echo "   Admin user id detected: ${ADMIN_ID}"
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
# Check every 3 seconds, up to 60 attempts (3 minutes total)
# Use /api/v3/ endpoint - returns 401 (Unauthorized) when API is ready, 404/000 when not ready
MAX_ATTEMPTS=60
ATTEMPT=0
while [ "${ATTEMPT}" -lt "${MAX_ATTEMPTS}" ]; do
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/api/v3/ 2>&1 || echo "000")
  # 401 (Unauthorized) or 200 means API is ready and responding
  # 404, 000, or connection errors mean API is not ready yet
  if [ "${HTTP_CODE}" = "401" ] || [ "${HTTP_CODE}" = "200" ]; then
    READY=1
    if [ "${ATTEMPT}" -gt 0 ]; then
      echo "   ✓ API is ready (after ${ATTEMPT} attempt(s), HTTP ${HTTP_CODE})"
    else
      echo "   ✓ API is ready (HTTP ${HTTP_CODE})"
    fi
    break
  fi
  ATTEMPT=$((ATTEMPT + 1))
  if [ $((ATTEMPT % 10)) -eq 0 ]; then
    echo "   ⏳ Still waiting... (attempt ${ATTEMPT}/${MAX_ATTEMPTS}, HTTP ${HTTP_CODE})"
  fi
  sleep 3
done
if [ "${READY}" != "1" ]; then
  echo "⚠ API not ready after ${MAX_ATTEMPTS} attempts (~$((MAX_ATTEMPTS * 3)) seconds); continuing to token generation"
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


