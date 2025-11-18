# PM MCP Server Architecture

## 🎯 Overview

The PM MCP Server is a standalone service that exposes Project Management operations as MCP (Model Context Protocol) tools. It enables multiple AI agents to interact with PM systems (OpenProject, JIRA, ClickUp) through a standardized protocol.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI Agents Ecosystem                          │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Research │  │ QC Agent │  │ HR Agent │  │ Resource │      │
│  │ Agent    │  │          │  │          │  │ Mgmt     │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│       │             │              │             │             │
│       └─────────────┴──────────────┴─────────────┘             │
│                     │                                           │
│       ┌─────────────▼────────────────┐                         │
│       │  MCP Client (LangChain)      │                         │
│       └─────────────┬────────────────┘                         │
└─────────────────────┼──────────────────────────────────────────┘
                      │ MCP Protocol
                      │ (stdio/sse/http)
┌─────────────────────▼──────────────────────────────────────────┐
│              PM MCP Server (This Package)                      │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  MCP Server Instance                                     │ │
│  │  - Tool Registration                                     │ │
│  │  - Request Handling                                      │ │
│  │  - Response Formatting                                   │ │
│  └────────────────────┬─────────────────────────────────────┘ │
│                       │                                         │
│  ┌────────────────────▼─────────────────────────────────────┐ │
│  │  PM Tools Layer (50+ tools)                             │ │
│  │  - Projects: list, get, create, update, delete          │ │
│  │  - Tasks: list, get, create, update, delete, assign     │ │
│  │  - Sprints: list, get, create, update, planning         │ │
│  │  - Epics: list, get, create, link                       │ │
│  │  - Users: list, get, assign                             │ │
│  │  - Analytics: burndown, velocity, gantt                 │ │
│  └────────────────────┬─────────────────────────────────────┘ │
│                       │                                         │
│  ┌────────────────────▼─────────────────────────────────────┐ │
│  │  PMHandler (Multi-Provider)                             │ │
│  │  - Provider routing                                      │ │
│  │  - Multi-provider aggregation                           │ │
│  │  - Error handling                                        │ │
│  └────────────────────┬─────────────────────────────────────┘ │
│                       │                                         │
│  ┌────────────────────▼─────────────────────────────────────┐ │
│  │  PM Providers                                            │ │
│  │  - OpenProject Provider                                  │ │
│  │  - JIRA Provider                                         │ │
│  │  - ClickUp Provider                                      │ │
│  │  - Internal Provider (PostgreSQL)                       │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 File Structure

```
src/mcp_servers/pm_server/
├── __init__.py              # Package exports
├── server.py                # Main MCP server implementation
├── tools/                   # MCP tool definitions
│   ├── __init__.py
│   ├── projects.py          # Project tools
│   ├── tasks.py             # Task tools
│   ├── sprints.py           # Sprint tools
│   ├── epics.py             # Epic tools
│   ├── users.py             # User tools
│   └── analytics.py         # Analytics tools
├── config.py                # Server configuration
├── auth.py                  # Authentication & authorization
├── transports/              # Transport implementations
│   ├── __init__.py
│   ├── stdio.py             # Stdio transport
│   ├── sse.py               # SSE transport
│   └── http.py              # HTTP transport
├── utils.py                 # Utility functions
└── README.md                # Server documentation

scripts/
├── run_pm_mcp_server.py     # Server startup script
└── test_pm_mcp_client.py    # Test client

docs/
└── PM_MCP_SERVER_USAGE.md   # Usage guide
```

## 🔧 Core Components

### 1. MCP Server Instance (`server.py`)

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server

