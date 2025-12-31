# PM MCP Server - Learning Guide

## 📚 Overview

This guide provides a comprehensive overview of the PM MCP Server codebase, its architecture, and how it integrates with the broader Project Management Agent system.

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI Agents Ecosystem                          │
│  - Researcher Agent                                             │
│  - Coder Agent                                                  │
│  - QC Agent (planned)                                           │
│  - HR Agent (planned)                                           │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ MCP Protocol
                      │ (stdio/sse/http)
┌─────────────────────▼───────────────────────────────────────────┐
│              PM MCP Server                                      │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  PMMCPServer (server.py)                                 │ │
│  │  - MCP protocol handler                                  │ │
│  │  - Tool registration                                     │ │
│  │  - Transport management                                  │ │
│  └────────────────────┬─────────────────────────────────────┘ │
│                       │                                         │
│  ┌────────────────────▼─────────────────────────────────────┐ │
│  │  Tools Layer (51 tools)                                  │ │
│  │  - projects.py (6 tools)                                │ │
│  │  - tasks.py (9 tools)                                   │ │
│  │  - sprints.py (10 tools)                                │ │
│  │  - epics.py (8 tools)                                   │ │
│  │  - users.py (5 tools)                                   │ │
│  │  - analytics.py (10 tools)                              │ │
│  │  - task_interactions.py (5 tools)                       │ │
│  └────────────────────┬─────────────────────────────────────┘ │
│                       │                                         │
│  ┌────────────────────▼─────────────────────────────────────┐ │
│  │  PMHandler (Multi-Provider Abstraction)                  │ │
│  │  - Provider routing                                      │ │
│  │  - Multi-provider aggregation                           │ │
│  │  - Unified interface                                     │ │
│  └────────────────────┬─────────────────────────────────────┘ │
│                       │                                         │
│  ┌────────────────────▼─────────────────────────────────────┐ │
│  │  PM Providers                                            │ │
│  │  - OpenProjectProvider                                   │ │
│  │  - JIRAProvider                                          │ │
│  │  - ClickUpProvider                                       │ │
│  │  - InternalProvider (PostgreSQL)                        │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Directory Structure

```
mcp_server/
├── __init__.py              # Package exports
├── server.py                # Main MCP server implementation (PMMCPServer class)
├── config.py                # Server configuration (PMServerConfig)
├── README.md                # Server documentation
│
├── tools/                   # MCP tool definitions (51 tools total)
│   ├── __init__.py          # Tool registration exports
│   ├── projects.py          # 6 project tools
│   ├── tasks.py             # 9 task tools
│   ├── sprints.py           # 10 sprint tools
│   ├── epics.py             # 8 epic tools
│   ├── users.py             # 5 user tools
│   ├── analytics.py         # 10 analytics tools
│   └── task_interactions.py # 5 task interaction tools
│
├── transports/              # Transport implementations
│   ├── __init__.py
│   ├── sse.py               # Server-Sent Events transport (for web agents)
│   └── http.py              # HTTP REST API transport
│
└── auth/                    # Authentication & Authorization
    ├── __init__.py
    ├── manager.py           # AuthManager class
    ├── models.py            # User, Token, Role, Permission models
    ├── decorators.py        # Auth decorators
    ├── middleware.py        # FastAPI middleware
    └── routes.py            # Auth API endpoints
```

## 🔑 Key Components

### 1. PMMCPServer (`server.py`)

The main server class that:
- Initializes the MCP server instance
- Manages database connections
- Registers all PM tools
- Handles different transport protocols (stdio, SSE, HTTP)

**Key Methods:**
- `__init__()` - Initialize server with configuration
- `_initialize_pm_handler()` - Set up PMHandler with database session
- `_register_all_tools()` - Register all 51 tools from tool modules
- `run_stdio()` - Run with stdio transport (for Claude Desktop)
- `run_sse()` - Run with SSE transport (for web agents)
- `run_http()` - Run with HTTP transport (REST API)
- `run()` - Main entry point that dispatches to appropriate transport

**Initialization Flow:**
1. Load configuration (from env or provided)
2. Create MCP Server instance
3. Initialize database session
4. Create PMHandler (multi-provider mode)
5. Register all tools
6. Start transport-specific server

### 2. PMServerConfig (`config.py`)

Configuration dataclass that manages:
- Server identity (name, version)
- Database connection
- Transport settings (stdio/sse/http, host, port)
- Authentication settings
- Authorization (RBAC) settings
- Audit logging
- Performance settings (cache TTL, timeouts)
- Tool filtering (for agent-specific access)

