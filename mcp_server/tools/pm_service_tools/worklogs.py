# PM Service - Worklog Tools
"""
Worklog tools using PM Service client.
"""

from typing import Any, Optional

from ..pm_service_base import PMServiceReadTool
from ..decorators import mcp_tool


@mcp_tool(
    name="list_worklogs",
    description=(
        "List worklogs (time entries) from PM providers. "
        "Can filter by user, project, or task. "
        "Each entry includes: id, user_id, task_id, date, hours, activity_type (e.g., 'Development', 'Management')."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "Filter by user ID (e.g., 'openproject_v13:123')"
            },
            "project_id": {
                "type": "string",
                "description": "Filter by project ID"
            },
            "task_id": {
                "type": "string",
                "description": "Filter by task/work package ID"
            },
            "start_date": {
                "type": "string",
                "description": "Filter by start date (inclusive, YYYY-MM-DD)"
            },
            "end_date": {
                "type": "string",
                "description": "Filter by end date (inclusive, YYYY-MM-DD)"
            }
        }
    }
)
class ListWorklogsTool(PMServiceReadTool):
    """List worklogs."""
    
    async def execute(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict[str, Any]:
        """
        List worklogs using PM Service.
        """
        try:
            async with self.client as client:
                result = await client.list_time_entries(
                    user_id=user_id,
                    project_id=project_id,
                    task_id=task_id,
                    start_date=start_date,
                    end_date=end_date
                )
            
            all_entries = result.get("items", [])
            total = result.get("total", len(all_entries))
            
            response = {
                "worklogs": all_entries,
                "total": total
            }
            
            if total == 0:
                 response["message"] = "No worklogs found matching the criteria."

            return response

        except PermissionError as e:
            raise PermissionError(
                f"Permission denied when listing worklogs: {str(e)}. "
                "Try filtering by a specific project you have access to."
            ) from e
        except Exception as e:
            # Wrap other errors
            error_msg = str(e)
            if "403" in error_msg or "Forbidden" in error_msg:
                 raise PermissionError(
                    f"Permission denied: {error_msg}. "
                    "Accessing global worklogs may require higher privileges. "
                    "Try specifying a project_id."
                ) from e
            raise
