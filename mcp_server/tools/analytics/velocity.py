"""
Velocity Chart Tool

Generates team velocity chart data for capacity planning.
"""

from typing import Any

from ..base import AnalyticsTool
from ..decorators import mcp_tool, require_project, default_value


@mcp_tool(
    name="velocity_chart",
    description=(
        "Generate team velocity chart showing planned vs. completed work across sprints. "
        "Use this to measure team delivery capacity, predict future sprint capacity, "
        "and identify trends in team performance over time."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Project ID (format: 'provider_uuid:project_key')"
            },
            "num_sprints": {
                "type": "integer",
                "description": "Number of sprints to include (default: 6)",
                "minimum": 1,
                "maximum": 20
            }
        },
        "required": ["project_id"]
    }
)
class VelocityChartTool(AnalyticsTool):
    """
    Velocity chart tool.
    
    Shows planned vs. completed work across multiple sprints to measure
    team delivery capacity and identify trends.
    
    Example usage:
    - "What's our team velocity?"
    - "Show velocity for last 6 sprints"
    - "Are we improving over time?"
    """
    
    @require_project
    @default_value("num_sprints", 6)
    async def execute(
        self,
        project_id: str,
        num_sprints: int = 6
    ) -> dict[str, Any]:
        """
        Generate velocity chart data.
        
        Args:
            project_id: Project ID (format: "provider_uuid:project_key")
            num_sprints: Number of sprints to include (default: 6)
        
        Returns:
            Velocity chart data with:
            - sprints: List of sprint data
              - name: Sprint name
              - planned_points: Planned story points
              - completed_points: Completed story points
              - planned_count: Planned task count
              - completed_count: Completed task count
            - average_velocity: Average velocity across sprints
            - trend: Velocity trend (improving, declining, stable)
        """
        # Get velocity chart from analytics manager
        result = await self.context.analytics_manager.get_velocity_chart(
            project_id=project_id,
            num_sprints=num_sprints
        )
        
        return result


