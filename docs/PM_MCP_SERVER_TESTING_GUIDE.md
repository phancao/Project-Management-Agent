# PM MCP Server - Testing Guide

This guide shows how to test the PM MCP Server independently without the frontend.

## 🎯 Quick Start

### 1. Test Docker Deployment (SSE Transport)

The easiest way to test is using the Docker deployment:

```bash
# Start the PM MCP Server in Docker
docker-compose up -d pm_mcp_server

# Run the comprehensive test script
uv run python scripts/test_pm_mcp_docker.py
```

This will test:
- ✅ Health endpoint
- ✅ Tools listing endpoint
- ✅ MCP client connection via SSE

### 2. Test via HTTP Endpoints (curl)

#### Health Check
```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "providers": 3,
  "tools": 53
}
```

#### List All Tools
```bash
curl -X POST http://localhost:8080/tools/list \
  -H "Content-Type: application/json" \
  -d '{}'
```

Expected response:
```json
{
  "tools": [
    {
      "name": "list_projects",
      "description": "List all projects...",
      "inputSchema": {...}
    },
    ...
  ]
}
```

#### Call a Tool
```bash
curl -X POST http://localhost:8080/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "list_projects",
    "arguments": {}
  }'
```

### 3. Test via SSE Transport (Python)

```bash
# Start server in SSE mode
uv run python scripts/run_pm_mcp_server.py --transport sse --port 8080

# In another terminal, run the test
uv run python scripts/test_pm_mcp_sse.py
```

Or use the MCP SDK directly:

```python
import asyncio
from mcp.client.sse import sse_client
from mcp import ClientSession
from datetime import timedelta

async def test():
    url = "http://localhost:8080/sse"
    async with sse_client(url=url, timeout=30) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)) as session:
            await session.initialize()
            
            # List tools
            result = await session.list_tools()
            print(f"Found {len(result.tools)} tools")
            
            # Call a tool
            if result.tools:
                tool_result = await session.call_tool("list_projects", {})
                print(f"Tool result: {tool_result}")

asyncio.run(test())
```

### 4. Test via stdio Transport (Local Development)

```bash
# Start server in stdio mode
uv run python scripts/run_pm_mcp_server.py --transport stdio

# The server will communicate via stdin/stdout
# You can pipe commands to it or use an MCP client
```

Or use the test script:

```bash
uv run python scripts/test_pm_mcp_server.py
```

This tests:
- ✅ Server initialization
- ✅ PM Handler initialization
- ✅ Tool registration (53 tools)
- ✅ Database connectivity

### 5. Test via HTTP REST API

```bash
# Start server in HTTP mode
uv run python scripts/run_pm_mcp_server.py --transport http --port 8080

# Test endpoints
curl http://localhost:8080/
curl http://localhost:8080/health
curl http://localhost:8080/docs  # OpenAPI documentation
```

## 📋 Available Test Scripts

### `scripts/test_pm_mcp_server.py`
**Purpose**: Basic server functionality and tool registration  
**Usage**: `uv run python scripts/test_pm_mcp_server.py`  
**Tests**:
- Server initialization
- PM Handler setup
- Tool registration (53 tools)
- Database connectivity

### `scripts/test_pm_mcp_docker.py`
**Purpose**: Test Docker deployment via SSE transport  
**Usage**: `uv run python scripts/test_pm_mcp_docker.py`  
**Tests**:
- Health endpoint (`/health`)
- Tools listing endpoint (`/tools/list`)
- MCP client connection via SSE
- Tool execution

### `scripts/test_pm_mcp_sse.py`
**Purpose**: Test SSE transport configuration  
**Usage**: `uv run python scripts/test_pm_mcp_sse.py`  
**Tests**:
- SSE server configuration
- Endpoint availability

### `scripts/test_pm_mcp_http.py`
**Purpose**: Test HTTP REST API transport  
**Usage**: `uv run python scripts/test_pm_mcp_http.py`  
**Tests**:
- HTTP server configuration
- REST API endpoints

### `scripts/test_pm_mcp_tool_registration.py`
**Purpose**: Diagnose tool registration issues  
**Usage**: `uv run python scripts/test_pm_mcp_tool_registration.py`  
**Tests**:
- Tool registration process
- `list_tools` handler
- Tool count verification

### `scripts/test_pm_mcp_integration.py`
**Purpose**: Test integration with DeerFlow graph nodes  
**Usage**: `uv run python scripts/test_pm_mcp_integration.py`  
**Tests**:
- MCP tool loading in DeerFlow
- Integration with flow manager

### `scripts/test_pm_mcp_auth.py`
**Purpose**: Test authentication and authorization  
**Usage**: `uv run python scripts/test_pm_mcp_auth.py`  
**Tests**:
- Token authentication
- Role-based access control (RBAC)
- Permission checks

## 🔧 Manual Testing with curl

### Health Check
```bash
curl http://localhost:8080/health
```

