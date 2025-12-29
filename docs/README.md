# PM Agent Documentation

## For AI Assistants (Antigravity)

### Quick Navigation by Log Prefix

| Log Prefix | Component | Read This |
|------------|-----------|-----------|
| `[COORDINATOR]` | Entry point & routing | `architecture/01_coordinator.md` |
| `[COORDINATOR] PM intent` | Intent detection | `architecture/02_intent_detection.md` |
| `[PM-AGENT]` | PM tool execution | `architecture/03_react_agent.md` |
| `[PM-TOOLS]` | Individual tool errors | `troubleshooting/tool_errors.md` |
| `[PLANNER]` | Multi-step planning | `architecture/04_planner.md` |
| `[PM-REPORTER]` | Report generation | `architecture/05_reporter.md` |
| `[STREAM-Q]` | SSE streaming | `architecture/06_streaming.md` |

### Search Strategy by Error Type

| Error/Issue Type | Read This |
|------------------|-----------|
| Query not reaching PM tools | `architecture/02_intent_detection.md` |
| Wrong routing / generic response | `troubleshooting/routing_issues.md` |
| Tool method not found / attribute error | `troubleshooting/tool_errors.md` |
| Results not streaming / batch delivery | `troubleshooting/streaming_issues.md` |
| Missing project context | `architecture/03_react_agent.md` |

---

## Architecture Docs (docs/architecture/)

Read in order (00 → 06) to understand the full flow.

### 00_overview.md
**Purpose:** System flow diagram and component map  
**When to read:** Starting point for any PM Agent investigation  
**Contains:** Mermaid flow diagram, component list, log prefix reference

### 01_coordinator.md  
**Purpose:** Entry point for ALL user messages  
**Function:** `coordinator_node()` in `nodes.py`  
**Responsibility:** Receives message → detects intent → routes to react_agent or END  
**Log prefix:** `[COORDINATOR]`  
**When to read:** Message not reaching PM tools, routing confusion

### 02_intent_detection.md
**Purpose:** Hybrid PM intent detection (keywords + LLM fallback)  
**Function:** `classify_pm_intent_with_llm()` in `nodes.py`  
**Responsibility:** Determines if query is PM-related using:
1. Fast keyword matching (English)
2. LLM fallback (multilingual - Vietnamese, etc.)  
**Log prefix:** `[COORDINATOR] PM intent`, `[COORDINATOR] 🤖 LLM`  
**When to read:** Non-English queries not being detected, false positives/negatives

### 03_react_agent.md
**Purpose:** PM tool execution using ReAct pattern  
**Function:** `react_agent_node()` in `nodes.py`  
**Responsibility:** Calls PM tools (list_sprints, list_users, etc.), returns results  
**Log prefix:** `[PM-AGENT]`  
**When to read:** Tools not being called, wrong project context, tool selection issues

### 04_planner.md
**Purpose:** Complex multi-step query handling  
**Function:** `planner_node()` in `nodes.py`  
**Responsibility:** Creates execution plan for complex analysis requiring multiple tools  
**Log prefix:** `[PLANNER]`  
**When to read:** Simple queries going to planner, infinite loops, escalation issues

### 05_reporter.md
**Purpose:** Final report generation  
**Function:** `reporter_node()` in `nodes.py`  
**Responsibility:** Formats tool results into markdown report  
**Log prefix:** `[PM-REPORTER]`  
**When to read:** Missing data in report, duplicate reports, formatting issues

### 06_streaming.md
**Purpose:** Real-time SSE event delivery  
**File:** `app.py`  
**Responsibility:** Pushes tool results to frontend via Server-Sent Events  
**Log prefix:** `[STREAM-Q]`  
**When to read:** Results appearing only at end, wrong user receiving events

---

## Troubleshooting Docs (docs/troubleshooting/)

### debug_markers.md
**Purpose:** Complete log prefix → component → doc mapping  
**When to read:** Don't know which component caused the error

### routing_issues.md
**Purpose:** PM intent detection and routing failures  
**Symptoms:** Generic response, no PM data, query not reaching react_agent

### tool_errors.md
**Purpose:** PM tool execution errors  
**Symptoms:** Method not found, attribute errors, dict vs object issues

### streaming_issues.md
**Purpose:** SSE streaming problems  
**Symptoms:** Batch delivery, events to wrong user, missing events
