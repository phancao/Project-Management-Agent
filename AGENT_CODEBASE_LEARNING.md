# Agent Codebase Architecture - Complete Learning Summary

## 🏗️ Three-Layer Separation Architecture

The system has been separated into three distinct layers:

### 1. Frontend + Backend (`src/server/` + `web/`)
- **Backend API** (`src/server/app.py`): FastAPI application serving HTTP endpoints
- **Frontend** (`web/`): Next.js React application
- **PM Service Client** (`src/server/pm_service_client.py`): Client wrapper that calls PM Service API
- **Database**: Backend database for user data, sessions, etc.

### 2. PM Service (`pm_service/`)
- **Independent Microservice**: Separate FastAPI service (port 8001)
- **PM Handler** (`pm_service/handlers/pm_handler.py`): Unified PM provider abstraction layer
- **PM Providers** (`pm_service/providers/`): OpenProject, JIRA, ClickUp implementations
- **Database**: PM Service database for provider connections
- **API Endpoints**: RESTful API for PM operations
- **Client Library** (`pm_service/client/`): Async client for other services

### 3. PM MCP Server (`src/mcp_servers/pm_server/`)
- **MCP Protocol Server**: Exposes PM operations as MCP tools for AI agents
- **MCP PM Handler** (`src/mcp_servers/pm_server/pm_handler.py`): Independent handler using MCP Server's own database
- **MCP Tools** (`src/mcp_servers/pm_server/tools/`): 55+ MCP tools for agents
- **Transports**: SSE (Server-Sent Events) and HTTP transports
- **Database**: MCP Server's own database (separate from Backend and PM Service)

## 🤖 Agent System Architecture

### Workflow Graph (LangGraph)

```
START
  ↓
Coordinator
  ↓
Planner → Research Team → Researcher/Coder/PM Agent
  ↓                              ↓
Reporter ←──────────────────────┘
  ↓
END
```

### Agent Nodes

#### 1. **Coordinator** (`coordinator_node`)
- Entry point for user queries
- Routes to Planner or Background Investigator
- Handles clarification flow

#### 2. **Planner** (`planner_node`)
- Analyzes user query
- Creates execution plan with steps
- Determines if enough context exists
- **Plan Structure**:
  ```python
  Plan:
    - title: str
    - has_enough_context: bool
    - steps: List[Step]
      Step:
        - title: str
        - description: str
        - step_type: StepType (RESEARCH | PROCESSING | PM_QUERY)
        - need_search: bool
        - execution_res: Optional[str]
  ```

#### 3. **Research Team** (`research_team_node`)
- **Routing hub**: Routes to appropriate agent based on step type
- `continue_to_running_research_team()` function:
  - Routes `RESEARCH` steps → `researcher`
  - Routes `PROCESSING` steps → `coder`
  - Routes `PM_QUERY` steps → `pm_agent`
  - Routes to `reporter` when all steps complete

#### 4. **Researcher** (`researcher_node`)
- Executes research steps
- **Tools**: Web search, crawling, backend API, RAG tools, MCP tools (optional)
- Used for: Web research, information gathering

#### 5. **Coder** (`coder_node`)
- Executes processing steps
- **Tools**: Python REPL, backend API, analytics tools, MCP tools (optional)
- Used for: Code execution, data analysis

#### 6. **PM Agent** (`pm_agent_node`) ⭐ **NEW**
- Executes PM query steps
- **Tools**: PM MCP tools ONLY (no web search, no code execution)
- Used for: Sprint analysis, project status, task queries, epic progress
- **Routing**: Activated when `step_type == StepType.PM_QUERY`

#### 7. **Reporter** (`reporter_node`)
- Generates final report from all observations
- Aggregates results from all steps
- Formats response for user

### Step Execution Flow

1. **Planner creates plan** with multiple steps
2. **Research Team routes** to appropriate agent based on `step_type`
3. **Agent executes step**:
   - `_execute_agent_step()` finds first unexecuted step
   - Agent invokes tools based on step description
   - Step result stored in `step.execution_res`
   - Routes back to `research_team`