**Key Features:**
- Environment variable support
- Validation
- Default values

### 3. Tool Registration Pattern

All tools follow a consistent pattern:

```python
def register_<category>_tools(
    server: Server,
    pm_handler: PMHandler,
    config: PMServerConfig
) -> int:
    """Register <category> tools."""
    tool_count = 0
    
    @server.call_tool()
    async def tool_name(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Tool description.
        
        Args:
            param1: Description
            param2: Description
        
        Returns:
            Formatted text content
        """
        try:
            # Extract parameters from arguments dict
            param1 = arguments.get("param1")
            param2 = arguments.get("param2")
            
            # Call PMHandler method
            result = await pm_handler.some_method(param1, param2)
            
            # Format response as TextContent
            return [TextContent(
                type="text",
                text=formatted_result
            )]
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]
    
    tool_count += 1
    return tool_count
```

**Key Points:**
- Tools receive `arguments` as a dictionary
- Tools return `list[TextContent]` (MCP format)
- All tools use async/await
- Error handling with try/except
- Logging for debugging

### 4. PMHandler Integration

The PM MCP Server uses `PMHandler` from `backend/server/pm_handler.py`:

**PMHandler Features:**
- **Multi-Provider Mode**: Aggregates data from all active providers
- **Single-Provider Mode**: Works with one specific provider
- **Unified Interface**: Same API regardless of underlying provider
- **Provider Abstraction**: Handles OpenProject, JIRA, ClickUp, Internal DB

**Key PMHandler Methods Used:**
- `list_all_projects()` - Get projects from all providers
- `list_tasks()` - Get tasks from providers
- `get_current_user()` - Get current user per provider
- `_get_active_providers()` - Get list of active providers

**How PMHandler Works:**
1. Queries database for active PM provider connections
2. Creates provider instances for each connection
3. Aggregates results from all providers
4. Returns unified data format

### 5. Transport Implementations

#### stdio Transport (Default)
- Used by Claude Desktop
- Process-based communication
- Standard MCP protocol over stdin/stdout
- Implemented in `run_stdio()` method

#### SSE Transport (`transports/sse.py`)
- Used by web-based agents
- FastAPI application with SSE endpoints
- Real-time streaming support
- Endpoints:
  - `GET /` - Server info
  - `GET /health` - Health check
  - `POST /tools/list` - List available tools
  - `POST /tools/call` - Call tool (non-streaming)
  - `POST /tools/call/stream` - Call tool (streaming)

#### HTTP Transport (`transports/http.py`)
- RESTful API access
- OpenAPI/Swagger documentation
- Category-based tool organization
- Direct resource endpoints

### 6. Authentication & Authorization (`auth/`)

**AuthManager** (`auth/manager.py`):
- Token-based authentication
- Role-based access control (RBAC)
- 6 pre-defined roles: Admin, PM, Developer, QC, Viewer, Agent
- 20+ granular permissions
- Token lifecycle management

**Default Users:**
- `admin` - Full access
- `developer` - Read/write tasks
- `viewer` - Read-only
- `deerflow-agent` - Agent access

**Permission System:**
- Tools mapped to permissions
- Role-to-permission mapping
- Permission checking middleware
- Audit logging

## 🛠️ Tool Categories

### Projects (6 tools)
- `list_projects` - List all accessible projects
- `get_project` - Get project details
- `create_project` - Create new project (not yet implemented)
- `update_project` - Update project (not yet implemented)
- `delete_project` - Delete project (not yet implemented)
- `search_projects` - Search projects by name/description

### Tasks (9 tools)
- `list_my_tasks` - List current user's tasks (context-aware)
- `list_tasks` - List tasks in project
- `get_task` - Get task details
- `create_task` - Create new task
- `update_task` - Update task
- `delete_task` - Delete task
- `assign_task` - Assign task to user
- `update_task_status` - Change task status
- `search_tasks` - Search tasks

### Sprints (10 tools)
- `list_sprints` - List sprints in project
- `get_sprint` - Get sprint details
- `create_sprint` - Create new sprint
- `update_sprint` - Update sprint
- `delete_sprint` - Delete sprint
- `start_sprint` - Start a sprint
- `complete_sprint` - Complete a sprint
- `add_task_to_sprint` - Add task to sprint
- `remove_task_from_sprint` - Remove task from sprint
- `get_sprint_tasks` - Get all tasks in sprint

