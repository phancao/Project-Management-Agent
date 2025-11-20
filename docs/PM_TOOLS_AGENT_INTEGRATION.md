# PM Tools Agent Integration - Agent Decision-Making

## ✅ Implementation Complete

PM Tools have been successfully integrated into the DeerFlow agent system, enabling **Agent Decision-Making** for project management queries.

---

## 🔧 What Was Changed

### 1. Integrated PM Tools into Agents

**File**: `backend/graph/nodes.py`

- **Researcher Agent**: Now has access to PM tools for querying project data during research
- **Coder Agent**: Now has access to PM tools for querying project data during analysis

**Changes**:
```python
# researcher_node and coder_node now include:
try:
    pm_tools = get_pm_tools()
    if pm_tools:
        tools.extend(pm_tools)
        logger.info(f"Added {len(pm_tools)} PM tools")
except Exception as e:
    logger.warning(f"Could not add PM tools: {e}")
```

### 2. Updated Researcher Prompt

**File**: `backend/prompts/researcher.md`

Added documentation about PM tools so agents know when and how to use them:
- Explained PM tools capabilities
- Added guidance for when to use PM tools during research
- Emphasized using PM data to compare with research findings

---

## 🎯 How It Works Now

### Agent Decision-Making Flow

```
User Query: "Research sprint planning best practices and compare with our current sprint"
    ↓
Coordinator → Routes to Planner
    ↓
Planner → Creates research plan with steps
    ↓
Researcher Agent (has PM tools available)
    ↓
Agent decides: "I need to:
  1. Research sprint planning best practices (web_search)
  2. Query our current sprint data (list_sprints PM tool)
  3. Compare findings with actual data
  4. Provide recommendations"
    ↓
Agent executes:
  → web_search("sprint planning best practices")
  → list_sprints()  [PM Tool]
  → list_tasks()    [PM Tool - to get sprint tasks]
  → Synthesizes results
    ↓
Final Report: Combines research + actual PM data
```

### Example Use Cases

#### 1. Research + PM Data Comparison
```
User: "Research agile estimation techniques and analyze our task completion rates"

Agent Flow:
1. web_search("agile estimation techniques")
2. list_tasks() - Get all tasks
3. python_repl_tool - Calculate completion rates
4. Compare research findings with actual data
5. Provide recommendations
```

#### 2. Project Health Analysis
```
User: "Analyze our sprint velocity trends"

Agent Flow:
1. list_sprints() - Get all sprints
2. list_tasks() - Get task data for each sprint
3. python_repl_tool - Calculate velocity metrics
4. Analyze trends
5. Provide insights
```

#### 3. Context-Aware Research
```
User: "Research best practices for backlog management and compare with our current backlog"

Agent Flow:
1. web_search("backlog management best practices")
2. list_projects() - Get project info
3. list_tasks() - Get backlog tasks
4. Compare research with actual backlog structure
5. Provide tailored recommendations
```

---

## 📋 Available PM Tools

Agents now have access to these PM tools (from `backend/tools/pm_tools.py`):

1. **list_projects()** - List all projects
2. **get_project(project_id)** - Get project details
3. **list_tasks(project_id, assignee_id)** - List tasks with filters
4. **get_task(task_id)** - Get task details
5. **list_sprints(project_id)** - List sprints
6. **get_sprint(sprint_id)** - Get sprint details
7. **list_epics(project_id)** - List epics
8. **get_epic(epic_id)** - Get epic details
9. **list_users(project_id)** - List users/members
10. **get_current_user()** - Get current authenticated user

---

## 🔄 Comparison: Before vs After

### Before (Direct Handler Only)
```
User: "Analyze sprint velocity"
    ↓
Intent Classification → IntentType.ANALYZE_SPRINT
    ↓
Direct Handler → _handle_analyze_sprint()
    ↓
Fixed logic → Returns analysis
```

**Limitations**:
- Can't combine with research
- Fixed analysis logic
- No agent reasoning

### After (Agent Decision-Making)
```
User: "Research sprint planning best practices and analyze our velocity"
    ↓
Agent receives query + has PM tools
    ↓
Agent reasons about what's needed:
  - Research best practices (web_search)
  - Get our sprint data (list_sprints)
  - Calculate velocity (python_repl_tool)
  - Compare and synthesize
    ↓
Agent executes dynamically:
  → web_search()
  → list_sprints()
  → python_repl_tool()
  → Synthesizes
```

**Benefits**:
- ✅ Combines research with PM data
- ✅ Agent decides what tools to use
- ✅ Dynamic composition of operations
- ✅ Context-aware analysis

---

## 🚀 Usage Examples

### Example 1: Research + PM Comparison
```python
User: "Research team capacity planning strategies and compare with our current team assignments"

# Agent will:
1. Use web_search to research capacity planning
2. Use list_users() to get team members
3. Use list_tasks() to see current assignments
4. Use python_repl_tool to calculate workload
5. Compare research findings with actual data
6. Provide recommendations
```

### Example 2: Multi-Query Analysis
```python
User: "What tasks are blocking our sprint goals?"

# Agent will:
1. Use list_sprints() to get current sprint
2. Use list_tasks() to get sprint tasks
3. Analyze dependencies and blockers
4. Use web_search if needed for blocker resolution strategies
5. Provide actionable insights
```

### Example 3: Context-Aware Research
```python
User: "Research WBS best practices and create a WBS for our project"

# Agent will:
1. Use web_search to research WBS methodologies
2. Use get_project() to understand project context
3. Use list_tasks() to see existing structure
4. Combine research with project context
5. Generate appropriate WBS structure
```

---

## 🔍 Technical Details

### PM Handler Initialization

The PM handler is initialized in `ConversationFlowManager` and made available to tools:

```python
# backend/conversation/flow_manager.py
from backend.tools.pm_tools import set_pm_handler

# During initialization:
self.pm_handler = PMHandler.from_single_provider(pm_provider)
set_pm_handler(self.pm_handler)  # Makes handler available to tools
```

### Tool Availability

PM tools are conditionally added to agents:
- If PM provider is configured → Tools are added
- If PM provider is not available → Tools are skipped (graceful degradation)

This ensures the system works even without PM provider configured.

---

## 📊 Benefits of Agent Decision-Making

1. **Intelligent Tool Selection**: Agent decides which tools to use based on context
2. **Dynamic Composition**: Can combine multiple PM queries with research
3. **Context-Aware**: Agents can query PM data when needed during research
4. **Flexible Analysis**: No fixed logic - agents adapt to each query
5. **Research Integration**: Can combine external research with internal PM data

---

## 🎓 Next Steps

1. **Test the Integration**: Try queries that combine research with PM data
2. **Monitor Agent Behavior**: Watch how agents use PM tools
3. **Refine Prompts**: Update prompts if agents need better guidance
4. **Add More Tools**: Consider adding more PM operations as tools if needed

---

## 📝 Notes

- PM tools are **optional** - system works without them if PM provider isn't configured
- Agents decide when to use PM tools - no forced usage
- Tools return JSON strings - agents parse and use the data
- PM handler uses single-provider mode for agent queries (consistent data source)

---

**Status**: ✅ **Implementation Complete - Ready for Testing**
