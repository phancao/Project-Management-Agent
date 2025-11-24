#!/usr/bin/env bash
set -euo pipefail

# Restore a SQL dump into the embedded PostgreSQL inside the OpenProject v13 app container
#
# Usage:
#   scripts/restore_op13_embedded.sh /path/to/openproject.sql [user_email]
#
# Arguments:
#   /path/to/openproject.sql - Path to the SQL dump file
#   user_email (optional)     - Email of user to setup permissions and generate token for
#                               Default: cao.phan@galaxytechnology.vn
#
# Notes:
# - This targets the embedded DB inside the app container (not the external DB container)
# - It will terminate active connections, drop and recreate the openproject DB, restore the dump,
#   and print basic verification counts.
# - After restore, it will setup the specified user's permissions (add to all projects) and generate an API token

DUMP_FILE="${1:-}"

# Get compose directory and service name
COMPOSE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVICE_NAME="openproject_v13"

# Auto-detect OpenProject v13 container (app container, not DB container) for reference
if [[ -z "${APP_CONTAINER:-}" ]]; then
  if [[ -f "${COMPOSE_DIR}/docker-compose.yml" ]]; then
    cd "${COMPOSE_DIR}"
    # Get app container (exclude _db_ containers)
    APP_CONTAINER=$(docker-compose ps --format '{{.Name}}' 2>/dev/null | grep -iE 'openproject.*v13|openproject.*13' | grep -vE '_db_|database' | head -n 1)
  fi
  # Fallback: try default name pattern
  if [[ -z "${APP_CONTAINER}" ]]; then
    APP_CONTAINER="project-management-agent-openproject_v13-1"
  fi
fi

# Auto-detect port from docker-compose or container
if [[ -z "${OP_PORT:-}" ]]; then
  if [[ -f "${COMPOSE_DIR}/docker-compose.yml" ]]; then
    cd "${COMPOSE_DIR}"
    # Get full ps output and parse port for openproject_v13 (not _db_)
    PORT_LINE=$(docker-compose ps 2>/dev/null | grep -iE 'openproject.*v13|openproject.*13' | grep -vE '_db_|database' | head -n 1)
    if [[ -n "${PORT_LINE}" ]]; then
      PORT_MAPPING=$(echo "${PORT_LINE}" | grep -oE '[0-9]+:80' | head -n 1 | cut -d: -f1)
      if [[ -n "${PORT_MAPPING}" ]]; then
        OP_PORT="${PORT_MAPPING}"
      fi
    fi
  fi
  # Fallback: try common ports (check which one responds)
  if [[ -z "${OP_PORT:-}" ]] || [[ "${OP_PORT}" = "0" ]]; then
    for port in 8083 8081 8080; do
      HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://localhost:${port}/api/v3/" 2>/dev/null || echo "000")
      if [[ "${HTTP_CODE}" =~ ^[0-9]+$ ]] && [[ "${HTTP_CODE}" != "000" ]]; then
        OP_PORT="${port}"
        break
      fi
    done
    # Final fallback
    if [[ -z "${OP_PORT:-}" ]] || [[ "${OP_PORT}" = "0" ]]; then
      OP_PORT="8081"
    fi
  fi
fi

if [[ -z "${DUMP_FILE}" || ! -f "${DUMP_FILE}" ]]; then
  echo "Usage: $0 /absolute/path/to/openproject.sql [user_email]"
  echo "Error: dump file not found: '${DUMP_FILE}'"
  exit 1
fi

echo "App container: ${APP_CONTAINER}"
echo "OpenProject port: ${OP_PORT}"
echo "Dump file: ${DUMP_FILE}"
echo ""

echo "1) Copy dump into app container..."
cd "${COMPOSE_DIR}"
docker-compose cp "${DUMP_FILE}" "${SERVICE_NAME}:/var/tmp/openproject.sql"

echo "1b) Preprocess dump to clean incompatible statements..."
# Create a cleaned dump inside the container to minimize restore noise/errors
# - Drop psql meta-commands: \restrict / \unrestrict
# - Remove transaction_timeout SET lines not supported
# - Map pg_database_owner to postgres
# - Normalize OWNER TO to postgres
cd "${COMPOSE_DIR}"
docker-compose exec -T "${SERVICE_NAME}" sh -lc "\
  awk 'BEGIN{IGNORECASE=1} \
    !/^\\\\restrict/ && !/^\\\\unrestrict/ && \
    !/^SET[[:space:]]+.*transaction_timeout/ { print }' \
  /var/tmp/openproject.sql | \
  sed -E -e 's/OWNER TO [^;]+;/OWNER TO postgres;/Ig' \
         -e 's/TO pg_database_owner/TO postgres/Ig' \
  > /var/tmp/openproject.cleaned.sql"

echo "2) Terminate active connections..."
cd "${COMPOSE_DIR}"
docker-compose exec -T "${SERVICE_NAME}" bash -lc "\
  su - postgres -c \"psql -d postgres -v ON_ERROR_STOP=1 -c \\\"UPDATE pg_database SET datallowconn=false WHERE datname='openproject'\\\"\" >/dev/null; \
  for i in {1..10}; do \
    su - postgres -c \"psql -d postgres -c \\\"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='openproject' AND pid <> pg_backend_pid()\\\"\" >/dev/null; \
    sleep 1; \
  done"

