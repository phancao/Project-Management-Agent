# Analytics Abstraction Layer - Visual Guide

## Quick Answer

**Yes, we have a comprehensive abstraction layer!** The analytics system uses multiple layers to handle different PM provider workflows and status definitions.

---

## The Abstraction Layers

### Layer 1: MCP Tools (AI Agent Interface)
```
┌──────────────────────────────────────────────────────────────┐
│  MCP Analytics Tools (AI Agent Interface)                    │
│  Location: mcp_server/tools/analytics.py                    │
├──────────────────────────────────────────────────────────────┤
│  • burndown_chart(project_id, sprint_id, scope_type)        │
│  • velocity_chart(project_id, num_sprints)                  │
│  • sprint_report(sprint_id, project_id)                     │
│  • project_health(project_id)                               │
├──────────────────────────────────────────────────────────────┤
│  Returns: JSON optimized for LLM consumption                 │
└──────────────────────────────────────────────────────────────┘
```

### Layer 2: Analytics Service (Business Logic)
```
┌──────────────────────────────────────────────────────────────┐
│  Analytics Service                                           │
│  Location: src/analytics/service.py                         │
├──────────────────────────────────────────────────────────────┤
│  • get_burndown_chart(project_id, sprint_id, scope_type)    │
│  • get_velocity_chart(project_id, num_sprints)              │
│  • get_sprint_report(sprint_id, project_id)                 │
│  • get_project_summary(project_id)                          │
├──────────────────────────────────────────────────────────────┤
│  Features: Caching, error handling, data processing          │
└──────────────────────────────────────────────────────────────┘
```

### Layer 3: Base Analytics Adapter (Abstract Interface)
```
┌──────────────────────────────────────────────────────────────┐
│  BaseAnalyticsAdapter (ABC)                                  │
│  Location: src/analytics/adapters/base.py                   │
├──────────────────────────────────────────────────────────────┤
│  @abstractmethod                                             │
│  • get_burndown_data() → Dict[str, Any]                     │
│  • get_velocity_data() → List[Dict[str, Any]]               │
│  • get_sprint_report_data() → Dict[str, Any]                │
│  • get_cfd_data() → Dict[str, Any]                          │
│  • get_cycle_time_data() → List[Dict[str, Any]]             │
├──────────────────────────────────────────────────────────────┤
│  Purpose: Define standard data format for all providers      │
└──────────────────────────────────────────────────────────────┘
```

### Layer 4: PM Provider Analytics Adapter (Implementation)
```
┌──────────────────────────────────────────────────────────────┐
│  PMProviderAnalyticsAdapter                                  │
│  Location: src/analytics/adapters/pm_adapter.py             │
├──────────────────────────────────────────────────────────────┤
│  __init__(provider: BasePMProvider):                         │
│      self.provider = provider                                │
│      self.status_resolver = create_task_status_resolver(     │
│          provider.config.provider_type                       │
│      )                                                        │
├──────────────────────────────────────────────────────────────┤
│  async get_burndown_data():                                  │
│      1. Fetch sprint from provider                           │
│      2. Fetch tasks from provider                            │
│      3. Use status_resolver for completion logic             │
│      4. Return in standard format                            │
└──────────────────────────────────────────────────────────────┘
```

### Layer 5: Task Status Resolver (Strategy Pattern)
```
┌──────────────────────────────────────────────────────────────┐
│  TaskStatusResolver (ABC)                                    │
│  Location: src/analytics/adapters/task_status_resolver.py   │
├──────────────────────────────────────────────────────────────┤
│  @abstractmethod                                             │
│  • is_completed(task) → bool                                 │
│  • is_burndowned(task) → bool                                │
│  • get_completion_date(task) → Optional[datetime]            │
│  • get_start_date(task) → Optional[datetime]                 │
│  • get_status_category(task) → str                           │
│  • extract_story_points(task) → float                        │
│  • get_status_history(task) → List[Dict[str, Any]]           │
├──────────────────────────────────────────────────────────────┤
│  Implementations:                                            │
│  • JIRATaskStatusResolver                                    │
│  • OpenProjectTaskStatusResolver                             │
│  • MockTaskStatusResolver                                    │
└──────────────────────────────────────────────────────────────┘
```