### Epics (8 tools)
- `list_epics` - List epics in project
- `get_epic` - Get epic details
- `create_epic` - Create new epic
- `update_epic` - Update epic
- `delete_epic` - Delete epic
- `link_task_to_epic` - Link task to epic
- `unlink_task_from_epic` - Unlink task from epic
- `get_epic_progress` - Get epic completion progress

### Users (5 tools)
- `list_users` - List users
- `get_current_user` - Get current user info
- `get_user` - Get user details
- `search_users` - Search users
- `get_user_workload` - Get user's task workload

### Analytics (10 tools)
- `burndown_chart` - Generate burndown chart
- `velocity_chart` - Calculate team velocity
- `sprint_report` - Generate sprint report
- `project_health` - Analyze project health
- `task_distribution` - Analyze task distribution
- `team_performance` - Analyze team performance
- `gantt_chart` - Generate Gantt chart data
- `epic_report` - Generate epic report
- `resource_utilization` - Resource utilization metrics
- `time_tracking_report` - Time tracking analysis

### Task Interactions (5 tools)
- `add_task_comment` - Add comment to task
- `get_task_comments` - Get task comments
- `add_task_watcher` - Add watcher to task
- `bulk_update_tasks` - Update multiple tasks
- `link_related_tasks` - Link related tasks

## 🚀 Usage Examples

### Starting the Server

```bash
# stdio transport (Claude Desktop)
uv run uv run uv run python scripts/run_pm_mcp_server.py --transport stdio

# SSE transport (web agents)
uv run uv run uv run python scripts/run_pm_mcp_server.py --transport sse --port 8080

# HTTP transport (REST API)
uv run uv run uv run python scripts/run_pm_mcp_server.py --transport http --port 8080
```

### Using from DeerFlow Agents

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
agent = create_agent("researcher", pm_tools)
```

### Using from Claude Desktop

Add to `claude_desktop_config.json`:
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

## 🔄 Data Flow

### Tool Call Flow

```
1. Agent/Client
   ↓ (MCP protocol)
2. PMMCPServer (server.py)
   ↓ (routes to tool)
