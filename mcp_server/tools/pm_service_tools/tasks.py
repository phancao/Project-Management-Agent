# PM Service - Tasks Tools
"""
Task tools using PM Service client.
"""

from typing import Any, Optional

from ..pm_service_base import PMServiceReadTool, PMServiceWriteTool
from ..decorators import mcp_tool


@mcp_tool(
    name="list_tasks",
    description=(
        "List tasks from PM providers. "
        "Supports filtering by project, sprint, assignee, and status."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Filter by project ID (format: provider_id:project_key)"
            },
            "sprint_id": {
                "type": "string",
                "description": "Filter by sprint ID"
            },
            "assignee_id": {
                "type": "string",
                "description": "Filter by assignee user ID"
            },
            "status": {
                "type": "string",
                "description": "Filter by task status"
            }
        }
    }
)
class ListTasksTool(PMServiceReadTool):
    """List tasks with filters."""
    
    async def execute(
        self,
        project_id: Optional[str] = None,
        sprint_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> dict[str, Any]:
        """List tasks using PM Service."""
        async with self.client as client:
            result = await client.list_tasks(
                project_id=project_id,
                sprint_id=sprint_id,
                assignee_id=assignee_id,
                status=status
            )
        
        return {
            "tasks": result.get("items", []),
            "total": result.get("total", 0)
        }


@mcp_tool(
    name="get_task",
    description="Get detailed information about a specific task.",
    input_schema={
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "Task ID (format: provider_id:task_id)"
            }
        },
        "required": ["task_id"]
    }
)
class GetTaskTool(PMServiceReadTool):
    """Get task details."""
    
    async def execute(self, task_id: str) -> dict[str, Any]:
        """Get task using PM Service."""
        async with self.client as client:
            return await client.get_task(task_id)


@mcp_tool(
    name="create_task",
    description="Create a new task in a project.",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Project ID (format: provider_id:project_key)"
            },
            "title": {
                "type": "string",
                "description": "Task title"
            },
            "description": {
                "type": "string",
                "description": "Task description"
            },
            "assignee_id": {
                "type": "string",
                "description": "Assignee user ID"
            },
            "sprint_id": {
                "type": "string",
                "description": "Sprint ID to add task to"
            },
            "story_points": {
                "type": "number",
                "description": "Story points estimate"
            },
            "priority": {
                "type": "string",
                "description": "Task priority"
            },
            "task_type": {
                "type": "string",
                "description": "Task type (e.g., Task, Bug, Story)"
            }
        },
        "required": ["project_id", "title"]
    }
)
class CreateTaskTool(PMServiceWriteTool):
    """Create a new task."""
    
    async def execute(
        self,
        project_id: str,
        title: str,
        description: Optional[str] = None,
        assignee_id: Optional[str] = None,
        sprint_id: Optional[str] = None,
        story_points: Optional[float] = None,
        priority: Optional[str] = None,
        task_type: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Create task using PM Service."""
        async with self.client as client:
            return await client.create_task(
                project_id=project_id,
                title=title,
                description=description,
                assignee_id=assignee_id,
                sprint_id=sprint_id,
                story_points=story_points,
                priority=priority,
                task_type=task_type,
                parent_id=parent_id
            )


@mcp_tool(
    name="update_task",
    description="Update an existing task.",
    input_schema={
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "Task ID (format: provider_id:task_id)"
            },
            "title": {
                "type": "string",
                "description": "New task title"
            },
            "description": {
                "type": "string",
                "description": "New task description"
            },
            "status": {
                "type": "string",
                "description": "New task status"
            },
            "assignee_id": {
                "type": "string",
                "description": "New assignee user ID"
            },
            "sprint_id": {
                "type": "string",
                "description": "New sprint ID"
            },
            "story_points": {
                "type": "number",
                "description": "New story points"
            },
            "priority": {
                "type": "string",
                "description": "New priority"
            },
            "progress": {
                "type": "integer",
                "description": "Progress percentage (0-100)"
            }
        },
        "required": ["task_id"]
    }
)
class UpdateTaskTool(PMServiceWriteTool):
    """Update an existing task."""
    
    async def execute(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        assignee_id: Optional[str] = None,
        sprint_id: Optional[str] = None,
        story_points: Optional[float] = None,
        priority: Optional[str] = None,
        progress: Optional[int] = None
    ) -> dict[str, Any]:
        """Update task using PM Service."""
        async with self.client as client:
            return await client.update_task(
                task_id=task_id,
                title=title,
                description=description,
                status=status,
                assignee_id=assignee_id,
                sprint_id=sprint_id,
                story_points=story_points,
                priority=priority,
                progress=progress
            )
