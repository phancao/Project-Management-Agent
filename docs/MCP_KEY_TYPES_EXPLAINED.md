# Understanding the Two Types of API Keys

This document clarifies the difference between **MCP API Keys** and **PM Provider API Keys**.

## Two Different Keys for Two Different Purposes

### 1. MCP API Key (For Connecting to MCP Server)

**Purpose**: Authenticate external clients (Cursor, VS Code, etc.) to the MCP Server

**Created by**: `generate_mcp_api_key()` and `create_user_api_key()` in `src/mcp_servers/pm_server/auth.py`

**Stored in**: `user_mcp_api_keys` table

**Format**: `mcp_a1b2c3d4e5f6...` (64 hex characters)

**Used by**: Cursor, VS Code, Windsurf (external MCP clients)

**Example**:
```json
// Cursor configuration
{
  "mcpServers": {
    "pm-server": {
      "url": "http://localhost:8080/sse",
      "headers": {
        "X-MCP-API-Key": "mcp_a1b2c3d4e5f6..."  // ← This is the MCP API Key
      }
    }
  }
}
```

**Flow**:
```
Cursor → Uses MCP API Key → Authenticates to MCP Server → Server identifies user
```

### 2. PM Provider API Keys (For External PM Systems)

**Purpose**: Authenticate to external PM systems (JIRA, OpenProject, ClickUp)

**Created by**: User in external system (JIRA, OpenProject, etc.)

**Stored in**: `pm_provider_connections` table

**Format**: Varies by provider
- JIRA: API token from Atlassian
- OpenProject: Base64-encoded "apikey:token"
- ClickUp: API key from ClickUp

**Used by**: MCP Server to make API calls to JIRA/OpenProject/etc.

**Example**:
```sql
-- Stored in pm_provider_connections table
INSERT INTO pm_provider_connections (
    user_id,
    provider_type,
    base_url,
    api_token,  -- ← This is the JIRA API token (PM Provider Key)
    username
) VALUES (
    'user-uuid',
    'jira',
    'https://company.atlassian.net',
    'ATATT3xFfGF0...',  -- JIRA API token
    'user@company.com'
);
```

**Flow**:
```
MCP Server → Uses JIRA API Token → Calls JIRA API → Gets user's projects
```

## Complete Flow Diagram

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       │ 1. User creates JIRA account
       │    Gets JIRA API token
       ▼
┌─────────────────┐
│  JIRA System    │
│  (External)     │
└──────┬──────────┘
       │
       │ 2. User stores JIRA credentials
       │    in pm_provider_connections
       ▼
┌─────────────────┐
│  Database       │
│  pm_provider_   │
│  connections    │
│  api_token:     │
│  "ATATT3x..."   │ ← PM Provider Key (JIRA)
└──────┬──────────┘
       │
       │ 3. User generates MCP API key
       │    for Cursor to use
       ▼
┌─────────────────┐
│  Database       │
│  user_mcp_      │
│  api_keys       │
│  api_key:       │
│  "mcp_abc..."   │ ← MCP API Key (for Cursor)
└──────┬──────────┘
       │
       │ 4. User configures Cursor
       │    with MCP API key
       ▼
┌─────────────┐
│   Cursor    │
│  (External) │
└──────┬──────┘
       │
       │ 5. Cursor connects with MCP API key
       │    GET /sse
       │    Headers: X-MCP-API-Key: mcp_abc...
       ▼
┌─────────────────┐
│  MCP Server     │
│  /sse           │
└──────┬──────────┘
       │
       │ 6. Server validates MCP API key
       │    → Gets user_id
       ▼
┌─────────────────┐
│  Database       │
│  user_mcp_      │
│  api_keys       │
│  → user_id      │
└──────┬──────────┘
       │
       │ 7. Server loads user's PM providers
       │    WHERE created_by = user_id
       ▼
┌─────────────────┐
│  Database       │
│  pm_provider_   │
│  connections    │
│  → JIRA API     │
│    token        │ ← PM Provider Key
└──────┬──────────┘
       │
       │ 8. Server uses JIRA API token
       │    to call JIRA API
       ▼
┌─────────────────┐
│  JIRA API       │
│  (External)     │
│  → Returns      │
│    user's        │
│    projects      │
└─────────────────┘
```

## Key Comparison Table

| Aspect | MCP API Key | PM Provider API Key |
|--------|-------------|---------------------|
| **Purpose** | Authenticate to MCP Server | Authenticate to JIRA/OpenProject/etc. |
| **Used by** | Cursor, VS Code, Windsurf | MCP Server (internally) |
| **Created by** | Your system (`generate_mcp_api_key()`) | External system (JIRA, OpenProject) |
| **Stored in** | `user_mcp_api_keys` table | `pm_provider_connections` table |
| **Format** | `mcp_<64-hex-chars>` | Varies (JIRA token, OpenProject key, etc.) |
| **Scope** | One key per user per client | One key per user per PM provider |
| **Example** | `mcp_a1b2c3d4e5f6...` | `ATATT3xFfGF0...` (JIRA) |

## Summary

**MCP API Key** (`generate_mcp_api_key()`):
- ✅ Key for **Cursor to connect to MCP Server**
- ✅ Stored in `user_mcp_api_keys` table
- ✅ Format: `mcp_xxx`
- ✅ One per user per client (Cursor, VS Code, etc.)

**PM Provider API Key** (JIRA/OpenProject credentials):
- ✅ Key for **MCP Server to connect to JIRA/OpenProject**
- ✅ Stored in `pm_provider_connections` table
- ✅ Format: Varies by provider
- ✅ One per user per PM provider (JIRA, OpenProject, ClickUp, etc.)

**The Flow**:
1. User has JIRA credentials → stored in `pm_provider_connections`
2. User generates MCP API key → stored in `user_mcp_api_keys`
3. Cursor uses MCP API key → connects to MCP Server
4. MCP Server uses JIRA credentials → calls JIRA API
5. User sees their JIRA projects in Cursor

Both keys are needed, but they serve different purposes in the authentication chain!