3. Tool Function (tools/*.py)
   ↓ (calls PMHandler)
4. PMHandler (backend/server/pm_handler.py)
   ↓ (routes to provider)
5. PM Provider (pm_providers/*.py)
   ↓ (API call)
6. External PM System (OpenProject/JIRA/etc.)
   ↓ (response)
7. Provider → PMHandler → Tool → Server → Agent
```

### Multi-Provider Aggregation

When `list_all_projects()` is called:
1. PMHandler queries database for active providers
2. For each provider:
   - Creates provider instance
   - Calls `list_projects()` on provider
   - Collects results
3. Aggregates all results
4. Returns unified list with provider metadata

## 🔍 Key Design Decisions

### 1. Why MCP?
- **Standardization**: MCP is a standard protocol for AI agent tools
- **Interoperability**: Works with Claude Desktop, LangChain, etc.
- **Separation of Concerns**: PM operations isolated from agent logic
- **Scalability**: Multiple agents can use same server

### 2. Why Multi-Provider?
- **Flexibility**: Support multiple PM systems simultaneously
- **Migration**: Easy to switch providers
- **Aggregation**: View data from all providers in one place
- **Abstraction**: Agents don't need to know about specific providers

### 3. Why Multiple Transports?
- **stdio**: Claude Desktop integration
- **SSE**: Web-based agents (DeerFlow frontend)
- **HTTP**: REST API for direct integration

### 4. Tool Design Pattern
- **Consistent Interface**: All tools follow same pattern
- **Error Handling**: Comprehensive error handling
- **Logging**: Detailed logging for debugging
- **TextContent Format**: MCP-compatible response format

## 🧪 Testing

The PM MCP Server includes a comprehensive test suite to verify functionality after making changes. All test scripts are located in the `scripts/` directory.

### Test Scripts Overview

| Script | Purpose | Requires Server Running |
|--------|---------|-------------------------|
| `test_pm_mcp_server.py` | Core server functionality | ❌ No |
| `test_pm_mcp_integration.py` | DeerFlow integration | ⚠️ Optional |
| `test_pm_mcp_auth.py` | Authentication & RBAC | ❌ No |
| `test_pm_mcp_sse.py` | SSE transport | ⚠️ Optional |
| `test_pm_mcp_http.py` | HTTP transport | ⚠️ Optional |

### 1. Core Server Tests (`test_pm_mcp_server.py`)

**Purpose**: Tests basic server functionality, initialization, and tool registration.

**What it tests:**
- Server initialization
- PM Handler initialization
- Tool registration
- Configuration validation

**Run:**
```bash
uv run python scripts/test_pm_mcp_server.py
```

**Expected Output:**
```
╔==========================================================╗
║               PM MCP SERVER TESTS                      ║
╚==========================================================╝

============================================================
Test 1: Server Initialization
============================================================
✅ Server initialized successfully
   Server name: pm-server
   Transport: stdio
   Database URL: postgresql://postgres:postgres@localhost:5432...

============================================================
Test 2: PM Handler Initialization
============================================================
✅ PM Handler initialized successfully
   Active Providers: 3
   - OpenProject (openproject)
   - JIRA (jira)
   - Internal (internal)

============================================================
Test 3: Tool Registration
============================================================
✅ Tools registered successfully
   Total tool modules: 7

============================================================
Test 4: Configuration Validation
============================================================
✅ Valid stdio config passed validation
✅ Invalid port correctly rejected
✅ Auth without secret correctly rejected

   Passed 3/3 validation tests

============================================================
TEST SUMMARY
============================================================
Passed: 4/4

✅ All tests passed!
```

**When to run**: After making changes to:
- `server.py`
- `config.py`
- Tool registration logic
- PMHandler initialization

### 2. Integration Tests (`test_pm_mcp_integration.py`)

**Purpose**: Tests integration with DeerFlow graph nodes and MCP tool loading.

**What it tests:**
- MCP tool loading in graph nodes
- Researcher node configuration
- Coder node configuration
- PM MCP Server connection (optional)

**Run:**
```bash
uv run python scripts/test_pm_mcp_integration.py
```

**Expected Output:**
```
╔==========================================================╗
║            PM MCP INTEGRATION TESTS                     ║
╚==========================================================╝

============================================================
Test 1: MCP Tool Loading in Graph Nodes
============================================================
✅ Configuration created
   MCP servers: 1
   PM Server config:
     - Transport: sse
     - URL: http://localhost:8080
     - Add to agents: ['researcher', 'coder']
✅ MCP configuration structure verified
   (Full execution test requires PM MCP server running)

============================================================
Test 2: Researcher Node Configuration
============================================================
✅ Researcher node configuration created
   State: 1 message
   MCP: PM server configured
✅ Configuration structure verified
   (Execution requires PM MCP server at http://localhost:8080)

============================================================
Test 3: Coder Node Configuration
============================================================
✅ Coder node configuration created
   State: 1 message
   MCP: PM server configured
✅ Configuration structure verified

============================================================
Test 4: PM MCP Server Connection
============================================================
🔄 Testing connection to http://localhost:8080...
⚠️  PM MCP Server not running at http://localhost:8080
   Start with: uv run uv run uv run python scripts/run_pm_mcp_server.py --transport sse --port 8080

============================================================
TEST SUMMARY
============================================================
Passed: 4/4

✅ All tests passed!

📝 Note: PM MCP Server is not running.
   To test full integration:
   1. Start PM MCP Server:
      uv run uv run uv run python scripts/run_pm_mcp_server.py --transport sse --port 8080

   2. Test with a chat request:
      curl -X POST http://localhost:8000/api/chat/stream \
        -H "Content-Type: application/json" \
        -d '{"messages":[{"role":"user","content":"List my projects"}],
              "mcp_settings":{"servers":{"pm-server":{
                "transport":"sse","url":"http://localhost:8080",
                "enabled_tools":null,"add_to_agents":["researcher","coder"]}}}}'
```

**When to run**: After making changes to:
- Graph node integration
- MCP tool loading logic
- Configuration handling

**Full Integration Test** (requires server running):
```bash
# Terminal 1: Start PM MCP Server
uv run uv run uv run python scripts/run_pm_mcp_server.py --transport sse --port 8080

# Terminal 2: Run integration tests
uv run python scripts/test_pm_mcp_integration.py
```

### 3. Authentication Tests (`test_pm_mcp_auth.py`)

**Purpose**: Tests authentication and authorization features.

**What it tests:**
- Authentication models (User, Token, Role, Permission)
- AuthManager functionality
- Token generation and validation
- Permission checking
- Tool access control
- Token revocation
- User creation

**Run:**
```bash
uv run python scripts/test_pm_mcp_auth.py
```

**Expected Output:**
```
╔==========================================================╗
║            PM MCP SERVER AUTH TESTS                     ║
╚==========================================================╝

============================================================
Test 1: Authentication Models
============================================================
✅ Created user: testuser
   Role: developer
   Permissions: 8
✅ Permission checks working
✅ Token created and valid
✅ Role permissions configured

============================================================
Test 2: Authentication Manager
============================================================
✅ Auth manager created
   Default users: 4
✅ Generated token: abc123def456...
✅ Token validated: admin
✅ Permission check working
✅ Tool access check working
✅ Token revocation working
✅ User creation working
✅ Stats: 5 users, 1 tokens

============================================================
Test 3: Authentication Integration
============================================================
✅ All auth modules imported successfully
✅ 6 roles defined
✅ Permissions system configured

============================================================
TEST SUMMARY
============================================================
Passed: 3/3

✅ All tests passed!

📝 Next steps:
   1. Start PM MCP Server with auth:
      uv run uv run uv run python scripts/run_pm_mcp_server.py --transport http --port 8080

   2. Generate token:
      curl -X POST http://localhost:8080/auth/token \
        -H 'Content-Type: application/json' \
        -d '{"username":"admin","expires_in_hours":24}'

   3. Use token:
      export TOKEN='your-token-here'
      curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/projects

   4. See full guide: docs/PM_MCP_SERVER_AUTH_GUIDE.md
```

**When to run**: After making changes to:
- `auth/models.py`
- `auth/manager.py`
- Permission mappings
- Role definitions

### 4. SSE Transport Tests (`test_pm_mcp_sse.py`)

**Purpose**: Tests SSE transport configuration and provides testing instructions.

**What it tests:**
- SSE server configuration
- Server instance creation

**Run:**
```bash
uv run python scripts/test_pm_mcp_sse.py
```

**Expected Output:**
```
============================================================
Testing PM MCP Server SSE Transport
============================================================

✅ Configuration created:
   Transport: sse
   Host: localhost
   Port: 8081

✅ Server instance created

📝 To test the SSE server, run:
   uv run uv run uv run python scripts/run_pm_mcp_server.py --transport sse --port 8081

   Then in another terminal:
   curl http://localhost:8081/
   curl http://localhost:8081/health
   curl http://localhost:8081/tools/list -X POST

============================================================
✅ SSE Transport Test Passed!
============================================================
```

**Manual SSE Testing** (requires server running):
```bash
# Terminal 1: Start SSE server
uv run uv run uv run python scripts/run_pm_mcp_server.py --transport sse --port 8081

# Terminal 2: Test endpoints
curl http://localhost:8081/
curl http://localhost:8081/health
curl -X POST http://localhost:8081/tools/list
curl -X POST http://localhost:8081/tools/call \
  -H 'Content-Type: application/json' \
  -d '{"tool":"list_projects","arguments":{}}'
```

**When to run**: After making changes to:
- `transports/sse.py`
- SSE endpoint configuration
- CORS settings

### 5. HTTP Transport Tests (`test_pm_mcp_http.py`)

**Purpose**: Tests HTTP transport configuration and provides testing instructions.

**What it tests:**
- HTTP server configuration
- Server instance creation

**Run:**
```bash
uv run python scripts/test_pm_mcp_http.py
```

**Expected Output:**
```
============================================================
Testing PM MCP Server HTTP Transport
============================================================

✅ Configuration created:
   Transport: http
   Host: localhost
   Port: 8082

✅ Server instance created

📝 To test the HTTP server, run:
   uv run uv run uv run python scripts/run_pm_mcp_server.py --transport http --port 8082

   Then in another terminal:
   # Server info
   curl http://localhost:8082/

   # API Documentation
   open http://localhost:8082/docs

   # Health check
   curl http://localhost:8082/health

   # List tools
   curl http://localhost:8082/tools

   # List projects
   curl http://localhost:8082/projects

   # List my tasks
   curl http://localhost:8082/tasks/my

   # Call a tool
   curl -X POST http://localhost:8082/tools/call \
     -H 'Content-Type: application/json' \
     -d '{"tool":"list_projects","arguments":{}}'

============================================================
✅ HTTP Transport Test Passed!
============================================================
```

**Manual HTTP Testing** (requires server running):
```bash
# Terminal 1: Start HTTP server
uv run uv run uv run python scripts/run_pm_mcp_server.py --transport http --port 8082

# Terminal 2: Test endpoints
curl http://localhost:8082/
curl http://localhost:8082/health
curl http://localhost:8082/tools
curl http://localhost:8082/projects
curl http://localhost:8082/tasks/my

# Open API docs in browser
open http://localhost:8082/docs
```

**When to run**: After making changes to:
- `transports/http.py`
- REST API endpoints
- OpenAPI documentation

### Running All Tests

To run all tests in sequence:

```bash
# Core tests (no server required)
uv run python scripts/test_pm_mcp_server.py
uv run python scripts/test_pm_mcp_auth.py

# Transport tests (configuration only)
uv run python scripts/test_pm_mcp_sse.py
uv run python scripts/test_pm_mcp_http.py

# Integration tests (optional server)
uv run python scripts/test_pm_mcp_integration.py
```

### Quick Test Checklist

When fixing or adding features, run these tests:

**After server changes:**
- ✅ `test_pm_mcp_server.py` - Verify core functionality

**After auth changes:**
- ✅ `test_pm_mcp_auth.py` - Verify auth system

**After transport changes:**
- ✅ `test_pm_mcp_sse.py` or `test_pm_mcp_http.py` - Verify transport config
- ✅ Manual testing with server running

**After integration changes:**
- ✅ `test_pm_mcp_integration.py` - Verify DeerFlow integration
- ✅ Manual testing with full stack

### Troubleshooting Tests

**Test fails with database error:**
```bash
# Check database connection
psql $DATABASE_URL -c "SELECT 1"

# Verify providers are configured
uv run python scripts/utils/check_providers.py
```

**Test fails with import error:**
```bash
# Ensure you're in project root
cd /path/to/Project-Management-Agent

# Check Python path
python -c "import sys; print(sys.path)"
```

**Integration test can't connect:**
```bash
# Start PM MCP Server first
uv run uv run uv run python scripts/run_pm_mcp_server.py --transport sse --port 8080

# Then run integration tests
uv run python scripts/test_pm_mcp_integration.py
```

### Continuous Testing

For development, consider running tests in watch mode:

```bash
# Install watchdog for file watching
pip install watchdog

# Watch for changes and run tests
watchmedo auto-restart \
  --patterns="*.py" \
  --recursive \
  --directory=mcp_server/pm_server \
  -- \
  uv run python scripts/test_pm_mcp_server.py
```

## 📊 Current Status

### ✅ Completed
- 51 tools implemented (100%+ of target)
- 3 transports (stdio, SSE, HTTP)
- Authentication & Authorization
- Multi-provider support
- Comprehensive documentation

### 🔄 In Progress
- Some tools marked as "not yet implemented" (create_project, etc.)
- Additional provider implementations

### 📋 Planned
- QC Agent integration
- HR Agent integration
- Performance optimizations
- Caching layer

## 🔗 Related Documentation

- `docs/PM_MCP_SERVER_ARCHITECTURE.md` - Detailed architecture
- `docs/PM_MCP_SERVER_STATUS.md` - Implementation status
- `docs/PM_MCP_USER_GUIDE.md` - User guide
- `docs/PM_MCP_SERVER_SSE_GUIDE.md` - SSE transport guide
- `docs/PM_MCP_SERVER_HTTP_GUIDE.md` - HTTP transport guide
- `docs/PM_MCP_SERVER_AUTH_GUIDE.md` - Authentication guide
- `mcp_server/README.md` - Server README

## 🎓 Learning Path

1. **Start Here**: Read this guide and `PM_MCP_SERVER_ARCHITECTURE.md`
2. **Understand Core**: Study `server.py` and `config.py`
3. **Explore Tools**: Look at `tools/projects.py` and `tools/tasks.py`
4. **Learn PMHandler**: Read `backend/server/pm_handler.py`
5. **Study Transports**: Check `transports/sse.py` and `transports/http.py`
6. **Review Auth**: Explore `auth/manager.py` and `auth/models.py`
7. **Run Examples**: Try the startup script and test suite

## 💡 Tips for Developers

1. **Tool Development**: Follow the pattern in existing tools
2. **Error Handling**: Always wrap in try/except and return TextContent
3. **Logging**: Use logger for debugging (check logs/pm_mcp_server.log)
4. **Testing**: Test with actual providers before committing
5. **Documentation**: Update docs when adding new features
6. **MCP Protocol**: Understand MCP spec for proper tool responses

## 🐛 Common Issues

### Tools Not Showing
- Check tool registration in `_register_all_tools()`
- Verify `@server.call_tool()` decorator
- Check server logs for errors

### Provider Connection Issues
- Verify database connection
- Check provider credentials in database
- Test provider directly

### Transport Errors
- Verify port is available
- Check CORS settings for SSE/HTTP
- Review transport-specific logs

---

**Last Updated**: 2025-01-15  
**Version**: 1.0.0

