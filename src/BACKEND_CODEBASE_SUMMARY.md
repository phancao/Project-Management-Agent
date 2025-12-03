# Backend Codebase Summary

## Overview

The backend is a sophisticated AI-powered project management system built with FastAPI, LangGraph, and DeerFlow. It combines deep research capabilities with intelligent conversation flow management and multi-provider PM integration.

## Architecture

### Entry Points

1. **`server.py`** (Root)
   - Main entry point for DeerFlow API server
   - Uses uvicorn to run `src.server:app`
   - Handles Windows event loop policy configuration
   - Supports reload, host, port, and log-level configuration

2. **`api/main.py`** (Alternative API)
   - FastAPI server for Project Management Agent
   - Provides RESTful APIs and WebSocket endpoints
   - Includes conversation flow management integration
   - Handles project/task/sprint management endpoints

3. **`backend/server/app.py`** (Main Backend Server)
   - Primary FastAPI application (3686 lines)
   - Handles chat streaming, MCP integration, PM operations
   - Analytics endpoints, RAG configuration
   - Provider management and synchronization

### Core Components

#### 1. Graph/Workflow System (`backend/graph/`)

**`builder.py`**
- Builds LangGraph state graph with nodes:
  - `coordinator` - Routes requests to appropriate agents
  - `background_investigator` - Performs web search before planning
  - `planner` - Generates execution plans
  - `research_team` - Orchestrates research tasks
  - `researcher` - Performs research steps
  - `coder` - Handles processing steps
  - `pm_agent` - Handles PM queries
  - `reporter` - Generates final reports
  - `human_feedback` - Handles user clarification

**`nodes.py`**
- Implements all graph node functions
- `background_investigation_node` - Web search using Tavily or other engines
- `planner_node` - Generates structured plans with steps
- `coordinator_node` - Routes based on user intent
- `pm_agent_node` - Handles project management queries
- Plan validation and repair logic

**`types.py`**
- `State` class extending `MessagesState`
- Tracks: locale, research_topic, current_plan, project_id
- Clarification state management
- Workflow control variables

**`workflow.py`**
- `run_agent_workflow_async()` - Non-streaming workflow execution
- `run_agent_workflow_stream()` - Streaming workflow with intermediate states
- Handles clarification rounds recursively
- Configures MCP servers (pm-server, github-trending)

#### 2. Agents System (`backend/agents/`)

**`agents.py`**
- `create_agent()` - Factory function for creating ReAct agents
- Uses `AGENT_LLM_MAP` to assign LLM types to agents
- Wraps tools with interceptors for interrupt logic
- Supports pre-model hooks and tool-specific interrupts

**`tool_interceptor.py`**
- Wraps tools to add interrupt-before-execution capability
- Allows human-in-the-loop workflows

#### 3. Conversation Flow (`backend/conversation/`)

**`flow_manager.py`**
- `ConversationFlowManager` - Manages conversation state
- Intent detection and classification
- Progressive data gathering
- Context management per session
- Integration with self-learning system

**`self_learning.py`**
- Intent classification learning from user feedback
- Adapts conversation flows based on corrections

#### 4. PM Providers (`backend/pm_providers/`)

**`base.py`**
- `BasePMProvider` - Abstract interface for all PM providers
- Defines operations: projects, tasks, sprints, users, epics
- Health check and optional bulk operations

**`factory.py`**
- Creates provider instances based on configuration
- Supports: OpenProject, JIRA, ClickUp, Internal (mock)

**`models.py`**
- Data models: PMProject, PMTask, PMSprint, PMUser, PMEpic
- PMProviderConfig for provider configuration
- Status and priority enums

**Provider Implementations:**
- `openproject.py` / `openproject_v13.py` - OpenProject integration
- `jira.py` - JIRA integration
- `clickup.py` - ClickUp integration
- `internal.py` - Mock provider for testing

#### 5. Tools (`backend/tools/`)

