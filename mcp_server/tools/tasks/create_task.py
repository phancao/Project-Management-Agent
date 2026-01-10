"""Create Task Tool"""
from typing import Any
from ..base import WriteTool
from ..decorators import mcp_tool, require_project

@mcp_tool(
    name="create_task",
    description="Create a new task in a project. Supports advanced fields: sprint, story points, priority, due date, parent_task, and type.",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project ID"},
            "title": {"type": "string", "description": "Task title"},
            "description": {"type": "string", "description": "Task description"},
            "assignee_id": {"type": "string", "description": "Assignee user ID"},
            "priority": {"type": "string", "description": "Priority"},
            "due_date": {"type": "string", "description": "Due date"},
            "sprint_id": {"type": "string", "description": "Sprint ID (optional)"},
            "story_points": {"type": "number", "description": "Story points (optional)"},
            "task_type": {"type": "string", "description": "Task type (bug, feature, etc.)"},
            "parent_id": {"type": "string", "description": "Parent task ID for subtasks"}
        },
        "required": ["project_id", "title"]
    }
)
class CreateTaskTool(WriteTool):
    # Removed @require_project as pm_service handles validation
    async def execute(
        self, 
        project_id: str, 
        title: str, 
        **kwargs
    ) -> dict[str, Any]:
        return await self.context.pm_service.create_task(
            project_id=project_id, 
            title=title, 
            **kwargs
        )

