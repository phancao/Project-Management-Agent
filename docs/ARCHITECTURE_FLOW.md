# System Flow Architecture

## Overview

The Project Management Agent follows a **Plan-Based Multi-Step Execution** architecture with intelligent context management and streaming support.

---

## End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. USER SENDS MESSAGE                                               │
│    POST /api/pm/chat/stream                                         │
│    { "messages": [{"content": "list all my tasks"}], "thread_id" } │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. FASTAPI SERVER (src/server/app.py:906)                           │
│    - Parses JSON request                                            │
│    - Extracts message & thread_id                                   │
│    - Gets database session                                          │
│    - Retrieves global ConversationFlowManager singleton             │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. GENERATE PM PLAN (flow_manager.py:870)                           │
│                                                                      │
│    a) Extract Context:                                               │
│       - _extract_key_facts() → Active project/sprint/task           │
│       - _select_relevant_messages() → Top 8 relevant messages       │
│    b) Call LLM with prompt:                                         │
│       - System prompt (pm_planner.md)                                │
│       - Key facts summary                                            │
│       - Conversation history (optimized)                             │
│       - Current user message                                         │
│    c) LLM returns JSON plan:                                        │
│       {                                                              │
│         "overall_thought": "...",                                    │
│         "steps": [                                                   │
│           {"step_type": "list_my_tasks", "title": "...", ...}       │
│         ]                                                            │
│       }                                                              │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. DEERFLOW PRE-RESEARCH (app.py:949) - OPTIONAL                   │
│    - Only for "create_wbs" steps                                    │
│    - Runs full DeerFlow research with streaming                     │
│    - Stores results in context.gathered_data                        │
│    - Note: Other research (ETA, sprint planning) happens later       │
│    - Note: LLM decides if research step is needed in the plan       │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. PROCESS MESSAGE (flow_manager.py:122)                            │
│                                                                      │
│    a) Get/Create Context:                                           │
│       - _get_or_create_context(thread_id)                           │
│       - Store in global self.contexts dict                          │
│                                                                      │
│    b) Update History:                                               │
│       - Append user message to conversation_history                 │
│                                                                      │
│    c) State Machine:                                                │
│       - COMPLETED → Reset to INTENT_DETECTION                       │
│       - INTENT_DETECTION → Generate plan OR classify intent         │
│       - CONTEXT_GATHERING → Extract & validate data                 │
│       - RESEARCH_PHASE → Run DeerFlow if needed                     │
│       - PLANNING_PHASE → Execute plan steps                         │
│       - EXECUTION_PHASE → Run intent handler                        │
│                                                                      │
│    d) Execute Based on State:                                       │
│       - PLANNING_PHASE → _handle_planning_phase()                   │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6. PLAN EXECUTION (flow_manager.py:469)                             │
│                                                                      │
│    For each step in plan:                                           │
│                                                                      │
│    a) Send Thinking & Plan via SSE:                                 │
│       "🤔 Thinking: ...\n📋 Plan: 1. ... 2. ..."                    │
│                                                                      │
│    b) Execute Step:                                                 │
│       - _execute_pm_step(step, context)                             │
│         ↓                                                            │
│       - Maps step_type to handler:                                  │
│         • list_my_tasks → _handle_list_my_tasks()                   │
│         • switch_project → _handle_switch_project()                 │
│         • research → Route to specific research handler             │
│                                                                      │
│    c) Stream Result:                                                │
│       "✅ List My Tasks\n   Found 20 tasks..."                      │
│                                                                      │
│    d) Continue until all steps done                                 │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 7. HANDLER EXECUTION (flow_manager.py:2272+)                        │
│                                                                      │
│    Example: _handle_list_my_tasks()                                 │
│                                                                      │
│    a) Data Extraction (if needed):                                  │
│       - Extract filters from message (week, date, period)           │
│                                                                      │
│    b) Identify Current User:                                        │
│       - Query OpenProject /api/v3/users/me                          │
│       - Get user ID from API key                                    │
│                                                                      │
│    c) Call PM Provider:                                             │
│       - self.pm_provider.list_tasks(filters={'assignee': user_id})  │
│                                                                      │
│    d) Format Response:                                              │
│       - Build markdown list of tasks                                │
│       - Calculate total hours                                       │
│       - Return {message, state, data}                               │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 8. PM PROVIDER (src/pm_providers/openproject.py)                    │
│                                                                      │
│    a) HTTP Request to OpenProject:                                  │
│       GET /api/v3/work_packages?                                  │
│       Headers: {Authorization, filters, pageSize}                   │
│                                                                      │
│    b) Parse JSON Response:                                          │
│       - Extract task fields                                         │
│       - Convert to PMTask objects                                   │
│       - Handle pagination                                           │
│                                                                      │
│    c) Return List[PMTask]                                           │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 9. STREAM TO CLIENT (app.py:937)                                    │
│                                                                      │
│    Server-Sent Events (SSE) format:                                 │
│                                                                      │
│    event: message_chunk                                             │
│    data: {"id": "...", "thread_id": "...",                          │
│           "role": "assistant", "content": "✅ ...",                 │
│           "finish_reason": null}                                    │
│                                                                      │
│    - Each step result streams immediately                           │
│    - Final chunk has finish_reason="stop"                           │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 10. CLIENT RECEIVES (Frontend at localhost:3000)                    │
│                                                                      │
│    - EventSource API parses SSE stream                              │
│    - Updates UI with incremental results                            │
│    - Shows "Thinking", "Plan", step results                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. ConversationFlowManager (Singleton)
- **Location**: `src/conversation/flow_manager.py`
- **Responsibility**: Orchestrates entire conversation flow
- **State Management**: Maintains `self.contexts[thread_id]` for each session
- **Key Methods**:
  - `process_message()` - Entry point
  - `generate_pm_plan()` - Creates execution plan
  - `_handle_planning_phase()` - Executes plan steps
  - `_execute_pm_step()` - Routes to specific handlers

