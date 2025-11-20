# Task Update Fields Status

This document lists all PMTask fields and their update support status across providers.

## PMTask Model Fields

| Field | Type | JIRA | OpenProject | Notes |
|-------|------|------|-------------|-------|
| **id** | `str` | ❌ Read-only | ❌ Read-only | Set on creation, cannot be updated |
| **title** | `str` | ✅ Supported | ✅ Supported | Maps to `summary` (JIRA) / `subject` (OpenProject) |
| **description** | `str` | ✅ Supported | ✅ Supported | ADF format (JIRA) / plain text (OpenProject) |
| **status** | `str` | ⚠️ Not Implemented | ✅ Supported | JIRA requires transitions API |
| **priority** | `str` | ❌ Not Implemented | ✅ Supported | OpenProject has priority lookup by name/ID |
| **project_id** | `str` | ❌ Read-only | ❌ Read-only | Set on creation, cannot be changed |
| **parent_task_id** | `str` | ❌ Not Implemented | ❌ Not Implemented | For subtasks |
| **epic_id** | `str` | ✅ Supported | ✅ Supported | Via parent field (JIRA) / parent link (OpenProject) |
| **assignee_id** | `str` | ✅ Supported | ✅ Supported | Can be set to `None` to unassign |
| **component_ids** | `List[str]` | ❌ Removed | ❌ Removed | Components removed from base interface |
| **label_ids** | `List[str]` | ❌ Not Implemented | ❌ Not Implemented | Labels not yet supported in updates |
| **sprint_id** | `str` | ✅ Supported | ✅ Supported | Via Agile API (JIRA) / version link (OpenProject) |
| **estimated_hours** | `float` | ❌ Not Implemented | ✅ Supported | OpenProject converts to ISO 8601 duration |
| **actual_hours** | `float` | ❌ Not Implemented | ❌ Not Implemented | Time tracking |
| **start_date** | `date` | ❌ Not Implemented | ❌ Not Implemented | Task start date |
| **due_date** | `date` | ❌ Not Implemented | ❌ Not Implemented | Task due date |
| **created_at** | `datetime` | ❌ Read-only | ❌ Read-only | Set on creation |
| **updated_at** | `datetime` | ❌ Read-only | ❌ Read-only | Auto-updated by provider |
| **completed_at** | `datetime` | ❌ Read-only | ❌ Read-only | Set when task is completed |

## Implementation Details

### JIRA Provider (`pm_providers/jira.py`)

**Currently Supported:**
- ✅ `title` / `summary` - Maps to JIRA `summary` field
- ✅ `description` - Converts to ADF format
- ✅ `assignee_id` - Maps to `assignee.accountId`
- ✅ `epic_id` - Maps to `parent` field (if parent is epic)
- ✅ `sprint_id` - Uses Agile API (`POST /rest/agile/1.0/sprint/{id}/issue`)

**Not Implemented:**
- ❌ `status` - Requires transitions API (logged as warning)
- ❌ `priority` - Not implemented
- ❌ `parent_task_id` - Not implemented
- ❌ `label_ids` - Not implemented
- ❌ `estimated_hours` - Not implemented (JIRA uses `timeoriginalestimate` in seconds)
- ❌ `actual_hours` - Not implemented
- ❌ `start_date` - Not implemented
- ❌ `due_date` - Not implemented (JIRA has `duedate` field)

### OpenProject Provider (`pm_providers/openproject.py`)

**Currently Supported:**
- ✅ `title` / `subject` - Maps to OpenProject `subject` field
- ✅ `description` - Maps to `description.raw` (plain text)
- ✅ `status` - Resolves status by ID or name, maps to `_links.status.href`
- ✅ `priority` - Resolves priority by ID or name with fuzzy matching, maps to `_links.priority.href`
- ✅ `assignee_id` - Maps to `_links.assignee.href`
- ✅ `epic_id` - Maps to `_links.parent.href` (if parent is epic)
- ✅ `sprint_id` - Maps to `_links.version.href`
- ✅ `estimated_hours` - Converts to ISO 8601 duration format (`PT2H30M`)

**Not Implemented:**
- ❌ `parent_task_id` - Not implemented
- ❌ `label_ids` - Not implemented
- ❌ `actual_hours` - Not implemented
- ❌ `start_date` - Not implemented
- ❌ `due_date` - Not implemented

## Missing Implementations

### High Priority (Common Use Cases)

1. **Status Updates (JIRA)**
   - Requires JIRA transitions API
   - Endpoint: `POST /rest/api/3/issue/{issueIdOrKey}/transitions`
   - Need to get available transitions and execute them

2. **Priority Updates (JIRA)**
   - JIRA has priority field
   - Field: `priority` with `id` or `name`
   - Should support priority name mapping

3. **Due Date (Both)**
   - JIRA: `duedate` field (date format: `YYYY-MM-DD`)
   - OpenProject: `dueDate` field (ISO 8601 date)
   - Common use case for task management

4. **Start Date (Both)**
   - JIRA: `startdate` field (date format: `YYYY-MM-DD`)
   - OpenProject: `startDate` field (ISO 8601 date)
   - Useful for scheduling

5. **Estimated Hours (JIRA)**
   - JIRA: `timeoriginalestimate` field (in seconds)
   - Need to convert hours to seconds
   - Common for time tracking

### Medium Priority

6. **Parent Task ID (Both)**
   - For creating subtasks
   - JIRA: `parent` field with issue key
   - OpenProject: `_links.parent.href` with work package ID

7. **Label IDs (Both)**
   - JIRA: `labels` field (array of strings)
   - OpenProject: `_links.categories` (array of category links)
   - Need to handle multiple labels

8. **Actual Hours (Both)**
   - Time tracking/spent time
   - JIRA: `timespent` field (in seconds)
   - OpenProject: `spentTime` field (ISO 8601 duration)

## Recommended Implementation Order

1. **Priority (JIRA)** - Simple field update
2. **Due Date (Both)** - Common use case
3. **Start Date (Both)** - Scheduling support
4. **Estimated Hours (JIRA)** - Time tracking
5. **Status (JIRA)** - Requires transitions API research
6. **Parent Task ID (Both)** - Subtask support
7. **Label IDs (Both)** - Tagging support
8. **Actual Hours (Both)** - Time tracking completion

