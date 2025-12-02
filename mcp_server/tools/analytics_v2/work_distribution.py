"""
Work Distribution Analysis Tool

Analyzes how work is distributed across different dimensions.
"""

from typing import Any, Optional

from ..base import AnalyticsTool
from ..decorators import mcp_tool, require_project, default_value


@mcp_tool(
    name="work_distribution_chart",
    description=(
        "Analyze work distribution across different dimensions (assignee, status, priority, type). "
        "Use this to identify workload imbalances, ensure fair distribution across team members, "
        "check if high-priority work is being addressed, and understand the mix of work types."
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
            "group_by": {
                "type": "string",
                "description": "Dimension to group by: 'assignee', 'status', 'priority', or 'type'",
                "enum": ["assignee", "status", "priority", "type"]
            }
        },
        "required": ["project_id"]
    }
)
class WorkDistributionChartTool(AnalyticsTool):
    """
    Work distribution analysis tool.
    
    Shows how work is spread across different dimensions:
    - By Assignee: Identify overloaded or underutilized team members
    - By Status: See workflow stage distribution
    - By Priority: Check priority alignment with business goals
    - By Type: Track ratio of stories, bugs, tasks, features
    
    Example usage:
    - "How is work distributed across the team?"
    - "Who has the most tasks?"
    - "What's our bug vs feature ratio?"
    - "Is anyone overloaded?"
    """
    
    @require_project
    @default_value("group_by", "assignee")
    async def execute(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        group_by: str = "assignee"
    ) -> dict[str, Any]:
        """
        Generate work distribution analysis.
        
        Args:
            project_id: Project ID (format: "provider_uuid:project_key")
            sprint_id: Optional sprint ID to filter by
            group_by: Dimension to group by (assignee, status, priority, type)
        
        Returns:
            Work distribution data with:
            - groups: Dict of group_name -> task details
            - total: Total task count
            - distribution: Percentage distribution
            - balance_assessment: Workload balance analysis
            - recommendations: Load balancing suggestions
        """
        result = await self.context.analytics_manager.get_work_distribution_chart(
            project_id=project_id,
            sprint_id=sprint_id,
            group_by=group_by
        )
        
        return result


