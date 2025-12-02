# PM MCP Server Architecture

## Overview

The PM MCP Server is a **standalone MCP (Model Context Protocol) server** that exposes Project Management operations as tools for AI agents. It is completely independent from the Backend API and Frontend, operating as a separate service.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│              Transport Layer (Transports)               │
│  - stdio (Claude Desktop)                              │
│  - SSE (Server-Sent Events for web agents)             │
│  - HTTP (REST API)                                     │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Server Core (server.py)                    │
│  - PMMCPServer class                                    │
│  - Tool registration                                    │
│  - MCP protocol handling                                │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Tool Context (core/tool_context.py)        │
│  - ProviderManager (provider lifecycle)                │
│  - AnalyticsManager (analytics services)                 │
│  - AuthManager (authentication)                          │
│  - PM Service Client (API calls)                        │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Tools Layer (tools/)                        │
│  - BaseTool, ReadTool, WriteTool, AnalyticsTool         │
│  - V2 Tools (projects_v2, tasks_v2, sprints_v2, etc.)  │
│  - Provider Config Tools                                │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Database Layer (database/)                 │
│  - Independent database (separate from backend)         │
│  - Models: User, UserMCPAPIKey, PMProviderConnection   │
└─────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Server Core (`server.py`)

**PMMCPServer Class** - Main server class that:
- Initializes MCP server instance
- Manages tool registration
- Handles transport selection (stdio/SSE/HTTP)
- Provides ToolContext to all tools
- Manages database sessions

**Key Methods:**
- `__init__(config, user_id)` - Initialize server with optional user scoping
- `_initialize_tool_context()` - Create ToolContext with database and user context
- `_register_all_tools()` - Register all PM tools
- `run_stdio()` - Run with stdio transport
- `run_sse()` - Run with SSE transport
- `run_http()` - Run with HTTP transport

### 2. Core Managers (`core/`)

#### **ToolContext** (`core/tool_context.py`)
Central context object shared by all tools:
- `provider_manager` - Provider lifecycle management
- `analytics_manager` - Analytics service management
- `auth_manager` - Authentication operations
- `pm_service_client` - API client for PM Service
- `db` - Database session
- `user_id` - User context for credential scoping

#### **ProviderManager** (`core/provider_manager.py`)
Manages PM provider instances:
- `get_active_providers()` - Get providers from database (user-scoped if user_id set)
- `get_provider(provider_id)` - Get provider instance (with caching)
- `create_provider_instance(provider)` - Create provider from DB connection
- Excludes mock providers (UI-only)

#### **AnalyticsManager** (`core/analytics_manager.py`)
Manages analytics services:
- `get_service(project_id)` - Get analytics service for project
- Parses composite project IDs (`provider_id:project_key`)
- Caches analytics services

#### **AuthManager** (`core/auth_manager.py`)
Handles authentication:
- `validate_api_key(api_key)` - Validate MCP API key
- `extract_user_from_request(request)` - Extract user from HTTP request
- API key format: `mcp_<64-hex-chars>`

### 3. Tools Architecture (`tools/`)

#### **Base Classes** (`tools/base.py`)
- `BaseTool` - Abstract base class for all tools
- `ReadTool` - Base for read-only operations
- `WriteTool` - Base for write operations
- `AnalyticsTool` - Base for analytics operations
- `ProviderConfigTool` - Base for provider configuration

#### **Tool Decorators** (`tools/decorators.py`)
- `@mcp_tool(name, description, input_schema)` - Register tool metadata
- `@default_value(param, value)` - Set default parameter values
- `@require_project` - Require project_id parameter

#### **V2 Tools Structure**
All tools follow a consistent pattern:
```
tools/
├── projects_v2/
│   ├── list_projects.py
│   ├── get_project.py
│   ├── create_project.py
│   ├── update_project.py
│   ├── delete_project.py
│   ├── search_projects.py
│   └── register.py
├── tasks_v2/
│   ├── list_tasks.py
│   ├── get_task.py
│   ├── create_task.py
│   ├── update_task.py
│   ├── delete_task.py
│   ├── assign_task.py
│   ├── update_task_status.py
│   ├── search_tasks.py
│   └── register.py
├── sprints_v2/
├── epics_v2/
└── analytics_v2/
```

