"""
Burndown Chart Tool

Generates burndown chart data for sprint progress tracking.
"""

from typing import Any, Optional

from ..base import AnalyticsTool
from ..decorators import mcp_tool, require_project


@mcp_tool(
    name="burndown_chart",
    description=(
        "Generate burndown chart data for a sprint to track progress. "
        "Shows how much work remains in a sprint over time, comparing actual progress "
        "against an ideal burndown line. Use this to check if a sprint is on track, "
        "identify if the team is ahead or behind schedule, and forecast sprint completion."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Project ID (format: 'provider_uuid:project_key')"
            },
            "sprint_id": {
                "type": "string",
                "description": "Sprint ID (uses current/active sprint if not provided)"
            },
            "scope_type": {
                "type": "string",
                "enum": ["story_points", "tasks", "hours"],
                "description": "What to measure (default: story_points)"
            }
        },
        "required": ["project_id"]
    }
)
class BurndownChartTool(AnalyticsTool):
    """
    Burndown chart tool.
    
    Shows how much work remains in a sprint over time, comparing actual progress
    against an ideal burndown line.
    
    Example usage:
    - "Show me the burndown for Sprint 4"
    - "Is our current sprint on track?"
    - "How much work is remaining in this sprint?"
    """
    
    @require_project
    async def execute(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        scope_type: str = "story_points"
    ) -> dict[str, Any]:
        """
        Generate burndown chart data.
        
        Args:
            project_id: Project ID (format: "provider_uuid:project_key")
            sprint_id: Sprint ID (uses current/active sprint if not provided)
            scope_type: What to measure - "story_points", "tasks", or "hours"
        
        Returns:
            Burndown chart data with:
            - sprint_name: Sprint name
            - start_date, end_date: Sprint dates
            - total_scope: Total work in sprint
            - completed: Work completed
            - remaining: Work remaining
            - completion_percentage: Percentage complete
            - is_on_track: Whether sprint is on track
            - daily_data: Daily burndown data points
        """
        # Get burndown chart from analytics manager
        result = await self.context.analytics_manager.get_burndown_chart(
            project_id=project_id,
            sprint_id=sprint_id,
            scope_type=scope_type
        )
        
        return result


