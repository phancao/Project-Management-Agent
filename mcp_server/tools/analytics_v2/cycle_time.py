"""
Cycle Time Analysis Tool

Analyzes how long work items take from start to completion.
"""

from typing import Any, Optional

from ..base import AnalyticsTool
from ..decorators import mcp_tool, require_project, default_value


@mcp_tool(
    name="cycle_time_chart",
    description=(
        "Analyze cycle time - how long work items take from start to completion. "
        "Use this to understand delivery predictability, identify outliers that need investigation, "
        "and set realistic expectations with stakeholders. Lower and more consistent cycle times "
        "indicate better flow and predictability."
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
                "description": "Optional sprint ID to filter by"
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
class CycleTimeChartTool(AnalyticsTool):
    """
    Cycle time analysis tool.
    
    Measures how long work items take from start to completion.
    Provides percentile analysis for realistic delivery commitments.
    
    Key percentiles:
    - 50th (median): Half of items complete faster than this
    - 85th: Use this for realistic stakeholder commitments
    - 95th: Items above this are outliers - investigate blockers
    
    Example usage:
    - "What's our average cycle time?"
    - "How predictable is our delivery?"
    - "Are there any outliers taking too long?"
    """
    
    @require_project
    @default_value("days", 30)
    async def execute(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        days: int = 30
    ) -> dict[str, Any]:
        """
        Generate cycle time analysis.
        
        Args:
            project_id: Project ID (format: "provider_uuid:project_key")
            sprint_id: Optional sprint ID to filter by
            days: Number of days to analyze (default: 30)
        
        Returns:
            Cycle time data with:
            - average: Average cycle time in days
            - median: Median (50th percentile)
            - p85: 85th percentile (realistic commitment)
            - p95: 95th percentile (outlier threshold)
            - items: List of completed items with cycle times
            - outliers: Items exceeding 95th percentile
            - recommendations: Improvement suggestions
        """
        result = await self.context.analytics_manager.get_cycle_time_chart(
            project_id=project_id,
            sprint_id=sprint_id,
            days=days
        )
        
        return result


