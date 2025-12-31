# PM Providers Integration Guide

Complete guide for integrating external Project Management systems.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Provider Configuration](#provider-configuration)
4. [API Integration](#api-integration)
5. [Data Mapping](#data-mapping)
6. [Sync Strategies](#sync-strategies)
7. [Examples](#examples)

## Overview

The PM Providers middleware provides a unified interface to multiple Project Management systems:
- Your internal PostgreSQL database (default)
- OpenProject
- JIRA
- ClickUp
- Others (via easy extension)

### Why Use PM Providers?

**Before**: Hard-coded to PostgreSQL  
**After**: Switch between any PM system via configuration

```python
# Your code doesn't change
provider = build_pm_provider(db_session)
tasks = await provider.list_tasks()

# Just change PM_PROVIDER env var to switch systems!
```

## Quick Start

### 1. Install Dependencies

```bash
# OpenProject support
pip install requests

# Future: JIRA support
# pip install jira

# Future: ClickUp support  
# pip install clickup-api
```

### 2. Configure Environment

```bash
# .env file
PM_PROVIDER=openproject  # or 'internal', 'jira', 'clickup'
OPENPROJECT_URL=https://demo.openproject.com
OPENPROJECT_API_KEY=base64-encoded-api-key
```

### 3. Use in Your Code

```python
from pm_providers import build_pm_provider, PMProject, PMTask

# Build provider (reads from env)
provider = build_pm_provider(db_session=db)

# Create a project
project = PMProject(
    id="",  # Auto-generated
    name="My New Project",
    description="A test project"
)
created_project = await provider.create_project(project)

# List tasks
tasks = await provider.list_tasks(project_id=created_project.id)
print(f"Found {len(tasks)} tasks")

# Health check
if await provider.health_check():
    print("Provider connection healthy!")
```

## Provider Configuration

### Internal Database (Default)

```bash
PM_PROVIDER=internal
# Uses your existing PostgreSQL database
# No additional configuration needed
```

### OpenProject

```bash
PM_PROVIDER=openproject
OPENPROJECT_URL=https://your-instance.openproject.com
OPENPROJECT_API_KEY=<base64-encoded-api-key>

# To generate API key in OpenProject:
# 1. Login to OpenProject
# 2. Go to My Account > Access Token
# 3. Generate new token
# 4. Base64 encode: "apikey:token" → base64 output
```

**Example:**
```bash
# Create API token in OpenProject
echo -n "apikey:your-token-here" | base64
# Output: YXBpa2V5OnlvdXItdG9rZW4taGVyZQ==

# Use in .env
OPENPROJECT_API_KEY=YXBpa2V5OnlvdXItdG9rZW4taGVyZQ==
```

### JIRA Cloud

```bash
PM_PROVIDER=jira
JIRA_URL=https://your-domain.atlassian.net
JIRA_API_TOKEN=<your-api-token>
JIRA_USERNAME=your-email@example.com

# To generate API token:
# 1. Login to https://id.atlassian.com/manage-profile/security/api-tokens
# 2. Create API token
# 3. Note: Username is your email
```

### ClickUp

```bash
PM_PROVIDER=clickup
CLICKUP_API_KEY=<your-api-key>
CLICKUP_TEAM_ID=<your-team-id>

# To get API key:
# 1. Login to ClickUp
# 2. Settings > Apps > API
# 3. Generate token
# 4. Find team ID in URL or API response
```

## API Integration

### Modify Flow Manager to Use Providers

Update `backend/conversation/flow_manager.py`:

```python
from pm_providers import build_pm_provider

class ConversationFlowManager:
    def __init__(self, db_session=None):
        self.db_session = db_session
        # ... existing code ...
        
        # Build PM provider
        self.pm_provider = None
        if db_session:
            self.pm_provider = build_pm_provider(db_session=db_session)
```

### Replace CRUD Calls

**Before:**
```python
from database import crud
project = crud.create_project(db, name="Test", ...)
tasks = crud.get_tasks_by_project(db, project_id)
```

**After:**
```python
# Provider handles everything
project = await self.pm_provider.create_project(PMProject(name="Test", ...))
tasks = await self.pm_provider.list_tasks(project_id=project.id)
```

### Update Handlers

Example: Modify `_handle_update_task` in `flow_manager.py`:

```python
async def _handle_update_task(self, context: ConversationContext) -> Dict[str, Any]:
    # ... extraction logic ...
    
    # Instead of database crud:
    # updated_task = update_task(self.db_session, task.id, **update_fields)
    
    # Use provider:
    updated_task = await self.pm_provider.update_task(
        task.id, 
        {"status": context.gathered_data["new_status"]}
    )
    
    return {
        "type": "execution_completed",
        "message": f"✅ Task updated successfully!",
        "data": {"task_id": updated_task.id}
    }
```

## Data Mapping

### Field Translation

Different PM systems use different field names. The providers handle translation:

| Internal | OpenProject | JIRA | ClickUp |
|----------|-------------|------|---------|
| `title` | `subject` | `summary` | `name` |
| `status` | `status.name` | `fields.status.name` | `status.status` |
| `assignee_id` | `_links.assignee.href` | `fields.assignee.accountId` | `assignees[].id` |

### Preserved Data

All providers preserve original data in `raw_data`:

```python
task = await provider.get_task("123")
print(task.title)           # Unified: "Fix bug"
print(task.raw_data)        # Provider-specific full data
print(task.raw_data.get("_links"))  # OpenProject-specific
```

### Custom Mapping

You can customize field mapping per provider:

```python
# In openproject.py
def _parse_task(self, data):
    task = PMTask(
        id=data["id"],
        title=data.get("subject", ""),
        # ... other fields ...
        raw_data=data  # Original data preserved
    )
    return task
```

## Sync Strategies

### Strategy 1: Shadow Mode (Recommended)

Keep internal DB as primary, sync to external on-demand:

```python
async def sync_to_openproject(project_id: str):
    """Sync internal project to OpenProject"""
    internal_provider = build_pm_provider(db_session)  # PM_PROVIDER=internal
    external_provider = OpenProjectProvider(openproject_config)
    
    # Get internal project
    internal = await internal_provider.get_project(project_id)
    tasks = await internal_provider.list_tasks(project_id)
    
    # Create in external
    external = await external_provider.create_project(internal)
    
    # Sync tasks
    for task in tasks:
        await external_provider.create_task(task)
    
    # Save mapping
    mapping = ProjectSyncMapping(
        internal_project_id=project_id,
        external_project_id=external.id,
        sync_enabled=True
    )
    db_session.add(mapping)
```

### Strategy 2: Dual-Write

Write to both systems simultaneously:

```python
async def create_task_dual(task_data):
    """Create task in both internal and external systems"""
    internal_provider = build_pm_provider(db_session)
    external_provider = OpenProjectProvider(config)
    
    # Create in parallel
    internal_task, external_task = await asyncio.gather(
        internal_provider.create_task(task_data),
        external_provider.create_task(task_data)
    )
    
    # Store mapping for future updates
    return internal_task, external_task
```

### Strategy 3: Full External

Use external system as primary, internal as cache:

```python
# Set PM_PROVIDER=openproject in .env
provider = build_pm_provider(db_session)

# All operations go to OpenProject
projects = await provider.list_projects()
```

## Examples

### Example 1: Create WBS in OpenProject

```python
from pm_providers import build_pm_provider, PMProject, PMTask

# Configure for OpenProject
import os
os.environ["PM_PROVIDER"] = "openproject"
os.environ["OPENPROJECT_URL"] = "https://demo.openproject.com"
os.environ["OPENPROJECT_API_KEY"] = "your-key"

# Build provider
provider = build_pm_provider(db_session)

# Create project
project = PMProject(
    name="QA Automation with AI Agent",
    description="Implement AI-powered QA testing"
)
created = await provider.create_project(project)

# Create tasks
tasks_data = [
    PMTask(title="Setup Environment", project_id=created.id),
    PMTask(title="Design Test Architecture", project_id=created.id),
    PMTask(title="Implement AI Agent", project_id=created.id),
]

created_tasks = await provider.bulk_create_tasks(tasks_data)
print(f"Created {len(created_tasks)} tasks in OpenProject")
```

### Example 2: Sync Internal to JIRA

```python
async def mirror_to_jira(internal_project_id: str):
    """Mirror internal project to JIRA"""
    internal = build_pm_provider(db_session)  # internal
    jira = JIRAProvider(jira_config)          # jira
    
    # Get internal data
    project = await internal.get_project(internal_project_id)
    tasks = await internal.list_tasks(internal_project_id)
    sprints = await internal.list_sprints(internal_project_id)
    
    # Create in JIRA
    jira_project = await jira.create_project(project)
    
    # Sync tasks
    for task in tasks:
        await jira.create_task(task)
    
    # Sync sprints
    for sprint in sprints:
        await jira.create_sprint(sprint)
    
    print(f"Successfully mirrored to JIRA project: {jira_project.id}")
```

### Example 3: Multi-Provider Support

```python
async def create_project_everywhere(name: str, description: str):
    """Create project in all configured systems"""
    providers = []
    
    # Always include internal
    providers.append(("internal", build_pm_provider(db_session)))
    
    # Add external if configured
    if os.getenv("OPENPROJECT_API_KEY"):
        providers.append(("openproject", OpenProjectProvider(...)))
    
    # Create in all
    results = {}
    for provider_name, provider in providers:
        try:
            project = PMProject(name=name, description=description)
            created = await provider.create_project(project)
            results[provider_name] = created
        except Exception as e:
            print(f"Failed in {provider_name}: {e}")
    
    return results
```

## Migration Guide

### Step 1: Test Provider Connection

```python
# Test script
from pm_providers import build_pm_provider

provider = build_pm_provider(db_session)
if await provider.health_check():
    print("✅ Provider connection successful")
else:
    print("❌ Provider connection failed")
```

### Step 2: Migrate One Handler

Start with simple handler like `_handle_list_tasks`:

```python
# Before
tasks = crud.get_tasks_by_project(self.db_session, project_id)

# After
tasks = await self.pm_provider.list_tasks(project_id=project_id)
```

### Step 3: Migrate CRUD Operations

Update all CRUD calls systematically:

```python
# create_project → provider.create_project
# update_project → provider.update_project
# get_tasks_by_project → provider.list_tasks
# etc.
```

### Step 4: Test Thoroughly

```bash
# Test with internal
PM_PROVIDER=internal python test_provider.py

# Test with OpenProject
PM_PROVIDER=openproject python test_provider.py
```

### Step 5: Deploy

```bash
# In production, just set env var
export PM_PROVIDER=openproject
export OPENPROJECT_URL=https://...
export OPENPROJECT_API_KEY=...

# Restart application
# No code changes needed!
```

## Troubleshooting

### Connection Issues

```python
# Check health
if not await provider.health_check():
    print("Provider connection failed")
    # Check credentials, network, firewall
```

### Field Mapping Issues

```python
# Debug by checking raw_data
task = await provider.get_task("123")
print(task.raw_data)  # See provider-specific fields
```

### Async Issues

```python
# All provider methods are async
# Make sure to await them
tasks = await provider.list_tasks()  # ✅ Correct
tasks = provider.list_tasks()        # ❌ Wrong - returns coroutine
```

## Next Steps

1. **Test OpenProject** - Set up demo instance and test
2. **Implement JIRA** - Complete JIRA provider
3. **Implement ClickUp** - Complete ClickUp provider
4. **Add Sync Engine** - Automatic bi-directional sync
5. **Add Webhooks** - Real-time updates
6. **Optimize** - Batch operations, caching

