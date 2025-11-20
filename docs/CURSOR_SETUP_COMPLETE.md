# Complete Setup: Cursor → MCP Server (No Web UI)

This is the **correct flow** for using Cursor with the MCP Server **without any web UI**.

## The Real Flow

### Step 1: User Gets MCP API Key

**Via API call (curl, Postman, etc.):**
```bash
# Option A: If user knows their user_id
curl -X POST http://localhost:8000/api/users/{user_id}/mcp-keys \
  -H "Content-Type: application/json" \
  -d '{"name": "Cursor Desktop"}'

# Returns: {"api_key": "mcp_a1b2c3d4e5f6..."}
```

**OR create user first, then generate key:**
```bash
# Create user
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "name": "John Doe"}'

# Get user_id from response, then generate MCP key
```

### Step 2: User Configures Cursor

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

### Step 3: User Adds JIRA Credentials (Directly in Cursor!)

**User types in Cursor:**
```
"Configure JIRA provider with URL https://company.atlassian.net, 
 API token ATATT3xFfGF0abc123..., and username user@company.com"
```

**Cursor calls the `configure_pm_provider` MCP tool:**
```json
{
  "tool": "configure_pm_provider",
  "arguments": {
    "provider_type": "jira",
    "base_url": "https://company.atlassian.net",
    "api_token": "ATATT3xFfGF0abc123...",
    "username": "user@company.com",
    "name": "My JIRA"
  }
}
```

**What happens:**
1. MCP Server gets `user_id` from MCP API key (already validated)
2. Tool stores credentials in `pm_provider_connections` with `created_by = user_id`
3. Tool tests connection to JIRA
4. Returns success message

### Step 4: User Uses MCP Tools

```
"list my projects"
→ MCP Server loads user's JIRA credentials
→ Calls JIRA API
→ Returns projects
```

## Alternative: Direct API Call (No Cursor Tool)

If the MCP tool doesn't work, user can call API directly:

```bash
curl -X POST http://localhost:8000/api/pm/providers/import-projects \
  -H "Content-Type: application/json" \
  -H "X-User-ID: user-uuid-here" \
  -d '{
    "provider_type": "jira",
    "base_url": "https://company.atlassian.net",
    "api_token": "ATATT3xFfGF0abc123...",
    "username": "user@company.com"
  }'
```

**Note**: The `/api/pm/providers/import-projects` endpoint needs to be updated to accept `X-User-ID` header and set `created_by`.

## Summary

**For Cursor-only usage:**

1. ✅ User gets MCP API key (via API call)
2. ✅ User configures Cursor with MCP API key
3. ✅ **User adds JIRA credentials via `configure_pm_provider` tool in Cursor** ← **This is the key!**
4. ✅ User uses other MCP tools (list_projects, create_task, etc.)

**No web UI needed!** Everything happens in Cursor or via direct API calls.

