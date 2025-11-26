# OpenProject Database Disk Space Issue

## Problem Summary

The OpenProject v13 database has run out of disk space, causing 500 Internal Server Errors when querying work packages for large projects.

## Evidence

### Error from OpenProject Logs
```
ERROR -- : PG::DiskFull: ERROR: could not write to file "base/pgsql_tmp/pgsql_tmp12110.65": No space left on device
```

### Disk Usage
```bash
$ docker exec project-management-agent-openproject_db_v13-1 df -h /var/lib/postgresql/data
Filesystem      Size  Used Avail Use% Mounted on
/dev/vda1        59G   56G  5.8M 100% /var/lib/postgresql/data
```

**Status**: 100% full (only 5.8MB available out of 59GB)

## Impact

- **Project 478**: Returns 500 error (has many work packages, triggers disk write)
- **Projects 492, 495, 496**: Work fine (fewer/no work packages, minimal disk usage)
- **Sprint analysis**: Works correctly after composite ID fix
- **Project listing**: Works (read-only operation)

## Solutions

### Immediate Fix (Recommended)
Free up disk space on the database volume:

```bash
# 1. Connect to the database container
docker exec -it project-management-agent-openproject_db_v13-1 bash

# 2. Clean up PostgreSQL temporary files
rm -rf /var/lib/postgresql/data/base/pgsql_tmp/*

# 3. Vacuum the database to reclaim space
psql -U postgres -d openproject -c "VACUUM FULL;"

# 4. Check disk usage again
df -h /var/lib/postgresql/data
```

### Long-term Solutions

1. **Increase Volume Size**
   - Expand the Docker volume or underlying storage
   - Recommended: At least 100GB for production use

2. **Database Maintenance**
   - Set up automatic VACUUM operations
   - Archive old work packages
   - Implement data retention policies

3. **Monitoring**
   - Add disk space monitoring alerts
   - Set up automated cleanup scripts

## Code Changes Made

Added graceful error handling in `src/pm_providers/openproject_v13.py`:
- Catches 500 errors during task fetching
- Logs informative error messages about potential disk space issues
- Returns partial results instead of crashing completely

## Testing After Fix

Once disk space is freed:
```bash
# Test the previously failing endpoint
curl "http://localhost:8000/api/pm/projects/8eedf4f4-6c0e-4061-bca2-4dc10a118f7a:478/tasks"

# Should return task data instead of 500 error
```
