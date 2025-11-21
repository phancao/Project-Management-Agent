# Docker URL Conversion Architecture

## Problem Statement

When running services in Docker, containers cannot use `localhost` to connect to other containers. They must use Docker service names (e.g., `openproject_v13:80` instead of `localhost:8081`).

However, storing Docker service names in the database creates problems:
1. **Cloud Deployment**: Docker service names don't exist in cloud environments (Kubernetes, ECS, etc.)
2. **Separate Servers**: If MCP server and backend are on different servers, Docker service names won't resolve
3. **User Experience**: Users see `localhost:8081` in the browser, but database has `openproject_v13:80` - inconsistent

## Solution

**Store original URLs in database, convert only at runtime when making API calls.**

### Architecture

```
User Input: http://localhost:8081
    ↓
Database: http://localhost:8081 (stored as-is)
    ↓
Runtime (create_pm_provider):
    - If running in Docker → converts to http://openproject_v13:80
    - If running in cloud → uses http://localhost:8081 (or actual URL)
    - If separate servers → uses http://localhost:8081 (or actual URL)
```

### Implementation

1. **Database Storage**: Store the URL exactly as the user entered it
   - `http://localhost:8081` → stored as `http://localhost:8081`
   - `https://openproject.example.com` → stored as `https://openproject.example.com`

2. **Runtime Conversion**: Convert URLs only when creating provider instances
   - Happens in `create_pm_provider()` function
   - Only converts if:
     - Running in Docker (`_is_running_in_docker()` returns True)
     - URL contains `localhost` or `127.0.0.1`
     - Port matches known Docker service mapping

3. **Duplicate Detection**: Use original URLs for duplicate checking
   - Compare `http://localhost:8081` with stored `http://localhost:8081`
   - Don't convert URLs during duplicate detection

## Deployment Scenarios

### Scenario 1: Local Docker Compose
- **User enters**: `http://localhost:8081`
- **Database stores**: `http://localhost:8081`
- **Runtime converts**: `http://openproject_v13:80` (for API calls)
- **Works**: ✅ Yes, containers can resolve service names

### Scenario 2: Cloud Deployment (Kubernetes/ECS)
- **User enters**: `https://openproject.example.com`
- **Database stores**: `https://openproject.example.com`
- **Runtime converts**: No conversion (not localhost, not in Docker)
- **Works**: ✅ Yes, uses actual URL

### Scenario 3: Separate Servers
- **MCP Server**: `mcp.example.com`
- **Backend**: `backend.example.com`
- **OpenProject**: `openproject.example.com`
- **User enters**: `https://openproject.example.com`
- **Database stores**: `https://openproject.example.com`
- **Runtime converts**: No conversion (not localhost)
- **Works**: ✅ Yes, each server uses actual URLs

### Scenario 4: Local Development (Not Docker)
- **User enters**: `http://localhost:8081`
- **Database stores**: `http://localhost:8081`
- **Runtime converts**: No conversion (not in Docker)
- **Works**: ✅ Yes, localhost resolves correctly

## Code Locations

1. **URL Conversion Logic**: `src/pm_providers/factory.py`
   - `_is_running_in_docker()`: Detects Docker environment
   - `_convert_localhost_to_docker_service()`: Converts URLs at runtime
   - `create_pm_provider()`: Applies conversion when creating providers

2. **Database Storage**: `src/server/app.py`
   - `pm_import_projects()`: Stores original URL (no conversion)
   - Duplicate detection: Uses original URL

3. **Provider Usage**: All provider classes use converted URLs automatically
   - OpenProjectProvider, JIRAProvider, etc. receive converted URLs
   - No changes needed in provider implementations

## Benefits

✅ **Consistent User Experience**: Users always see the URL they entered  
✅ **Cloud Compatible**: Works in any deployment environment  
✅ **Multi-Server Support**: Each server can use actual URLs  
✅ **Backward Compatible**: Existing URLs in database continue to work  
✅ **Transparent**: Conversion happens automatically, no user intervention needed

## Migration Notes

If you have existing providers with Docker service names in the database:
1. They will continue to work (conversion logic handles both)
2. Consider migrating to original URLs for consistency
3. No breaking changes required

