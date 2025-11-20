# How to Add JIRA/OpenProject Credentials for MCP Server

This guide explains the complete workflow for users to add their PM provider credentials (JIRA, OpenProject, etc.) so they can use them via Cursor and the MCP Server.

## Complete User Journey

### Step 1: User Gets JIRA API Token

**From JIRA:**
1. Login to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Name it (e.g., "MCP Server Access")
4. Copy the token (e.g., `ATATT3xFfGF0...`)

**Required Information:**
- **JIRA URL**: `https://your-domain.atlassian.net`
- **Email**: Your JIRA account email (e.g., `user@company.com`)
- **API Token**: The token you just created

### Step 2: User Adds Credentials to System

Users can add their JIRA credentials via **three methods**:

#### Method A: Web UI (Recommended)

1. **User logs into web application**
2. **Navigate to Provider Management** (usually in Settings or PM section)
3. **Click "Add Provider"** or "Connect JIRA"
4. **Fill in the form:**
   - Provider Type: `jira`
   - Base URL: `https://your-domain.atlassian.net`
   - API Token: `ATATT3xFfGF0...`
   - Username: `user@company.com` (your email)
5. **Click "Save" or "Import Projects"**

**What happens:**
- Frontend calls: `POST /api/pm/providers/import-projects`
- Backend stores credentials in `pm_provider_connections` table
- `created_by` field is set to the authenticated user's ID
- Credentials are now available for that user

#### Method B: API Endpoint

```bash
POST /api/pm/providers/import-projects
Authorization: Bearer <user-jwt-token>
Content-Type: application/json

{
  "provider_type": "jira",
  "base_url": "https://your-domain.atlassian.net",
  "api_token": "ATATT3xFfGF0...",
  "username": "user@company.com",
  "import_options": {
    "skip_existing": true,
    "auto_sync": false
  }
}
```

**Note**: The `created_by` field should be automatically set from the authenticated user's JWT token.

#### Method C: Direct SQL (For Testing/Admin)

```sql
-- Get user ID
SELECT id FROM users WHERE email = 'user@example.com';

-- Add JIRA provider for that user
INSERT INTO pm_provider_connections (
    id,
    name,
    provider_type,
    base_url,
    api_token,
    username,
    created_by,
    is_active
) VALUES (
    gen_random_uuid(),
    'My JIRA',
    'jira',
    'https://company.atlassian.net',
    'ATATT3xFfGF0...',
    'user@company.com',
    'user-uuid-here',  -- User's UUID
    TRUE
);
```

### Step 3: User Generates MCP API Key

After adding JIRA credentials, user needs an MCP API key for Cursor:

