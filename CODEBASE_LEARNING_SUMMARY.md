# Project Management Agent - Codebase Learning Summary

## 🎯 Overview

**Project Management Agent** is a sophisticated AI-powered PM system that combines:
- **DeerFlow** (deep research framework) for intelligent research
- **LangGraph** for agent orchestration and workflows
- **Multiple PM Providers** (OpenProject, JIRA, ClickUp) via unified abstraction
- **MCP Protocol** for tool integration with AI agents
- **Analytics Module** for charts and metrics

---

## 🏗️ Core Architecture

### **Three-Tier Architecture**

```
┌──────────────────────────────────────────────────────┐
│              Frontend Layer (Next.js)                │
│  - Chat interface (OpenAI ChatKit)                   │
│  - Project/Task dashboards                           │
│  - Real-time WebSocket updates                       │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│         API Gateway Layer (FastAPI)                  │
│  - REST APIs (/api/*)                                │
│  - WebSocket endpoints                               │
│  - PM endpoints (/api/pm/*)                          │
│  - Analytics endpoints (/api/analytics/*)            │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│           Agent Orchestration Layer                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │
│  │  LangGraph  │  │ Conversation│  │  PM Handler  │ │
│  │  Workflow   │  │ Flow Manager│  │  (Unified)   │ │
│  └─────────────┘  └─────────────┘  └──────────────┘ │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│          Data & Integration Layer                    │
│  - PostgreSQL (projects, tasks, users)               │
│  - PM Providers (OpenProject, JIRA, ClickUp)         │
│  - Vector Store (Qdrant/Milvus) for RAG              │
│  - Redis (caching)                                    │
└──────────────────────────────────────────────────────┘
```

---

## 📦 Key Modules & Their Roles

### **1. Graph Module (`src/graph/`)**
**Purpose**: LangGraph workflow orchestration

**Key Files**:
- `nodes.py` - Agent nodes (coordinator, planner, researcher, coder, reporter)
- `builder.py` - Builds the LangGraph workflow
- `types.py` - State definitions
- `utils.py` - Workflow utilities

**What it does**:
- Routes user requests to appropriate agents
- Manages multi-agent workflows
- Handles research → planning → execution flow
- Supports clarification rounds with users
- Streams agent progress in real-time

**Agents Available**:
- **Coordinator**: Routes and manages workflow
- **Planner**: Creates research plans
- **Researcher**: Conducts web research (uses search tools)
- **Coder**: Executes Python code, calculations
- **Reporter**: Generates final reports

### **2. Conversation Flow Manager (`src/conversation/`)**
**Purpose**: Adaptive conversation handling for PM tasks

**Key Files**:
- `flow_manager.py` - Main conversation orchestrator
- `self_learning.py` - Learn from user feedback

**What it does**:
- **Intent Classification**: Detects what user wants (create project, plan sprint, etc.)
- **Context Gathering**: Progressively collects required data
- **Validation**: Ensures data completeness before execution
- **State Management**: Tracks conversation state per session
- **Multi-Intent Support**: Handles complex, multi-step requests

**Supported Intents**:
```python
CREATE_PROJECT, PLAN_TASKS, RESEARCH_TOPIC
CREATE_WBS, SPRINT_PLANNING, ASSIGN_TASKS
LIST_PROJECTS, LIST_TASKS, LIST_SPRINTS
GET_PROJECT_STATUS, SWITCH_PROJECT
UPDATE_TASK, UPDATE_SPRINT
# + 10 more...
```

### **3. PM Providers (`src/pm_providers/`)**
**Purpose**: Unified abstraction for PM systems

**Architecture**:
```
BasePMProvider (Interface)
    ├── InternalProvider (PostgreSQL)
    ├── OpenProjectProvider (OpenProject API)
    ├── OpenProjectV13Provider (legacy support)
    ├── JiraProvider (WIP)
    └── ClickUpProvider (stub)
```

**Key Files**:
- `base.py` - Base interface (all providers must implement)
- `factory.py` - Creates provider instances
- `builder.py` - Builds provider from config
- `models.py` - Unified data models (PMProject, PMTask, PMSprint, etc.)
- `openproject.py` - Full OpenProject v16 integration ✅
- `jira.py` - JIRA integration (in progress)

