# Setting Up External Clients (Cursor) with PM MCP Server

This guide explains how external clients like Cursor can connect to the PM MCP Server with user-specific credentials.

## Problem

When Cursor (or any external MCP client) connects to the PM MCP Server:
- **How does Cursor know which user it represents?**
- **How does the server identify the user?**
- **How does the server load only that user's PM provider credentials?**

## Solution: User API Keys

Each user gets a unique **MCP API Key** that:
1. **Authenticates** the connection
2. **Identifies** the user
3. **Loads** only that user's PM provider credentials

## Step-by-Step Setup

### Step 1: Run Database Migration

```bash
# Apply the migration to create user_mcp_api_keys table
psql -U postgres -d pm_agent -f database/migrations/add_user_mcp_api_keys.sql
```

Or via Docker:
```bash
docker-compose exec db psql -U postgres -d pm_agent -f /app/database/migrations/add_user_mcp_api_keys.sql
```

### Step 2: Generate API Key for User

**Option A: Via API (Recommended)**
```bash
# User authenticates via web UI, gets JWT token
# Then generates MCP API key
POST /api/users/me/mcp-keys
Authorization: Bearer <jwt-token>
{
  "name": "Cursor Desktop"
}

# Response:
{
  "api_key": "mcp_a1b2c3d4e5f6...",
  "user_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Option B: Via SQL (For Testing)**
```sql
-- Get user ID
SELECT id FROM users WHERE email = 'user@example.com';

-- Generate API key
INSERT INTO user_mcp_api_keys (user_id, api_key, name, is_active)
VALUES (
    'user-uuid-here',
    'mcp_' || encode(gen_random_bytes(32), 'hex'),
    'Cursor Desktop',
    TRUE
);

-- Get the generated key
SELECT api_key FROM user_mcp_api_keys 
WHERE user_id = 'user-uuid-here' 
ORDER BY created_at DESC 
LIMIT 1;
```

**Option C: Via Python Script**
```python
from mcp_server.auth import create_user_api_key

# Generate API key for user
api_key = await create_user_api_key(
    user_id="123e4567-e89b-12d3-a456-426614174000",
    name="Cursor Desktop"
)
print(f"Your MCP API Key: {api_key}")
```

### Step 3: Configure Cursor

In Cursor's MCP configuration file (usually `~/.cursor/mcp.json` or similar):

```json
{
  "mcpServers": {
    "pm-server": {
      "url": "http://localhost:8080/sse",
      "transport": "sse",
      "headers": {
        "X-MCP-API-Key": "mcp_a1b2c3d4e5f6..."
      }
    }
  }
}
```

**Alternative: Using Authorization Header**
```json
{
  "mcpServers": {
    "pm-server": {
      "url": "http://localhost:8080/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer mcp_a1b2c3d4e5f6..."
      }
    }
  }
}
```

### Step 4: Verify Connection

1. **Restart Cursor** to load the new MCP configuration
2. **Check Cursor logs** for connection status
3. **Test MCP tools** - try "list my projects"

## How It Works

```
┌─────────────┐
│   User      │
│  (Browser)  │
└──────┬──────┘
       │
       │ 1. Login → Generate API Key
       ▼
┌─────────────────┐
│  Database       │
│  user_mcp_      │
│  api_keys       │
│  (stores key)   │
└──────┬──────────┘
       │
       │ 2. Copy API Key
       ▼
┌─────────────┐
│   Cursor    │
│  (External) │
└──────┬──────┘
       │
       │ 3. Connect with API Key
       │    GET /sse
       │    Headers: X-MCP-API-Key: mcp_xxx
       ▼
┌─────────────────┐
│  MCP Server     │
│  /sse           │
└──────┬──────────┘
       │
       │ 4. Validate API Key
       │    → Lookup in database
       │    → Get user_id
       ▼
┌─────────────────┐
│  Database       │
│  user_mcp_      │
│  api_keys       │
│  → user_id      │
└──────┬──────────┘
       │
       │ 5. Load user's providers
       │    WHERE created_by = user_id
       ▼