**`pm_tools.py`**
- Tools for agents to interact with PM data:
  - `list_projects()` - List all projects
  - `get_project()` - Get project details
  - `list_tasks()` - List tasks with filters
  - `list_my_tasks()` - Get current user's tasks
  - `create_task()` - Create new tasks
  - `update_task()` - Update task properties
  - `list_sprints()` - List sprints
  - `get_sprint()` - Get sprint details
  - Uses global `_pm_handler` instance

**`analytics_tools.py`**
- Tools for generating analytics charts:
  - Burndown charts
  - Velocity charts
  - Sprint reports
  - Project summaries

**`backend_api.py`**
- Tools for calling backend REST APIs
- Allows agents to trigger backend operations

**`search.py`**
- Web search tools (Tavily, etc.)
- `LoggedTavilySearch` - Search with logging

**`crawl.py`**
- Web crawling tools
- `crawl_tool()` - Crawl and extract content from URLs

**`retriever.py`**
- RAG retrieval tools
- Vector search integration

**`python_repl.py`**
- Python REPL tool for code execution
- Sandboxed execution environment

#### 6. Analytics (`backend/analytics/`)

**`service.py`**
- `AnalyticsService` - Main analytics service
- Methods:
  - `get_burndown_chart()` - Sprint burndown
  - `get_velocity_chart()` - Team velocity
  - `get_sprint_report()` - Comprehensive sprint report
  - `get_project_summary()` - Project overview
  - `get_cfd_chart()` - Cumulative Flow Diagram
  - `get_cycle_time_chart()` - Cycle time analysis
  - `get_work_distribution_chart()` - Work distribution
  - `get_issue_trend_chart()` - Issue trends
- Caching with TTL (5 minutes)
- Data transformation from PM provider format

**`calculators/`**
- `burndown.py` - Burndown calculation logic
- `velocity.py` - Velocity calculation
- `sprint_report.py` - Sprint report generation
- `cfd.py` - Cumulative Flow Diagram
- `cycle_time.py` - Cycle time metrics
- `work_distribution.py` - Work distribution analysis
- `issue_trend.py` - Issue trend analysis

**`adapters/`**
- `base.py` - `BaseAnalyticsAdapter` interface
- `pm_adapter.py` - Adapter for PM providers
- `task_status_resolver.py` - Status mapping logic

**`models.py`**
- Data models: ChartResponse, SprintReport, SprintData, WorkItem
- Enums: ChartType, TaskStatus, Priority, WorkItemType

#### 7. Server Endpoints (`backend/server/`)

**`app.py`** (Main API Server - 3686 lines)

**Chat Endpoints:**
- `POST /api/chat/stream` - Streaming chat with SSE
- Handles DeerFlow research integration
- Progress updates during workflow execution
- Tool call streaming and interrupts

**PM Endpoints:**
- `GET /api/pm/projects` - List projects
- `POST /api/pm/projects/{id}/tasks` - Create task
- `GET /api/pm/projects/{id}/tasks` - List tasks
- `GET /api/pm/projects/{id}/sprints` - List sprints
- `GET /api/pm/projects/{id}/epics` - List epics
- `POST /api/pm/projects/{id}/epics` - Create epic
- `PUT /api/pm/tasks/{id}` - Update task
- `POST /api/pm/tasks/{id}/assign` - Assign task
- `POST /api/pm/tasks/{id}/sprint` - Assign to sprint
- `GET /api/pm/users` - List users
- `GET /api/pm/providers` - List providers
- `POST /api/pm/providers/import` - Import projects
- `PUT /api/pm/providers/{id}` - Update provider
- `POST /api/pm/providers/{id}/sync` - Sync to MCP

**Analytics Endpoints:**
- `GET /api/analytics/projects/{id}/burndown` - Burndown chart
- `GET /api/analytics/projects/{id}/velocity` - Velocity chart
- `GET /api/analytics/sprints/{id}/report` - Sprint report
- `GET /api/analytics/projects/{id}/summary` - Project summary
- `GET /api/analytics/projects/{id}/cfd` - CFD chart
- `GET /api/analytics/projects/{id}/cycle-time` - Cycle time
- `GET /api/analytics/projects/{id}/work-distribution` - Distribution
- `GET /api/analytics/projects/{id}/issue-trend` - Issue trend

