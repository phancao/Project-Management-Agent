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
    config: PMServerConfig,
    tool_names: list[str] | None = None
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
            
            # Burndown chart requires project_id to determine which provider to use
            # Return a message indicating this needs project_id
            return [TextContent(
                type="text",
                text=f"Burndown chart requires both project_id and sprint_id. "
                     f"Please use the web interface or API endpoint "
                     f"/api/analytics/projects/<project_id>/burndown?sprint_id={sprint_id} "
                     f"to get burndown data for sprint {sprint_id}."
            )]
            
        except Exception as e:
            logger.error(f"Error in burndown_chart: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error generating burndown chart: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("burndown_chart")
    
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
            
            # Velocity chart is available via analytics API endpoint
            return [TextContent(
                type="text",
                text=f"Velocity chart is available via the analytics API endpoint. "
                     f"Please use the web interface or API endpoint "
                     f"/api/analytics/projects/{project_id}/velocity?sprint_count={sprint_count} "
                     f"to get velocity data for {sprint_count} sprints."
            )]
            
        except Exception as e:
            logger.error(f"Error in velocity_chart: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error generating velocity chart: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("velocity_chart")
    
    # Tool 3: sprint_report
    @server.call_tool()
    async def sprint_report(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Generate comprehensive sprint report.
        
        Args:
            sprint_id (required): Sprint ID
            project_id (required): Project ID
        
        Returns:
            Sprint report with metrics and insights
        """
        try:
            sprint_id = arguments.get("sprint_id")
            if not sprint_id:
                return [TextContent(
                    type="text",
                    text="Error: sprint_id is required"
                )]
            
            logger.info(f"sprint_report called: sprint_id={sprint_id}")
            
            # Sprint report requires project_id to determine which provider to use
            project_id = arguments.get("project_id")
            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required for sprint_report. "
                         "Please provide both project_id and sprint_id."
                )]
            
            # Return a message directing users to the API
            return [TextContent(
                type="text",
                text=f"Sprint report is available via the analytics API endpoint. "
                     f"Please use the web interface or API endpoint "
                     f"/api/analytics/projects/{project_id}/sprint-report?sprint_id={sprint_id} "
                     f"to get the sprint report."
            )]
            
        except Exception as e:
            logger.error(f"Error in sprint_report: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error generating sprint report: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("sprint_report")
    
    # Tool 4: project_health
    @server.call_tool()
    async def project_health(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Analyze project health indicators.
        
        Args:
            project_id (required): Project ID
        
        Returns:
            Project health metrics and status
        """
        try:
            project_id = arguments.get("project_id")
            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required"
                )]
            
            logger.info(f"project_health called: project_id={project_id}")
            
            # Get project health via analytics service
            # Note: project_health is not yet implemented in AnalyticsService
            # Return a message indicating this feature is not available
            return [TextContent(
                type="text",
                text=f"Project health analysis is not yet implemented. "
                     f"Please use other analytics tools like velocity_chart or sprint_report for project {project_id}."
            )]
            
            
        except Exception as e:
            logger.error(f"Error in project_health: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error analyzing project health: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("project_health")
    
    # Tool 5: task_distribution
    @server.call_tool()
    async def task_distribution(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Analyze task distribution across team members.
        
        Args:
            project_id (required): Project ID
        
        Returns:
            Task distribution analysis
        """
        try:
            project_id = arguments.get("project_id")
            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required"
                )]
            
            logger.info(f"task_distribution called: project_id={project_id}")
            
            # Task distribution is available via analytics API endpoint
            return [TextContent(
                type="text",
                text=f"Task distribution is available via the analytics API endpoint. "
                     f"Please use the web interface or API endpoint "
                     f"/api/analytics/projects/{project_id}/work-distribution "
                     f"to get task distribution data."
            )]
            
        except Exception as e:
            logger.error(f"Error in task_distribution: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error analyzing task distribution: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("task_distribution")
    
    # Tool 6: team_performance
    @server.call_tool()
    async def team_performance(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Analyze team performance metrics.
        
        Args:
            project_id (required): Project ID
            time_period (optional): Time period in days (default: 30)
        
        Returns:
            Team performance analysis
        """
        try:
            project_id = arguments.get("project_id")
            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required"
                )]
            
            time_period = arguments.get("time_period", 30)
            
            logger.info(
                f"team_performance called: project_id={project_id}, "
                f"time_period={time_period}"
            )
            
            # Team performance is not yet implemented
            return [TextContent(
                type="text",
                text=f"Team performance analysis is not yet implemented. "
                     f"Please use other analytics tools like velocity_chart or sprint_report for project {project_id}."
            )]
            
        except Exception as e:
            logger.error(f"Error in team_performance: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error analyzing team performance: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("team_performance")
    
    # Tool 7: gantt_chart
    @server.call_tool()
    async def gantt_chart(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Generate Gantt chart data for project timeline.
        
        Args:
            project_id (required): Project ID
            start_date (optional): Start date filter (YYYY-MM-DD)
            end_date (optional): End date filter (YYYY-MM-DD)
        
        Returns:
            Gantt chart data with task timelines
        """
        try:
            project_id = arguments.get("project_id")
            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required"
                )]
            
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            
            logger.info(
                f"gantt_chart called: project_id={project_id}, "
                f"start_date={start_date}, end_date={end_date}"
            )
            
            # Gantt chart is not yet implemented
            return [TextContent(
                type="text",
                text=f"Gantt chart is not yet implemented. "
                     f"Please use other analytics tools like velocity_chart or sprint_report for project {project_id}."
            )]
            
        except Exception as e:
            logger.error(f"Error in gantt_chart: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error generating Gantt chart: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("gantt_chart")
    
    # Tool 8: epic_report
    @server.call_tool()
    async def epic_report(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Generate comprehensive epic report.
        
        Args:
            epic_id (required): Epic ID
        
        Returns:
            Epic report with progress and metrics
        """
        try:
            epic_id = arguments.get("epic_id")
            if not epic_id:
                return [TextContent(
                    type="text",
                    text="Error: epic_id is required"
                )]
            
            logger.info(f"epic_report called: epic_id={epic_id}")
            
            # Epic report is not yet implemented
            return [TextContent(
                type="text",
                text=f"Epic report is not yet implemented. "
                     f"Please use other analytics tools like velocity_chart or sprint_report."
            )]
            
        except Exception as e:
            logger.error(f"Error in epic_report: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error generating epic report: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("epic_report")
    
    # Tool 9: resource_utilization
    @server.call_tool()
    async def resource_utilization(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Analyze resource utilization across team.
        
        Args:
            project_id (optional): Filter by project
            provider_id (optional): Filter by provider
        
        Returns:
            Resource utilization metrics
        """
        try:
            project_id = arguments.get("project_id")
            provider_id = arguments.get("provider_id")
            
            logger.info(
                f"resource_utilization called: project_id={project_id}, "
                f"provider_id={provider_id}"
            )
            
            # Resource utilization is not yet implemented
            return [TextContent(
                type="text",
                text=f"Resource utilization analysis is not yet implemented. "
                     f"Please use other analytics tools like velocity_chart or sprint_report"
                     f"{' for project ' + project_id if project_id else ''}."
            )]
            
        except Exception as e:
            logger.error(f"Error in resource_utilization: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error analyzing resource utilization: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("resource_utilization")
    
    # Tool 10: time_tracking_report
    @server.call_tool()
    async def time_tracking_report(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Generate time tracking report.
        
        Args:
            project_id (optional): Filter by project
            user_id (optional): Filter by user
            start_date (optional): Start date (YYYY-MM-DD)
            end_date (optional): End date (YYYY-MM-DD)
        
        Returns:
            Time tracking report with hours logged
        """
        try:
            project_id = arguments.get("project_id")
            user_id = arguments.get("user_id")
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            
            logger.info(
                f"time_tracking_report called: project_id={project_id}, "
                f"user_id={user_id}, start_date={start_date}, end_date={end_date}"
            )
            
            # Time tracking report is not yet implemented
            return [TextContent(
                type="text",
                text=f"Time tracking report is not yet implemented. "
                     f"Please use other analytics tools like velocity_chart or sprint_report"
                     f"{' for project ' + project_id if project_id else ''}."
            )]
            
        except Exception as e:
            logger.error(f"Error in time_tracking_report: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error generating time tracking report: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("time_tracking_report")
    
    logger.info(f"Registered {tool_count} analytics tools")
    return tool_count

