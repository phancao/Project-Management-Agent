# Task Status Resolver - Middle Layer Design

## Overview

The **Task Status Resolver** is a middle layer that abstracts provider-specific differences in how task completion, burndown eligibility, and status are determined. This allows charts to work consistently across different PM providers (JIRA, OpenProject, Mock) without needing to know provider-specific details.

## Problem

Different PM providers use different mechanisms to mark tasks as "done":

- **JIRA**: Uses `resolution` field - if resolution exists, task is done
- **OpenProject**: Uses `status.is_closed` flag, status name ("Done"/"Closed"), or `percentage_complete = 100`
- **Mock**: Uses simple status field matching ("done", "closed", "completed")

Without a unified interface, each chart calculator would need to handle these differences, leading to code duplication and maintenance issues.

## Solution

The `TaskStatusResolver` interface provides a unified API for all status-related queries:

```python
class TaskStatusResolver(ABC):
    def is_completed(task: PMTask) -> bool
    def is_burndowned(task: PMTask) -> bool
    def get_completion_date(task: PMTask) -> Optional[datetime]
    def get_start_date(task: PMTask) -> Optional[datetime]
    def get_status_category(task: PMTask) -> str  # "todo", "in_progress", "done", "blocked"
    def extract_story_points(task: PMTask) -> float
    def get_status_history(task: PMTask) -> List[Dict[str, Any]]
    def get_task_type(task: PMTask) -> str
```

Each provider has its own implementation:
- `JIRATaskStatusResolver`
- `OpenProjectTaskStatusResolver`
- `MockTaskStatusResolver`

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Chart Calculators (burndown.py, cfd.py, etc.)              │
│  - Don't know about provider differences                    │
│  - Work with standardized data                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Analytics Service (service.py)                             │
│  - Orchestrates data fetching and calculation              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  PMProviderAnalyticsAdapter (pm_adapter.py)                 │
│  - Uses TaskStatusResolver for all status queries          │
│  - Transforms provider data to standardized format         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  TaskStatusResolver (task_status_resolver.py)              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────┐ │
│  │ JIRA Resolver    │  │ OpenProject      │  │ Mock     │ │
│  │ - resolution     │  │ Resolver         │  │ Resolver │ │
│  │ - resolutiondate │  │ - is_closed      │  │ - status │ │
│  └──────────────────┘  │ - percentage     │  └──────────┘ │
│                        └──────────────────┘                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  PM Providers (JIRA, OpenProject, Mock)                    │
│  - Return PMTask objects with raw_data                      │
└─────────────────────────────────────────────────────────────┘
```

## Provider-Specific Implementations

### JIRA (`JIRATaskStatusResolver`)

**Completion Logic:**
- Primary: Check if `fields.resolution` exists
- Fallback: Check status name for "done", "closed", "completed", "resolved"

**Completion Date:**
- From `fields.resolutiondate`

**Story Points:**
- From `fields.customfield_10016` (varies by JIRA instance)
- Fallback: `estimated_hours / 8`

**Status History:**
- From `changelog.histories` (status field changes)

### OpenProject (`OpenProjectTaskStatusResolver`)

**Completion Logic:**
1. Check `_embedded.status.isClosed` flag
2. Check status name for "done", "closed", "completed"
3. Check `percentageComplete >= 100`

**Completion Date:**
- From `completed_at` field or `date` field in raw_data

**Story Points:**
- From `raw_data.storyPoints`
- Fallback: `estimated_hours / 8`

**Status History:**
- Basic history from `created_at` and `completed_at` (full history may require API calls)

### Mock (`MockTaskStatusResolver`)

**Completion Logic:**
- Simple status field matching: "done", "closed", "completed"

**Completion Date:**
- From `completed_at` field

**Story Points:**
- From `raw_data.storyPoints`
- Fallback: `estimated_hours / 8`

**Status History:**
- Basic history from `created_at` and `completed_at`

## Usage in Adapter

The `PMProviderAnalyticsAdapter` uses the resolver for all status-related operations:

```python
class PMProviderAnalyticsAdapter(BaseAnalyticsAdapter):
    def __init__(self, provider: BasePMProvider):
        self.provider = provider
        provider_type = getattr(provider.config, "provider_type", ...)
        self.status_resolver = create_task_status_resolver(provider_type)
    
    async def get_burndown_data(...):
        for task in sprint_tasks:
            # Use resolver instead of hardcoded logic
            story_points = self.status_resolver.extract_story_points(task)
            is_burndowned = self.status_resolver.is_burndowned(task)
            completion_date = self.status_resolver.get_completion_date(task)
```

## Benefits

1. **Separation of Concerns**: Provider-specific logic is isolated in resolver implementations
2. **Maintainability**: Changes to provider logic only affect one file
3. **Testability**: Each resolver can be tested independently
4. **Extensibility**: Adding new providers only requires creating a new resolver
5. **Consistency**: All charts use the same logic for status determination

## Chart Requirements

Each chart type needs specific data from the resolver:

### Burndown Chart
- `is_burndowned()` - Is task counted in burndown?
- `extract_story_points()` - Story points for scope
- `get_completion_date()` - When was task completed?

### Velocity Chart
- `is_completed()` - Is task completed?
- `extract_story_points()` - Story points for velocity calculation

### CFD Chart
- `get_status_history()` - Status changes over time
- `get_status_category()` - Categorize status for flow

### Cycle Time Chart
- `is_completed()` - Only completed tasks
- `get_start_date()` - When work started
- `get_completion_date()` - When work completed

### Work Distribution Chart
- `extract_story_points()` - Story points for distribution
- `get_task_type()` - Task type (Story, Bug, etc.)
- `get_status_category()` - Status category

### Issue Trend Chart
- `get_completion_date()` - When issues were resolved
- `get_task_type()` - Task type for categorization

## Factory Function

The `create_task_status_resolver()` function automatically selects the appropriate resolver:

```python
resolver = create_task_status_resolver("jira")  # Returns JIRATaskStatusResolver
resolver = create_task_status_resolver("openproject")  # Returns OpenProjectTaskStatusResolver
resolver = create_task_status_resolver("mock")  # Returns MockTaskStatusResolver
```

## Future Enhancements

1. **Status History Caching**: Cache status history to avoid repeated API calls
2. **Custom Resolvers**: Allow custom resolver implementations for special cases
3. **Status Mapping Configuration**: Allow configuration of status name mappings
4. **Performance Optimization**: Batch status queries for better performance

## Testing

Each resolver should be tested with:
- Sample PMTask objects from the provider
- Edge cases (missing fields, null values, etc.)
- Different status values
- Different story point formats

Example test:
```python
def test_jira_resolver_completion():
    resolver = JIRATaskStatusResolver()
    task = PMTask(
        id="TEST-123",
        raw_data={"fields": {"resolution": {"name": "Done"}}}
    )
    assert resolver.is_completed(task) == True
```