**Other Endpoints:**
- `GET /health` - Health check
- `GET /api/config` - Configuration
- `GET /api/rag/config` - RAG configuration
- `GET /api/rag/resources` - RAG resources
- `POST /api/tts` - Text-to-speech
- `POST /api/podcast` - Generate podcast
- `POST /api/ppt` - Generate PPT
- `POST /api/prose` - Generate prose
- `POST /api/enhance-prompt` - Enhance prompt

**`mcp_utils.py`**
- `load_mcp_tools()` - Load tools from MCP servers
- Supports stdio, SSE, and streamable_http transports
- Timeout handling and error management

**`mcp_sync.py`**
- Synchronizes PM providers to MCP server
- Ensures MCP server has latest provider configurations

**`pm_service_client.py`**
- Client for PM service communication
- Handles provider operations

#### 8. Configuration (`backend/config/`)

**`configuration.py`**
- `Configuration` dataclass
- Fields: resources, max_plan_iterations, max_step_num, max_search_results
- MCP settings, report style, deep thinking, web search enforcement
- `from_runnable_config()` - Creates from LangGraph config

**`agents.py`**
- `AGENT_LLM_MAP` - Maps agent types to LLM types
- Agent configuration

**`tools.py`**
- Tool selection and configuration
- `SELECTED_RAG_PROVIDER` - RAG provider selection

**`loader.py`**
- Environment variable loaders
- `get_str_env()`, `get_int_env()`, `get_bool_env()`

**`debug_config.py`**
- Debug configuration from environment
- Smart debug flags

#### 9. LLM Integration (`backend/llms/`)

**`llm.py`**
- `get_llm_by_type()` - Get LLM instance by type
- `get_llm_token_limit_by_type()` - Get token limits
- `get_configured_llm_models()` - Get all configured models
- Supports multiple LLM providers

**`providers/dashscope.py`**
- DashScope (Alibaba Cloud) LLM provider

#### 10. Memory (`backend/memory/`)

**`conversation_memory.py`**
- `ConversationMemory` - Hybrid memory system
- Three levels:
  1. Short-term: Recent messages (full text)
  2. Working: Summarized older messages
  3. Long-term: Vector store for semantic retrieval
- Prevents context overflow
- Token limit management

#### 11. RAG (`backend/rag/`)

**`builder.py`**
- Builds RAG retriever instances
- Supports multiple providers

**`retriever.py`**
- `Resource` model for RAG resources
- Retrieval logic

**`milvus.py`**
- Milvus vector database integration
- `load_examples()` - Load example data

**Providers:**
- `dify.py` - Dify integration
- `ragflow.py` - RAGFlow integration
- `moi.py` - MoI integration
- `vikingdb_knowledge_base.py` - VikingDB integration

#### 12. Prompts (`backend/prompts/`)

Template files for different agents:
- `planner.md` - Planning agent prompts
- `researcher.md` - Research agent prompts
- `coder.md` - Coding agent prompts
- `coordinator.md` - Coordinator agent prompts
- `reporter.md` - Reporter agent prompts
- `pm_agent.md` - PM agent prompts
- `sprint_planner.md` - Sprint planning prompts
- Multi-language support (zh_CN variants)

**`template.py`**
- `apply_prompt_template()` - Applies prompt templates
- Handles locale and state variables

**`planner_model.py`**
- `Plan` and `Step` Pydantic models
- Plan structure definition

#### 13. MCP Server Integration (`backend/mcp_servers/pm_server/`)

**`server.py`**
- MCP server implementation for PM tools
- Exposes PM operations as MCP tools
- Supports SSE and HTTP transports

**`pm_handler.py`**
- Handles PM operations
- Multi-provider support
- Single and multi-provider modes

**`tools/`**
- Individual tool implementations
- Wraps PM handler methods

**`auth/`**
- Authentication for MCP server
- API key validation

**`transports/`**
- `sse.py` - Server-Sent Events transport
- `http.py` - HTTP transport

#### 14. Utils (`backend/utils/`)

