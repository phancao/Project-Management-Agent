"""
Capacity Planning Tool

Generates resource capacity vs demand chart.
"""

from typing import Any

from ..base import AnalyticsTool
from ..decorators import mcp_tool, require_project, default_value


@mcp_tool(
    name="capacity_chart",
    description=(
        "Generate capacity planning chart comparing resource availability against "
        "scheduled work demand. Use this to identify bottlenecks, visualize team workload, "
        "and balance resource allocation across projects for the upcoming weeks."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Project ID (format: 'provider_uuid:project_key')"
            },
            "weeks": {
                "type": "integer",
                "description": "Number of weeks to project (default: 12)",
                "minimum": 1,
                "maximum": 52
            }
        },
        "required": ["project_id"]
    }
)
class CapacityPlanningTool(AnalyticsTool):
    """
    Capacity planning tool.
    
    Shows total team capacity vs demand (allocated hours from tasks with due dates).
    Breakdown by team member shows individual allocation.
    
    Example usage:
    - "Show me capacity planning for the next 12 weeks"
    - "Are we over-allocated in the upcoming sprint?"
    - "Who has free capacity next week?"
    """
    
    @require_project
    @default_value("weeks", 12)
    async def execute(
        self,
        project_id: str,
        weeks: int = 12
    ) -> dict[str, Any]:
        """
        Generate capacity chart.
        
        Args:
            project_id: Project ID
            weeks: Number of weeks to project
            
        Returns:
            Chart data with capacity line and stacked demand bars
        """
        result = await self.context.analytics_manager.get_capacity_chart(
            project_id=project_id,
            weeks=weeks
        )
        return result
