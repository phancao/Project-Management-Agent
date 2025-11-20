# PM MCP Server

A standalone MCP (Model Context Protocol) server that exposes Project Management operations as tools for AI agents.

## 🎯 Features

- **Multi-Provider Support**: Works with OpenProject, JIRA, ClickUp, and Internal DB
- **50+ PM Tools**: Comprehensive operations for projects, tasks, sprints, epics, users, and analytics
- **Multiple Transports**: stdio (Claude Desktop), SSE (web agents), HTTP (REST API)
- **Authentication & Authorization**: Token-based auth and RBAC support
- **Audit Logging**: Track all tool usage for compliance

## 🚀 Quick Start

### 1. Run with stdio (for Claude Desktop)

```bash
# Start the server
uv run uv run uv run python scripts/run_pm_mcp_server.py --transport stdio

# Or with custom database
DATABASE_URL=postgresql://user:pass@host:port/db \
  uv run uv run uv run python scripts/run_pm_mcp_server.py --transport stdio
```

### 2. Configure Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pm-server": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "/path/to/Project-Management-Agent/scripts/run_pm_mcp_server.py",
        "--transport",
        "stdio"
      ],
      "env": {
        "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/pm_agent"
      }
    }
  }
}
```

### 3. Use in Claude Desktop

Now you can ask Claude to:
- "List all my projects"
- "Show me my tasks"
- "Create a new task in project X"
- "What's the burndown for sprint Y?"

## 📚 Available Tools

### Projects (6 tools)
- `list_projects` - List all accessible projects
- `get_project` - Get project details
- `create_project` - Create new project
- `update_project` - Update project
- `delete_project` - Delete project
- `search_projects` - Search projects

### Tasks (9 tools)
- `list_my_tasks` - List current user's tasks
- `list_tasks` - List tasks in project
- `get_task` - Get task details
- `create_task` - Create new task
- `update_task` - Update task
- `delete_task` - Delete task
- `assign_task` - Assign task to user
- `update_task_status` - Change task status
- `search_tasks` - Search tasks

### Sprints (2 tools)
- `list_sprints` - List sprints in project
- `get_sprint` - Get sprint details

### Epics (2 tools)
- `list_epics` - List epics in project
- `get_epic` - Get epic details

### Users (2 tools)
- `list_users` - List users
- `get_current_user` - Get current user info

### Analytics (2 tools)
- `burndown_chart` - Generate burndown chart
- `velocity_chart` - Calculate team velocity

## 🔧 Configuration

### Environment Variables

```bash
# Database connection
DATABASE_URL=postgresql://user:pass@host:port/db

# Server settings
MCP_SERVER_NAME=pm-server
MCP_TRANSPORT=stdio
MCP_HOST=localhost
MCP_PORT=8080

# Authentication
MCP_ENABLE_AUTH=false
MCP_AUTH_SECRET=your-secret-key

# Authorization
MCP_ENABLE_RBAC=false

# Logging
LOG_LEVEL=INFO
MCP_ENABLE_AUDIT=true
```

### Command Line Options

```bash
uv run uv run python scripts/run_pm_mcp_server.py --help

Options:
  --transport {stdio,sse,http}  Transport protocol (default: stdio)
  --host HOST                   Host to bind to (default: localhost)
  --port PORT                   Port to bind to (default: 8080)
  --log-level {DEBUG,INFO,WARNING,ERROR}
                                Logging level (default: INFO)
  --enable-auth                 Enable authentication
  --enable-rbac                 Enable role-based access control
```

## 🌐 Using with Web Agents (SSE Transport)

```bash
# Start server with SSE transport
uv run uv run uv run python scripts/run_pm_mcp_server.py --transport sse --port 8080
```

In your agent code:

```python
from langchain_mcp import MultiServerMCPClient

# Connect to PM MCP Server
mcp_client = MultiServerMCPClient({
    "pm-server": {
        "transport": "sse",
        "url": "http://localhost:8080/sse"
    }
})

# Load tools
pm_tools = await mcp_client.get_tools()

# Use in agent
agent = create_agent("my_agent", pm_tools)
```

## 🔐 Authentication & Authorization

### Enable Authentication

```bash
MCP_ENABLE_AUTH=true \
MCP_AUTH_SECRET=your-secret-key \
  uv run uv run uv run python scripts/run_pm_mcp_server.py
```

### Enable RBAC

```bash
MCP_ENABLE_RBAC=true \
  uv run uv run uv run python scripts/run_pm_mcp_server.py
```

## 📊 Audit Logging

All tool calls are logged to `logs/pm_mcp_audit.log`:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "agent_id": "research_agent",
  "tool": "list_projects",
  "params": {"provider_id": "openproject-1"},
  "success": true
}
```

## 🧪 Testing

### Test with Python Client

```python
# scripts/test_pm_mcp_client.py
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_pm_server():
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "scripts/run_pm_mcp_server.py", "--transport", "stdio"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {len(tools.tools)}")
            
            # Call a tool
            result = await session.call_tool("list_projects", {})
            print(f"Projects: {result.content}")

asyncio.run(test_pm_server())
```

