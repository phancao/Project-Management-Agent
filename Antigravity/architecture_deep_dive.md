# Project Management Agent - Architecture Deep Dive

## 🎯 System Architecture

### Complete System Overview

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[Next.js UI]
        Chat[Chat Interface]
        Dashboard[Project Dashboard]
        Tasks[Task Management]
    end

    subgraph "API Gateway Layer"
        FastAPI[FastAPI Server]
        WS[WebSocket Handler]
        REST[REST Endpoints]
        Auth[Authentication]
    end

    subgraph "Agent Layer"
        FlowMgr[Conversation Flow Manager]
        DeerFlow[DeerFlow Research Agent]
        PMAgent[PM Agent]
        CustomAgents[Custom Agents]
    end

    subgraph "MCP Layer"
        MCPServer[MCP Server]
        MCPTools[MCP Tools]
        MCPAuth[MCP Auth]
    end

    subgraph "Provider Layer"
        PMHandler[PM Handler]
        InternalProvider[Internal Provider]
        OpenProjectProvider[OpenProject Provider]
        JiraProvider[JIRA Provider - Stub]
        ClickUpProvider[ClickUp Provider - Stub]
    end

    subgraph "Data Layer"
        MainDB[(PostgreSQL - Main)]
        MCPDB[(PostgreSQL - MCP)]
        VectorDB[(Qdrant - Vectors)]
        Cache[(Redis - Cache)]
    end

    subgraph "External Systems"
        OpenAI[OpenAI API]
        OpenProject[OpenProject Instance]
        Search[DuckDuckGo Search]
    end

    UI --> FastAPI
    Chat --> FastAPI
    Dashboard --> FastAPI
    Tasks --> FastAPI

    FastAPI --> WS
    FastAPI --> REST
    FastAPI --> Auth

    REST --> FlowMgr
    REST --> PMHandler
    WS --> FlowMgr

    FlowMgr --> DeerFlow
    FlowMgr --> PMAgent
    FlowMgr --> CustomAgents

    DeerFlow --> MCPServer
    PMAgent --> MCPServer

    MCPServer --> MCPTools
    MCPServer --> MCPAuth

    MCPTools --> PMHandler

    PMHandler --> InternalProvider
    PMHandler --> OpenProjectProvider
    PMHandler --> JiraProvider
    PMHandler --> ClickUpProvider

    InternalProvider --> MainDB
    OpenProjectProvider --> OpenProject
    
    DeerFlow --> OpenAI
    DeerFlow --> Search
    PMAgent --> OpenAI

    MCPAuth --> MCPDB
    FlowMgr --> Cache
    DeerFlow --> VectorDB
```

## 🔄 Data Flow Patterns

### Pattern 1: Research Query Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant FastAPI
    participant Workflow
    participant DeerFlow
    participant Search
    participant LLM
    participant VectorDB

    User->>Frontend: "Research quantum computing"
    Frontend->>FastAPI: POST /api/chat
    FastAPI->>Workflow: run_agent_workflow_async()
    
    Workflow->>DeerFlow: Initialize research
    
    alt Background Investigation Enabled
        DeerFlow->>Search: Web search
        Search-->>DeerFlow: Search results
    end
    
    alt Clarification Needed
        DeerFlow->>LLM: Check if clarification needed
        LLM-->>DeerFlow: Clarification questions
        DeerFlow-->>User: Ask clarifying questions
        User->>DeerFlow: Provide answers
    end
    
    DeerFlow->>LLM: Generate research plan
    LLM-->>DeerFlow: Research plan
    
    loop For each research step
        DeerFlow->>Search: Execute search
        Search-->>DeerFlow: Results
        DeerFlow->>LLM: Analyze results
        LLM-->>DeerFlow: Analysis
    end
    
    DeerFlow->>VectorDB: Store research results
    DeerFlow->>LLM: Generate final report
    LLM-->>DeerFlow: Report
    
    DeerFlow-->>Workflow: Research complete
    Workflow-->>FastAPI: Stream results
    FastAPI-->>Frontend: SSE stream
    Frontend-->>User: Display results
```

### Pattern 2: Direct PM Operation (UI)

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant FastAPI
    participant PMHandler
    participant Provider
    participant ExternalPM

    User->>Frontend: Create new task
    Frontend->>FastAPI: POST /api/pm/projects/{id}/tasks
    FastAPI->>PMHandler: create_task(task_data)
    PMHandler->>Provider: create_task(PMTask)
    
    alt Internal Provider
        Provider->>Database: INSERT task
        Database-->>Provider: Task created
    else OpenProject Provider
        Provider->>ExternalPM: POST /api/v3/work_packages
        ExternalPM-->>Provider: Work package created
        Provider->>Provider: Transform to PMTask
    end
    
    Provider-->>PMHandler: PMTask
    PMHandler-->>FastAPI: Task response
    FastAPI-->>Frontend: JSON response
    Frontend-->>User: Task created confirmation
