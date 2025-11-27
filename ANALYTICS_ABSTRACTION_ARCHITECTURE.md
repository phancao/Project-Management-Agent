# Analytics Abstraction Architecture

## Overview

Yes, we have a **well-designed abstraction layer** that handles different PM provider workflows and status definitions! The architecture uses multiple layers of abstraction to ensure analytics work consistently across different PM systems.

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                   Layer 1: MCP Analytics Tools                   │
│  Location: mcp_server/tools/analytics.py                        │
│  Purpose: AI agent interface (burndown_chart, velocity_chart)   │
│  Format: JSON responses optimized for LLM consumption            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Layer 2: Analytics Service                     │
│  Location: src/analytics/service.py                              │
│  Purpose: Business logic, caching, provider-agnostic interface  │
│  Methods: get_burndown_chart(), get_velocity_chart(), etc.      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Layer 3: Base Analytics Adapter (ABC)               │
│  Location: src/analytics/adapters/base.py                       │
│  Purpose: Define standard data format for analytics             │
│  Methods: get_burndown_data(), get_velocity_data(), etc.        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           Layer 4: PM Provider Analytics Adapter                 │
│  Location: src/analytics/adapters/pm_adapter.py                 │
│  Purpose: Fetch data from PM provider, transform to standard    │
│  Uses: TaskStatusResolver for provider-specific logic           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│            Layer 5: Task Status Resolver (Strategy)              │
│  Location: src/analytics/adapters/task_status_resolver.py       │
│  Purpose: Handle provider-specific status/workflow logic        │
│  Implementations: JIRA, OpenProject, Mock resolvers             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Layer 6: PM Provider Base                      │
│  Location: src/pm_providers/base.py                             │
│  Purpose: Unified interface to PM systems                        │
│  Methods: list_sprints(), list_tasks(), get_sprint()            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Layer 7: Specific PM Provider                       │
│  Location: src/pm_providers/openproject_v13.py, jira.py, etc.  │
│  Purpose: Provider-specific API calls and data mapping          │
│  Returns: PMTask, PMSprint objects (unified models)             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Actual PM System                              │
│  Examples: OpenProject, JIRA, ClickUp, etc.                     │
│  Returns: Provider-specific JSON/API responses                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Abstraction Components

### 1. BaseAnalyticsAdapter (Abstract Interface)

**Location**: `src/analytics/adapters/base.py`

**Purpose**: Defines the **standard data format** that analytics calculators expect

**Key Methods**:
```python
class BaseAnalyticsAdapter(ABC):
    @abstractmethod
    async def get_burndown_data(
        self, project_id: str, sprint_id: Optional[str] = None, 
        scope_type: str = "story_points"
    ) -> Dict[str, Any]:
        """
        Returns standardized format:
        {
            "sprint": {...},           # Sprint info
            "tasks": [...],            # List of tasks with status
            "scope_changes": [...]     # Scope changes during sprint
        }
        """
    
    @abstractmethod
    async def get_velocity_data(
        self, project_id: str, num_sprints: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Returns standardized format:
        [
            {
                "name": "Sprint 1",
                "planned_points": 50,
                "completed_points": 45,
                ...
            },
            ...
        ]
        """
    
    @abstractmethod
    async def get_sprint_report_data(...) -> Dict[str, Any]
    
    @abstractmethod
    async def get_cfd_data(...) -> Dict[str, Any]
    
    @abstractmethod
    async def get_cycle_time_data(...) -> List[Dict[str, Any]]
    
    @abstractmethod
    async def get_work_distribution_data(...) -> List[Dict[str, Any]]
    
    @abstractmethod
    async def get_issue_trend_data(...) -> Dict[str, Any]
```

**Benefits**:
- ✅ Analytics calculators work with **any** provider
- ✅ New providers just implement this interface
- ✅ Standard data format ensures consistency

### 2. TaskStatusResolver (Strategy Pattern)

**Location**: `src/analytics/adapters/task_status_resolver.py`

**Purpose**: Handle **provider-specific workflow and status logic**

**Key Methods**:
```python
class TaskStatusResolver(ABC):
    @abstractmethod
    def is_completed(self, task: PMTask) -> bool:
        """Check if task is completed (done/closed/resolved)"""
    
    @abstractmethod
    def is_burndowned(self, task: PMTask) -> bool:
        """Check if task counts toward burndown"""
    
    @abstractmethod
    def get_completion_date(self, task: PMTask) -> Optional[datetime]:
        """Get when task was completed"""
    
    @abstractmethod
    def get_start_date(self, task: PMTask) -> Optional[datetime]:
        """Get when task started (for cycle time)"""
    
    @abstractmethod
    def get_status_category(self, task: PMTask) -> str:
        """Categorize: 'todo', 'in_progress', 'done', 'blocked'"""
    
    @abstractmethod
    def extract_story_points(self, task: PMTask) -> float:
        """Extract story points (different fields per provider)"""
    
    @abstractmethod
    def get_status_history(self, task: PMTask) -> List[Dict[str, Any]]:
        """Get status change history (for CFD charts)"""
```

