# PM Providers - Unified Project Management Middleware

A unified abstraction layer for connecting to different Project Management systems, similar to how we support multiple RAG providers.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│         FlowManager / Handlers / API Endpoints         │
│              (Your PM Agent Code)                       │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              BasePMProvider Interface                   │
│  - Projects: list, get, create, update, delete         │
│  - Tasks: list, get, create, update, delete            │
│  - Sprints: list, get, create, update, delete          │
│  - Users: list, get                                     │
│  - Health check                                         │
└─────────────────────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
┌─────────▼─────┐ ┌────────▼─────┐ ┌──────▼────────┐
│  Internal     │ │ OpenProject  │ │ JIRA/ClickUp  │
│  Provider     │ │  Provider    │ │   Providers   │
│ (Database)    │ │              │ │  (Stubs)      │
└───────────────┘ └──────────────┘ └───────────────┘
```

## Supported Providers

### ✅ Fully Implemented
- **Internal**: Uses our own PostgreSQL database (default)
- **OpenProject**: Full CRUD operations via OpenProject API

### 🚧 Planned (Stubs Created)
- **JIRA**: Atlassian JIRA Cloud API
- **ClickUp**: ClickUp API v2

## Configuration

Set the `PM_PROVIDER` environment variable:

```bash
# Use internal database (default)
PM_PROVIDER=internal

# Use OpenProject
PM_PROVIDER=openproject
OPENPROJECT_URL=https://your-instance.openproject.com
OPENPROJECT_API_KEY=your-api-key

# Use JIRA (when implemented)
PM_PROVIDER=jira
JIRA_URL=https://your-domain.atlassian.net
JIRA_API_TOKEN=your-api-token
JIRA_USERNAME=your-email@example.com

# Use ClickUp (when implemented)
PM_PROVIDER=clickup
CLICKUP_API_KEY=your-api-key
CLICKUP_TEAM_ID=your-team-id
```

## Usage

### Build a Provider Instance

```python
from pm_providers import build_pm_provider
from database import get_db_session

# Get database session
db = next(get_db_session())

# Build provider based on configuration
provider = build_pm_provider(db_session=db)

# Use the provider - works the same regardless of backend!
projects = await provider.list_projects()
tasks = await provider.list_tasks(project_id="some-id")
sprint = await provider.create_sprint(sprint_data)
```

### Provider Operations

All providers support the same interface:

```python
# Projects
projects = await provider.list_projects()
project = await provider.get_project("project-id")
new_project = await provider.create_project(PMProject(...))
updated = await provider.update_project("project-id", {"name": "New Name"})
await provider.delete_project("project-id")

# Tasks
tasks = await provider.list_tasks(project_id="project-id")
task = await provider.get_task("task-id")
new_task = await provider.create_task(PMTask(...))
updated = await provider.update_task("task-id", {"status": "completed"})
await provider.delete_task("task-id")

# Sprints
sprints = await provider.list_sprints(project_id="project-id")
sprint = await provider.get_sprint("sprint-id")
new_sprint = await provider.create_sprint(PMSprint(...))
updated = await provider.update_sprint("sprint-id", {"status": "active"})
await provider.delete_sprint("sprint-id")

# Users
users = await provider.list_users()
user = await provider.get_user("user-id")

# Health
is_healthy = await provider.health_check()
```

## Data Models

All providers use unified data models:

### PMProject
```python
@dataclass
class PMProject:
    id: str
    name: str
    description: Optional[str]
    status: Optional[str]
    priority: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    owner_id: Optional[str]
    raw_data: Optional[Dict]  # Provider-specific data preserved
```

### PMTask
```python
@dataclass
class PMTask:
    id: str
    title: str
    description: Optional[str]
    status: Optional[str]
    priority: Optional[str]
    project_id: Optional[str]
    parent_task_id: Optional[str]
    assignee_id: Optional[str]
    estimated_hours: Optional[float]
    actual_hours: Optional[float]
    due_date: Optional[date]
    raw_data: Optional[Dict]
```

### PMSprint
```python
@dataclass
class PMSprint:
    id: str
    name: str
    project_id: str
    start_date: date
    end_date: date
    status: Optional[str]
    capacity_hours: Optional[float]
    planned_hours: Optional[float]
    goal: Optional[str]
    raw_data: Optional[Dict]
```

## Database Tables

Two new tables support external provider connections:

### pm_provider_connections
Stores connection configurations for external PM systems:
- `name`, `provider_type`, `base_url`
- Authentication: `api_key`, `api_token`, `username`
- Provider-specific: `organization_id`, `project_key`, `workspace_id`
- `additional_config` (JSONB) for extra settings

### project_sync_mappings
Maps internal projects to external PM system projects:
- `internal_project_id` → `external_project_id`
- `sync_enabled`, `last_sync_at`
- `sync_config` (JSONB) for sync settings

## Integration with Existing System

### Option 1: Replace Internal DB with External Provider
Simply change `PM_PROVIDER` environment variable. All existing code continues to work!

```python
# In flow_manager.py or handlers
from pm_providers import build_pm_provider

provider = build_pm_provider(db_session=self.db_session)
# Use provider.create_task() instead of crud.create_task()
```

### Option 2: Dual-Mode Operation
Support both internal and external simultaneously:

```python
internal_provider = build_pm_provider(db_session=db)  # PM_PROVIDER=internal
external_provider = OpenProjectProvider(config)        # Direct external

# Sync between them
tasks_internal = await internal_provider.list_tasks()
for task in tasks_internal:
    await external_provider.create_task(task)
```

### Option 3: Shadow Mode
Keep internal DB as primary, sync selected projects to external:

```python
# Create sync mapping for a project
mapping = ProjectSyncMapping(
    internal_project_id="internal-123",
    provider_connection_id="op-connection-456",
    external_project_id="external-789",
    sync_enabled=True
)

# Bi-directional sync based on mapping
```

## Benefits

✅ **Unified Interface**: Same code works with any PM system  
✅ **Easy Migration**: Switch between providers via config  
✅ **Fallback Support**: Internal DB always available  
✅ **Multi-Provider**: Use different systems for different projects  
✅ **Future-Proof**: Add new providers without changing calling code  
✅ **Preserved Data**: `raw_data` field keeps provider-specific info  

## Implementation Status

| Provider | Status | Features |
|----------|--------|----------|
| Internal | ✅ Complete | Full CRUD, all operations |
| OpenProject | ✅ Complete | Full CRUD, API v3 |
| JIRA | 🚧 Stub | Needs implementation |
| ClickUp | 🚧 Stub | Needs implementation |
| Asana | 📋 Planned | Not started |
| Trello | 📋 Planned | Not started |

## Next Steps

1. **Complete JIRA implementation** - Full Atlassian JIRA API integration
2. **Complete ClickUp implementation** - ClickUp API v2 integration
3. **Add Asana provider** - Asana API integration
4. **Sync Engine** - Automatic bi-directional sync
5. **Webhooks** - Real-time updates from external systems
6. **Batch Operations** - Optimize bulk operations