## 🏗️ Architecture

```
PM MCP Server
├── Server Instance (MCP protocol handler)
├── Tools Layer (50+ PM tools)
├── PMHandler (Multi-provider abstraction)
└── PM Providers (OpenProject, JIRA, ClickUp, Internal)
```

## 🔄 Extending the Server

### Add New Tools

1. Create or edit a tool module in `mcp_server/tools/`
2. Register the tool using `@server.call_tool()` decorator
3. **CRITICAL**: Store tool function in `tool_functions` dict (see Troubleshooting section)
4. Use correct function signature: `(tool_name: str, arguments: dict[str, Any])`
5. Return `list[TextContent]` with formatted results

Example:

```python
def register_my_tools(
    server: Any,
    pm_handler: Any,
    config: Any,
    tool_names: list[str] | None = None,
    tool_functions: dict[str, Any] | None = None,  # ✅ REQUIRED
) -> int:
    tool_count = 0
    
    @server.call_tool()
    async def my_new_tool(tool_name: str, arguments: dict[str, Any]) -> list[TextContent]:  # ✅ Correct signature
        """Tool description."""
        try:
            # Your logic here
            result = pm_handler.do_something()
            
            return [TextContent(
                type="text",
                text=f"Result: {result}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]
    
    # ✅ CRITICAL: Store in both tool_names AND tool_functions
    if tool_names is not None:
        tool_names.append("my_new_tool")
    if tool_functions is not None:
        tool_functions["my_new_tool"] = my_new_tool  # ✅ REQUIRED
    tool_count += 1
    
    return tool_count
```

**⚠️ IMPORTANT**: See the "Tools not being recognized/callable" section in Troubleshooting for detailed explanation of why this is critical.

### Add New Transport

1. Create transport module in `mcp_server/transports/`
2. Implement `run_<transport>()` method in `server.py`
3. Update `PMServerConfig` to support new transport

## 📖 References

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [LangChain MCP Integration](https://python.langchain.com/docs/integrations/tools/mcp)

## 🐛 Troubleshooting

### Server won't start

```bash
# Check database connection
psql $DATABASE_URL -c "SELECT 1"

# Check logs
tail -f logs/pm_mcp_server.log
```

### Tools not showing in Claude Desktop

1. Restart Claude Desktop
2. Check `claude_desktop_config.json` syntax
3. Check server logs for errors

### Permission errors

```bash
# Ensure script is executable
chmod +x scripts/run_pm_mcp_server.py

# Check database permissions
# Ensure user has access to pm_provider_connections table
```

### Tools not being recognized/callable (CRITICAL)

**Symptom:**
- Tools appear in `list_tools` but return "Tool not found" or "takes 1 positional argument but 2 were given" errors
- Routing handler logs show: `Tool 'tool_name' not found in tool_functions`
- Agent reports tools as "unavailable" despite being in enabled tools list

**Root Cause:**
When registering new tools, you MUST:
1. **Store tool functions in `tool_functions` dict** - The routing handler uses this dict to find and call tools
2. **Use correct function signature** - Tools must accept `(tool_name: str, arguments: dict[str, Any])` to match the routing handler

**Fix:**

When creating a new tool registration function (e.g., `register_my_tools`):

```python
def register_my_tools(
    server: Any,
    pm_handler: Any,
    config: Any,
    tool_names: list[str] | None = None,
    tool_functions: dict[str, Any] | None = None,  # ✅ REQUIRED parameter
) -> int:
    tool_count = 0
    
    @server.call_tool()
    async def my_tool(tool_name: str, arguments: dict[str, Any]) -> list[TextContent]:  # ✅ Correct signature
        """Tool description."""
        # Your tool logic here
        return [TextContent(type="text", text="Result")]
    
    # ✅ CRITICAL: Store in both tool_names AND tool_functions
    if tool_names is not None:
        tool_names.append("my_tool")
    if tool_functions is not None:
        tool_functions["my_tool"] = my_tool  # ✅ REQUIRED - routing handler uses this
    tool_count += 1
    
    return tool_count
```

**Common Mistakes:**
1. ❌ Forgetting to add `tool_functions` parameter
2. ❌ Forgetting to store function: `tool_functions["my_tool"] = my_tool`
3. ❌ Wrong signature: `async def my_tool(arguments)` instead of `async def my_tool(tool_name: str, arguments: dict[str, Any])`
4. ❌ Only storing in `tool_names` but not in `tool_functions`

**Verification:**
After fixing, check logs for:
- ✅ `[ROUTER] Found tool function for 'my_tool'`
- ✅ `[ROUTER] Tool 'my_tool' completed successfully`
- ❌ NOT: `Tool 'my_tool' not found in tool_functions`
- ❌ NOT: `takes 1 positional argument but 2 were given`

**Reference Implementation:**
See `mcp_server/tools/projects.py` for correct pattern, or `mcp_server/tools/provider_config.py` (after fix applied on 2025-11-20).

## 📝 License

Same as parent project.