class PMMCPServer:
    """Main PM MCP Server class."""
    
    def __init__(self, db_session):
        self.server = Server("pm-server")
        self.pm_handler = PMHandler.from_db_session(db_session)
        self._register_all_tools()
    
    def _register_all_tools(self):
        """Register all PM tools with the MCP server."""
        # Import and register tools from each module
        from .tools import (
            register_project_tools,
            register_task_tools,
            register_sprint_tools,
            register_epic_tools,
            register_user_tools,
            register_analytics_tools
        )
        
        register_project_tools(self.server, self.pm_handler)
        register_task_tools(self.server, self.pm_handler)
        register_sprint_tools(self.server, self.pm_handler)
        register_epic_tools(self.server, self.pm_handler)
        register_user_tools(self.server, self.pm_handler)
        register_analytics_tools(self.server, self.pm_handler)
    
    async def run_stdio(self):
        """Run server with stdio transport."""
        async with stdio_server() as streams:
            await self.server.run(
                streams[0], streams[1],
                self.server.create_initialization_options()
            )
    
    async def run_sse(self, host: str, port: int):
        """Run server with SSE transport."""
        # Implementation for SSE
        pass
    
    async def run_http(self, host: str, port: int):
        """Run server with HTTP transport."""
        # Implementation for HTTP
        pass
```

### 2. Tool Registration Pattern

Each tool module follows this pattern:

```python
# tools/projects.py
def register_project_tools(server: Server, pm_handler: PMHandler):
    """Register project-related tools."""
    
    @server.tool()
    async def list_projects(
        provider_id: str | None = None
    ) -> list[dict]:
        """
        List all accessible projects across all PM providers.
        
        Args:
            provider_id: Optional provider ID to filter projects
        
        Returns:
            List of project dictionaries with id, name, description, etc.
        """
        try:
            projects = await pm_handler.list_all_projects(provider_id)
            return [project.dict() for project in projects]
        except Exception as e:
            logger.error(f"Error listing projects: {e}")
            raise
    
    @server.tool()
    async def get_project(
        project_id: str
    ) -> dict:
        """Get detailed information about a specific project."""
        project = await pm_handler.get_project(project_id)
        return project.dict()
    
    @server.tool()
    async def create_project(
        name: str,
        description: str | None = None,
        provider_id: str | None = None
    ) -> dict:
        """Create a new project."""
        project = await pm_handler.create_project(
            name=name,
            description=description,
            provider_id=provider_id
        )
        return project.dict()
    
    # ... more project tools
```

## 🔐 Authentication & Authorization

```python
# auth.py
class AuthManager:
    """Manages authentication and authorization for PM MCP Server."""
    
    def __init__(self):
        self.agent_permissions = {}
        self.audit_logger = AuditLogger()
    
    async def authenticate_agent(self, agent_id: str, token: str) -> bool:
        """Authenticate an agent."""
        # Verify agent token
        pass
    
    async def authorize_tool(
        self, 
        agent_id: str, 
        tool_name: str, 
        params: dict
    ) -> bool:
        """Check if agent is authorized to use tool."""
        # Check permissions
        pass
    
    async def audit_log(
        self, 
        agent_id: str, 
        tool_name: str, 
        params: dict, 
        result: any
    ):
        """Log tool usage for audit."""
        self.audit_logger.log({
            "timestamp": datetime.now(),
            "agent_id": agent_id,
            "tool": tool_name,
            "params": params,
            "success": result is not None
        })