**Tool Registration Pattern:**
1. Each tool is a class inheriting from `ReadTool`, `WriteTool`, or `AnalyticsTool`
2. Decorated with `@mcp_tool()` for metadata
3. Implements `async def execute(**kwargs)` method
4. Registered via `register_*_tools_v2()` function in `register.py`
5. Tools receive `ToolContext` in constructor

### 4. Transports (`transports/`)

#### **SSE Transport** (`transports/sse.py`)
- FastAPI app with SSE endpoint
- Uses MCP SDK's `SseServerTransport`
- Authentication via `AuthManager.extract_user_from_request()`
- User-scoped server instances via `UserContext.create_user_scoped_server()`

#### **HTTP Transport** (`transports/http.py`)
- RESTful API endpoints
- `/tools/list` - List available tools
- `/tools/call` - Call a tool
- `/tools/call/stream` - Stream tool results
- `/health` - Health check
- Full OpenAPI documentation at `/docs`

#### **STDIO Transport** (`transports/stdio.py`)
- Standard input/output for Claude Desktop
- Uses MCP SDK's `stdio_server()`
- No authentication (local subprocess)

### 5. Services (`services/`)

#### **AuthService** (`services/auth_service.py`)
- **DEPRECATED** - Use `AuthManager` directly
- Kept for backward compatibility

#### **UserContext** (`services/user_context.py`)
- `create_user_scoped_server(user_id, config)` - Create user-scoped server
- Ensures credential isolation (only providers where `created_by = user_id`)

#### **ToolRegistry** (`services/tool_registry.py`)
- Tool registration service (for future use)

### 6. Database (`database/`)

**Independent Database** - Completely separate from backend database

**Models:**
- `User` - User accounts
- `UserMCPAPIKey` - API keys for MCP server access
- `PMProviderConnection` - PM provider configurations
  - `created_by` - User ID (for credential scoping)
  - `backend_provider_id` - Maps to backend provider IDs
  - `is_active` - Active status

**Connection:**
- `get_mcp_db_session()` - Get database session
- `init_mcp_db()` - Initialize database

### 7. Configuration (`config.py`)

**PMServerConfig** - Server configuration:
- `server_name` - Server identifier
- `database_url` - Database connection string
- `transport` - Transport type (stdio/sse/http)
- `host`, `port` - Network settings
- `enable_auth` - Authentication enabled (default: True)
- `auth_token_secret` - Secret for token validation
- `log_level` - Logging level

## Tool Execution Flow

```
1. Client calls tool via transport (SSE/HTTP/stdio)
   ↓
2. Transport extracts user_id from request (if authenticated)
   ↓
3. Server routes to tool handler
   ↓
4. Tool receives ToolContext (with user_id)
   ↓
5. Tool calls ProviderManager.get_provider() or get_active_providers()
   ↓
6. ProviderManager filters providers by user_id (if set)
   ↓
7. Tool executes operation via provider instance
   ↓
8. Result returned to client
```

## User Scoping & Credential Isolation

**Key Feature:** User-scoped credential isolation

1. **Server Initialization:**
   - `PMMCPServer(user_id=user_id)` - Creates user-scoped server
   - `ToolContext(user_id=user_id)` - Passes user_id to context

2. **Provider Filtering:**
   - `ProviderManager.get_active_providers()` filters by `created_by = user_id`
   - Only providers created by the user are accessible

3. **Transport Integration:**
   - SSE transport extracts user_id from API key
   - Creates user-scoped server instance per connection
   - HTTP transport validates API key and extracts user_id

## Tool Registration

**V2 Tools Pattern:**
```python
@mcp_tool(
    name="list_tasks",
    description="List tasks from PM providers",
    input_schema={...}
)
class ListTasksTool(ReadTool):
    async def execute(self, project_id: str | None = None, ...):
        # Tool logic here
        return result

# In register.py:
def register_task_tools_v2(server, context, tool_names, tool_functions):
    tool = ListTasksTool(context)
    # Register with server...
```