```

### Pattern 3: Conversational PM Operation (MCP)

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant FastAPI
    participant DeerFlow
    participant MCPServer
    participant PMHandler
    participant Provider
    participant ExternalPM

    User->>Frontend: "Show me sprint 4 progress"
    Frontend->>FastAPI: POST /api/chat
    FastAPI->>DeerFlow: Process query
    
    DeerFlow->>DeerFlow: Classify intent
    DeerFlow->>MCPServer: Call list_sprints tool
    
    MCPServer->>MCPServer: Authenticate request
    MCPServer->>PMHandler: list_sprints(project_id)
    PMHandler->>Provider: list_sprints(project_id)
    
    Provider->>ExternalPM: GET /api/v3/versions
    ExternalPM-->>Provider: Sprint data
    Provider->>Provider: Transform to PMSprint[]
    
    Provider-->>PMHandler: PMSprint[]
    PMHandler-->>MCPServer: Sprint list
    MCPServer-->>DeerFlow: Tool result
    
    DeerFlow->>DeerFlow: Analyze sprint data
    DeerFlow->>MCPServer: Call get_sprint_tasks tool
    MCPServer->>PMHandler: get_sprint_tasks(sprint_id)
    PMHandler->>Provider: list_tasks(sprint_id=sprint_id)
    Provider->>ExternalPM: GET /api/v3/work_packages
    ExternalPM-->>Provider: Tasks
    Provider-->>PMHandler: PMTask[]
    PMHandler-->>MCPServer: Task list
    MCPServer-->>DeerFlow: Tool result
    
    DeerFlow->>DeerFlow: Calculate progress metrics
    DeerFlow-->>FastAPI: Formatted response
    FastAPI-->>Frontend: Stream response
    Frontend-->>User: "Sprint 4 is 65% complete..."
```

## 🗄️ Database Architecture

### Main Database Schema

```mermaid
erDiagram
    USERS ||--o{ PROJECTS : owns
    USERS ||--o{ TEAM_MEMBERS : "is member"
    PROJECTS ||--o{ TASKS : contains
    PROJECTS ||--o{ SPRINTS : has
    PROJECTS ||--o{ TEAM_MEMBERS : has
    TASKS ||--o{ TASKS : "parent of"
    TASKS }o--|| USERS : "assigned to"
    SPRINTS ||--o{ TASKS : contains
    PROJECTS ||--o{ RESEARCH_SESSIONS : "researched for"
    USERS ||--o{ CONVERSATION_SESSIONS : has
    PROJECTS ||--o{ PROJECT_METRICS : tracks

    USERS {
        uuid id PK
        string email
        string username
        string password_hash
        timestamp created_at
    }

    PROJECTS {
        uuid id PK
        string name
        text description
        string status
        uuid owner_id FK
        date start_date
        date end_date
    }

    TASKS {
        uuid id PK
        string title
        text description
        string status
        string priority
        uuid project_id FK
        uuid parent_task_id FK
        uuid assignee_id FK
        float estimated_hours
        float actual_hours
        date due_date
    }

    SPRINTS {
        uuid id PK
        string name
        uuid project_id FK
        date start_date
        date end_date
        string status
        float capacity_hours
        text goal
    }

    TEAM_MEMBERS {
        uuid id PK
        uuid project_id FK
        uuid user_id FK
        string role
        timestamp joined_at
    }
```

### MCP Database Schema

```mermaid
erDiagram
    USERS ||--o{ API_KEYS : has
    USERS ||--o{ PM_PROVIDER_CONNECTIONS : owns
    PM_PROVIDER_CONNECTIONS ||--o{ PROJECT_SYNC_MAPPINGS : has

    USERS {
        uuid id PK
        string username
        string email
        string password_hash
        boolean is_active
    }

    API_KEYS {
        uuid id PK
        uuid user_id FK
        string key_hash
        string name
        timestamp expires_at
        timestamp last_used_at
    }

    PM_PROVIDER_CONNECTIONS {
        uuid id PK
        string name
        string provider_type
        string base_url
        string api_key
        string api_token
        uuid user_id FK
        jsonb additional_config
    }

    PROJECT_SYNC_MAPPINGS {
        uuid id PK
        uuid internal_project_id
        uuid provider_connection_id FK
        string external_project_id
        boolean sync_enabled
        timestamp last_sync_at
        jsonb sync_config
    }
```