**Operations Supported**:
```python
# Projects
list_projects(), get_project(), create_project()
update_project(), delete_project()

# Tasks
list_tasks(), get_task(), create_task()
update_task(), delete_task()

# Sprints
list_sprints(), get_sprint(), create_sprint()
update_sprint(), delete_sprint()

# Users
list_users(), get_user()
```

**Configuration**:
```bash
# Set provider via env var
PM_PROVIDER=openproject  # or internal, jira, clickup
OPENPROJECT_URL=https://your-instance.com
OPENPROJECT_API_KEY=your-key
```

### **4. PM Handler (`src/server/pm_handler.py`)**
**Purpose**: Parent abstraction above PM providers

**Two Modes**:

**Single-Provider Mode** (for agents/conversations):
```python
provider = build_pm_provider(db_session)
handler = PMHandler.from_single_provider(provider)
```

**Multi-Provider Mode** (for API endpoints):
```python
handler = PMHandler.from_db_session(db_session, user_id="user-123")
# Aggregates data from ALL active providers for that user
```

**Why it exists**:
- API endpoints need to query ALL providers at once
- Agents/conversations work with ONE provider at a time
- PMHandler provides unified interface for both patterns

### **5. Analytics Module (`src/analytics/`)** 🆕
**Purpose**: Server-side chart generation for PM metrics

**Structure**:
```
analytics/
├── models.py          # Pydantic data models
├── service.py         # Main analytics service
├── mock_data.py       # Realistic test data generator
├── calculators/       # Chart-specific logic
│   ├── burndown.py
│   ├── velocity.py
│   ├── sprint_report.py
│   ├── cfd.py
│   ├── cycle_time.py
│   └── work_distribution.py
└── adapters/          # Data source adapters
    ├── base.py
    └── pm_adapter.py  # Connects to PM providers
```

**Charts Available**:
- ✅ **Burndown Chart** - Sprint progress tracking
- ✅ **Velocity Chart** - Team performance over sprints
- ✅ **Sprint Report** - Comprehensive sprint summary
- ✅ **CFD** - Cumulative Flow Diagram
- ✅ **Cycle Time** - Task completion time analysis
- ✅ **Work Distribution** - Workload by assignee/priority/type
- ✅ **Issue Trends** - Created vs resolved over time

**API Endpoints**:
```
GET /api/analytics/projects/{id}/burndown
GET /api/analytics/projects/{id}/velocity
GET /api/analytics/sprints/{id}/report
GET /api/analytics/projects/{id}/summary
GET /api/analytics/projects/{id}/cfd
GET /api/analytics/projects/{id}/cycle-time
```

**Usage**:
```python
from src.analytics.service import AnalyticsService

service = AnalyticsService(data_source="pm_providers")
chart = service.get_burndown_chart("PROJECT-1", "SPRINT-1")
```

### **6. Tools Module (`src/tools/`)**
**Purpose**: Tools that AI agents can call

**Available Tools**:
- `search.py` - Web search (Tavily, DuckDuckGo)
- `crawl.py` - Web page crawling
- `python_repl.py` - Execute Python code
- `retriever.py` - RAG vector search
- `pm_tools.py` - PM operations (via PM Handler)
- `analytics_tools.py` - Analytics queries 🆕
- `backend_api.py` - Call backend API endpoints

**PM Tools** (for agents to interact with PM providers):
```python
list_pm_projects()
get_pm_project(project_id)
create_pm_task(project_id, title, description, ...)
update_pm_task(task_id, updates)
list_pm_sprints(project_id)
# + 15 more PM operations
```

**Analytics Tools** (for agents to query analytics):
```python
get_sprint_burndown(project_id, sprint_id)
get_team_velocity(project_id, sprint_count=6)
get_sprint_report(sprint_id, project_id)
get_project_analytics_summary(project_id)
```

**Tool Registration**:
Tools are automatically registered with agents in `src/graph/nodes.py`:
```python
# researcher_node()
tools = [get_web_search_tool(), crawl_tool]
tools.extend(get_pm_tools())  # Add PM tools
tools.extend(get_analytics_tools())  # Add analytics tools
```