4. **Research Team checks** for next unexecuted step
5. **Repeat** until all steps complete
6. **Route to Reporter** when done

## 🔧 Tool Loading System

### MCP Tool Loading (`_setup_and_execute_agent_step`)

Agents receive tools via MCP configuration:

```python
config = {
    "mcp_settings": {
        "servers": {
            "pm-server": {
                "transport": "sse",
                "url": "http://pm_mcp_server:8080/sse",
                "headers": {"X-MCP-API-Key": "..."},
                "enabled_tools": None,  # None = all tools
                "add_to_agents": ["pm_agent"]  # Which agents get these tools
            }
        }
    }
}
```

**Process**:
1. Check if agent type is in `add_to_agents` list
2. Connect to MCP server(s) using `MultiServerMCPClient`
3. Load tools via `client.get_tools()`
4. Filter tools if `enabled_tools` specified
5. Add tools to agent's tool list
6. Agent can now call tools via function calling

### Tool Types by Agent

| Agent | Tools Available |
|-------|----------------|
| **Researcher** | Web search, crawling, backend API, RAG, analytics, MCP (optional) |
| **Coder** | Python REPL, backend API, analytics, MCP (optional) |
| **PM Agent** | PM MCP tools ONLY (55+ tools) |

## 📋 Step Types

### StepType Enum (`src/prompts/planner_model.py`)

```python
class StepType(str, Enum):
    RESEARCH = "research"      # → Routes to researcher
    PROCESSING = "processing"  # → Routes to coder
    PM_QUERY = "pm_query"      # → Routes to pm_agent ⭐
```

### When to Use Each

- **RESEARCH**: Web search, information gathering, external research
- **PROCESSING**: Code execution, data analysis, calculations
- **PM_QUERY**: Sprint analysis, project status, task queries, epic progress

## 🎯 PM Agent Workflow

### Example: "Analyze Sprint 4"

1. **Planner creates plan**:
   ```json
   {
     "has_enough_context": false,
     "title": "Sprint 4 Performance Analysis",
     "steps": [
       {
         "step_type": "pm_query",
         "title": "Retrieve Sprint 4 Details",
         "description": "Use list_sprints and get_sprint tools"
       },
       {
         "step_type": "pm_query",
         "title": "Get Sprint 4 Tasks",
         "description": "Use list_tasks with sprint_id filter"
       }
     ]
   }
   ```

2. **Research Team routes** to PM Agent (step_type == PM_QUERY)

3. **PM Agent executes**:
   - Calls `list_sprints(project_id="...")`
   - Calls `get_sprint(sprint_id="sprint-4")`
   - Calls `sprint_report(sprint_id="sprint-4")`
   - Calls `list_tasks(sprint_id="sprint-4")`
   - Gets REAL data from PM MCP Server

4. **Result stored** in `step.execution_res`

5. **Next step executed** (repeat)

6. **Reporter generates** final report

## 🔄 Data Flow

### For PM Queries

```
User Query
  ↓
Backend API (/api/pm/chat/stream)
  ↓
Agent Workflow (LangGraph)
  ↓
PM Agent Node
  ↓
MCP Client → PM MCP Server
  ↓
MCP PM Handler → PM Providers (OpenProject/JIRA/ClickUp)
  ↓
PM Data Retrieved
  ↓
Step Result → Reporter
  ↓
Final Response → Frontend
```

### Tool Call Flow

```
Agent decides to call tool
  ↓
Function calling mechanism
  ↓
MultiServerMCPClient
  ↓
PM MCP Server (SSE transport)
  ↓
Tool handler (e.g., list_sprints)
  ↓
MCP PM Handler
  ↓
PM Provider (OpenProject/JIRA/ClickUp)
  ↓
Tool result returned
  ↓
Agent receives result
  ↓
Agent continues/responds
```