### Layer 6: PM Provider Base (Unified Interface)
```
┌──────────────────────────────────────────────────────────────┐
│  BasePMProvider (ABC)                                        │
│  Location: src/pm_providers/base.py                         │
├──────────────────────────────────────────────────────────────┤
│  @abstractmethod                                             │
│  • list_sprints(project_id) → List[PMSprint]                │
│  • list_tasks(project_id) → List[PMTask]                    │
│  • get_sprint(sprint_id) → PMSprint                          │
│  • get_task(task_id) → PMTask                                │
├──────────────────────────────────────────────────────────────┤
│  Returns: Unified models (PMTask, PMSprint)                  │
└──────────────────────────────────────────────────────────────┘
```

### Layer 7: Specific PM Provider (Implementation)
```
┌──────────────────────────────────────────────────────────────┐
│  Specific Provider Implementation                            │
│  Location: src/pm_providers/openproject_v13.py, jira.py     │
├──────────────────────────────────────────────────────────────┤
│  • OpenProjectV13Provider                                    │
│  • JIRAProvider                                              │
│  • ClickUpProvider                                           │
│  • MockProvider                                              │
├──────────────────────────────────────────────────────────────┤
│  Purpose: Provider-specific API calls and data mapping       │
└──────────────────────────────────────────────────────────────┘
```

### Layer 8: Actual PM System
```
┌──────────────────────────────────────────────────────────────┐
│  Actual PM System API                                        │
├──────────────────────────────────────────────────────────────┤
│  • OpenProject API (https://openproject.example.com/api/v3) │
│  • JIRA API (https://jira.example.com/rest/api/2)           │
│  • ClickUp API (https://api.clickup.com/api/v2)             │
└──────────────────────────────────────────────────────────────┘
```

---

## How It Handles Different Workflows

### Example 1: Task Completion Status

Different PM systems have different ways to mark tasks as "done":

#### JIRA
```
Workflow: To Do → In Progress → Code Review → Done
                                                ↑
                                        resolution field set
```

**TaskStatusResolver Implementation**:
```python
class JIRATaskStatusResolver(TaskStatusResolver):
    def is_completed(self, task: PMTask) -> bool:
        # JIRA: Task is done when resolution field exists
        fields = task.raw_data.get("fields", {})
        resolution = fields.get("resolution")
        return resolution is not None
```

#### OpenProject
```
Workflow: New → In Progress → Specified → Ready4SIT → Closed
                                                        ↑
                                                isClosed = true
```

**TaskStatusResolver Implementation**:
```python
class OpenProjectTaskStatusResolver(TaskStatusResolver):
    def is_completed(self, task: PMTask) -> bool:
        # OpenProject: Check status.isClosed flag
        status_obj = task.raw_data.get("_embedded", {}).get("status", {})
        is_closed = status_obj.get("isClosed", False)
        if is_closed:
            return True
        
        # Or check percentage_complete = 100%
        percentage = task.raw_data.get("percentageComplete")
        if percentage is not None:
            return float(percentage) >= 100.0
        
        return False
```

#### Custom Provider
```
Workflow: Backlog → Development → Testing → Deployed
                                              ↑
                                      status = "Deployed"
```

**TaskStatusResolver Implementation**:
```python
class CustomTaskStatusResolver(TaskStatusResolver):
    def is_completed(self, task: PMTask) -> bool:
        # Custom: Task is done when status is "Deployed"
        return task.status == "Deployed"
```

### Example 2: Story Points Extraction

Different PM systems store story points in different fields:

| Provider | Story Points Location |
|----------|----------------------|
| JIRA | `fields.customfield_10016` (or similar) |
| OpenProject | `storyPoints` |
| ClickUp | `custom_fields.story_points` |
| Azure DevOps | `fields.Microsoft.VSTS.Scheduling.StoryPoints` |
| Custom | `custom_data.points` |

**Abstraction**:
```python
class TaskStatusResolver(ABC):
    @abstractmethod
    def extract_story_points(self, task: PMTask) -> float:
        """Each provider implements this differently"""
        pass

# JIRA implementation
class JIRATaskStatusResolver(TaskStatusResolver):
    def extract_story_points(self, task: PMTask) -> float:
        fields = task.raw_data.get("fields", {})
        return (
            fields.get("customfield_10016") or
            fields.get("storyPoints") or
            0.0
        )

# OpenProject implementation
class OpenProjectTaskStatusResolver(TaskStatusResolver):
    def extract_story_points(self, task: PMTask) -> float:
        return task.raw_data.get("storyPoints") or 0.0

# Custom implementation
class CustomTaskStatusResolver(TaskStatusResolver):
    def extract_story_points(self, task: PMTask) -> float:
        return task.raw_data.get("custom_data", {}).get("points") or 0.0
```

