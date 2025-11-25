# Key Workflows and Data Flows

> **Last Updated**: November 25, 2025

## 🔄 Core Workflows

### 1. User Chat → Research → PM Action

This is the primary workflow for conversational PM operations.

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant API as FastAPI
    participant CFM as ConversationFlowManager
    participant LG as LangGraph
    participant PMH as PMHandler
    participant PM as PM Provider

    U->>FE: "Create a mobile app project"
    FE->>API: POST /api/chat/stream
    API->>CFM: process_message()
    
    CFM->>CFM: classify_intent() → CREATE_PROJECT
    CFM->>CFM: extract_entities()
    CFM->>CFM: check_required_fields()
    
    alt Missing fields
        CFM-->>API: Clarification question
        API-->>FE: SSE stream
        FE-->>U: "What's the timeline?"
        U->>FE: "3 months"
        FE->>API: POST /api/chat/stream
    end
    
    CFM->>LG: Route to workflow
    LG->>LG: Planner creates plan
    LG->>LG: Researcher gathers info
    LG->>LG: Coder processes data
    
    LG->>PMH: create_project()
    PMH->>PM: create_project()
    PM-->>PMH: Project created
    PMH-->>LG: Success
    
    LG->>LG: Reporter generates response
    LG-->>API: Final response
    API-->>FE: SSE stream
    FE-->>U: "Project created successfully!"
```

### 2. Frontend Dashboard → REST API → PM Providers

Direct data fetching for UI components.

```mermaid
sequenceDiagram
    participant C as Component
    participant RQ as React Query
    participant API as REST API
    participant PMH as PMHandler
    participant P1 as OpenProject
    participant P2 as JIRA

    C->>RQ: useProjects()
    RQ->>API: GET /api/pm/projects
    API->>PMH: list_projects()
    
    par Query all providers
        PMH->>P1: list_projects()
        PMH->>P2: list_projects()
    end
    
    P1-->>PMH: [projects from OP]
    P2-->>PMH: [projects from JIRA]
    
    PMH->>PMH: Aggregate results
    PMH-->>API: Combined project list
    API-->>RQ: JSON response
    RQ->>RQ: Cache data
    RQ-->>C: projects array
    C->>C: Render UI
```

### 3. Analytics Chart Generation

Server-side chart data generation.

```mermaid
sequenceDiagram
    participant FE as Frontend Chart
    participant API as Analytics API
    participant AS as AnalyticsService
    participant Adapter as PM Adapter
    participant Calc as Calculator
    participant PMH as PMHandler

    FE->>API: GET /api/analytics/projects/P1/burndown?sprint_id=S1
    API->>AS: get_burndown_chart(P1, S1)
    AS->>Adapter: get_sprint_data(P1, S1)
    Adapter->>PMH: get_sprint(S1)
    Adapter->>PMH: list_tasks(project_id=P1, sprint_id=S1)
    PMH-->>Adapter: Sprint + Tasks data
    Adapter-->>AS: Formatted data
    AS->>Calc: BurndownCalculator.calculate(data)
    Calc->>Calc: Calculate ideal/actual burndown
    Calc-->>AS: ChartResponse
    AS-->>API: ChartResponse JSON
    API-->>FE: Chart data
    FE->>FE: Render chart with Recharts
```

### 4. MCP Tool Call Flow

External agents calling PM tools via MCP.

```mermaid
sequenceDiagram
    participant Agent as External Agent
    participant MCP as MCP Server
    participant Auth as Auth Layer
    participant PMH as PMHandler
    participant PM as PM Provider

    Agent->>MCP: Call tool: list_projects
    MCP->>Auth: Verify API key
    Auth-->>MCP: Authenticated
    
    MCP->>MCP: Validate tool params
    MCP->>PMH: list_projects()
    PMH->>PM: list_projects()
    PM-->>PMH: Projects data
    PMH-->>MCP: Formatted response
    MCP-->>Agent: Tool result (JSON)
```

## 📊 Data Flow Patterns

### Pattern 1: Multi-Provider Aggregation

**Use Case**: Frontend needs to show all projects from all providers

```python
# PMHandler in multi-provider mode
class PMHandler:
    def __init__(self, db_session, user_id):
        self.providers = self._load_user_providers(db_session, user_id)
    
    async def list_projects(self):
        all_projects = []
        for provider in self.providers:
            projects = await provider.list_projects()
            all_projects.extend(projects)
        return all_projects
```

**Flow**:
```
Frontend → API → PMHandler (multi-provider)
                    ↓
    ┌───────────────┼───────────────┐
    ↓               ↓               ↓
OpenProject 1   OpenProject 2    JIRA
    ↓               ↓               ↓
    └───────────────┼───────────────┘
                    ↓
            Aggregate & Return
```

### Pattern 2: Single-Provider Context

**Use Case**: Agent working within a specific provider context

```python
# PMHandler in single-provider mode
provider = build_pm_provider(db_session, provider_name="OpenProject Main")
handler = PMHandler.from_single_provider(provider)

# All operations use this one provider
projects = await handler.list_projects()
```

**Flow**:
```
Agent → Tool → PMHandler (single-provider)
                    ↓
              OpenProject
                    ↓
                Return
