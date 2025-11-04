# Project Import Feature Guide

## Overview

The Project Import feature allows you to automatically import projects from external PM providers (JIRA, OpenProject, ClickUp) into your internal database. Simply provide the provider URL/IP and API credentials, and the system will scan and import all available projects.

## Features

- **Automatic Project Scanning**: Automatically discovers all projects from the provider
- **Duplicate Detection**: Skips existing projects to prevent duplicates
- **Sync Mapping**: Creates mappings between external and internal projects for future synchronization
- **Status/Priority Mapping**: Automatically maps provider-specific statuses and priorities to internal format
- **Error Handling**: Comprehensive error reporting for failed imports
- **Multi-Provider Support**: Works with OpenProject, JIRA Cloud, and ClickUp

## API Endpoint

### Import Projects

**POST** `/api/pm/providers/import-projects`

#### Request Body

```json
{
  "provider_type": "openproject",  // "openproject", "jira", "clickup"
  "base_url": "http://localhost:8080",
  "api_key": "your-api-key",  // For OpenProject, ClickUp
  "api_token": "your-api-token",  // For JIRA
  "email": "user@example.com",  // For JIRA Cloud
  "username": "username",  // Optional, for JIRA
  "organization_id": "team-id",  // Optional, for ClickUp
  "workspace_id": "workspace-id",  // Optional, for OpenProject
  "import_options": {
    "skip_existing": true,  // Skip projects that already exist
    "project_filter": "keyword",  // Optional: filter projects by name
    "auto_sync": false  // Enable auto-sync for future updates
  }
}
```

#### Response

```json
{
  "success": true,
  "total_projects": 5,
  "imported": 5,
  "skipped": 0,
  "errors": [],
  "project_mappings": [
    {
      "internal_project_id": "uuid",
      "external_project_id": "external-id",
      "project_name": "Project Name"
    }
  ],
  "message": "Successfully imported 5 projects. 0 skipped, 0 errors."
}
```

## Testing

### Prerequisites

1. **Database Running**: PostgreSQL database must be running
   ```bash
   docker-compose up -d postgres
   # Or if using local PostgreSQL:
   # Ensure PostgreSQL is running on localhost:5432
   ```

2. **API Server Running**: Start the FastAPI server
   ```bash
   uv run uvicorn src.server.app:app --reload --port 8000
   ```

3. **Provider Available**: Ensure the provider (OpenProject, JIRA, etc.) is accessible

### Test via API (Recommended)

#### Using curl

```bash
curl -X POST "http://localhost:8000/api/pm/providers/import-projects" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_type": "openproject",
    "base_url": "http://localhost:8080",
    "api_key": "your-api-key",
    "import_options": {
      "skip_existing": true
    }
  }'
```

#### Using the test script

```bash
./test_import_via_api.sh
```

### Test via Python Script

```bash
uv run python test_project_import.py
```

This script will:
1. Connect to the provider
2. List available projects
3. Import projects into the database
4. Verify the import in the database
5. Display detailed results

## Examples

### Import from OpenProject

```bash
curl -X POST "http://localhost:8000/api/pm/providers/import-projects" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_type": "openproject",
    "base_url": "http://localhost:8080",
    "api_key": "90b967ae7affc1b377fa9a40dc6e7cfd1dc1c992d30308fa5a7b75dbb2b08841"
  }'
```

### Import from JIRA Cloud

```bash
curl -X POST "http://localhost:8000/api/pm/providers/import-projects" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_type": "jira",
    "base_url": "https://your-domain.atlassian.net",
    "api_token": "your-jira-api-token",
    "email": "your-email@example.com"
  }'
```

### Import with Filtering

```bash
curl -X POST "http://localhost:8000/api/pm/providers/import-projects" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_type": "openproject",
    "base_url": "http://localhost:8080",
    "api_key": "your-api-key",
    "import_options": {
      "skip_existing": true,
      "project_filter": "production",  // Only import projects with "production" in name
      "auto_sync": true
    }
  }'
```

## Status Mapping

The system automatically maps provider-specific statuses to internal statuses:

| Provider Status | Internal Status |
|----------------|-----------------|
| active, open, in progress | active |
| completed, done, closed | completed |
| on hold, paused | on_hold |
| cancelled | cancelled |
| (others) | planning |

## Priority Mapping

| Provider Priority | Internal Priority |
|-------------------|-------------------|
| highest, critical, blocker | high |
| high, major | high |
| low, minor, trivial | low |
| lowest | low |
| (others) | medium |

## Database Schema

Projects are stored in the `projects` table, and mappings are created in the `project_sync_mappings` table:

- **projects**: Internal project storage
- **project_sync_mappings**: Maps external project IDs to internal project IDs for synchronization

## Troubleshooting

### "Connection refused" error
- Ensure the database is running: `docker-compose ps postgres`
- Check database connection string in `.env`

### "PM Provider not configured" error
- Verify provider credentials are correct
- Check provider URL/IP is accessible
- For JIRA Cloud, ensure email and API token are correct

### No projects imported
- Verify the provider has projects available
- Check API credentials have proper permissions
- Review error messages in the response

### Projects not appearing in database
- Check user exists in database (the system uses the first available user)
- Verify database connection
- Check import response for errors

## Next Steps

After importing projects, you can:
- View imported projects via the PM chat interface
- Set up automatic synchronization (if `auto_sync: true` was set)
- Import tasks and other project data (future enhancement)
- Manage projects through the unified interface