## 🔧 Component Details

### 1. DeerFlow Workflow

```mermaid
graph LR
    Start[User Input] --> Clarify{Needs Clarification?}
    Clarify -->|Yes| AskQuestions[Ask Questions]
    AskQuestions --> GetAnswers[Get Answers]
    GetAnswers --> Investigate
    Clarify -->|No| Investigate[Background Investigation]
    
    Investigate --> Plan[Generate Research Plan]
    Plan --> Execute[Execute Plan Steps]
    Execute --> Reflect[Reflect on Results]
    Reflect --> Complete{Plan Complete?}
    Complete -->|No| Plan
    Complete -->|Yes| Report[Generate Report]
    Report --> End[Return Results]
```

### 2. PM Provider Architecture

```mermaid
graph TB
    subgraph "Application Layer"
        FlowManager[Flow Manager]
        Handlers[Handlers]
        API[API Endpoints]
    end

    subgraph "Abstraction Layer"
        Factory[Provider Factory]
        Base[BasePMProvider Interface]
    end

    subgraph "Implementation Layer"
        Internal[Internal Provider]
        OpenProject[OpenProject Provider]
        JIRA[JIRA Provider]
        ClickUp[ClickUp Provider]
    end

    subgraph "Data Layer"
        DB[(PostgreSQL)]
        OPInstance[OpenProject Instance]
        JIRACloud[JIRA Cloud]
        ClickUpAPI[ClickUp API]
    end

    FlowManager --> Factory
    Handlers --> Factory
    API --> Factory

    Factory --> Base
    Base --> Internal
    Base --> OpenProject
    Base --> JIRA
    Base --> ClickUp

    Internal --> DB
    OpenProject --> OPInstance
    JIRA --> JIRACloud
    ClickUp --> ClickUpAPI
```

### 3. MCP Server Architecture

```mermaid
graph TB
    subgraph "Transport Layer"
        SSE[SSE Transport]
        HTTP[HTTP Transport]
        STDIO[STDIO Transport]
    end

    subgraph "Server Core"
        MCPServer[MCP Server]
        ToolRegistry[Tool Registry]
        Auth[Authentication]
        RBAC[RBAC]
    end

    subgraph "Tools"
        ProjectTools[Project Tools]
        TaskTools[Task Tools]
        SprintTools[Sprint Tools]
        UserTools[User Tools]
        AnalyticsTools[Analytics Tools]
    end

    subgraph "Services"
        PMHandler[PM Handler]
        ProviderFactory[Provider Factory]
    end

    SSE --> MCPServer
    HTTP --> MCPServer
    STDIO --> MCPServer

    MCPServer --> ToolRegistry
    MCPServer --> Auth
    MCPServer --> RBAC

    ToolRegistry --> ProjectTools
    ToolRegistry --> TaskTools
    ToolRegistry --> SprintTools
    ToolRegistry --> UserTools
    ToolRegistry --> AnalyticsTools

    ProjectTools --> PMHandler
    TaskTools --> PMHandler
    SprintTools --> PMHandler
    UserTools --> PMHandler
    AnalyticsTools --> PMHandler

    PMHandler --> ProviderFactory
```

## 🚀 Deployment Architecture

### Docker Compose Services

```mermaid
graph TB
    subgraph "Frontend Services"
        Frontend[frontend:3000]
    end

    subgraph "Backend Services"
        API[api:8000]
        MCPServer[pm_mcp_server:8080]
    end

    subgraph "Database Services"
        MainDB[postgres:5432]
        MCPDB[mcp_postgres:5435]
        VectorDB[qdrant:6333]
        Cache[redis:6379]
    end

    subgraph "External PM Services"
        OPDB[openproject_db:5433]
        OP[openproject:8080]
        OPDB13[openproject_db_v13:5434]
        OP13[openproject_v13:8081]
    end

    Frontend --> API
    API --> MainDB
    API --> Cache
    API --> MCPServer
    MCPServer --> MCPDB
    MCPServer --> OP
    MCPServer --> OP13
    API --> VectorDB
    OP --> OPDB
    OP13 --> OPDB13
```

