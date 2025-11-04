# PM Provider Enhancements Design

## Overview
This document outlines the design for additional PM concepts: Epics, Components, Labels, and Status Workflows.

## 1. Models

### 1.1 PMEpic
```python
@dataclass
class PMEpic:
    """Unified epic representation (large work items spanning multiple sprints)"""
    id: Optional[str] = None
    name: str = ""
    description: Optional[str] = None
    project_id: Optional[str] = None
    status: Optional[str] = None  # PMStatus
    priority: Optional[str] = None  # PMPriority
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    owner_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None
```

### 1.2 PMComponent
```python
@dataclass
class PMComponent:
    """Unified component/module representation (technical components)"""
    id: Optional[str] = None
    name: str = ""
    description: Optional[str] = None
    project_id: Optional[str] = None
    lead_id: Optional[str] = None  # Component owner/lead
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None
```

### 1.3 PMLabel
```python
@dataclass
class PMLabel:
    """Unified label/tag representation"""
    id: Optional[str] = None
    name: str = ""
    color: Optional[str] = None  # Hex color code (e.g., "#FF5733")
    description: Optional[str] = None
    project_id: Optional[str] = None  # Project-specific or global
    created_at: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None
```

### 1.4 Status Operations
```python
# Status list is the primary need for UI/UX (Kanban columns)
# Transitions are optional for validation
@dataclass
class PMStatusTransition:
    """Represents a valid status transition (optional, for advanced workflows)"""
    from_status: str
    to_status: str
    name: Optional[str] = None  # User-friendly transition name
    requires_fields: Optional[List[str]] = None  # Fields required for transition
    conditions: Optional[Dict[str, Any]] = None  # Conditions that must be met
```

## 2. BasePMProvider Interface Extensions

### 2.1 Epic Operations
```python
@abstractmethod
async def list_epics(self, project_id: Optional[str] = None) -> List[PMEpic]:
    """List all epics, optionally filtered by project"""
    pass

@abstractmethod
async def get_epic(self, epic_id: str) -> Optional[PMEpic]:
    """Get a single epic by ID"""
    pass

@abstractmethod
async def create_epic(self, epic: PMEpic) -> PMEpic:
    """Create a new epic"""
    pass

@abstractmethod
async def update_epic(self, epic_id: str, updates: Dict[str, Any]) -> PMEpic:
    """Update an existing epic"""
    pass

@abstractmethod
async def delete_epic(self, epic_id: str) -> bool:
    """Delete an epic"""
    pass

async def get_epic_tasks(self, epic_id: str) -> List[PMTask]:
    """Get all tasks associated with an epic (optional)"""
    all_tasks = await self.list_tasks()
    return [t for t in all_tasks if t.epic_id == epic_id]
```

### 2.2 Component Operations
```python
@abstractmethod
async def list_components(self, project_id: Optional[str] = None) -> List[PMComponent]:
    """List all components, optionally filtered by project"""
    pass

@abstractmethod
async def get_component(self, component_id: str) -> Optional[PMComponent]:
    """Get a single component by ID"""
    pass

@abstractmethod
async def create_component(self, component: PMComponent) -> PMComponent:
    """Create a new component"""
    pass

@abstractmethod
async def update_component(self, component_id: str, updates: Dict[str, Any]) -> PMComponent:
    """Update an existing component"""
    pass

@abstractmethod
async def delete_component(self, component_id: str) -> bool:
    """Delete a component"""
    pass

async def get_component_tasks(self, component_id: str) -> List[PMTask]:
    """Get all tasks associated with a component (optional)"""
    all_tasks = await self.list_tasks()
    return [t for t in all_tasks if component_id in (t.component_ids or [])]
```

### 2.3 Label Operations
```python
@abstractmethod
async def list_labels(self, project_id: Optional[str] = None) -> List[PMLabel]:
    """List all labels, optionally filtered by project"""
    pass

@abstractmethod
async def get_label(self, label_id: str) -> Optional[PMLabel]:
    """Get a single label by ID"""
    pass

@abstractmethod
async def create_label(self, label: PMLabel) -> PMLabel:
    """Create a new label"""
    pass

@abstractmethod
async def update_label(self, label_id: str, updates: Dict[str, Any]) -> PMLabel:
    """Update an existing label"""
    pass

@abstractmethod
async def delete_label(self, label_id: str) -> bool:
    """Delete a label"""
    pass

async def get_label_tasks(self, label_id: str) -> List[PMTask]:
    """Get all tasks with a specific label (optional)"""
    all_tasks = await self.list_tasks()
    return [t for t in all_tasks if label_id in (t.label_ids or [])]
```