### **7. MCP Server (`src/mcp_servers/pm_server/`)**
**Purpose**: Model Context Protocol server for external tool access

**Architecture**:
```
MCP Server (stdio/HTTP/SSE)
    ↓
pm_handler.py (Unified PM operations)
    ↓
PMHandler (multi-provider aggregation)
    ↓
PM Providers (OpenProject, JIRA, etc.)
```

**Key Components**:
- `server.py` - MCP server implementation
- `tools/` - MCP tool definitions (mirrors pm_tools.py)
- `auth/` - User authentication and provider credentials
- `transports/` - stdio, HTTP, SSE transports

**Usage**:
- Cursor IDE can connect to MCP server
- External AI agents can use MCP tools
- Provides same functionality as direct PM tools

### **8. Handlers (`src/handlers/`)**
**Purpose**: High-level business logic handlers

**Files**:
- `report_generator.py` - Generate project reports
- `sprint_planner.py` - Intelligent sprint planning
- `wbs_generator.py` - Work Breakdown Structure generation

**Example - Sprint Planner**:
```python
from src.handlers.sprint_planner import SprintPlanner

planner = SprintPlanner(pm_handler)
plan = await planner.plan_sprints(
    project_id="proj-123",
    tasks=task_list,
    team_capacity=40,
    sprint_duration_weeks=2
)
```

---

## 🔄 Data Flow Patterns

### **Pattern 1: User Chat → Research → Action**

```
1. User: "Create a project for a mobile app"
   ↓
2. ConversationFlowManager
   - Classifies intent: CREATE_PROJECT
   - Checks required fields: name, description, domain
   - Missing: timeline, team_size
   ↓
3. Asks clarifying questions
   - "How long do you expect this project to take?"
   - "How many people will work on it?"
   ↓
4. User provides answers
   ↓
5. FlowManager gathers complete data
   ↓
6. Routes to DeerFlow for research
   - Researches best practices for mobile apps
   - Estimates tasks and timeline
   ↓
7. Routes to PM execution
   - Creates project via PMHandler
   - Generates WBS
   - Creates initial tasks
   ↓
8. Returns success message with project ID
```

### **Pattern 2: Frontend → REST API → PM Providers**

```
Frontend Dashboard
   ↓
GET /api/pm/projects
   ↓
PMHandler (multi-provider mode)
   ↓
Queries ALL active providers:
   - OpenProject instance 1
   - OpenProject instance 2
   - JIRA instance 1
   ↓
Aggregates results
   ↓
Returns unified list to frontend
```

### **Pattern 3: Agent → Tools → External APIs**

```
Researcher Agent
   ↓
Needs PM context
   ↓
Calls list_pm_projects tool
   ↓
Tool → PMHandler → PM Provider
   ↓
Returns project list
   ↓
Agent uses context in research
```

### **Pattern 4: Analytics Chart Generation**

```
Frontend Chart Component
   ↓
GET /api/analytics/projects/P1/burndown
   ↓
AnalyticsService
   ↓
PM Adapter fetches sprint data
   ↓
BurndownCalculator processes data
   ↓
Returns ChartResponse (JSON)
   ↓
Frontend renders with Chart.js/Recharts
```

---

## 🗄️ Database Schema

### **Core Tables**

**`projects`** - Internal projects
```sql
- id, name, description
- status, priority
- start_date, end_date
- created_by, created_at
```

**`tasks`** - Internal tasks
```sql
- id, title, description
- project_id, parent_task_id
- status, priority
- assignee_id, estimated_hours
```

**`users`** - User accounts
```sql
- id, email, name
- role, created_at
```

**`pm_provider_connections`** - External PM system configs
```sql
- id, name, provider_type
- base_url, api_key
- organization_id, workspace_id
- is_active, created_by
```

**`project_sync_mappings`** - Map internal ↔ external projects
```sql
- internal_project_id
- provider_connection_id
- external_project_id
- sync_enabled, last_sync_at
```

**`sprints`** - Sprint data
```sql
- id, name, project_id
- start_date, end_date
- capacity_hours, planned_hours
- status
```

---

## 🔧 Configuration System

### **Environment Variables**