**Implementations**:

#### **JIRATaskStatusResolver**
```python
def is_completed(self, task: PMTask) -> bool:
    # JIRA: Task is completed if resolution field exists
    fields = task.raw_data.get("fields", {})
    resolution = fields.get("resolution")
    return resolution is not None

def extract_story_points(self, task: PMTask) -> float:
    # JIRA: Story points in customfield_10016 (or similar)
    fields = task.raw_data.get("fields", {})
    return fields.get("customfield_10016") or 0.0
```

#### **OpenProjectTaskStatusResolver**
```python
def is_completed(self, task: PMTask) -> bool:
    # OpenProject: Check status.is_closed flag
    status_obj = task.raw_data.get("_embedded", {}).get("status", {})
    is_closed = status_obj.get("isClosed", False)
    if is_closed:
        return True
    
    # Or check percentage_complete = 100%
    percentage = task.raw_data.get("percentageComplete")
    return percentage >= 100.0 if percentage else False

def extract_story_points(self, task: PMTask) -> float:
    # OpenProject: Story points in storyPoints field
    return task.raw_data.get("storyPoints") or 0.0
```

#### **MockTaskStatusResolver**
```python
def is_completed(self, task: PMTask) -> bool:
    # Mock: Simple status field matching
    status_lower = (task.status or "").lower()
    return any(keyword in status_lower 
               for keyword in ["done", "closed", "completed"])
```

**Factory Function**:
```python
def create_task_status_resolver(provider_type: str) -> TaskStatusResolver:
    if "jira" in provider_type.lower():
        return JIRATaskStatusResolver()
    elif "openproject" in provider_type.lower():
        return OpenProjectTaskStatusResolver()
    else:
        return MockTaskStatusResolver()
```

### 3. PMProviderAnalyticsAdapter (Implementation)

**Location**: `src/analytics/adapters/pm_adapter.py`

**Purpose**: Fetch data from PM provider and transform to standard format

**Key Features**:
```python
class PMProviderAnalyticsAdapter(BaseAnalyticsAdapter):
    def __init__(self, provider: BasePMProvider):
        self.provider = provider
        
        # Create appropriate status resolver based on provider type
        provider_type = getattr(provider.config, "provider_type", "mock")
        self.status_resolver = create_task_status_resolver(provider_type)
    
    async def get_burndown_data(self, project_id, sprint_id, scope_type):
        # 1. Fetch sprint info
        sprint = await self.provider.get_sprint(sprint_id)
        
        # 2. Fetch all tasks
        all_tasks = await self.provider.list_tasks(project_id=project_id)
        
        # 3. Filter tasks in this sprint
        sprint_tasks = [t for t in all_tasks if t.sprint_id == sprint_id]
        
        # 4. Use status resolver to determine completion
        for task in sprint_tasks:
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
            "scope_changes": []  # Calculate scope changes
        }
```

---

## How It Handles Different Workflows

### Example: Task Completion Status

Different PM systems define "done" differently:

#### **JIRA Workflow**
```
To Do → In Progress → Code Review → Done
                                      ↑
                              resolution field set
```

**Logic**:
```python
# JIRA: Task is done when resolution field exists
def is_completed(task):
    return task.raw_data["fields"]["resolution"] is not None
```

#### **OpenProject Workflow**
```
New → In Progress → Specified → Ready4SIT → Closed
                                              ↑
                                      isClosed = true
```

**Logic**:
```python
# OpenProject: Task is done when status.isClosed = true
def is_completed(task):
    status = task.raw_data["_embedded"]["status"]
    return status["isClosed"] == True
```

#### **Custom Workflow**
```
Backlog → Development → Testing → Deployed
                                    ↑
                            status = "Deployed"
```

**Logic**:
```python
# Custom: Create new resolver
class CustomTaskStatusResolver(TaskStatusResolver):
    def is_completed(self, task):
        return task.status == "Deployed"
```

### Example: Story Points Extraction

Different PM systems store story points differently:

| Provider | Story Points Location |
|----------|----------------------|
| JIRA | `fields.customfield_10016` |
| OpenProject | `storyPoints` |
| ClickUp | `custom_fields.story_points` |
| Azure DevOps | `fields.Microsoft.VSTS.Scheduling.StoryPoints` |

**Abstraction**:
```python
class TaskStatusResolver:
    @abstractmethod
    def extract_story_points(self, task: PMTask) -> float:
        """Each provider implements this differently"""
        pass

# JIRA implementation
def extract_story_points(self, task):
    return task.raw_data["fields"]["customfield_10016"] or 0.0

# OpenProject implementation
def extract_story_points(self, task):
    return task.raw_data["storyPoints"] or 0.0
```