```bash
POST /api/users/me/mcp-keys
Authorization: Bearer <user-jwt-token>
{
  "name": "Cursor Desktop"
}

# Response:
{
  "api_key": "mcp_a1b2c3d4e5f6...",
  "user_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

### Step 4: User Configures Cursor

User copies the MCP API key and configures Cursor:

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

### Step 5: Cursor Connects and Uses Credentials

**Flow:**
1. Cursor connects with MCP API key
2. MCP Server validates API key → gets `user_id`
3. MCP Server loads providers where `created_by = user_id`
4. MCP Server finds user's JIRA credentials
5. MCP Server uses JIRA API token to call JIRA API
6. User can now use MCP tools: "list my projects", "create task", etc.

## Important: Current Implementation Issue

⚠️ **The current `/api/pm/providers/import-projects` endpoint may not set `created_by` correctly!**

**Current Code** (`src/server/app.py` line 2749):
```python
provider = PMProviderConnection(
    name=f"{request.provider_type} - {request.base_url}",
    provider_type=request.provider_type,
    base_url=request.base_url,
    # ... other fields ...
    # created_by is NOT set! ❌
)
```

**Fix Needed:**
The endpoint should extract `user_id` from the JWT token and set `created_by`:

```python
# Get user from JWT token
user = await get_current_user(request)  # Extract from Authorization header
provider = PMProviderConnection(
    # ... other fields ...
    created_by=user["user_id"],  # ✅ Set user ID
)
```

## Complete Flow Diagram

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       │ 1. Gets JIRA API token from Atlassian
       ▼
┌─────────────────┐
│  JIRA System    │
│  (External)     │
└──────┬──────────┘
       │
       │ 2. User adds credentials via Web UI
       │    POST /api/pm/providers/import-projects
       │    { api_token, username, base_url }
       ▼
┌─────────────────┐
│  Backend API    │
│  /api/pm/       │
│  providers/      │
│  import-projects │
└──────┬──────────┘
       │
       │ 3. Extract user_id from JWT
       │    Store in pm_provider_connections
       │    created_by = user_id
       ▼
┌─────────────────┐
│  Database       │
│  pm_provider_   │
│  connections    │
│  created_by:    │
│  user_id        │
└──────┬──────────┘
       │
       │ 4. User generates MCP API key
       │    POST /api/users/me/mcp-keys
       ▼
┌─────────────────┐
│  Database       │
│  user_mcp_      │
│  api_keys       │
│  api_key:       │
│  mcp_xxx        │
└──────┬──────────┘
       │
       │ 5. User configures Cursor
       │    with MCP API key
       ▼
┌─────────────┐
│   Cursor    │
└──────┬──────┘
       │
       │ 6. Cursor connects
       │    GET /sse
       │    Headers: X-MCP-API-Key: mcp_xxx
       ▼
┌─────────────────┐
│  MCP Server     │
│  /sse           │
└──────┬──────────┘
       │
       │ 7. Validate MCP API key
       │    → Get user_id
       ▼
┌─────────────────┐
│  Database       │
│  user_mcp_      │
│  api_keys       │
│  → user_id      │
└──────┬──────────┘
       │
       │ 8. Load user's providers
       │    WHERE created_by = user_id
       ▼
┌─────────────────┐
│  Database       │
│  pm_provider_   │
│  connections    │
│  → JIRA API     │
│    token        │
└──────┬──────────┘
       │
       │ 9. Use JIRA API token
       │    to call JIRA API
       ▼
┌─────────────────┐
│  JIRA API       │
│  → Returns      │
│    user's        │
│    projects      │
└─────────────────┘
```

## Example: Complete Setup

### 1. User Gets JIRA Token
```bash
# User goes to Atlassian
# Creates API token: ATATT3xFfGF0abc123...
```

### 2. User Adds via Web UI
```
Provider Type: jira
Base URL: https://company.atlassian.net
API Token: ATATT3xFfGF0abc123...
Username: user@company.com
```

### 3. Backend Stores (with user_id)
```sql
INSERT INTO pm_provider_connections (
    created_by,  -- Set from JWT token
    provider_type,
    api_token,
    username,
    base_url
) VALUES (
    'user-uuid-from-jwt',
    'jira',
    'ATATT3xFfGF0abc123...',
    'user@company.com',
    'https://company.atlassian.net'
);
```

### 4. User Gets MCP API Key
```bash
POST /api/users/me/mcp-keys
→ Returns: mcp_a1b2c3d4e5f6...
```

### 5. Cursor Uses It
```json
{
  "headers": {
    "X-MCP-API-Key": "mcp_a1b2c3d4e5f6..."
  }
}
```

### 6. MCP Server Loads User's JIRA
```python
# Server validates MCP API key → user_id
# Server queries: WHERE created_by = user_id
# Finds JIRA credentials
# Uses them to call JIRA API
```

## Summary

**To use JIRA with Cursor:**

1. ✅ Get JIRA API token from Atlassian
2. ✅ Add credentials via Web UI (`/api/pm/providers/import-projects`)
3. ✅ Generate MCP API key (`/api/users/me/mcp-keys`)
4. ✅ Configure Cursor with MCP API key
5. ✅ Use MCP tools in Cursor!

**Key Point**: The JIRA credentials are stored in `pm_provider_connections` with `created_by = user_id`, so when Cursor connects with the MCP API key, the server knows which user's JIRA credentials to use.









