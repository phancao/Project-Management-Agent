# OpenProject v13.4.1 Database Restore Guide

This guide documents how to restore a production OpenProject database dump to OpenProject v13.4.1.

## Important Discovery

**OpenProject v13.4.1 uses EMBEDDED PostgreSQL by default**, not an external database container.

- **Embedded PostgreSQL location**: `/var/openproject/pgdata` (inside container)
- **Connection**: `127.0.0.1` (localhost)
- **Database**: `openproject`
- **User**: `openproject`
- **Password**: `openproject`

The `OPENPROJECT_DB_*` environment variables are ignored if OpenProject detects embedded PostgreSQL is available.

## Prerequisites

- OpenProject v13.4.1 running in Docker (port 8081)
- SQL dump file from production OpenProject
- Docker Compose configured with `openproject_v13` service

## Quick Restore (Automated)

Use the automated script:

```bash
./scripts/restore_op13_database.sh /path/to/your/dump.sql
```

Or with default location:

```bash
./scripts/restore_op13_database.sh
```

## Manual Restore Steps

### Step 1: Stop OpenProject

```bash
docker-compose stop openproject_v13
```

### Step 2: Start Container (for PostgreSQL Access)

```bash
docker-compose start openproject_v13
sleep 30
```

### Step 3: Wait for Embedded PostgreSQL

```bash
# Wait for PostgreSQL to be ready
for i in {1..30}; do
    if docker exec project-management-agent-openproject_v13-1 \
        bash -c "su - postgres -c 'psql -d postgres -c \"SELECT 1;\"'" >/dev/null 2>&1; then
        echo "PostgreSQL is ready"
        break
    fi
    sleep 2
done
```

### Step 4: Drop and Recreate Database

```bash
CONTAINER_NAME="project-management-agent-openproject_v13-1"

# Terminate connections
docker exec $CONTAINER_NAME bash -c \
    "su - postgres -c 'psql -d postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '\''openproject'\'' AND pid <> pg_backend_pid();\"'"

# Drop database
docker exec $CONTAINER_NAME bash -c \
    "su - postgres -c 'psql -d postgres -c \"DROP DATABASE IF EXISTS openproject;\"'"

# Create fresh database
docker exec $CONTAINER_NAME bash -c \
    "su - postgres -c 'psql -d postgres -c \"CREATE DATABASE openproject;\"'"
```

### Step 5: Restore SQL Dump

```bash
DUMP_FILE="/path/to/your/dump.sql"

docker exec -i $CONTAINER_NAME bash -c \
    "su - postgres -c 'psql -d openproject'" < "$DUMP_FILE" > /tmp/restore_op13.log 2>&1
```

**Note**: You may see warnings like:
- `invalid command \unrestrict` - This is harmless, can be ignored
- `ERROR: there is no unique constraint` - May occur but data is still restored

### Step 6: Verify Restore

```bash
docker exec $CONTAINER_NAME bash -c \
    "su - postgres -c 'psql -d openproject -c \"SELECT COUNT(*) as projects FROM projects; SELECT COUNT(*) as users FROM users;\"'"
```

Expected output:
- Projects: 465+ (or your production count)
- Users: 600+ (or your production count)

### Step 7: Restart OpenProject

```bash
docker-compose restart openproject_v13
```

Wait 3-5 minutes for OpenProject to fully start.

## Verification

After restore, verify:

1. **Check container status**:
   ```bash
   docker-compose ps openproject_v13
   ```

2. **Check database from inside container**:
   ```bash
   docker exec project-management-agent-openproject_v13-1 bash -c \
       "cd /app && bundle exec rails runner 'puts \"Projects: #{Project.count}\"; puts \"Users: #{User.count}\"'"
   ```

3. **Access web interface**:
   - URL: http://localhost:8081
   - Log in and verify all projects and users are visible

## Common Issues

### Issue 1: "Container is not running"
**Solution**: Start the container first:
```bash
docker-compose start openproject_v13
sleep 30
```

### Issue 2: "PostgreSQL did not start in time"
**Solution**: Increase wait time or check container logs:
```bash
docker-compose logs openproject_v13 | grep -i postgres
```

### Issue 3: "invalid command \unrestrict"
**Solution**: This is harmless. The dump contains PostgreSQL commands that may not be recognized, but data is still restored.

### Issue 4: "ERROR: there is no unique constraint"
**Solution**: This may occur during restore but doesn't prevent data from being restored. Verify the counts after restore.

### Issue 5: Still seeing only 2 projects and 4 users
**Solution**: 
1. Verify you restored to the embedded database (not external)
2. Check which database OpenProject is using:
   ```bash
   docker exec project-management-agent-openproject_v13-1 bash -c \
       "cd /app && bundle exec rails runner 'puts \"Projects: #{Project.count}\"'"
   ```
3. If it shows 2 projects, the restore didn't work - check logs at `/tmp/restore_op13.log`

## Key Points

1. **OpenProject v13 uses embedded PostgreSQL** - Don't try to use external database container
2. **Database location**: `/var/openproject/pgdata` inside container
3. **Connection**: Always `127.0.0.1` (localhost)
4. **Always stop OpenProject** before restoring to avoid connection conflicts
5. **Wait for PostgreSQL** to be ready before attempting restore
6. **Verify counts** after restore to confirm success

## Summary

The restore process:
1. Stop OpenProject
2. Access embedded PostgreSQL
3. Drop old database
4. Create fresh database
5. Restore SQL dump
6. Verify restore
7. Restart OpenProject

Total time: ~10-15 minutes (mostly waiting for restore and restart)