**`json_utils.py`**
- JSON repair and sanitization
- `repair_json_output()` - Fixes malformed JSON
- `sanitize_tool_response()` - Cleans tool responses

**`log_sanitizer.py`**
- Log sanitization functions
- Removes sensitive data from logs

**`context_manager.py`**
- `ContextManager` - Manages agent context
- `validate_message_content()` - Validates messages

#### 15. Handlers (`backend/handlers/`)

**`report_generator.py`**
- Generates project reports
- WBS generation

**`sprint_planner.py`**
- Sprint planning logic
- Capacity calculation

**`wbs_generator.py`**
- Work Breakdown Structure generation
- Task decomposition

## Data Flow

### Chat Flow
```
User Message
  ↓
FastAPI Endpoint (/api/chat/stream)
  ↓
ConversationFlowManager
  ↓
DeerFlow Workflow (run_agent_workflow_stream)
  ↓
Graph Execution (coordinator → planner → research_team → reporter)
  ↓
Agent Tools (PM tools, search, RAG, etc.)
  ↓
Streaming Response (SSE)
```

### PM Operations Flow
```
Frontend Request
  ↓
FastAPI Endpoint (/api/pm/*)
  ↓
PMHandler (from conversation flow or direct)
  ↓
PM Provider (OpenProject/JIRA/ClickUp)
  ↓
Response
```

### Analytics Flow
```
Analytics Request
  ↓
AnalyticsService
  ↓
PMProviderAnalyticsAdapter
  ↓
PM Provider (fetch data)
  ↓
Calculator (burndown, velocity, etc.)
  ↓
ChartResponse
```

## Key Patterns

### 1. Multi-Provider Architecture
- Abstract `BasePMProvider` interface
- Factory pattern for provider creation
- Unified data models across providers
- Provider-specific implementations

### 2. Agent Orchestration
- LangGraph for workflow management
- ReAct agents for tool use
- Conditional routing based on state
- Streaming for real-time updates

### 3. Conversation Management
- Session-based context management
- Intent detection and classification
- Progressive data gathering
- Self-learning from feedback

### 4. Caching Strategy
- Analytics service caching (5 min TTL)
- React Query on frontend
- In-memory caches for frequently accessed data

### 5. Error Handling
- Graceful degradation when providers unavailable
- Fallback to mock data
- Comprehensive error logging
- User-friendly error messages

## Configuration

### Environment Variables
- `OPENAI_API_KEY` - OpenAI API key
- `PM_MCP_API_KEY` - MCP server API key
- `DATABASE_URL` - PostgreSQL connection
- `ALLOWED_ORIGINS` - CORS origins
- `AGENT_RECURSION_LIMIT` - Graph recursion limit
- Various LLM provider keys

### MCP Settings
- PM server: SSE transport at `http://pm_mcp_server:8080/sse`
- GitHub trending: stdio transport
- Dynamic tool loading from MCP servers

## Testing

- Unit tests in `tests/` directory
- Integration tests for PM providers
- Mock providers for testing

## Deployment

- Docker containerization
- Docker Compose for local development
- Separate containers for:
  - Backend API
  - MCP Server
  - Frontend
  - Database
  - Redis

## Key Files Reference

- **Entry**: `server.py`, `api/main.py`, `backend/server/app.py`
- **Workflow**: `backend/workflow.py`, `backend/graph/builder.py`
- **Agents**: `backend/agents/agents.py`
- **PM**: `backend/pm_providers/base.py`, `backend/pm_providers/factory.py`
- **Tools**: `backend/tools/pm_tools.py`, `backend/tools/analytics_tools.py`
- **Analytics**: `backend/analytics/service.py`
- **Conversation**: `backend/conversation/flow_manager.py`
- **Config**: `backend/config/configuration.py`

## Dependencies

- FastAPI - Web framework
- LangGraph - Agent workflows
- LangChain - LLM framework
- Pydantic - Data validation
- SQLAlchemy - ORM
- PostgreSQL - Database
- Redis - Caching
- MCP - Model Context Protocol
- Tavily - Web search
- Various LLM SDKs