### Example 3: Status Categories

Different PM systems have different status names:

| Provider | Todo | In Progress | Done | Blocked |
|----------|------|-------------|------|---------|
| JIRA | "To Do", "Backlog" | "In Progress", "Doing" | "Done", "Resolved" | "Blocked", "On Hold" |
| OpenProject | "New" | "In Progress", "Specified" | "Closed", "Done" | "Blocked" |
| Custom | "Backlog" | "Development", "Testing" | "Deployed" | "Waiting" |

**Abstraction**:
```python
class TaskStatusResolver(ABC):
    @abstractmethod
    def get_status_category(self, task: PMTask) -> str:
        """Categorize status into: 'todo', 'in_progress', 'done', 'blocked'"""
        pass

# JIRA implementation
class JIRATaskStatusResolver(TaskStatusResolver):
    def get_status_category(self, task: PMTask) -> str:
        status_lower = (task.status or "").lower()
        
        if any(keyword in status_lower for keyword in ["done", "resolved"]):
            return "done"
        elif "block" in status_lower or "hold" in status_lower:
            return "blocked"
        elif "progress" in status_lower or "doing" in status_lower:
            return "in_progress"
        else:
            return "todo"

# Custom implementation
class CustomTaskStatusResolver(TaskStatusResolver):
    def get_status_category(self, task: PMTask) -> str:
        if task.status == "Deployed":
            return "done"
        elif task.status in ["Development", "Testing"]:
            return "in_progress"
        elif task.status == "Waiting":
            return "blocked"
        else:
            return "todo"
```

---

## Data Flow Example: Burndown Chart

Let's trace how a burndown chart request flows through the layers:

### Step 1: AI Agent Request
```
Agent: "Show me the burndown for Sprint 4"
↓
MCP Tool: burndown_chart(project_id="abc123:proj-1", sprint_id="4")
```

### Step 2: MCP Tool Processing
```python
# mcp_server/tools/analytics.py
async def burndown_chart(arguments: dict[str, Any]):
    project_id = arguments.get("project_id")  # "abc123:proj-1"
    sprint_id = arguments.get("sprint_id")     # "4"
    scope_type = arguments.get("scope_type", "story_points")
    
    # Get analytics service
    service, actual_project_id = await _get_analytics_service(
        project_id, pm_handler
    )
    ↓
```

### Step 3: Get Analytics Service
```python
# mcp_server/tools/analytics.py
async def _get_analytics_service(project_id, pm_handler):
    # Parse composite ID
    provider_id, actual_project_id = project_id.split(":", 1)
    # "abc123", "proj-1"
    
    # Get provider from database
    provider_conn = db.query(PMProviderConnection).filter(
        PMProviderConnection.id == provider_id
    ).first()
    # Found: OpenProject v13 provider
    
    # Create provider instance
    provider = pm_handler._create_provider_instance(provider_conn)
    # Returns: OpenProjectV13Provider instance
    
    # Create analytics adapter
    adapter = PMProviderAnalyticsAdapter(provider)
    # Creates adapter with OpenProjectTaskStatusResolver
    
    # Create analytics service
    service = AnalyticsService(adapter=adapter)
    
    return service, actual_project_id
    ↓
```

### Step 4: Analytics Service Call
```python
# src/analytics/service.py
class AnalyticsService:
    async def get_burndown_chart(self, project_id, sprint_id, scope_type):
        # Get data from adapter
        data = await self.adapter.get_burndown_data(
            project_id, sprint_id, scope_type
        )
        
        # Calculate burndown
        calculator = BurndownCalculator()
        result = calculator.calculate(data)
        
        return result
        ↓
```