┌─────────────────┐
│  PMHandler      │
│  (user-scoped)  │
│  → Only user's  │
│    credentials  │
└─────────────────┘
```

## Authentication Methods

The MCP Server supports multiple authentication methods (in priority order):

### 1. MCP API Key (Recommended for External Clients)
```bash
# Header
X-MCP-API-Key: mcp_a1b2c3d4e5f6...

# Or Authorization header
Authorization: Bearer mcp_a1b2c3d4e5f6...

# Or query parameter
?api_key=mcp_a1b2c3d4e5f6...
```

### 2. Direct User ID (For Internal/Testing)
```bash
# Header
X-User-ID: 123e4567-e89b-12d3-a456-426614174000

# Or query parameter
?user_id=123e4567-e89b-12d3-a456-426614174000
```

### 3. JWT Token (Future)
```bash
# Authorization header with JWT
Authorization: Bearer <jwt-token>
# Server extracts user_id from JWT claims
```

## Security Best Practices

1. **Never share API keys** - Each user should have their own
2. **Rotate keys regularly** - Revoke and regenerate periodically
3. **Use HTTPS in production** - Always encrypt connections
4. **Name your keys** - Helps identify which client is using which key
5. **Revoke unused keys** - Delete keys for clients you no longer use

## Managing API Keys

### List User's API Keys
```sql
SELECT id, name, api_key, last_used_at, created_at, is_active
FROM user_mcp_api_keys
WHERE user_id = 'user-uuid-here'
ORDER BY created_at DESC;
```

### Revoke an API Key
```sql
UPDATE user_mcp_api_keys
SET is_active = FALSE
WHERE api_key = 'mcp_a1b2c3d4e5f6...'
  AND user_id = 'user-uuid-here';
```

### Check API Key Usage
```sql
SELECT 
    name,
    last_used_at,
    created_at,
    is_active
FROM user_mcp_api_keys
WHERE user_id = 'user-uuid-here'
ORDER BY last_used_at DESC NULLS LAST;
```

## Troubleshooting

### "Invalid API key" Error
- Check API key is correct (no extra spaces)
- Verify key exists in database: `SELECT * FROM user_mcp_api_keys WHERE api_key = 'your-key';`
- Check key is active: `SELECT is_active FROM user_mcp_api_keys WHERE api_key = 'your-key';`
- Check key hasn't expired: `SELECT expires_at FROM user_mcp_api_keys WHERE api_key = 'your-key';`

### "No providers found" Error
- Verify user has providers: `SELECT * FROM pm_provider_connections WHERE created_by = 'user-uuid';`
- Check providers are active: `SELECT * FROM pm_provider_connections WHERE created_by = 'user-uuid' AND is_active = TRUE;`

### Connection Issues
- Verify MCP Server is running: `curl http://localhost:8080/health`
- Check Cursor logs for connection errors
- Verify URL is correct: `http://localhost:8080/sse`
- Check headers are set correctly in Cursor config

## Example: Complete User Journey

1. **User registers/logs in** → Gets user account
2. **User adds PM provider** → JIRA credentials stored in `pm_provider_connections` with `created_by = user_id`
3. **User generates MCP API key** → Key stored in `user_mcp_api_keys` with `user_id`
4. **User configures Cursor** → Adds API key to Cursor's MCP config
5. **Cursor connects** → Sends API key in header
6. **Server validates** → Looks up user_id from API key
7. **Server loads providers** → Only providers where `created_by = user_id`
8. **User uses tools** → "list my projects" → Only sees their projects

## Summary

✅ **Database stores**: User API keys in `user_mcp_api_keys` table  
✅ **External clients**: Send API key in `X-MCP-API-Key` header  
✅ **Server validates**: API key → gets user_id → loads user's providers  
✅ **User isolation**: Each user only sees their own PM provider credentials  
✅ **Secure**: API keys are unique, can be revoked, and track usage

This ensures that when User A connects via Cursor, they only see their own JIRA/OpenProject projects, and User B sees only their own projects.









