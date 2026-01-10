"""
Cumulative Flow Diagram (CFD) Tool

Generates CFD data to visualize work flow and identify bottlenecks.
"""

from typing import Any, Optional

from ..base import AnalyticsTool
from ..decorators import mcp_tool, require_project, default_value


@mcp_tool(
    name="cfd_chart",
    description=(
        "Generate Cumulative Flow Diagram (CFD) showing work distribution across statuses over time. "
        "Use this to visualize workflow, identify bottlenecks (wide bands indicate WIP buildup), "
        "monitor flow efficiency, and spot when work is piling up in certain stages."
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
                "description": "Number of days to include (default: 30)",
                "minimum": 7,
                "maximum": 90
            }
        },
        "required": ["project_id"]
    }
)
class CFDChartTool(AnalyticsTool):
    """
    Cumulative Flow Diagram tool.
    
    Shows cumulative count of work items in each status over time.
    Each colored band represents a workflow stage, and the width of 
    the band shows how many items are in that stage.
    
    Example usage:
    - "Show me the CFD for this project"
    - "Are there any bottlenecks in our workflow?"
    - "What does our work flow look like?"
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
        Generate CFD data.
        
        Args:
            project_id: Project ID (format: "provider_uuid:project_key")
            sprint_id: Optional sprint ID to filter by
            days: Number of days to include (default: 30)
        
        Returns:
            CFD data with:
            - dates: List of dates
            - statuses: Dict of status -> count per date
            - wip_analysis: WIP analysis and bottleneck detection
            - recommendations: Flow improvement recommendations
        """
        result = await self.context.analytics_manager.get_cfd_chart(
            project_id=project_id,
            sprint_id=sprint_id,
            days=days
        )
        
        return result


