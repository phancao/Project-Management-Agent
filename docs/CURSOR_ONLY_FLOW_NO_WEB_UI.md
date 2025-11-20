# Cursor-Only Flow: Adding JIRA Credentials (No Web UI)

Since you're using **Cursor → MCP Server** directly (no web UI), here's how users provide their JIRA credentials.

## The Problem

- ✅ User has Cursor
- ✅ User connects Cursor to MCP Server
- ❌ **No web UI** to add JIRA credentials
- ❓ **How does user provide JIRA API key?**

## Solution Options

### Option 1: Direct API Call (Recommended)

User calls the API endpoint directly (via `curl`, Postman, or any HTTP client):

```bash
# Step 1: User gets their user_id (if they know it)
# OR user gets MCP API key first, then uses it

# Step 2: User adds JIRA credentials via API
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

**Problem**: User needs to know their `user_id` first!

### Option 2: MCP Tool to Configure Providers (Best Solution)

Add an MCP tool that allows users to configure providers **directly from Cursor**:

```python
@server.call_tool()
async def configure_pm_provider(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Configure a PM provider (JIRA, OpenProject, etc.) for the current user.
    
    Args:
        provider_type: "jira", "openproject", "clickup"
        base_url: Provider base URL
        api_token: API token (for JIRA)
        api_key: API key (for OpenProject/ClickUp)
        username: Username/email (for JIRA)
    
    Returns:
        Success message with provider ID
    """
    # Get user_id from MCP connection context
    user_id = get_user_from_mcp_context()  # From MCP API key
    
    # Store in database
    provider = PMProviderConnection(
        created_by=user_id,  # ✅ User-scoped
        provider_type=arguments["provider_type"],
        base_url=arguments["base_url"],
        api_token=arguments.get("api_token"),
        api_key=arguments.get("api_key"),
        username=arguments.get("username"),
        is_active=True
    )
    db.add(provider)
    db.commit()
    
    return [TextContent(type="text", text=f"Provider configured: {provider.id}")]
```

**Usage in Cursor:**
```
User types: "configure JIRA provider with URL https://company.atlassian.net, 
             API token ATATT3xFfGF0abc123..., username user@company.com"

Cursor calls: configure_pm_provider tool
→ Credentials stored in database with created_by = user_id
→ User can now use list_projects, create_task, etc.
```

### Option 3: Pass Credentials in MCP Connection Config

User provides credentials as part of Cursor's MCP configuration:

```json
{
  "mcpServers": {
    "pm-server": {
      "url": "http://localhost:8080/sse",
      "transport": "sse",
      "headers": {
        "X-MCP-API-Key": "mcp_xxx",
        "X-Provider-JIRA-URL": "https://company.atlassian.net",
        "X-Provider-JIRA-Token": "ATATT3x...",
        "X-Provider-JIRA-Username": "user@company.com"
      }
    }
  }
}
```

**MCP Server extracts and stores:**
```python
@app.get("/sse")
async def sse_endpoint(request: Request):
    user_id = validate_mcp_api_key(request.headers.get("X-MCP-API-Key"))
    
    # Extract provider credentials from headers
    jira_url = request.headers.get("X-Provider-JIRA-URL")
    jira_token = request.headers.get("X-Provider-JIRA-Token")
    jira_username = request.headers.get("X-Provider-JIRA-Username")
    
    if jira_url and jira_token:
        # Store in database
        provider = PMProviderConnection(
            created_by=user_id,
            provider_type="jira",
            base_url=jira_url,
            api_token=jira_token,
            username=jira_username,
            is_active=True
        )
        db.add(provider)
        db.commit()
```

**Problem**: Credentials in config file (less secure, not ideal)

### Option 4: Environment Variables (Per-User)

Each user runs their own MCP Server instance with environment variables:

```bash
# User's .env file
MCP_USER_ID=user-uuid-here
JIRA_URL=https://company.atlassian.net
JIRA_API_TOKEN=ATATT3x...
JIRA_USERNAME=user@company.com
```

**Problem**: Requires each user to run their own server instance (not scalable)

## Recommended Solution: MCP Tool

**Best approach**: Add `configure_pm_provider` MCP tool so users can configure providers **directly from Cursor**.

### Implementation

1. **Add tool to MCP Server:**
   ```python
   # src/mcp_servers/pm_server/tools/providers.py
   
   @server.call_tool()
   async def configure_pm_provider(arguments: dict[str, Any]) -> list[TextContent]:
       """Configure a PM provider for the current user."""
       # Get user_id from MCP server context
       user_id = mcp_server.user_id  # From connection
       
       # Store provider
       # ...
   ```

2. **User uses it in Cursor:**
   ```
   "Configure JIRA provider: URL https://company.atlassian.net, 
    token ATATT3xFfGF0abc123..., email user@company.com"
   ```

3. **Credentials stored automatically:**
   - Stored in `pm_provider_connections` with `created_by = user_id`
   - Available for all other MCP tools

## Complete Flow (No Web UI)

### Step 1: User Gets MCP API Key

**Via API call:**
```bash
# User needs to know their user_id or email
# OR create user first, then generate key

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

### Step 3: User Adds JIRA Credentials (Via MCP Tool)

**In Cursor, user types:**
```
"Configure JIRA provider with URL https://company.atlassian.net, 
 API token ATATT3xFfGF0abc123..., and username user@company.com"
```

**OR via API call:**
```bash
curl -X POST http://localhost:8000/api/pm/providers/import-projects \
  -H "Content-Type: application/json" \
  -H "X-User-ID: user-uuid" \
  -d '{
    "provider_type": "jira",
    "base_url": "https://company.atlassian.net",
    "api_token": "ATATT3xFfGF0abc123...",
    "username": "user@company.com"
  }'
```

### Step 4: User Uses MCP Tools

```
"list my projects"
→ MCP Server loads user's JIRA credentials
→ Calls JIRA API
→ Returns projects
```

## Summary

**For Cursor-only usage (no web UI):**

1. ✅ User gets MCP API key (via API call)
2. ✅ User configures Cursor with MCP API key
3. ✅ User adds JIRA credentials via:
   - **MCP tool** (best): `configure_pm_provider` tool in Cursor
   - **API call**: Direct HTTP request to `/api/pm/providers/import-projects`
4. ✅ User uses MCP tools in Cursor

**The key is**: Either add an MCP tool for configuration, or users call the API directly (no web UI needed).