---

## Benefits of This Architecture

### 1. **Provider Agnostic** ✅
- Analytics calculators don't know about providers
- Same burndown/velocity logic works for all providers
- Add new provider = implement adapters only

### 2. **Customizable per Provider** ✅
- Each provider has its own `TaskStatusResolver`
- Handles provider-specific workflows
- Handles provider-specific data formats

### 3. **Testable** ✅
- Mock adapters for testing
- Test analytics without real PM systems
- Test each layer independently

### 4. **Maintainable** ✅
- Changes to provider logic isolated to resolver
- Changes to analytics logic isolated to calculators
- Clear separation of concerns

### 5. **Extensible** ✅
- Add new analytics: implement in service
- Add new provider: implement resolver
- Add new status logic: override methods

---

## Adding a New PM Provider

To add support for a new PM provider (e.g., Azure DevOps):

### Step 1: Create Provider Implementation
```python
# src/pm_providers/azure_devops.py
class AzureDevOpsProvider(BasePMProvider):
    async def list_sprints(self, project_id):
        # Call Azure DevOps API
        pass
    
    async def list_tasks(self, project_id):
        # Call Azure DevOps API
        pass
```

### Step 2: Create Task Status Resolver
```python
# src/analytics/adapters/task_status_resolver.py
class AzureDevOpsTaskStatusResolver(TaskStatusResolver):
    def is_completed(self, task: PMTask) -> bool:
        # Azure DevOps: Check State field
        state = task.raw_data["fields"]["System.State"]
        return state in ["Closed", "Resolved", "Done"]
    
    def extract_story_points(self, task: PMTask) -> float:
        # Azure DevOps: Story points in specific field
        return task.raw_data["fields"]["Microsoft.VSTS.Scheduling.StoryPoints"] or 0.0
    
    def get_status_category(self, task: PMTask) -> str:
        state = task.raw_data["fields"]["System.State"]
        if state in ["Closed", "Resolved", "Done"]:
            return "done"
        elif state in ["Active", "Committed"]:
            return "in_progress"
        else:
            return "todo"
```

### Step 3: Register in Factory
```python
def create_task_status_resolver(provider_type: str) -> TaskStatusResolver:
    if "jira" in provider_type.lower():
        return JIRATaskStatusResolver()
    elif "openproject" in provider_type.lower():
        return OpenProjectTaskStatusResolver()
    elif "azure" in provider_type.lower():
        return AzureDevOpsTaskStatusResolver()  # Add this
    else:
        return MockTaskStatusResolver()
```

### Step 4: Done! ✅

Analytics automatically work with the new provider:
- Burndown charts work
- Velocity charts work
- Sprint reports work
- All analytics work

**No changes needed** to:
- Analytics service
- Analytics calculators
- MCP tools
- Frontend

---

## Customization Points

### 1. Status Logic
Override in `TaskStatusResolver`:
```python
def is_completed(self, task: PMTask) -> bool:
    # Custom logic for your workflow
    return task.status == "Your Custom Status"
```

### 2. Story Points
Override in `TaskStatusResolver`:
```python
def extract_story_points(self, task: PMTask) -> float:
    # Custom field location
    return task.raw_data["your_custom_field"] or 0.0
```

### 3. Status Categories
Override in `TaskStatusResolver`:
```python
def get_status_category(self, task: PMTask) -> str:
    # Map your statuses to categories
    if task.status in ["Deployed", "Released"]:
        return "done"
    elif task.status in ["Dev", "QA"]:
        return "in_progress"
    elif task.status == "Blocked":
        return "blocked"
    else:
        return "todo"
```

### 4. Completion Date
Override in `TaskStatusResolver`:
```python
def get_completion_date(self, task: PMTask) -> Optional[datetime]:
    # Custom completion date logic
    return task.raw_data["your_completion_field"]
```

---

## Summary

**Yes, we have a comprehensive abstraction layer!**

### Architecture Summary:
1. **BaseAnalyticsAdapter** - Defines standard data format
2. **TaskStatusResolver** - Handles provider-specific logic
3. **PMProviderAnalyticsAdapter** - Fetches and transforms data
4. **Factory Pattern** - Creates appropriate resolvers

### Key Benefits:
- ✅ Works with any PM provider
- ✅ Customizable per provider
- ✅ Handles different workflows
- ✅ Handles different status definitions
- ✅ Easy to extend
- ✅ Easy to test

### Current Support:
- ✅ JIRA (with resolution field)
- ✅ OpenProject (with isClosed flag)
- ✅ Mock (for testing)

### Easy to Add:
- Azure DevOps
- ClickUp
- Monday.com
- Linear
- Any other PM system

The architecture is **production-ready** and follows best practices for abstraction and extensibility!