## 📁 Key Files

### Agent System
- `src/graph/builder.py`: LangGraph workflow builder
- `src/graph/nodes.py`: All agent node implementations
- `src/graph/types.py`: State type definitions
- `src/prompts/planner_model.py`: Plan and Step models

### PM Agent
- `src/graph/nodes.py:pm_agent_node()`: PM Agent implementation
- `src/prompts/pm_agent.md`: PM Agent prompt
- `src/graph/builder.py:continue_to_running_research_team()`: Routing logic

### MCP Server
- `src/mcp_servers/pm_server/server.py`: MCP Server main class
- `src/mcp_servers/pm_server/pm_handler.py`: MCP PM Handler
- `src/mcp_servers/pm_server/tools/*.py`: Tool implementations (55+ tools)

### PM Service
- `pm_service/main.py`: PM Service FastAPI app
- `pm_service/handlers/pm_handler.py`: PM Handler for service
- `pm_service/client/`: Client library for other services

### Backend
- `src/server/app.py`: Backend FastAPI application
- `src/server/pm_service_client.py`: PM Service client wrapper
- `src/workflow.py`: Agent workflow runner

## 🔐 Authentication & User Context

### MCP Server Authentication
- Uses `X-MCP-API-Key` header
- User ID extracted from API key
- MCP PM Handler filters providers by `user_id`
- User-scoped tool execution

### PM Service Authentication
- Separate authentication mechanism
- User ID passed via API calls
- PM Service Handler filters by `user_id`

## 🎨 Key Design Patterns

### 1. **Separation of Concerns**
- Backend: User interface, sessions
- PM Service: PM provider logic, unified API
- MCP Server: Tool exposure for AI agents

### 2. **Unified Abstraction**
- PM Handler pattern used in both PM Service and MCP Server
- Consistent interface across layers
- Provider-agnostic design

### 3. **Agent Specialization**
- Each agent has specific tools
- Routing based on step type
- Clear responsibility boundaries

### 4. **MCP Protocol**
- Standardized tool communication
- Multi-server support
- Transport abstraction (SSE, HTTP, stdio)

## 🚀 Execution Flow Example

**User**: "Analyze Sprint 4 performance"

```
1. Backend receives request
2. Creates workflow with MCP config
3. Coordinator → Planner
4. Planner creates plan with PM_QUERY steps
5. Research Team routes to PM Agent
6. PM Agent connects to MCP Server (SSE)
7. PM Agent loads 55+ PM tools
8. PM Agent calls: list_sprints, get_sprint, sprint_report
9. MCP Server → MCP PM Handler → PM Provider
10. Real data returned
11. Step results stored
12. Reporter generates final analysis
13. Response streamed to frontend
```

## 📝 Important Notes

1. **Step Type Matters**: Wrong step type = wrong agent = wrong tools
2. **MCP Configuration**: Agents must be in `add_to_agents` list
3. **User Context**: User ID flows through all layers for scoping
4. **Tool Granularity**: Each MCP tool call should be a separate step
5. **Sequential Execution**: Steps execute one at a time
6. **State Management**: LangGraph manages state across workflow

## 🔍 Debugging Tips

1. **Check step_type**: Is it PM_QUERY, RESEARCH, or PROCESSING?
2. **Check MCP config**: Is agent in `add_to_agents`?
3. **Check tool loading**: Are tools being loaded from MCP server?
4. **Check routing**: Is Research Team routing to correct agent?
5. **Check MCP logs**: Are tool calls reaching MCP server?
6. **Check step execution**: Is `execution_res` being populated?

## 📚 Related Documentation

- `PM_AGENT_IMPLEMENTATION.md`: PM Agent implementation details
- `PM_AGENT_TOOL_ACCESS_FIX.md`: Tool loading fixes
- `PM_SERVICE_IMPLEMENTATION_PLAN.md`: PM Service architecture
- `docs/ARCHITECTURE.md`: Overall system architecture