## 🔐 Authentication & Authorization Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Auth
    participant MCPServer
    participant MCPAuth
    participant Database

    Client->>FastAPI: Request with credentials
    FastAPI->>Auth: Validate credentials
    Auth->>Database: Check user
    Database-->>Auth: User data
    Auth-->>FastAPI: JWT token
    FastAPI-->>Client: Token

    Client->>FastAPI: Request with JWT
    FastAPI->>Auth: Validate JWT
    Auth-->>FastAPI: User context

    FastAPI->>MCPServer: Request with API key
    MCPServer->>MCPAuth: Validate API key
    MCPAuth->>Database: Check API key
    Database-->>MCPAuth: Key valid + user
    MCPAuth->>MCPAuth: Check RBAC permissions
    MCPAuth-->>MCPServer: Authorized
    MCPServer-->>FastAPI: Response
    FastAPI-->>Client: Response
```

## 📊 Agent Workflow States

```mermaid
stateDiagram-v2
    [*] --> Initialize
    Initialize --> Clarification: enable_clarification=true
    Initialize --> Investigation: enable_clarification=false
    
    Clarification --> CheckClarityNeeded
    CheckClarityNeeded --> AskQuestion: Needs clarification
    CheckClarityNeeded --> Investigation: Clear enough
    AskQuestion --> ReceiveAnswer
    ReceiveAnswer --> CheckClarityNeeded
    
    Investigation --> Planning: Background research done
    Planning --> Execution
    Execution --> Reflection
    Reflection --> Planning: Need more steps
    Reflection --> Finalization: Plan complete
    
    Finalization --> [*]
```

## 🎯 Key Design Patterns

### 1. Factory Pattern (PM Providers)
```python
# Factory creates appropriate provider based on config
provider = build_pm_provider(db_session=db)
# Returns: InternalProvider | OpenProjectProvider | JiraProvider | ClickUpProvider
```

### 2. Strategy Pattern (Transports)
```python
# MCP Server can use different transport strategies
transport = SSETransport()  # or HTTPTransport() or StdioTransport()
server.run(transport)
```

### 3. Adapter Pattern (PM Provider Interface)
```python
# Each provider adapts its API to the common interface
class OpenProjectProvider(BasePMProvider):
    async def create_task(self, task: PMTask) -> PMTask:
        # Adapt PMTask to OpenProject work package format
        op_data = self._to_openproject_format(task)
        result = await self.client.post("/work_packages", op_data)
        # Adapt OpenProject response back to PMTask
        return self._from_openproject_format(result)
```

### 4. Observer Pattern (WebSocket Updates)
```python
# Frontend subscribes to real-time updates
websocket.on('task_updated', handleTaskUpdate)
# Backend publishes updates
await websocket.emit('task_updated', task_data)
```

## 🔍 Code Organization Principles

### Separation of Concerns
- **Presentation**: Frontend (Next.js)
- **API**: FastAPI server
- **Business Logic**: Handlers, Services
- **Data Access**: Providers, CRUD
- **AI/ML**: Agents, Workflows
- **Infrastructure**: Database, Cache, MCP

### Dependency Flow
```
Frontend → API → Handlers → Services → Providers → External Systems
                    ↓
                 Agents → MCP Server → Providers
```

### Configuration Hierarchy
```
Environment Variables (.env)
    ↓
Runtime Config (conf.yaml)
    ↓
Code Defaults
```

## 🎓 Understanding the Codebase

### Critical Files to Master

1. **Entry Points**
   - `main.py` - CLI research mode
   - `server.py` - API server startup
   - `src/workflow.py` - Agent workflow orchestration

2. **Core Logic**
   - `src/server/app.py` - All API endpoints (151KB!)
   - `pm_providers/base.py` - Provider interface
   - `mcp_server/server.py` - MCP protocol implementation

3. **Data Models**
   - `database/models.py` - Pydantic models
   - `database/orm_models.py` - SQLAlchemy models
   - `pm_providers/models.py` - PM data models

4. **Configuration**
   - `pyproject.toml` - Dependencies
   - `docker-compose.yml` - Services
   - `database/schema.sql` - Database structure

### Code Reading Order

**For Backend Developers:**
1. Read `README.md` for overview
2. Study `docker-compose.yml` to understand services
3. Review `database/schema.sql` for data model
4. Explore `pm_providers/base.py` for abstraction
5. Read `src/server/app.py` for API endpoints
6. Study `src/workflow.py` for agent logic

**For AI/ML Developers:**
1. Start with `src/workflow.py`
2. Explore `src/graph/` for LangGraph
3. Review `src/agents/` for agent implementations
4. Study `src/prompts/` for LLM prompts
5. Check `src/tools/` for agent tools

**For Full Stack Developers:**
1. Review `docker-compose.yml` for full picture
2. Study `src/server/app.py` for backend API
3. Explore `web/src/app/` for frontend pages
4. Check `web/src/components/` for UI components
5. Review API integration in `web/src/lib/`

---

**Last Updated**: 2025-11-22
