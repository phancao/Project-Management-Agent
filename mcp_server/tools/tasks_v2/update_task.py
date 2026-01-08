"""Update Task Tool"""
from typing import Any
from ..base import WriteTool
from ..decorators import mcp_tool, require_task

@mcp_tool(
    name="update_task",
    description="Update an existing task. Supports reassigning, moving sprints, changing status, priority, due date, and hours.",
    input_schema={
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "Task ID"},
            "title": {"type": "string", "description": "New title"},
            "description": {"type": "string", "description": "New description"},
            "status": {"type": "string", "description": "New status"},
            "priority": {"type": "string", "description": "New priority"},
            "assignee_id": {"type": "string", "description": "New assignee ID"},
            "sprint_id": {"type": "string", "description": "New sprint ID"},
            "due_date": {"type": "string", "description": "New due date (YYYY-MM-DD)"},
            "estimated_hours": {"type": "number", "description": "Estimated hours"},
            "remaining_hours": {"type": "number", "description": "Remaining hours"}
        },
        "required": ["task_id"]
    }
)
class UpdateTaskTool(WriteTool):
    # Removed @require_task as pm_service handles parsing and validation
    async def execute(self, task_id: str, **kwargs) -> dict[str, Any]:
        return await self.context.pm_service.update_task(task_id, **kwargs)

