# Permanent Debug Logs (Default List)

This document lists the baseline debug instrumentation that must be preserved in the codebase. These logs are critical for diagnosing message flow, state updates, rendering issues, backend planning logic, and MCP tool execution.

## 1. Frontend Debug Logs (`[PM-DEBUG]`)
**Global Prefix**: `[PM-DEBUG]`

### Network Layer (SSE)
**File**: [web/src/core/sse/fetch-stream.ts](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/web/src/core/sse/fetch-stream.ts)
**Purpose**: Verifies that the frontend is actually receiving events from the backend API.
- **Log**: `[PM-DEBUG][SSE] <timestamp> YIELD: type=<type>, dataLen=<length>`

### State Layer (Store)
**File**: [web/src/core/store/store.ts](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/web/src/core/store/store.ts)
**Purpose**: Verifies that the global store is receiving and dispatching events correctly.
- **Log**: `[PM-DEBUG][STORE] <timestamp> EVENT: type=<type>, id=<id>, agent=<agent>`

### Data Logic Layer (Merging)
**File**: [web/src/core/messages/merge-message.ts](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/web/src/core/messages/merge-message.ts)
**Purpose**: Tracks how incremental updates are applied to message objects.
- **Text Merge**: `[PM-DEBUG][MERGE] <timestamp> TEXT: +<count> chars, total=<total>`
- **Tools Merge**: `[PM-DEBUG][MERGE] <timestamp> TOOLS: existing=<count>, new=<count>`
- **Thoughts Merge**: `[PM-DEBUG][MERGE] <timestamp> THOUGHTS: count=<count>`
- **Tool Result**: `[PM-DEBUG][MERGE] <timestamp> RESULT: tool=<name>, tool_call_id=<id>`

### UI Layer (Rendering)
**File**: [web/src/app/pm/chat/components/message-list-view.tsx](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/web/src/app/pm/chat/components/message-list-view.tsx)
**Purpose**: Debugs why a message is visible or hidden.
- **Render Decision**: `[PM-DEBUG][RENDER] <timestamp> SHOW/SKIP ...`

---

## 2. Backend Debug Logs
**Primary File**: [backend/graph/nodes.py](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/backend/graph/nodes.py)

### Planner Node (`[PLANNER]`)
**Purpose**: Tracks the core planning logic, including plan generation, validation, and tool selection.
- **Missing Tools**: `[PLANNER] Missing tools detected: ...`
- **LLM Invocation**: `[PLANNER] LLM invocation failed: ...`
- **Plan Type**: Info logs identifying if a plan is a "PM Query" or "Research Plan".

### Coordinator (`[COORDINATOR]`)
**Purpose**: Tracks intent classification and escalation decisions.
- **Classification Error**: `[COORDINATOR] LLM classification failed: ...`

### PM Agent (`[PM-AGENT]`)
**File**: [backend/agents/pm_agent.py](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/backend/agents/pm_agent.py)
**Purpose**: Tracks specific project management tool execution contexts.
- **Context Optimization**: `[{agent_name}] Created context optimization tool call: ...`

---

## 3. MCP Server Logs

### PM MCP Server
**File**: [mcp_server/server.py](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/mcp_server/server.py)
**Purpose**: Tracks the registration and routing of MCP tools.

- **Tool Routing (Critical)**:
  - `[ROUTER] Routing tool call: <tool_name>`
  - `[ROUTER] Found tool function for '<tool_name>': ...`
  - `[ROUTER] Tool '<tool_name>' completed successfully`
  - `[ROUTER] Error calling tool '<tool_name>': ...`

- **Registration**:
  - `[{module_name}] Registering with context`
  - `Registered <count> {module_name} tools`

### Meeting MCP Server
**File**: [mcp_meeting_server/server.py](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/mcp_meeting_server/server.py)
**Purpose**: Tracks meeting tool server status.

- **Startup**:
  - `Starting Meeting MCP Server on <host>:<port>`
  - `Transport: <transport_type>`
- **Database**:
  - `Database initialized successfully`

---

## 4. System Logger Hierarchy
This section documents the Python logger names used across the backend. Use these names if you need to configure specific log levels manually (e.g. in `logging.getLogger("src.workflow").setLevel(logging.DEBUG)`).

### Core Modules
| Logical Component | Logger Names |
|-------------------|--------------|
| **Workflow & Graph** | `src.workflow`, `src.graph`, `src.agents` |
| **PM Provider** | `pm_providers`, `src.server.pm_handler`, `mcp_server` |
| **Analytics** | `src.analytics`, `src.analytics.service`, `src.analytics.adapters`, `src.analytics.calculators` |
| **Conversation** | `src.conversation` |
| **Tools** | `src.tools`, `src.tools.search`, `src.tools.pm_tools`, `src.tools.pm_mcp_tools`, `src.tools.analytics_tools` |
| **RAG** | `src.rag` |
| **Crawler** | `src.crawler` |

### MCP Integration
| Logical Component | Logger Names |
|-------------------|--------------|
| **MCP Utils** | `src.server.mcp_utils` |
| **PM MCP Server** | `mcp_server` |