```bash
# LLM Configuration
OPENAI_API_KEY=sk-...
BASIC_MODEL=gpt-4o-mini
REASONING_MODEL=o1-mini

# Database
DATABASE_URL=postgresql://user:pass@localhost/db

# PM Providers
PM_PROVIDER=openproject  # internal, jira, clickup
OPENPROJECT_URL=https://...
OPENPROJECT_API_KEY=...

# MCP Server
MCP_SERVER_PORT=8001
MCP_TRANSPORT=sse  # stdio, http, sse

# Search
SEARCH_API=tavily  # duckduckgo, brave
TAVILY_API_KEY=...

# Analytics
ANALYTICS_DATA_SOURCE=pm_providers  # or mock
```

### **conf.yaml Configuration**

```yaml
BASIC_MODEL:
  base_url: "https://api.openai.com/v1"
  model: "gpt-4o-mini"
  api_key: "${OPENAI_API_KEY}"

REASONING_MODEL:
  model: "o1-mini"

SEARCH_ENGINE:
  engine: tavily
  max_results: 5

RAG:
  provider: milvus  # dify, ragflow, moi
  collection_name: "research_docs"
```

---

## 🚀 Key Entry Points

### **1. Start DeerFlow Research**
```bash
python main.py
# Interactive CLI for research queries
```

### **2. Start FastAPI Server**
```bash
uvicorn src.server.app:app --reload --port 8000
# REST API + WebSocket server
```

### **3. Start MCP Server**
```bash
python scripts/run_pm_mcp_server.py
# MCP server for tool access
```

### **4. Start Frontend**
```bash
cd frontend && npm run dev
# Next.js dev server on port 3000
```

### **5. Docker Compose (All Services)**
```bash
docker-compose up
# Starts everything: API, frontend, PostgreSQL, Redis
```

---

## 🧪 Testing

### **Test Organization**

```
tests/           # Official pytest test suite
scripts/tests/   # Manual/debugging test scripts
```

**Run tests**:
```bash
# All tests
pytest

# Specific module
pytest tests/test_pm_providers.py

# With coverage
pytest --cov=src --cov-report=html

# Manual test script
python scripts/tests/test_openproject_all_pagination.py
```

---

## 📚 Documentation Structure

```
docs/
├── API.md                      # API reference
├── ARCHITECTURE.md             # System architecture
├── USER_GUIDE.md               # End-user guide
├── guides/
│   ├── TESTING_GUIDE.md
│   ├── DEBUG_LOGGING.md
│   └── README.md
├── reports/
│   ├── JIRA_IMPLEMENTATION_SUMMARY.md
│   ├── OPENPROJECT_V13_PROVIDER_REPORT.md
│   └── EMAIL_FIELD_REMOVAL_SUMMARY.md
└── PM_MCP_SERVER_*.md         # MCP server docs

Antigravity/                    # AI-generated learning materials
├── learning_guide.md           # Learning path
├── codebase_overview.md        # High-level overview
├── architecture_deep_dive.md   # Detailed architecture
└── developer_quick_reference.md # Quick reference

src/analytics/README.md         # Analytics module docs
```

---

## 🎯 Common Development Tasks

### **Add a New PM Provider**

1. Create provider class in `src/pm_providers/`
```python
class AsanaProvider(BasePMProvider):
    async def list_projects(self):
        # Implementation
```

2. Register in `factory.py`
```python
PMProvider.ASANA: AsanaProvider
```

3. Add config to `.env`
```bash
ASANA_API_TOKEN=...
```

### **Add a New Chart Type**

1. Create calculator in `src/analytics/calculators/`
```python
class EpicProgressCalculator:
    @staticmethod
    def calculate(epic_data) -> ChartResponse:
        # Implementation
```

2. Add method to `AnalyticsService`
```python
def get_epic_progress(self, epic_id):
    data = self.adapter.get_epic_data(epic_id)
    return EpicProgressCalculator.calculate(data)
```

3. Add API endpoint in `api/main.py`
```python
@app.get("/api/analytics/epics/{epic_id}/progress")
async def get_epic_progress(epic_id: str):
    return analytics_service.get_epic_progress(epic_id)
```

### **Add a New Agent Tool**

