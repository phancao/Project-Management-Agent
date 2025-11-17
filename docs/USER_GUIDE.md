# OpenProject Import Scripts User Guide

This guide explains how to use the database restore and work package import scripts for OpenProject v13 and v16.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Restore Database](#restore-database)
3. [Import Work Packages](#import-work-packages)
4. [Common Options](#common-options)
5. [Examples](#examples)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Docker** and **Docker Compose** (for running OpenProject)
- **Python 3.8+** (for the import script)
- **PostgreSQL SQL dump file** (`.sql` file) for database restore
- **Excel workbook** (`.xlsx` file) with work package data for import

### OpenProject Setup

1. Ensure OpenProject v13 or v16 is running via Docker Compose
2. For v13: The script targets the embedded PostgreSQL database inside the app container
3. For v16: The script can work with either embedded or external PostgreSQL

### Excel Workbook Format

Your Excel workbook should contain the following columns:
- **Project Name**: Name of the OpenProject project
- **Work Package**: Task/work package name (may include type and issue ID, e.g., "Task #123: Description")
- **Assignee Name**: Full name of the person assigned to the task
- **Date**: Date when work was performed (format: DD/MM/YYYY or YYYY-MM-DD)
- **Hours**: Number of hours worked (numeric)
- **Activity**: Time entry activity name (e.g., "Development", "Testing")

---

## Restore Database

The `restore_op13_embedded.sh` script restores a PostgreSQL dump file into the embedded database of OpenProject v13.

### Basic Usage

```bash
./scripts/restore_op13_embedded.sh /path/to/openproject.sql
```

### What It Does

1. **Copies** the SQL dump into the OpenProject v13 container
2. **Preprocesses** the dump to remove incompatible statements (`\restrict`, `\unrestrict`, `transaction_timeout`)
3. **Terminates** active database connections
4. **Drops and recreates** the `openproject` database
5. **Resets** the `public` schema to avoid duplicate schema warnings
6. **Restores** the cleaned dump file
7. **Validates** the restore by checking basic counts (projects, users)
8. **Fixes** user table issues (primary keys, admin uniqueness)
9. **Generates** a fresh admin API token and saves it to `/tmp/op13_token.txt`

### Example

```bash
# Restore from a dump file in Downloads
./scripts/restore_op13_embedded.sh "/Users/phancao/Downloads/openproject.sql"
```

### Output

The script will:
- Display progress for each step
- Show basic verification counts (projects, users)
- Generate and save an API token to `/tmp/op13_token.txt`
- Report any errors encountered during restore

### Notes

- **Container Name**: The script defaults to `project-management-agent-openproject_v13-1`. You can override this by setting the `APP_CONTAINER` environment variable.
- **Token Storage**: The generated API token is saved to `/tmp/op13_token.txt` for use with the import script.
- **Database Cleanup**: The script will terminate all active connections before dropping the database to avoid "database is being accessed by other users" errors.

---

## Import Work Packages

The `import_work_packages.py` script imports work packages, time entries, users, and projects from an Excel workbook into OpenProject.

### Basic Usage

```bash
python3 scripts/import_work_packages.py \
  --server http://localhost:8081 \
  --token YOUR_API_TOKEN \
  --workbook "/path/to/workbook.xlsx" \
  --auto-assign-memberships \
  --yes
```

### Required Arguments

- `--server`: OpenProject server URL (e.g., `http://localhost:8081` for v13, `http://localhost:8080` for v16)
- `--token`: OpenProject API token (can be retrieved from `/tmp/op13_token.txt` after restore)
- `--workbook`: Path to the Excel workbook file

### Recommended Arguments

- `--auto-assign-memberships`: Automatically add users to projects as members (required for task assignments)
- `--yes`: Automatically confirm all interactive prompts (useful for automated runs)
- `--clean-cache-and-logs`: Remove previous caches and logs for a clean run
- `--op-version`: Specify OpenProject version (`auto`, `v13`, or `v16`). Default: `auto` (auto-detects)

### Data Source Options

For better performance on v13, use database sources:

- `--time-entry-source db`: Read time entries from database (faster for v13)
- `--verification-source db`: Use database for verification totals (faster for v13)
- `--logged-by-source db`: Read time entries from database for logged_by updates (faster for v13)

### Example: Full Import with Database Sources (v13)

```bash
TOKEN=$(cat /tmp/op13_token.txt)
python3 scripts/import_work_packages.py \
  --server http://localhost:8081 \
  --token "$TOKEN" \
  --op-version v13 \
  --workbook "/Users/phancao/Downloads/full Work Pakages - Intranet.xlsx" \
  --time-entry-source db \
  --verification-source db \
  --logged-by-source db \
  --clean-cache-and-logs \
  --auto-assign-memberships \
  --yes
```

### Import Process Steps

The script performs the following steps:

1. **Clean caches and logs** (if `--clean-cache-and-logs` is used)
2. **Validate workbook** structure and content
3. **Load workbook data** into staging structures
4. **Load staging cache** (if exists) to speed up matching
5. **Fetch users** from OpenProject and map to Excel users
6. **Create missing users** (with login=email format: `first.last@galaxytechnology.vn`)
7. **Fetch projects** from OpenProject
8. **Create missing projects**
9. **Fetch work package types**
10. **Inspect project configuration**
11. **Validate time entry activities** (create missing ones if needed)
12. **Pre-activate users** (activate/unlock users before membership assignment)
13. **Ensure project type permissions**
14. **Ensure project memberships** (add users to projects)
15. **Check existing work packages** (match by issue ID or subject)
16. **Create missing work packages**
17. **Log time entries** (create time entries for work packages)
18. **Update time entry logged_by field** (set correct author)
19. **Adjust activity history** (align timestamps)
20. **Update project creation dates**
21. **Verify import** (compare Excel totals with OpenProject totals)

### Output

The script provides:
- **Progress bars** for long-running operations (1% increments)
- **Summary tables** showing existing/missing/created counts for users, projects, work packages
- **Verification summary** comparing Excel totals with OpenProject totals
- **Per-project breakdown** showing hours per project
- **Instance totals** showing before/after counts for projects, users, work packages
- **Total duration** in H:MM:SS format

### Special Modes

#### Analyze Only

Check which Excel rows are missing time entries without importing:

```bash
python3 scripts/import_work_packages.py \
  --server http://localhost:8081 \
  --token "$TOKEN" \
  --workbook "/path/to/workbook.xlsx" \
  --analyze-only
```

#### Update Logged By Only

Update the `logged_by` field for existing time entries:

```bash
python3 scripts/import_work_packages.py \
  --server http://localhost:8081 \
  --token "$TOKEN" \
  --workbook "/path/to/workbook.xlsx" \
  --update-logged-by
```

#### Update Project Dates Only

Update project creation dates based on earliest work package/time entry dates:

```bash
python3 scripts/import_work_packages.py \
  --server http://localhost:8081 \
  --token "$TOKEN" \
  --update-project-dates
```

#### Dry Run

Validate and show planned actions without creating anything:

```bash
python3 scripts/import_work_packages.py \
  --server http://localhost:8081 \
  --token "$TOKEN" \
  --workbook "/path/to/workbook.xlsx" \
  --dry-run
```

---

## Common Options

### Import Script Options

| Option | Description | Default |
|--------|-------------|---------|
| `--workbook` | Path to Excel workbook | `assets/openproject/very short Openproject Data.xlsx` |
| `--server` | OpenProject server URL | Prompted if not provided |
| `--token` | OpenProject API token | Prompted if not provided |
| `--op-version` | OpenProject version (`auto`, `v13`, `v16`) | `auto` |
| `--auto-assign-memberships` | Automatically add users to projects | `false` |
| `--yes` | Auto-confirm all prompts | `false` |
| `--clean-cache-and-logs` | Remove previous caches/logs | `false` |
| `--time-entry-source` | Source for time entries (`auto`, `db`, `api`) | `auto` |
| `--verification-source` | Source for verification (`auto`, `db`, `api`) | `auto` |
| `--logged-by-source` | Source for logged_by updates (`auto`, `db`, `api`) | `auto` |
| `--default-type` | Default work package type | `Task` |
| `--member-role` | Role name for project members | `Member` |
| `--user-email-domain` | Email domain for new users | `galaxytechnology.vn` |
| `--dry-run` | Show planned actions without creating | `false` |
| `--analyze-only` | Only analyze missing entries | `false` |
| `--update-logged-by` | Only update logged_by field | `false` |
| `--update-project-dates` | Only update project dates | `false` |
| `--debug-log` | Path to debug log file | `/tmp/op_import_debug.log` |

---

## Examples

### Example 1: Complete Workflow (Restore + Import)

```bash
# Step 1: Restore database
./scripts/restore_op13_embedded.sh "/Users/phancao/Downloads/openproject.sql"

# Step 2: Import work packages
TOKEN=$(cat /tmp/op13_token.txt)
python3 scripts/import_work_packages.py \
  --server http://localhost:8081 \
  --token "$TOKEN" \
  --op-version v13 \
  --workbook "/Users/phancao/Downloads/full Work Pakages - Intranet.xlsx" \
  --time-entry-source db \
  --verification-source db \
  --logged-by-source db \
  --clean-cache-and-logs \
  --auto-assign-memberships \
  --yes
```

### Example 2: Quick Test with Small Dataset

```bash
TOKEN=$(cat /tmp/op13_token.txt)
python3 scripts/import_work_packages.py \
  --server http://localhost:8081 \
  --token "$TOKEN" \
  --workbook "/Users/phancao/Downloads/very short Openproject Data.xlsx" \
  --auto-assign-memberships \
  --yes
```

### Example 3: Resume After Interruption

If the import was interrupted, you can resume by running the same command again. The script uses caches to avoid creating duplicates:

```bash
TOKEN=$(cat /tmp/op13_token.txt)
python3 scripts/import_work_packages.py \
  --server http://localhost:8081 \
  --token "$TOKEN" \
  --workbook "/path/to/workbook.xlsx" \
  --auto-assign-memberships \
  --yes
```

### Example 4: Import to OpenProject v16

```bash
python3 scripts/import_work_packages.py \
  --server http://localhost:8080 \
  --token "YOUR_V16_TOKEN" \
  --op-version v16 \
  --workbook "/path/to/workbook.xlsx" \
  --auto-assign-memberships \
  --yes
```

---

## Troubleshooting

### Database Restore Issues

#### Error: "database is being accessed by other users"

**Solution**: The restore script automatically handles this by terminating active connections. If it still fails, manually stop OpenProject:

```bash
docker-compose stop openproject_v13
# Then run restore script
docker-compose start openproject_v13
```

#### Error: "schema public already exists"

**Solution**: The restore script automatically resets the schema. If you see this error, it's usually harmless and the restore continues.

#### Error: "could not create unique index users_pkey"

**Solution**: This indicates duplicate user IDs in the dump. The restore script attempts to fix this by moving special principals (AnonymousUser, SystemUser) to new IDs. If issues persist, check the dump file for data integrity.

### Import Script Issues

#### Error: "Principal cannot be assigned to a project"

**Cause**: User is not active, locked, or has duplicate ID conflicts.

**Solution**: 
- The script automatically attempts to activate/unlock users before assignment
- If it fails, manually activate the user in OpenProject Web UI
- Check for duplicate user IDs in the database

#### Error: "User 618 not found in database"

**Cause**: API returned a user ID that doesn't exist in the database (version mismatch or data inconsistency).

**Solution**:
- Ensure you're using the correct OpenProject version (`--op-version v13` or `v16`)
- Restore the database again to ensure consistency
- Check that the API token belongs to the correct OpenProject instance

#### Error: "Email has already been taken"

**Cause**: User creation attempted with an email that already exists.

**Solution**: The script automatically handles this by:
- Mapping existing users by email/login before creating new ones
- Adding numeric suffixes to emails if needed (e.g., `user@domain.com2`)

#### Import is Slow

**Solution**: Use database sources for v13:

```bash
--time-entry-source db \
--verification-source db \
--logged-by-source db
```

#### Verification Shows Mismatched Totals

**Solution**:
- Check the debug log at `/tmp/op_import_debug.log` for detailed information
- Ensure all time entries were created successfully
- Verify that the Excel workbook data is correct
- Run with `--verification-source db` for more accurate totals on v13

### General Issues

#### Script Hangs or Takes Too Long

**Solution**:
- Check Docker container status: `docker ps`
- Check OpenProject logs: `docker logs project-management-agent-openproject_v13-1`
- Use database sources instead of API for large datasets
- Check network connectivity to OpenProject server

#### Token Authentication Fails

**Solution**:
- For v13: Generate a new token via the restore script or Rails console
- Ensure the token is not expired
- Verify the token belongs to an admin user
- Check that OpenProject is running and accessible

---

## Additional Resources

- **OpenProject v13 API Research**: See `docs/OP_V13_API_RESEARCH.md`
- **Database Restore Guide**: See `docs/OP_V13_DATABASE_RESTORE.md`
- **Debug Logs**: Check `/tmp/op_import_debug.log` for detailed execution logs
- **Import Logs**: Check `/tmp/op_import_run_latest.log` for the latest import run

---

## Support

For issues or questions:
1. Check the debug log: `/tmp/op_import_debug.log`
2. Check the import log: `/tmp/op_import_run_latest.log`
3. Review OpenProject container logs: `docker logs project-management-agent-openproject_v13-1`
4. Verify database state: Check for duplicate IDs or missing constraints