### 2. PM Planner (LLM-Based)
- **Prompt**: `src/prompts/pm_planner.md`
- **Model**: PMPlan Pydantic model (pm_planner_model.py)
- **Input**: User message + context + history
- **Output**: `{overall_thought, steps: [{step_type, title, description}]}`

### 3. Context Management
- **Key Facts Extraction**: Active project/sprint/task, recent plans
- **Message Selection**: Top 8 relevant messages (semantic scoring)
- **Sliding Window**: Limits tokens for LLM input
- **Persistent Context**: Stored in memory per thread_id

### 4. Handler Architecture
59+ specialized handlers for different intents:
- **List Handlers**: list_projects, list_tasks, list_my_tasks, list_sprints
- **Switch Handlers**: switch_project, switch_sprint, switch_task
- **Create Handlers**: create_wbs, sprint_planning, create_project
- **Update Handlers**: update_task, update_sprint
- **Analytics**: burndown_chart, team_assignments, gantt_chart
- **Research**: eta_research, dependency_research, generic_research
- **Actions**: time_tracking, task_assignment

### 5. PM Provider Abstraction
- **Interface**: BasePMProvider (base.py)
- **Implementations**: OpenProjectProvider, JIRAProvider, ClickUpProvider
- **Unified Models**: PMProject, PMTask, PMSprint, PMUser
- **Configuration**: PM_PROVIDER env var

### 6. Streaming
- **Format**: Server-Sent Events (SSE)
- **Events**: message_chunk, system, finish
- **Incremental**: Each step result streams immediately
- **Callbacks**: stream_callback in process_message()

---

## State Machine Flow

