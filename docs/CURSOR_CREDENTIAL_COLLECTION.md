# How Users Provide JIRA Credentials (Cursor Only, No Frontend)

Since users **only use Cursor → MCP Server** (no web UI), here's how they provide their JIRA credentials.

## Solution: Users Type Credentials Directly in Cursor

Users provide their JIRA credentials **by typing in Cursor**, and Cursor calls the `configure_pm_provider` MCP tool.

## Complete Flow

### Step 1: User Gets MCP API Key

**User calls API directly (curl, Postman, etc.) - NO FRONTEND:**
```bash
curl -X POST http://localhost:8000/api/users/{user_id}/mcp-keys \
  -H "Content-Type: application/json" \
  -d '{"name": "Cursor Desktop"}'

# Returns: {"api_key": "mcp_xxx"}
```

### Step 2: User Configures Cursor

```json
{
  "mcpServers": {
    "pm-server": {
      "url": "http://localhost:8080/sse",
      "transport": "sse",
      "headers": {
        "X-MCP-API-Key": "mcp_xxx"
      }
    }
  }
}
```

### Step 3: User Provides JIRA Credentials IN CURSOR

**User types directly in Cursor chat:**

```
"Configure JIRA provider:
 - URL: https://company.atlassian.net
 - API token: ATATT3xFfGF0abc123...
 - Username: user@company.com"
```

**OR more naturally:**

```
"I want to connect to JIRA. 
 My JIRA URL is https://company.atlassian.net
 My API token is ATATT3xFfGF0abc123...
 My email is user@company.com"
```

**What happens:**
1. Cursor understands the user wants to configure a provider
2. Cursor calls the `configure_pm_provider` MCP tool with the credentials
3. Tool extracts `user_id` from MCP connection context (from MCP API key)
4. Tool stores credentials in database with `created_by = user_id`
5. Tool tests connection and returns success

**No frontend needed!** Everything happens in Cursor.

## Alternative: Direct API Call (If Tool Doesn't Work)

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

**But this requires user to know their `user_id`**, which they might not have.

## Better Solution: MCP Tool with User Context

The `configure_pm_provider` tool automatically gets `user_id` from the MCP connection:

```python
# src/mcp_servers/pm_server/tools/provider_config.py

@server.call_tool()
async def configure_pm_provider(arguments: dict[str, Any]):
    # Get user_id from MCP server context
    # This is set when Cursor connects with MCP API key
    user_id = server._mcp_server_instance.user_id  # ✅ From connection!
    
    # Store credentials
    provider = PMProviderConnection(
        created_by=user_id,  # ✅ Automatically set!
        provider_type=arguments["provider_type"],
        api_token=arguments["api_token"],
        username=arguments["username"],
        ...
    )
    db.add(provider)
    db.commit()
```

**User doesn't need to provide `user_id`** - it's automatically extracted from the MCP API key!

## Summary

**How users provide JIRA credentials (NO FRONTEND):**

1. ✅ User types credentials **directly in Cursor chat**
2. ✅ Cursor calls `configure_pm_provider` MCP tool
3. ✅ Tool gets `user_id` from MCP connection (from API key)
4. ✅ Tool stores credentials in database
5. ✅ Done! User can now use `list_projects`, etc.

**OR**

1. ✅ User calls API directly via `curl`/Postman
2. ✅ Provides `X-User-ID` header (if they know it)
3. ✅ Credentials stored

**NO WEB UI NEEDED!** Everything happens in Cursor or via direct API calls.