1. Create tool function in `src/tools/`
```python
from langchain.tools import tool

@tool
def my_new_tool(param: str) -> str:
    """Tool description for LLM"""
    # Implementation
    return result
```

2. Register in `src/graph/nodes.py`
```python
from src.tools.my_tools import my_new_tool

# In researcher_node or coder_node
tools.append(my_new_tool)
```

### **Debug Agent Workflow**

```python
# Enable debug logging
export DEBUG_PM=true

# Or in code:
import logging
logging.getLogger("src").setLevel(logging.DEBUG)

# Run workflow with debug flag
from src.workflow import run_agent_workflow_async
await run_agent_workflow_async(
    "your query",
    debug=True  # Enables debug logging
)
```

---

## 🔍 Important Design Patterns

### **1. Factory Pattern** (PM Providers)
```python
provider = create_pm_provider(
    provider_type="openproject",
    config=config
)
```

### **2. Builder Pattern** (PM Providers)
```python
provider = build_pm_provider(
    db_session=db,
    provider_name="OpenProject Main"
)
```

### **3. Adapter Pattern** (Analytics)
```python
# Analytics service adapts to different data sources
service = AnalyticsService(data_source="pm_providers")
# or
service = AnalyticsService(data_source="mock")
```

### **4. Strategy Pattern** (Multi-Provider)
```python
# PMHandler uses different strategies based on mode
handler = PMHandler(single_provider=provider)  # Single
# or
handler = PMHandler(db_session=db)  # Multi
```

### **5. Observer Pattern** (Streaming)
```python
# Agents stream progress updates
async for chunk in agent.astream(...):
    yield chunk  # Frontend observes and displays
```

---

## 🎓 Learning Path

**If you're new, read in this order**:

1. **README.md** - Project overview
2. **Antigravity/learning_guide.md** - Structured learning path
3. **Antigravity/codebase_overview.md** - Architecture overview
4. **src/pm_providers/README.md** - PM provider system
5. **src/analytics/README.md** - Analytics module
6. **docs/API.md** - API reference
7. **Antigravity/developer_quick_reference.md** - Commands & snippets

**For specific areas**:
- **Backend**: Explore `src/graph/`, `src/conversation/`, `src/pm_providers/`
- **Frontend**: Explore `web/` or `frontend/`
- **PM Integration**: Read `docs/pm_providers_integration.md`
- **MCP Server**: Read `docs/PM_MCP_SERVER_*.md`
- **Analytics**: Read `src/analytics/README.md`

---

## 📊 System Status

### **Implemented ✅**
- ✅ DeerFlow research integration
- ✅ LangGraph multi-agent workflows
- ✅ Conversation flow management
- ✅ OpenProject provider (full CRUD)
- ✅ PM Handler (single/multi provider)
- ✅ MCP Server (stdio/HTTP/SSE)
- ✅ Analytics module (7 chart types)
- ✅ PM tools for agents
- ✅ Analytics tools for agents
- ✅ REST API for frontend
- ✅ WebSocket real-time updates

### **In Progress 🚧**
- 🚧 JIRA provider implementation
- 🚧 ClickUp provider implementation
- 🚧 Frontend analytics dashboard
- 🚧 Real-time sync with external systems

### **Planned 📋**
- 📋 Asana provider
- 📋 Trello provider
- 📋 Webhooks for external updates
- 📋 Advanced analytics (ML-based predictions)
- 📋 Multi-tenant support

---

## 🎉 Summary

This is a **production-ready, modular, extensible** PM Agent system with:
- **Intelligent agents** powered by LangGraph and DeerFlow
- **Unified PM abstraction** supporting multiple providers
- **Comprehensive analytics** with 7+ chart types
- **Flexible architecture** supporting chat, API, and MCP protocols
- **Well-documented** codebase with extensive guides

**You can**:
- Chat with the agent naturally ("create a mobile app project")
- Use REST APIs for frontend integration
- Connect via MCP for external tool access
- Switch PM providers with configuration
- Generate charts and reports programmatically
- Extend with new providers, tools, or charts easily

---

**Generated**: 2025-11-24  
**Status**: Comprehensive codebase learning complete ✅



