### Step 5: Adapter Fetches Data
```python
# src/analytics/adapters/pm_adapter.py
class PMProviderAnalyticsAdapter:
    async def get_burndown_data(self, project_id, sprint_id, scope_type):
        # 1. Fetch sprint info
        sprint = await self.provider.get_sprint(sprint_id)
        # Calls OpenProjectV13Provider.get_sprint()
        
        # 2. Fetch all tasks
        all_tasks = await self.provider.list_tasks(project_id=project_id)
        # Calls OpenProjectV13Provider.list_tasks()
        
        # 3. Filter tasks in this sprint
        sprint_tasks = [t for t in all_tasks if t.sprint_id == sprint_id]
        
        # 4. Use status resolver for provider-specific logic
        for task in sprint_tasks:
            # OpenProjectTaskStatusResolver determines completion
            task.is_completed = self.status_resolver.is_completed(task)
            task.completion_date = self.status_resolver.get_completion_date(task)
            task.story_points = self.status_resolver.extract_story_points(task)
        
        # 5. Return in standard format
        return {
            "sprint": {
                "name": sprint.name,
                "start_date": sprint.start_date,
                "end_date": sprint.end_date
            },
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "story_points": t.story_points,
                    "is_completed": t.is_completed,
                    "completion_date": t.completion_date
                }
                for t in sprint_tasks
            ],
            "scope_changes": []
        }
        ↓
```

### Step 6: Status Resolver Logic
```python
# src/analytics/adapters/task_status_resolver.py
class OpenProjectTaskStatusResolver:
    def is_completed(self, task: PMTask) -> bool:
        # Check OpenProject-specific completion logic
        status_obj = task.raw_data.get("_embedded", {}).get("status", {})
        is_closed = status_obj.get("isClosed", False)
        if is_closed:
            return True
        
        # Check percentage complete
        percentage = task.raw_data.get("percentageComplete")
        if percentage is not None:
            return float(percentage) >= 100.0
        
        return False
    
    def extract_story_points(self, task: PMTask) -> float:
        # Extract from OpenProject-specific field
        return task.raw_data.get("storyPoints") or 0.0
        ↓
```

### Step 7: Provider API Call
```python
# src/pm_providers/openproject_v13.py
class OpenProjectV13Provider:
    async def get_sprint(self, sprint_id: str) -> PMSprint:
        # Call OpenProject API
        response = await self.client.get(
            f"/api/v3/versions/{sprint_id}"
        )
        
        # Map to unified PMSprint model
        return PMSprint(
            id=response["id"],
            name=response["name"],
            start_date=response["startDate"],
            end_date=response["endDate"],
            raw_data=response
        )
        ↓
```

### Step 8: OpenProject API Response
```json
{
  "id": "4",
  "name": "Sprint 4",
  "startDate": "2025-11-01",
  "endDate": "2025-11-14",
  "_embedded": {
    "status": {
      "name": "open",
      "isClosed": false
    }
  }
}
```

### Step 9: Return to Agent
```json
{
  "sprint_name": "Sprint 4",
  "start_date": "2025-11-01",
  "end_date": "2025-11-14",
  "scope_type": "story_points",
  "total_scope": 50.0,
  "completed": 42.5,
  "remaining": 7.5,
  "completion_percentage": 85.0,
  "is_on_track": true,
  "daily_data": [
    {"date": "2025-11-01", "remaining": 50.0, "ideal": 50.0},
    {"date": "2025-11-02", "remaining": 47.0, "ideal": 46.4},
    ...
  ]
}
```

---

## Benefits Summary

### 1. Provider Agnostic ✅
- Same analytics logic works for **all** providers
- Add new provider = implement adapters only
- No changes to analytics calculators

### 2. Customizable per Provider ✅
- Each provider has its own `TaskStatusResolver`
- Handles provider-specific workflows
- Handles provider-specific data formats
- Handles provider-specific field locations

### 3. Testable ✅
- Mock adapters for unit testing
- Test each layer independently
- Test analytics without real PM systems

### 4. Maintainable ✅
- Changes isolated to appropriate layer
- Clear separation of concerns
- Easy to understand and debug

### 5. Extensible ✅
- Add new analytics: implement in service
- Add new provider: implement resolver
- Add new status logic: override methods
- No breaking changes to existing code

---

## Conclusion

**Yes, we have a comprehensive abstraction layer!**

The architecture uses:
- **Abstract Base Classes** (ABC) for interfaces
- **Strategy Pattern** for provider-specific logic
- **Adapter Pattern** for data transformation
- **Factory Pattern** for resolver creation

This ensures that analytics work consistently across different PM systems while allowing customization for provider-specific workflows and status definitions.

The abstraction layer is **production-ready** and follows industry best practices! 🎉