echo "3) Drop and recreate database..."
cd "${COMPOSE_DIR}"
docker-compose exec -T "${SERVICE_NAME}" sh -lc "\
  su - postgres -c 'dropdb --if-exists openproject' || true; \
  su - postgres -c 'createdb openproject'; \
  su - postgres -c \"psql -d postgres -c \\\"UPDATE pg_database SET datallowconn = true WHERE datname = 'openproject'\\\"\" >/dev/null"

echo "3b) Reset public schema to avoid duplicate schema warnings..."
cd "${COMPOSE_DIR}"
docker-compose exec -T "${SERVICE_NAME}" sh -lc "su - postgres -c \"psql -d openproject -v ON_ERROR_STOP=1 -c 'DROP SCHEMA IF EXISTS public CASCADE;' -c 'CREATE SCHEMA public AUTHORIZATION postgres;' -c 'GRANT ALL ON SCHEMA public TO postgres;' -c 'GRANT ALL ON SCHEMA public TO public;'\""

echo "4) Restore dump into embedded DB (this may take a few minutes)..."
cd "${COMPOSE_DIR}"
docker-compose exec -T "${SERVICE_NAME}" sh -lc "su - postgres -c 'psql -v ON_ERROR_STOP=0 -d openproject -f /var/tmp/openproject.cleaned.sql' >/dev/null"

echo "5) Verify basic counts:"
cd "${COMPOSE_DIR}"
docker-compose exec -T "${SERVICE_NAME}" sh -lc "su - postgres -c \"psql -d openproject -t -A -c 'SELECT count(*) FROM projects;'\""
docker-compose exec -T "${SERVICE_NAME}" sh -lc "su - postgres -c \"psql -d openproject -t -A -c 'SELECT count(*) FROM users;'\""

echo "✅ Embedded database restore completed."

echo ""
echo "6) Validate/fix users table for token auth (PK and admin uniqueness)..."
# Determine admin user's current id (by login), then move any non-User duplicate that shares that id
cd "${COMPOSE_DIR}"
ADMIN_ID=$(docker-compose exec -T "${SERVICE_NAME}" sh -lc "su - postgres -c \"psql -d openproject -t -A -c 'SELECT id FROM users WHERE login='\\''admin'\\'' ORDER BY created_at ASC LIMIT 1;'\"" | tail -n 1)
if [ -z "${ADMIN_ID}" ]; then
  echo "⚠ Could not find admin user id by login; skipping duplicate fix"
else
  echo "   Admin user id detected: ${ADMIN_ID}"
  docker-compose exec -T "${SERVICE_NAME}" sh -lc "su - postgres <<'EOSQL'
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
docker-compose exec -T "${SERVICE_NAME}" sh -lc "su - postgres <<'EOSQL'
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
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${OP_PORT}/api/v3/ 2>&1 || echo "000")
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
cd "${COMPOSE_DIR}"
NEW_TOKEN=$(docker-compose exec -T "${SERVICE_NAME}" bash -lc "export RAILS_ENV=production && cd /app && ./bin/rails runner \"u=User.find_by(login: 'admin'); t=::Token::API.create!(user: u); puts t.plain_value\"" | tail -n 1)
if [ -z "${NEW_TOKEN}" ]; then
  echo "⚠ Failed to generate token via Rails."
  exit 1
fi
printf %s "${NEW_TOKEN}" > /tmp/op13_token.txt
# Quick test against API (retry once if needed)
B64=$(printf 'apikey:%s' "${NEW_TOKEN}" | base64)
STATUS=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Basic ${B64}" -H 'Accept: application/json' http://localhost:${OP_PORT}/api/v3/users/me || true)
if [ "${STATUS}" != "200" ]; then
  sleep 2
  STATUS=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Basic ${B64}" -H 'Accept: application/json' http://localhost:${OP_PORT}/api/v3/users/me || true)
fi
if [ "${STATUS}" = "200" ]; then
  echo "✓ Token verified (HTTP 200). Saved to /tmp/op13_token.txt"
else
  echo "⚠ Token test failed (HTTP ${STATUS}). Token still saved to /tmp/op13_token.txt"
fi

echo ""
echo "9) Setup user permissions and generate API token..."
# Copy the Ruby script into the container
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${COMPOSE_DIR}"
docker-compose cp "${SCRIPT_DIR}/setup_user_permissions_and_token.rb" "${SERVICE_NAME}:/tmp/setup_user_permissions_and_token.rb"

# Run the script to setup user permissions and generate token
USER_EMAIL="${2:-cao.phan@galaxytechnology.vn}"
echo "   Checking user: ${USER_EMAIL}"
docker-compose exec -T "${SERVICE_NAME}" bash -lc "export RAILS_ENV=production && cd /app && ./bin/rails runner /tmp/setup_user_permissions_and_token.rb '${USER_EMAIL}' Member" || {
  echo "⚠ Failed to setup user permissions or generate token"
  echo "   (This is non-fatal - restore completed successfully)"
}

echo ""
echo "✅ Database restore and user setup completed!"