### 2.4 Status Operations
```python
@abstractmethod
async def list_statuses(self, entity_type: str, project_id: Optional[str] = None) -> List[str]:
    """
    Get list of available statuses for an entity type.
    
    This is primarily used for UI/UX to create status columns in Kanban boards.
    Returns ordered list of status names (e.g., ["todo", "in_progress", "done"]).
    """
    pass

async def get_valid_transitions(self, entity_id: str, entity_type: str) -> List[str]:
    """
    Get valid status transitions for an entity (optional)
    
    Returns list of status names that the entity can transition to.
    Default implementation returns all available statuses.
    """
    return await self.list_statuses(entity_type)

async def transition_status(
    self,
    entity_id: str,
    entity_type: str,
    to_status: str,
    comment: Optional[str] = None
) -> bool:
    """
    Transition an entity to a new status (optional)
    
    Validates that target status exists and optionally validates transition rules.
    """
    # Validate that target status exists
    valid_statuses = await self.list_statuses(entity_type)
    if to_status not in valid_statuses:
        raise ValueError(f"Invalid status '{to_status}'. Valid: {valid_statuses}")
    
    # Optionally validate transition rules
    valid_transitions = await self.get_valid_transitions(entity_id, entity_type)
    if valid_transitions and to_status not in valid_transitions:
        raise ValueError(f"Invalid transition to '{to_status}'. Valid: {valid_transitions}")
    
    # Perform transition
    if entity_type == "task":
        await self.update_task(entity_id, {"status": to_status})
    elif entity_type == "epic":
        await self.update_epic(entity_id, {"status": to_status})
    elif entity_type == "project":
        await self.update_project(entity_id, {"status": to_status})
    else:
        raise ValueError(f"Unsupported entity type: {entity_type}")
    
    return True
```

## 3. Enhanced PMTask Model

```python
@dataclass
class PMTask:
    """Unified task/issue/work package representation"""
    id: Optional[str] = None
    title: str = ""
    description: Optional[str] = None
    status: Optional[str] = None  # PMStatus
    priority: Optional[str] = None  # PMPriority
    project_id: Optional[str] = None
    parent_task_id: Optional[str] = None  # For subtasks
    epic_id: Optional[str] = None  # Associated epic
    assignee_id: Optional[str] = None
    component_ids: Optional[List[str]] = None  # Associated components
    label_ids: Optional[List[str]] = None  # Associated labels
    sprint_id: Optional[str] = None  # Associated sprint
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None
```

## 4. UI/UX Considerations

### 4.1 Status Board View
- Display tasks/epics in columns based on status
- Show valid transitions as action buttons
- Visual indicators for blocked transitions
- Drag-and-drop status transitions

### 4.2 Filtering & Grouping
- Filter by: Epic, Component, Label, Sprint, Assignee
- Group by: Epic, Component, Status, Sprint
- Quick filters for common combinations

### 4.3 Agent/Chat Integration
- "Move task X to In Progress"
- "Show me all tasks in Epic Y"
- "What are the valid next statuses for this task?"
- "Create a new epic for feature Z"
- "Assign component Backend to task ABC"

## 5. Implementation Priority

1. **Phase 1 (Core)**: Models + Base interface definitions
2. **Phase 2 (Basic)**: Epic operations in providers
3. **Phase 3 (Enhanced)**: Components and Labels
4. **Phase 4 (Advanced)**: Status workflows and transitions

## 6. Provider-Specific Notes

### JIRA
- Epics: Use Epic issue type
- Components: Built-in component field
- Labels: Built-in labels field
- Workflows: Use JIRA workflow definitions

### OpenProject
- Epics: Use work packages with type "Epic"
- Components: Use custom fields or work package categories
- Labels: Use work package categories or custom fields
- Workflows: Use status workflow definitions

### ClickUp
- Epics: Use parent tasks or custom fields
- Components: Use custom fields or tags
- Labels: Use tags
- Workflows: Use status lists

