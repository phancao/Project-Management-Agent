"""
Analytics and Reporting Tools

MCP tools for analytics, charts, and reports across all PM providers.
"""

import logging
from typing import Any

from mcp.server import Server
from mcp.types import TextContent

from src.server.pm_handler import PMHandler
from ..config import PMServerConfig

logger = logging.getLogger(__name__)


def register_analytics_tools(
    server: Server,
    pm_handler: PMHandler,
    config: PMServerConfig
) -> int:
    """
    Register analytics-related MCP tools.
    
    Args:
        server: MCP server instance
        pm_handler: PM handler for multi-provider operations
        config: Server configuration
    
    Returns:
        Number of tools registered
    """
    tool_count = 0
    
    # Tool 1: burndown_chart
    @server.call_tool()
    async def burndown_chart(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Generate burndown chart data for a sprint.
        
        Args:
            sprint_id (required): Sprint ID
        
        Returns:
            Burndown chart data
        """
        try:
            sprint_id = arguments.get("sprint_id")
            if not sprint_id:
                return [TextContent(
                    type="text",
                    text="Error: sprint_id is required"
                )]
            
            logger.info(f"burndown_chart called: sprint_id={sprint_id}")
            
            # Get burndown data from PM handler
            data = pm_handler.get_burndown_chart(sprint_id)
            
            if not data:
                return [TextContent(
                    type="text",
                    text=f"No burndown data available for sprint {sprint_id}."
                )]
            
            # Format output
            output_lines = [f"# Burndown Chart - Sprint {sprint_id}\n\n"]
            output_lines.append("Date | Remaining Work\n")
            output_lines.append("-----|---------------\n")
            
            for point in data.get("points", []):
                output_lines.append(
                    f"{point.get('date')} | {point.get('remaining')}\n"
                )
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in burndown_chart: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error generating burndown chart: {str(e)}"
            )]
    
    tool_count += 1
    
    # Tool 2: velocity_chart
    @server.call_tool()
    async def velocity_chart(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Calculate team velocity over recent sprints.
        
        Args:
            project_id (required): Project ID
            sprint_count (optional): Number of sprints to analyze (default: 5)
        
        Returns:
            Velocity chart data
        """
        try:
            project_id = arguments.get("project_id")
            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required"
                )]
            
            sprint_count = arguments.get("sprint_count", 5)
            
            logger.info(
                f"velocity_chart called: project_id={project_id}, "
                f"sprint_count={sprint_count}"
            )
            
            # Get velocity data from PM handler
            data = pm_handler.get_velocity_chart(project_id, sprint_count)
            
            if not data:
                return [TextContent(
                    type="text",
                    text=f"No velocity data available for project {project_id}."
                )]
            
            # Format output
            output_lines = [f"# Velocity Chart - Project {project_id}\n\n"]
            output_lines.append("Sprint | Completed Points\n")
            output_lines.append("-------|------------------\n")
            
            for sprint in data.get("sprints", []):
                output_lines.append(
                    f"{sprint.get('name')} | {sprint.get('completed_points')}\n"
                )
            
            avg_velocity = data.get("average_velocity", 0)
            output_lines.append(f"\n**Average Velocity:** {avg_velocity} points/sprint\n")
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in velocity_chart: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error generating velocity chart: {str(e)}"
            )]
    
    tool_count += 1
    
    # TODO: Add more analytics tools:
    # - gantt_chart
    # - task_distribution
    # - sprint_report
    # - epic_report
    # - team_performance
    # - time_tracking_report
    # - resource_utilization
    # - project_health
    
    logger.info(f"Registered {tool_count} analytics tools")
    return tool_count