```
INTENT_DETECTION
    ↓
    ├─> [Generate Plan] → PLANNING_PHASE → [Execute Steps] → COMPLETED
    │
    └─> [Classify Intent] → CONTEXT_GATHERING
                            ↓
                            ├─> [Not Enough Data] → Ask Questions
                            │
                            ├─> [Needs Research] → RESEARCH_PHASE → EXECUTION_PHASE → COMPLETED
                            │
                            └─> [Ready] → EXECUTION_PHASE → COMPLETED
```

---

## Data Flow Example

**User**: "list all my tasks"

1. **Plan Generation**:
   ```json
   {
     "overall_thought": "List tasks assigned to user",
     "steps": [{"step_type": "list_my_tasks", "title": "List My Tasks"}]
   }
   ```

2. **Step Execution**:
   - Extract current user from OpenProject
   - Call `pm_provider.list_tasks(filters={'assignee': user_id})`
   - Format response with task details

3. **Stream Response**:
   ```
   🤔 Thinking: List tasks assigned to user
   📋 Plan: 1. List My Tasks
   🚀 Executing plan...
   ✅ List My Tasks
      Found 20 tasks assigned to you...
   ```

---

## Context Persistence

- **Thread-based**: Each `thread_id` maintains separate context
- **Session Storage**: `ConversationFlowManager.contexts` dict
- **Active Contexts**: project_id, sprint_id, task_id
- **Gathered Data**: Extracted fields, research results, PM plans
- **History**: Conversation messages (user + assistant)

---

## Extensibility

To add new features:

1. **Add Step Type**: Update `PMStepType` enum (pm_planner_model.py)
2. **Add Handler**: Create `_handle_*()` method in flow_manager.py
3. **Update Router**: Map step_type to handler in `_execute_pm_step()`
4. **Add Prompt**: Document in pm_planner.md examples
5. **Provider Support**: Add method to BasePMProvider if needed

---

## Performance Optimizations

1. **Context Selection**: Semantic importance scoring reduces LLM tokens
2. **Sliding Window**: Max 8 messages sent to LLM
3. **Key Facts**: Summarized context instead of full history
4. **Streaming**: Incremental results, not waiting for completion
5. **Singleton Pattern**: Single ConversationFlowManager instance

---

## Research Routing

The system uses **intelligent research routing** based on step descriptions:

### Pre-Research Phase (app.py)
- **Trigger**: Only for `create_wbs` steps
- **Method**: Full DeerFlow research with web search
- **Purpose**: Gather industry knowledge for WBS generation
- **Streaming**: Real-time DeerFlow progress shown to user

### Dynamic Research During Execution (flow_manager.py)
When the LLM generates a plan with `research` step type, `_execute_pm_step` routes based on keywords:

```python
if step_type == "research":
    if "eta" in description or "estimate" in description:
        → _handle_eta_research()  # LLM estimates task durations
    elif "wbs" in description:
        → _handle_create_wbs_with_deerflow_planner()
    elif "dependency" in description:
        → _handle_dependency_research()  # LLM analyzes dependencies
    elif "sprint" in description:
        → _handle_sprint_planning_with_deerflow_planner()  # LLM planning
    else:
        → _handle_generic_research()  # Generic LLM research
```

### Research Handler Types
- **ETA Research**: Uses LLM to estimate task durations, updates via PM provider
- **Dependency Research**: Uses LLM to identify task dependencies
- **Sprint Planning**: Uses LLM thinking + internal sprint creation
- **WBS Generation**: Can use DeerFlow or LLM-based generation
- **Generic Research**: Flexible LLM-based research for any topic

**Key Insight**: The LLM decides **when** research is needed, and the system routes **how** to execute it.

---

## Error Handling

- **Graceful Degradation**: Falls back to intent-based if plan fails
- **Handler Try/Catch**: Each handler wraps in try/except
- **Validation**: Pydantic models validate LLM responses
- **Logging**: Comprehensive logging for debugging
- **User Feedback**: Error messages included in streaming response

