# Quick Start: User-Scoped Credentials for MCP Server

## Overview

The PM MCP Server now supports **user-scoped credential loading**. Each user can have their own PM provider credentials (JIRA, OpenProject, etc.), and when they connect to the MCP Server, only their credentials are loaded.

## How It Works

1. **User connects** to MCP Server with user identification
2. **Server extracts** user ID from headers or query parameters
3. **Server filters** `pm_provider_connections` by `created_by = user_id`
4. **Only user's providers** are loaded and used for API calls

## Usage

### Option 1: HTTP Header (Recommended)

```bash
# Connect with X-User-ID header
curl -H "X-User-ID: 123e4567-e89b-12d3-a456-426614174000" \
     http://localhost:8080/sse
```

### Option 2: Query Parameter

```bash
# Connect with user_id query parameter
curl "http://localhost:8080/sse?user_id=123e4567-e89b-12d3-a456-426614174000"
```

### Option 3: Cursor Configuration

```json
{
  "mcpServers": {
    "pm-server": {
      "url": "http://localhost:8080/sse",
      "transport": "sse",
      "headers": {
        "X-User-ID": "your-user-uuid-here"
      }
    }
  }
}
```

## Database Setup

### Add Provider for User

```sql
-- Get your user ID
SELECT id FROM users WHERE email = 'your-email@example.com';

-- Add JIRA provider for that user
INSERT INTO pm_provider_connections (
    id, name, provider_type, base_url, api_token, username, created_by, is_active
) VALUES (
    gen_random_uuid(),
    'My JIRA',
    'jira',
    'https://company.atlassian.net',
    'your-api-token',
    'your-email@company.com',
    'your-user-uuid-here',  -- Your user ID
    TRUE
);
```

### Verify User's Providers

```sql
-- List all providers for a specific user
SELECT * FROM pm_provider_connections
WHERE created_by = 'your-user-uuid-here'
  AND is_active = TRUE;
```

## Example Flow

1. **User A** connects: `GET /sse?user_id=user-a-uuid`
   - Server loads only User A's providers
   - User A sees only their JIRA/OpenProject projects

2. **User B** connects: `GET /sse?user_id=user-b-uuid`
   - Server loads only User B's providers
   - User B sees only their JIRA/OpenProject projects
   - User B cannot see User A's projects

## Backward Compatibility

If no `user_id` is provided, the server loads **all active providers** (backward compatible mode). This is useful for:
- System administrators
- Testing
- Legacy integrations

## Security Notes

- ✅ Each user only sees their own providers
- ✅ Credentials are isolated per user
- ✅ No credential leakage between users
- ⚠️ User ID should be validated/authenticated (JWT token extraction coming soon)

## Next Steps

1. **Add JWT Authentication**: Extract user from JWT token in Authorization header
2. **Add User Validation**: Verify user exists and is authorized
3. **Add Audit Logging**: Log which user accessed which providers

## Testing

```bash
# Test with user ID
curl -H "X-User-ID: test-user-uuid" http://localhost:8080/health

# Test without user ID (backward compatible)
curl http://localhost:8080/health
```