**Legacy Tools:**
- Some tools still use old pattern (e.g., `provider_config.py`)
- Uses `@server.call_tool()` decorator directly
- Must store in `tool_functions` dict for routing

## Authentication

**Default:** Authentication is **enabled by default** (security)

**API Key Format:**
- `mcp_<64-hex-chars>`
- Stored in `user_mcp_api_keys` table
- Validated by `AuthManager.validate_api_key()`

**Request Headers:**
- `X-MCP-API-Key: mcp_xxx` - API key header
- `X-User-ID: <uuid>` - Direct user ID (testing only)

**Transport Behavior:**
- **SSE/HTTP:** Requires authentication (extracts user_id from API key)
- **STDIO:** No authentication (local subprocess)

## Entry Point

**Script:** `scripts/run_pm_mcp_server.py`

**Usage:**
```bash
# STDIO (Claude Desktop)
python scripts/run_pm_mcp_server.py --transport stdio

# SSE (Web agents)
python scripts/run_pm_mcp_server.py --transport sse --port 8080

# HTTP (REST API)
python scripts/run_pm_mcp_server.py --transport http --port 8080
```

**Flow:**
1. Parse command line arguments
2. Create `PMServerConfig` from env/args
3. Create `PMMCPServer` instance
4. Call `server.run()` which dispatches to appropriate transport

## Key Design Decisions

1. **Independent Database:** MCP Server has its own database, separate from backend
2. **User Scoping:** All operations are user-scoped for credential isolation
3. **Tool Context:** Single context object passed to all tools (replaces multiple parameters)
4. **Manager Pattern:** ProviderManager, AnalyticsManager, AuthManager separate concerns
5. **V2 Tools:** New tools use class-based pattern with decorators
6. **Transport Abstraction:** Three transports (stdio/SSE/HTTP) with unified interface
7. **Authentication by Default:** Security-first approach

## File Structure Summary

```
mcp_server/
├── __init__.py
├── server.py              # Main server class
├── config.py              # Configuration
├── auth.py                # Legacy auth (deprecated)
│
├── core/                  # Core managers
│   ├── tool_context.py   # Shared context for tools
│   ├── provider_manager.py  # Provider lifecycle
│   ├── analytics_manager.py # Analytics services
│   └── auth_manager.py   # Authentication
│
├── services/              # Service layer
│   ├── auth_service.py   # DEPRECATED
│   ├── user_context.py   # User-scoped servers
│   └── tool_registry.py  # Tool registration
│
├── tools/                 # MCP tools
│   ├── base.py           # Base tool classes
│   ├── decorators.py     # Tool decorators
│   ├── provider_config.py # Provider config tools
│   ├── users.py          # User tools
│   ├── task_interactions.py # Task interaction tools
│   ├── projects_v2/      # Project tools (V2)
│   ├── tasks_v2/         # Task tools (V2)
│   ├── sprints_v2/       # Sprint tools (V2)
│   ├── epics_v2/         # Epic tools (V2)
│   ├── analytics_v2/     # Analytics tools (V2)
│   └── pm_service_tools/ # PM Service integration tools
│
├── transports/            # Transport implementations
│   ├── stdio.py          # STDIO transport
│   ├── sse.py            # SSE transport
│   └── http.py           # HTTP transport
│
├── database/             # Database layer
│   ├── models.py         # ORM models
│   ├── connection.py     # Database connection
│   └── __init__.py
│
└── api/                  # API routes
    └── provider_sync.py  # Provider sync endpoint
```

## Dependencies

- **MCP SDK:** `mcp` package for protocol implementation
- **FastAPI:** For SSE and HTTP transports
- **SQLAlchemy:** For database ORM
- **pm_providers:** PM provider abstraction layer
- **pm_service:** PM Service client (optional, for API calls)

## Testing

Tests located in `tests/mcp_server/`:
- `unit/` - Unit tests
- `integration/` - Integration tests

## Future Improvements

1. **Tool Registry:** Use `ToolRegistry` service for all tool registration
2. **Error Handling:** Standardize error handling across all modules
3. **Logging:** Clean up excessive debug logging
4. **Documentation:** Update API documentation with authentication requirements
5. **PM Service Integration:** Complete PM Service client integration

