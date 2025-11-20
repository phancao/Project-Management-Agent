# Complete User Flow: Using Cursor with JIRA via MCP Server

This document explains the **complete end-to-end flow** for a user to connect Cursor to the MCP Server and use their JIRA credentials.

## The Question

**"How do we collect the JIRA API key when using Cursor?"**

**Answer**: Users add their JIRA credentials **before** connecting Cursor, via the **Web UI** or **API**. The credentials are stored in the database, and when Cursor connects, the MCP Server automatically loads them.

## Complete Step-by-Step Flow

### Step 1: User Gets JIRA API Token

**User Action:**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Name it: "MCP Server Access"
4. Copy the token: `ATATT3xFfGF0abc123...`

**What User Needs:**
- ✅ JIRA URL: `https://company.atlassian.net`
- ✅ Email: `user@company.com`
- ✅ API Token: `ATATT3xFfGF0abc123...`

### Step 2: User Adds JIRA Credentials to System

**User logs into Web Application** and adds credentials:

**Option A: Via Web UI (Recommended)**
1. Navigate to **Settings** → **PM Providers** or **Provider Management**
2. Click **"Add Provider"** or **"Connect JIRA"**
3. Fill in the form:
   ```
   Provider Type: JIRA
   Base URL: https://company.atlassian.net
   API Token: ATATT3xFfGF0abc123...
   Username: user@company.com
   ```
4. Click **"Save"** or **"Import Projects"**

**What Happens Behind the Scenes:**
```javascript
// Frontend calls API
POST /api/pm/providers/import-projects
Authorization: Bearer <user-jwt-token>
{
  "provider_type": "jira",
  "base_url": "https://company.atlassian.net",
  "api_token": "ATATT3xFfGF0abc123...",
  "username": "user@company.com"
}
```

**Backend Stores:**
```sql
INSERT INTO pm_provider_connections (
    id,
    name,
    provider_type,
    base_url,
    api_token,
    username,
    created_by,  -- ✅ Set from JWT token (user_id)
    is_active
) VALUES (
    gen_random_uuid(),
    'jira - https://company.atlassian.net',
    'jira',
    'https://company.atlassian.net',
    'ATATT3xFfGF0abc123...',
    'user@company.com',
    'user-uuid-from-jwt',  -- ✅ User's ID
    TRUE
);
```

**Option B: Via API Directly**
```bash
curl -X POST http://localhost:8000/api/pm/providers/import-projects \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_type": "jira",
    "base_url": "https://company.atlassian.net",
    "api_token": "ATATT3xFfGF0abc123...",
    "username": "user@company.com"
  }'
```

### Step 3: User Generates MCP API Key

**User Action:**
1. Go to **Settings** → **MCP API Keys**
2. Click **"Generate New Key"**
3. Name it: "Cursor Desktop"
4. Copy the key: `mcp_a1b2c3d4e5f6...`

**What Happens:**
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

**Stored in Database:**
```sql
INSERT INTO user_mcp_api_keys (
    user_id,
    api_key,
    name,
    is_active
) VALUES (
    'user-uuid',
    'mcp_a1b2c3d4e5f6...',
    'Cursor Desktop',
    TRUE
);
```

### Step 4: User Configures Cursor

**User Action:**
1. Open Cursor settings
2. Navigate to **MCP Servers** configuration
3. Add configuration:

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

4. **Restart Cursor**

### Step 5: Cursor Connects and Uses JIRA

**When User Types in Cursor:**
```
"list my projects"
```

**What Happens:**

1. **Cursor sends request:**
   ```
   GET http://localhost:8080/sse
   Headers:
     X-MCP-API-Key: mcp_a1b2c3d4e5f6...
   ```

2. **MCP Server validates API key:**
   ```python
   # Validate MCP API key
   user_id = validate_mcp_api_key("mcp_a1b2c3d4e5f6...")
   # Returns: "123e4567-e89b-12d3-a456-426614174000"
   ```

3. **MCP Server loads user's providers:**
   ```python
   # Query database
   providers = db.query(PMProviderConnection).filter(
       PMProviderConnection.created_by == user_id,
       PMProviderConnection.is_active == True
   ).all()
   
   # Finds: JIRA provider with api_token = "ATATT3xFfGF0abc123..."
   ```

4. **MCP Server calls JIRA API:**
   ```python
   # Use user's JIRA credentials
   jira_provider = JIRAProvider(config={
       "base_url": "https://company.atlassian.net",
       "api_token": "ATATT3xFfGF0abc123...",  # From database
       "username": "user@company.com"         # From database
   })
   
   # Call JIRA API
   projects = await jira_provider.list_projects()
   ```

5. **Results returned to Cursor:**
   ```
   Your Projects:
   - Project A (JIRA-123)
   - Project B (JIRA-456)
   ```

## Key Points

### ✅ Credentials Are Collected BEFORE Cursor Connection

- Users add JIRA credentials via **Web UI** or **API**
- Credentials stored in `pm_provider_connections` with `created_by = user_id`
- **No need to enter credentials in Cursor!**

### ✅ MCP API Key Links Cursor to User

- MCP API key identifies which user is connecting
- Server uses MCP API key → gets `user_id` → loads that user's providers
- Each user's credentials are isolated

### ✅ Automatic Credential Loading

- When Cursor connects, MCP Server automatically:
  1. Validates MCP API key
  2. Gets `user_id`
  3. Loads user's JIRA credentials from database
  4. Uses them to call JIRA API

## Visual Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    USER SETUP (One Time)                     │
└─────────────────────────────────────────────────────────────┘

1. User gets JIRA API token from Atlassian
   └─> Token: ATATT3xFfGF0abc123...

2. User adds credentials via Web UI
   POST /api/pm/providers/import-projects
   └─> Stored in pm_provider_connections
       created_by = user_id
       api_token = ATATT3xFfGF0abc123...

3. User generates MCP API key
   POST /api/users/me/mcp-keys
   └─> Stored in user_mcp_api_keys
       api_key = mcp_a1b2c3d4e5f6...

4. User configures Cursor
   └─> Cursor config: X-MCP-API-Key: mcp_a1b2c3d4e5f6...

┌─────────────────────────────────────────────────────────────┐
│              CURSOR USAGE (Every Time)                      │
└─────────────────────────────────────────────────────────────┘

5. User types: "list my projects"

6. Cursor → MCP Server
   GET /sse
   Headers: X-MCP-API-Key: mcp_a1b2c3d4e5f6...

7. MCP Server validates key
   └─> Gets user_id

8. MCP Server loads user's JIRA credentials
   └─> FROM pm_provider_connections WHERE created_by = user_id
   └─> Finds: api_token = ATATT3xFfGF0abc123...

9. MCP Server calls JIRA API
   └─> Uses api_token to authenticate
   └─> Returns user's projects

10. Results shown in Cursor
    └─> "Your Projects: Project A, Project B"
```

## Summary

**To answer your question:**

> "How do we collect the JIRA API key when using Cursor?"

**Answer:**
1. ✅ User adds JIRA credentials **via Web UI** (before using Cursor)
2. ✅ Credentials stored in database with `created_by = user_id`
3. ✅ User generates MCP API key for Cursor
4. ✅ Cursor connects with MCP API key
5. ✅ MCP Server automatically loads user's JIRA credentials
6. ✅ User can use MCP tools without entering credentials again!

**The JIRA API key is collected once via the Web UI, then automatically used by the MCP Server when Cursor connects.**









