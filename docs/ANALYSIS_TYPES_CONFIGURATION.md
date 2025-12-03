# Analysis Types Configuration

## Overview

Instead of hardcoding validation rules for different analysis types (project, sprint, epic, etc.), we use a **configuration-based approach** that maps analysis types to their required tools.

## Architecture

### Benefits

1. **Scalable**: Easy to add new analysis types (epic, milestone, resource, etc.)
2. **Maintainable**: All analysis type rules in one place (`src/graph/analysis_types.py`)
3. **Flexible**: No need to split into multiple agents - one PM agent handles all types
4. **Clear**: Explicit mapping of analysis type → required tools

### How It Works

```
User Query: "Analyze Sprint 4"
    ↓
Planner creates plan
    ↓
Validation detects: AnalysisType.SPRINT
    ↓
Checks if plan includes required tools: [list_sprints, sprint_report, burndown_chart, list_tasks]
    ↓
If missing tools → Adds warning to step description
    ↓
PM Agent executes plan with appropriate tools
```

## Current Analysis Types

| Type | Required Tools | Example Queries |
|------|---------------|-----------------|
| **PROJECT** | 11 tools (get_project, project_health, list_sprints, list_tasks, velocity_chart, burndown_chart, sprint_report, cfd_chart, cycle_time_chart, work_distribution_chart, issue_trend_chart) | "Analyze this project", "Project analysis", "Full project report" |
| **SPRINT** | 4 tools (list_sprints, sprint_report, burndown_chart, list_tasks) | "Analyze Sprint 4", "Sprint 5 performance", "Sprint report" |
| **EPIC** | 3 tools (list_epics, list_tasks, get_epic) | "Epic analysis", "Epic progress", "Analyze epic X" |
| **MILESTONE** | 2 tools (list_tasks, list_sprints) | "Milestone analysis", "Milestone progress" |
| **RESOURCE** | 3 tools (list_users, list_tasks, work_distribution_chart) | "Resource analysis", "Team workload", "Resource allocation" |
| **USER** | 2 tools (list_users, list_tasks) | "User analysis", "Team member analysis" |
| **TASK** | 2 tools (list_tasks, get_task) | "Task analysis", "Task progress" |

## Adding New Analysis Types

### Step 1: Add to Enum

In `src/graph/analysis_types.py`:

```python
class AnalysisType(str, Enum):
    # ... existing types ...
    CUSTOM_TYPE = "custom_type"  # Add your new type
```

### Step 2: Define Required Tools

```python
ANALYSIS_TOOL_REQUIREMENTS: Dict[AnalysisType, List[str]] = {
    # ... existing mappings ...
    AnalysisType.CUSTOM_TYPE: [
        "tool1",
        "tool2",
        "tool3",
    ],
}
```

### Step 3: Add Detection Keywords

```python
ANALYSIS_TYPE_KEYWORDS: Dict[AnalysisType, List[str]] = {
    # ... existing keywords ...
    AnalysisType.CUSTOM_TYPE: [
        "custom analysis",
        "custom report",
        "analyze custom",
    ],
}
```

### Step 4: Update Planner Prompt (Optional)

If needed, add guidance in `src/prompts/planner.md`:

```markdown
### For Custom Type Analysis

**User asks**: "Analyze custom type"

**YOU MUST USE THIS FORMAT:**
```json
{
  "title": "Custom Type Analysis",
  "steps": [
    {
      "description": "Use tool1, tool2, tool3 for custom analysis",
      "step_type": "pm_query"
    }
  ]
}
```
```

## Detection Logic

The system detects analysis types by checking:

1. **Plan title** (e.g., "Sprint 4 Performance Analysis")
2. **Plan thought** (e.g., "User wants to analyze Sprint 4")
3. **Step titles** (e.g., "Analyze Sprint 4 Metrics")
4. **Step descriptions** (e.g., "Use sprint_report, burndown_chart...")

### Priority Order

1. **Sprint-specific patterns** (most specific) - e.g., "sprint 4 analysis"
2. **Other analysis types** - checked in order
3. **Unknown** - if no match

### Pattern Matching

- **Exact keywords**: "project analysis" → `AnalysisType.PROJECT`
- **Patterns**: "sprint [number]" → `AnalysisType.SPRINT`
- **Context-aware**: "project analysis" that mentions sprint → `AnalysisType.PROJECT` (project takes priority)

## Validation Flow

```python
# In validate_and_fix_plan() in src/graph/nodes.py

1. Detect analysis type from plan content
2. Get required tools for that type
3. Check if plan mentions all required tools
4. If missing tools:
   - Log warning
   - Add warning to step description
   - PM agent will see warning and call missing tools
```

## Why Not Multiple Agents?

### Current Approach (Single PM Agent) ✅

**Pros:**
- ✅ One agent with all tools
- ✅ Flexible tool selection
- ✅ Less code duplication
- ✅ Easier maintenance

**Cons:**
- ⚠️ Agent needs to understand different analysis types

### Alternative (Multiple Agents) ❌

**Pros:**
- ✅ Specialized agents for each type
- ✅ Clear separation of concerns

**Cons:**
- ❌ Code duplication (each agent needs same tools)
- ❌ More complex routing logic
- ❌ Harder to maintain
- ❌ Overkill for similar operations

## Example: Adding Epic Analysis

```python
# 1. Add to enum
class AnalysisType(str, Enum):
    EPIC = "epic"  # Already exists!

# 2. Define tools (already done)
ANALYSIS_TOOL_REQUIREMENTS[AnalysisType.EPIC] = [
    "list_epics",
    "list_tasks",
    "get_epic",
]

# 3. Add keywords (already done)
ANALYSIS_TYPE_KEYWORDS[AnalysisType.EPIC] = [
    "epic analysis",
    "epic progress",
    "epic status",
]

# 4. Update planner prompt (optional)
# Add example in planner.md for epic analysis
```

That's it! The system will automatically:
- Detect "epic analysis" queries
- Validate that required tools are called
- Warn if tools are missing

## Testing

To test a new analysis type:

1. Ask: "Analyze epic X"
2. Check logs for: `[VALIDATION] Detected analysis type: epic`
3. Verify correct tools are called
4. Check if validation warns about missing tools

## Future Enhancements

1. **Dynamic tool requirements**: Based on project configuration
2. **Custom analysis types**: User-defined analysis types
3. **Tool dependencies**: Some tools require others to be called first
4. **Conditional requirements**: Different tools based on project state

