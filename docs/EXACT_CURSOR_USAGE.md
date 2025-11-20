# Exact Usage: What Users Type in Cursor

This document shows **exactly** what users type in Cursor and which MCP tool gets called.

## The MCP Tool: `configure_pm_provider`

**Tool Name**: `configure_pm_provider`

**Available in**: MCP Server (registered when server starts)

## What User Types in Cursor

### Example 1: Natural Language (Recommended)

**User types in Cursor:**
```
"Configure JIRA provider with URL https://company.atlassian.net, 
 API token ATATT3xFfGF0abc123..., and username user@company.com"
```

**What Cursor does:**
- Cursor understands the user wants to configure a provider
- Cursor calls the `configure_pm_provider` MCP tool
- Cursor extracts the information and calls:

```json
{
  "tool": "configure_pm_provider",
  "arguments": {
    "provider_type": "jira",
    "base_url": "https://company.atlassian.net",
    "api_token": "ATATT3xFfGF0abc123...",
    "username": "user@company.com"
  }
}
```

### Example 2: More Explicit

**User types:**
```
"I want to connect to my JIRA instance.
 Provider type: jira
 Base URL: https://company.atlassian.net
 API Token: ATATT3xFfGF0abc123...
 Username: user@company.com"
```

**Cursor calls**: Same `configure_pm_provider` tool with same arguments

### Example 3: For OpenProject

**User types:**
```
"Configure OpenProject provider:
 URL: http://localhost:8080
 API Key: YXBpa2V5OnlvdXItdG9rZW4taGVyZQ=="
```

**Cursor calls:**
```json
{
  "tool": "configure_pm_provider",
  "arguments": {
    "provider_type": "openproject",
    "base_url": "http://localhost:8080",
    "api_key": "YXBpa2V5OnlvdXItdG9rZW4taGVyZQ=="
  }
}
```

## Tool Definition

**Tool Name**: `configure_pm_provider`

**Location**: `mcp_server/tools/provider_config.py`

**Tool Signature**:
```python
@server.call_tool()
async def configure_pm_provider(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Configure a PM provider (JIRA, OpenProject, ClickUp) for the current user.
    
    Args:
        provider_type (required): "jira", "openproject", "clickup"
        base_url (required): Provider base URL
        api_token (optional): API token for JIRA
        api_key (optional): API key for OpenProject/ClickUp
        username (optional): Username/email for JIRA
        name (optional): Custom name for this provider
    """
```

## Complete Example Flow

### Step 1: User Types in Cursor

```
User: "I need to connect to JIRA. 
       My JIRA URL is https://mycompany.atlassian.net
       My API token is ATATT3xFfGF0abc123def456
       My email is john@company.com"
```

### Step 2: Cursor Processes and Calls MCP Tool

**Cursor internally calls:**
```json
POST /sse (via MCP protocol)
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "configure_pm_provider",
    "arguments": {
      "provider_type": "jira",
      "base_url": "https://mycompany.atlassian.net",
      "api_token": "ATATT3xFfGF0abc123def456",
      "username": "john@company.com",
      "name": "My JIRA"
    }
  }
}
```

### Step 3: MCP Server Executes Tool

**Code**: `mcp_server/tools/provider_config.py:configure_pm_provider()`

```python
async def configure_pm_provider(arguments: dict[str, Any]):
    # Get user_id from MCP connection (from API key)
    user_id = server._mcp_server_instance.user_id  # "123e4567-e89b-12d3-a456-426614174000"
    
    # Extract arguments
    provider_type = arguments["provider_type"]  # "jira"
    base_url = arguments["base_url"]            # "https://mycompany.atlassian.net"
    api_token = arguments["api_token"]         # "ATATT3xFfGF0abc123def456"
    username = arguments["username"]           # "john@company.com"
    
    # Store in database
    provider = PMProviderConnection(
        created_by=user_id,  # ✅ From MCP connection
        provider_type=provider_type,
        base_url=base_url,
        api_token=api_token,
        username=username,
        is_active=True
    )
    db.add(provider)
    db.commit()
    
    # Test connection
    # ...
    
    return [TextContent(
        type="text",
        text="✅ Provider configured successfully! Found 5 project(s)."
    )]
```

### Step 4: Response to Cursor

**MCP Server responds:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "✅ Provider configured successfully!\nProvider ID: abc-123\nFound 5 project(s).\nYou can now use list_projects, create_task, and other PM tools."
      }
    ]
  }
}
```

**Cursor displays to user:**
```
✅ Provider configured successfully!
Provider ID: abc-123
Found 5 project(s).
You can now use list_projects, create_task, and other PM tools.
```

## Required Information by Provider

### For JIRA:
- `provider_type`: `"jira"`
- `base_url`: `"https://your-domain.atlassian.net"`
- `api_token`: `"ATATT3x..."` (from Atlassian)
- `username`: `"your-email@company.com"` (your JIRA email)

**User types:**
```
"Configure JIRA:
 URL: https://company.atlassian.net
 Token: ATATT3xFfGF0abc123...
 Email: user@company.com"
```

### For OpenProject:
- `provider_type`: `"openproject"`
- `base_url`: `"https://your-instance.openproject.com"`
- `api_key`: `"YXBpa2V5OnlvdXItdG9rZW4taGVyZQ=="` (base64-encoded)

**User types:**
```
"Configure OpenProject:
 URL: https://myproject.openproject.com
 API Key: YXBpa2V5OnlvdXItdG9rZW4taGVyZQ=="
```

### For ClickUp:
- `provider_type`: `"clickup"`
- `api_key`: `"pk_xxx..."`
- `organization_id`: `"12345678"` (optional)

**User types:**
```
"Configure ClickUp:
 API Key: pk_abc123def456
 Organization ID: 12345678"
```

## Summary

**What user types in Cursor:**
```
"Configure JIRA provider with URL https://company.atlassian.net, 
 API token ATATT3xFfGF0abc123..., and username user@company.com"
```

**Which MCP tool gets called:**
- Tool name: `configure_pm_provider`
- Location: `mcp_server/tools/provider_config.py`
- Registered: Automatically when MCP Server starts

**What the tool does:**
1. Gets `user_id` from MCP connection (from API key)
2. Stores credentials in `pm_provider_connections` table
3. Tests connection
4. Returns success message

**Result:**
- Credentials stored in database
- User can now use `list_projects`, `create_task`, etc.