```

## 🛠️ Complete Tool List (50+ tools)

### Projects (6 tools)
- `list_projects` - List all projects
- `get_project` - Get project details
- `create_project` - Create new project
- `update_project` - Update project
- `delete_project` - Delete project
- `search_projects` - Search projects

### Tasks (12 tools)
- `list_tasks` - List tasks in project
- `list_my_tasks` - List current user's tasks
- `get_task` - Get task details
- `create_task` - Create new task
- `update_task` - Update task
- `delete_task` - Delete task
- `assign_task` - Assign task to user
- `update_task_status` - Change task status
- `add_task_comment` - Add comment to task
- `link_tasks` - Link related tasks
- `search_tasks` - Search tasks
- `bulk_update_tasks` - Update multiple tasks

### Sprints (10 tools)
- `list_sprints` - List sprints
- `get_sprint` - Get sprint details
- `create_sprint` - Create new sprint
- `update_sprint` - Update sprint
- `delete_sprint` - Delete sprint
- `start_sprint` - Start a sprint
- `complete_sprint` - Complete a sprint
- `add_task_to_sprint` - Add task to sprint
- `remove_task_from_sprint` - Remove task from sprint
- `sprint_planning` - Generate sprint plan

### Epics (8 tools)
- `list_epics` - List epics
- `get_epic` - Get epic details
- `create_epic` - Create new epic
- `update_epic` - Update epic
- `delete_epic` - Delete epic
- `link_task_to_epic` - Link task to epic
- `unlink_task_from_epic` - Unlink task from epic
- `get_epic_progress` - Get epic completion progress

### Users (5 tools)
- `list_users` - List all users
- `get_user` - Get user details
- `get_current_user` - Get current user info
- `search_users` - Search users
- `get_user_workload` - Get user's task workload

### Analytics (10+ tools)
- `burndown_chart` - Generate burndown chart data
- `velocity_chart` - Calculate team velocity
- `gantt_chart` - Generate Gantt chart data
- `task_distribution` - Analyze task distribution
- `sprint_report` - Generate sprint report
- `epic_report` - Generate epic report
- `team_performance` - Analyze team performance
- `time_tracking_report` - Time tracking analysis
- `resource_utilization` - Resource utilization metrics
- `project_health` - Project health indicators

## 🚀 Usage Examples

### From DeerFlow Agent

```python
# src/graph/nodes.py
async def researcher_node(state, config):
    # Load PM tools from MCP server
    mcp_client = MultiServerMCPClient({
        "pm-server": {
            "transport": "sse",
            "url": "http://localhost:8080/sse"
        }
    })
    
    pm_tools = await mcp_client.get_tools()
    tools = [web_search, crawl] + pm_tools
    
    agent = create_agent("researcher", tools)
    return await execute_agent(state, agent)
```

### From QC Agent (New)

```python
# agents/qc_agent.py
async def qc_agent_node(state, config):
    mcp_client = MultiServerMCPClient({
        "pm-server": {
            "transport": "sse",
            "url": "http://localhost:8080/sse",
            "enabled_tools": [
                "list_tasks",
                "update_task_status",
                "create_task",  # For creating defects
                "link_tasks"    # For linking defects to tasks
            ]
        }
    })
    
    tools = await mcp_client.get_tools()
    agent = create_agent("qc_agent", tools)
    return await execute_agent(state, agent)
```

### From Claude Desktop

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "pm-server": {
      "command": "python",
      "args": [
        "/path/to/scripts/run_pm_mcp_server.py"
      ],
      "env": {
        "DATABASE_URL": "postgresql://..."
      }
    }
  }
}
```

## 🔄 Migration Path

### Phase 1: Build PM MCP Server
1. Create package structure
2. Implement core MCP server
3. Register 10 core tools
4. Test with stdio transport

### Phase 2: Complete Tool Set
1. Implement all 50+ tools
2. Add SSE and HTTP transports
3. Add authentication
4. Add audit logging

### Phase 3: Migrate DeerFlow
1. Update researcher/coder agents to use MCP
2. Remove direct PM tool imports
3. Test thoroughly
4. Deploy

### Phase 4: New Agents
1. Implement QC Agent
2. Implement HR Agent
3. Implement Resource Management Agent
4. Document agent creation process

## 📊 Performance Considerations

- **Latency**: Target < 200ms for tool calls
- **Caching**: Cache frequently accessed data (projects, users)
- **Connection Pooling**: Reuse PM provider connections
- **Rate Limiting**: Prevent abuse of PM APIs
- **Monitoring**: Track tool usage, errors, latency

## 🔒 Security

- **Authentication**: Token-based agent authentication
- **Authorization**: Role-based access control (RBAC)
- **Audit Logging**: Log all tool calls
- **Data Validation**: Validate all inputs
- **Error Handling**: Don't leak sensitive info in errors

## 📚 References

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [LangChain MCP Integration](https://python.langchain.com/docs/integrations/tools/mcp)

