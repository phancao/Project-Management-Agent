"""
Sprint Report Tool

Generates comprehensive sprint analysis reports.
"""

import logging
from typing import Any, Optional

from ..base import AnalyticsTool
from ..decorators import mcp_tool, require_sprint

logger = logging.getLogger(__name__)


@mcp_tool(
    name="sprint_report",
    description=(
        "Generate comprehensive sprint report with completion rate, task breakdown, "
        "scope changes, and team member contributions. Use this for sprint retrospectives, "
        "stakeholder updates, and performance analysis."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "sprint_id": {
                "type": "string",
                "description": "Sprint ID (numeric ID, sprint name, or 'current' for active sprint)"
            },
            "project_id": {
                "type": "string",
                "description": "Project ID (format: 'provider_uuid:project_key', optional)"
            }
        },
        "required": ["sprint_id"]
    }
)
class SprintReportTool(AnalyticsTool):
    """
    Sprint report tool.
    
    Generates comprehensive sprint analysis including completion rate,
    task breakdown, scope changes, and team contributions.
    
    Example usage:
    - "Generate Sprint 4 report"
    - "What was completed in last sprint?"
    - "Who contributed the most in Sprint 3?"
    """
    
    @require_sprint
    async def execute(
        self,
        sprint_id: str,
        project_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Generate sprint report.
        
        Args:
            sprint_id: Sprint ID (can include "#" prefix, e.g., "#7" or "7", or "current" for active sprint)
            project_id: Project ID (optional, uses first active provider if not provided)
        
        Returns:
            Sprint report data with:
            - sprint: Sprint information
            - completion_rate: Percentage of work completed
            - completed_tasks: List of completed tasks
            - incomplete_tasks: List of incomplete tasks
            - scope_changes: Tasks added/removed during sprint
            - team_contributions: Breakdown by team member
            - sprint_goals: Sprint goals and their status
        """
        # Normalize sprint_id: strip "#" prefix if present
        if sprint_id and sprint_id.startswith("#"):
            sprint_id = sprint_id[1:]
        
        # Resolve 'current' to actual active sprint ID
        # Note: This is handled by _resolve_sprint_id in PMProviderAnalyticsAdapter,
        # but we can also handle it here for better error messages
        # The analytics manager will call the adapter which will resolve 'current'
        
        # Get sprint report from analytics manager
        result = await self.context.analytics_manager.get_sprint_report(
            sprint_id=sprint_id,
            project_id=project_id
        )
        
        return result