### List Tools
```bash
curl -X POST http://localhost:8080/tools/list \
  -H "Content-Type: application/json" \
  -d '{}' | jq '.tools | length'
```

### Call a Tool (List Projects)
```bash
curl -X POST http://localhost:8080/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "list_projects",
    "arguments": {}
  }' | jq
```

### Call a Tool (List Tasks)
```bash
curl -X POST http://localhost:8080/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "list_my_tasks",
    "arguments": {}
  }' | jq
```

### Call a Tool (Get Project)
```bash
curl -X POST http://localhost:8080/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "get_project",
    "arguments": {
      "project_id": "your-project-id"
    }
  }' | jq
```

## 🐍 Python Testing Examples

### Example 1: List All Tools

```python
#!/usr/bin/env python3
import asyncio
from mcp.client.sse import sse_client
from mcp import ClientSession
from datetime import timedelta

async def list_tools():
    url = "http://localhost:8080/sse"
    async with sse_client(url=url, timeout=30) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)) as session:
            await session.initialize()
            result = await session.list_tools()
            print(f"Total tools: {len(result.tools)}")
            for tool in result.tools:
                print(f"  - {tool.name}")

asyncio.run(list_tools())
```

### Example 2: Call a Tool

```python
#!/usr/bin/env python3
import asyncio
from mcp.client.sse import sse_client
from mcp import ClientSession
from datetime import timedelta

async def call_tool():
    url = "http://localhost:8080/sse"
    async with sse_client(url=url, timeout=30) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)) as session:
            await session.initialize()
            
            # Call list_projects tool
            result = await session.call_tool("list_projects", {})
            print(f"Result: {result}")

asyncio.run(call_tool())
```

### Example 3: Test Multiple Tools

```python
#!/usr/bin/env python3
import asyncio
from mcp.client.sse import sse_client
from mcp import ClientSession
from datetime import timedelta

async def test_tools():
    url = "http://localhost:8080/sse"
    async with sse_client(url=url, timeout=30) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)) as session:
            await session.initialize()
            
            # List tools
            tools_result = await session.list_tools()
            print(f"Available tools: {len(tools_result.tools)}")
            
            # Test a few tools
            test_tools = ["list_projects", "list_my_tasks", "list_sprints"]
            for tool_name in test_tools:
                try:
                    result = await session.call_tool(tool_name, {})
                    print(f"✅ {tool_name}: Success")
                except Exception as e:
                    print(f"❌ {tool_name}: {e}")

asyncio.run(test_tools())
```

## 🔍 Debugging Tips

### Check Server Logs

```bash
# Docker logs
docker-compose logs -f pm_mcp_server

# Or if running locally
uv run python scripts/run_pm_mcp_server.py --transport sse --log-level DEBUG
```

### Verify Environment Variables

```bash
# Check if PM MCP Server URL is set
echo $PM_MCP_SERVER_URL
echo $PM_MCP_TRANSPORT

# For Docker, check docker-compose.yml
docker-compose config | grep PM_MCP
```

### Test Database Connection

```python
from database.connection import get_db_session
db = next(get_db_session())
print("✅ Database connected")
db.close()
```

### Verify Tool Registration

```python
from src.mcp_servers.pm_server import PMMCPServer, PMServerConfig

config = PMServerConfig(transport="stdio")
server = PMMCPServer(config)
print(f"Tools registered: {len(server._tool_names)}")
```

## 🚀 Quick Test Checklist

- [ ] Health endpoint returns `200 OK`
- [ ] `/tools/list` returns 53 tools
- [ ] Can connect via SSE transport
- [ ] Can call `list_projects` tool
- [ ] Can call `list_my_tasks` tool
- [ ] Server logs show no errors
- [ ] Database connection works
- [ ] PM Handler initializes correctly

## 📚 Additional Resources

- [PM MCP Server Learning Guide](./PM_MCP_SERVER_LEARNING_GUIDE.md) - Architecture and codebase overview
- [PM MCP Server Docker Setup](./PM_MCP_SERVER_DOCKER_SETUP.md) - Docker deployment guide
- [MCP Protocol Documentation](https://modelcontextprotocol.io/) - Official MCP documentation

## 🐛 Common Issues

### Issue: "Connection refused"
**Solution**: Make sure the server is running:
```bash
docker-compose ps pm_mcp_server
# or
ps aux | grep run_pm_mcp_server
```

### Issue: "0 tools returned"
**Solution**: Check tool registration:
```bash
uv run python scripts/test_pm_mcp_tool_registration.py
```

### Issue: "Database connection failed"
**Solution**: Verify database is running:
```bash
docker-compose ps postgres
# or check connection string in .env
```

### Issue: "Method not found"
**Solution**: Ensure tools capability is enabled and tools are registered:
```bash
# Check server logs for tool registration
docker-compose logs pm_mcp_server | grep -i tool
```


