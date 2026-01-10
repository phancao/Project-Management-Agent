"""
Project Health Tool

Generates project health and summary reports.
"""

from typing import Any

from ..base import AnalyticsTool
from ..decorators import mcp_tool, require_project


@mcp_tool(
    name="project_health",
    description=(
        "Generate project health report showing overall status, task distribution, "
        "overdue tasks, upcoming deadlines, and team workload. Use this for project "
        "health checks, status updates, and identifying bottlenecks."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Project ID (format: 'provider_uuid:project_key')"
            }
        },
        "required": ["project_id"]
    }
)
class ProjectHealthTool(AnalyticsTool):
    """
    Project health tool.
    
    Generates overall project health report with task distribution,
    overdue tasks, deadlines, and team workload.
    
    Example usage:
    - "What's the project health?"
    - "Show me project summary"
    - "How many overdue tasks?"
    """
    
    @require_project
    async def execute(
        self,
        project_id: str
    ) -> dict[str, Any]:
        """
        Generate project health report.
        
        Args:
            project_id: Project ID (format: "provider_uuid:project_key")
        
        Returns:
            Project health data with:
            - total_tasks: Total number of tasks
            - tasks_by_status: Breakdown by status
            - completion_percentage: Overall completion rate
            - overdue_tasks: Number of overdue tasks
            - upcoming_deadlines: Tasks with upcoming deadlines
            - team_workload: Workload distribution across team
            - blockers: Blocked tasks
        """
        # Get project summary from analytics manager
        result = await self.context.analytics_manager.get_project_summary(
            project_id=project_id
        )
        
        return result


