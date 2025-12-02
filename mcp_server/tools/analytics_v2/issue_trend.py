"""
Issue Trend Analysis Tool

Tracks how issues are created and resolved over time.
"""

from typing import Any

from ..base import AnalyticsTool
from ..decorators import mcp_tool, require_project, default_value


@mcp_tool(
    name="issue_trend_chart",
    description=(
        "Analyze issue trends - how issues are created and resolved over time. "
        "Use this to monitor backlog health, identify capacity issues, track team productivity, "
        "and forecast future backlog size. A growing backlog (created > resolved) indicates "
        "capacity issues that need attention."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Project ID (format: 'provider_uuid:project_key')"
            },
            "days": {
                "type": "integer",
                "description": "Number of days to analyze (default: 30)",
                "minimum": 7,
                "maximum": 90
            }
        },
        "required": ["project_id"]
    }
)
class IssueTrendChartTool(AnalyticsTool):
    """
    Issue trend analysis tool.
    
    Tracks how issues are created and resolved over time to understand
    backlog health and team capacity.
    
    Key insights:
    - Resolved > Created: Backlog shrinking (healthy)
    - Created > Resolved: Backlog growing (capacity issue)
    - Equal rates: Backlog stable (neutral)
    
    Example usage:
    - "Is our backlog growing or shrinking?"
    - "Do we have capacity issues?"
    - "What's our resolution rate?"
    - "How many issues are we creating vs resolving?"
    """
    
    @require_project
    @default_value("days", 30)
    async def execute(
        self,
        project_id: str,
        days: int = 30
    ) -> dict[str, Any]:
        """
        Generate issue trend analysis.
        
        Args:
            project_id: Project ID (format: "provider_uuid:project_key")
            days: Number of days to analyze (default: 30)
        
        Returns:
            Issue trend data with:
            - dates: List of dates
            - created: Issues created per day
            - resolved: Issues resolved per day
            - net_change: Net change per day (created - resolved)
            - cumulative: Cumulative backlog size over time
            - summary: Period summary statistics
            - backlog_health: Health assessment (growing/shrinking/stable)
            - recommendations: Capacity recommendations
        """
        result = await self.context.analytics_manager.get_issue_trend_chart(
            project_id=project_id,
            days=days
        )
        
        return result