```

### Pattern 3: Streaming Response

**Use Case**: Real-time chat with progressive updates

```python
async def stream_chat():
    async for event in graph.astream_events(...):
        if event["event"] == "on_chat_model_stream":
            yield f"data: {json.dumps(event)}\n\n"
```

**Flow**:
```
User Message
    ↓
LangGraph Workflow
    ↓
┌───┴────┐
│ Agent  │ → Streams chunks
└───┬────┘
    ↓
SSE Stream → Frontend
    ↓
Progressive UI Update
```

### Pattern 4: Background Task Processing

**Use Case**: Long-running operations (WBS generation, sprint planning)

```python
from celery import Celery

@celery.task
async def generate_wbs(project_id: str):
    # Long-running task
    wbs = await wbs_generator.generate(project_id)
    return wbs

# Trigger
task = generate_wbs.delay(project_id)
task_id = task.id

# Poll for result
result = AsyncResult(task_id)
if result.ready():
    wbs = result.get()
```

**Flow**:
```
User Request
    ↓
API → Celery Task (async)
    ↓
Return task_id immediately
    ↓
Frontend polls for status
    ↓
Task completes → Return result
```

## 🔄 State Management Flows

### LangGraph State Flow

```python
class State(TypedDict):
    messages: List[BaseMessage]
    current_plan: Optional[Plan]
    observations: List[str]
    goto: str
```

**State Transitions**:
```
Initial State
    ↓
Coordinator → Add messages, set goto
    ↓
Planner → Create plan, add to current_plan
    ↓
Research Team → Execute steps, add observations
    ↓
Reporter → Generate final response
    ↓
Final State
```

### Frontend State Flow (Zustand)

```typescript
interface AppState {
  user: User | null;
  currentProject: Project | null;
  chatMessages: ChatMessage[];
}
```

**State Updates**:
```
User Login
    ↓
setUser(user) → Update store
    ↓
Select Project
    ↓
setCurrentProject(project) → Update store
    ↓
Send Chat Message
    ↓
addChatMessage(message) → Update store
    ↓
Components re-render
```

## 🎯 Intent Classification Flow

```mermaid
graph TD
    A[User Message] --> B{Intent Classifier}
    B -->|CREATE_PROJECT| C[Check Required Fields]
    B -->|LIST_PROJECTS| D[Direct Execution]
    B -->|RESEARCH_TOPIC| E[Route to DeerFlow]
    B -->|SPRINT_PLANNING| F[Check Required Fields]
    
    C -->|Complete| G[Execute Action]
    C -->|Incomplete| H[Ask Clarification]
    
    F -->|Complete| I[Route to Planner]
    F -->|Incomplete| H
    
    H --> J[Wait for User Response]
    J --> B
    
    G --> K[Return Result]
    I --> K
    D --> K
    E --> K
```

## 🔐 Authentication Flow

### JWT Authentication

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant API as API
    participant DB as Database

    U->>FE: Login (email, password)
    FE->>API: POST /api/auth/login
    API->>DB: Verify credentials
    DB-->>API: User found
    API->>API: Generate JWT token
    API-->>FE: {token, user}
    FE->>FE: Store token in localStorage
    
    Note over FE,API: Subsequent requests
    
    FE->>API: GET /api/pm/projects<br/>Authorization: Bearer {token}
    API->>API: Verify JWT
    API->>DB: Fetch data
    DB-->>API: Data
    API-->>FE: Response
```

### MCP API Key Authentication

```mermaid
sequenceDiagram
    participant Agent as External Agent
    participant MCP as MCP Server
    participant DB as MCP Database

    Agent->>MCP: Tool call<br/>X-API-Key: {key}
    MCP->>DB: Verify API key
    DB-->>MCP: Key valid, user_id
    MCP->>MCP: Load user providers
    MCP->>MCP: Execute tool
    MCP-->>Agent: Result
```

## 📦 Provider Configuration Flow

```mermaid
graph TD
    A[User Creates Provider] --> B[POST /api/pm/providers]
    B --> C[Store in Database]
    C --> D[Encrypt Credentials]
    D --> E[Save to pm_provider_connections]
    
    F[Agent Needs Provider] --> G[Load from Database]
    G --> H[Decrypt Credentials]
    H --> I[Build Provider Instance]
    I --> J[Use for Operations]
    
    K[MCP Server Starts] --> L[Load All Providers]
    L --> M[Configure MCP Tools]
    M --> N[Ready for Tool Calls]
```

## 🔄 Real-time Update Flow (WebSocket)

```mermaid
sequenceDiagram
    participant U1 as User 1
    participant FE1 as Frontend 1
    participant API as API Server
    participant WS as WebSocket Hub
    participant FE2 as Frontend 2
    participant U2 as User 2

    U1->>FE1: Update task status
    FE1->>API: PUT /api/pm/tasks/123
    API->>API: Update database
    API->>WS: Broadcast task_updated
    
    par Notify all connected clients
        WS-->>FE1: task_updated event
        WS-->>FE2: task_updated event
    end
    
    FE1->>FE1: Update UI
    FE2->>FE2: Update UI
    FE2-->>U2: Task updated notification
```

---

**Next**: [Troubleshooting Guide →](./08_troubleshooting.md)
