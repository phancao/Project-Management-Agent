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
    
    # Tool 3: sprint_report
    @server.call_tool()
    async def sprint_report(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Generate comprehensive sprint report.
        
        Args:
            sprint_id (required): Sprint ID
        
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
            
            # Get sprint report
            report = pm_handler.get_sprint_report(sprint_id)
            
            if not report:
                return [TextContent(
                    type="text",
                    text=f"No report data available for sprint {sprint_id}."
                )]
            
            # Format output
            output_lines = [
                f"# Sprint Report: {report.get('sprint_name')}\n\n",
                f"**Duration:** {report.get('start_date')} - {report.get('end_date')}\n",
                f"**Status:** {report.get('status')}\n\n",
                f"## Metrics\n",
                f"- **Planned Points:** {report.get('planned_points', 0)}\n",
                f"- **Completed Points:** {report.get('completed_points', 0)}\n",
                f"- **Completion Rate:** {report.get('completion_rate', 0)}%\n",
                f"- **Total Tasks:** {report.get('total_tasks', 0)}\n",
                f"- **Completed Tasks:** {report.get('completed_tasks', 0)}\n",
                f"- **Carry Over:** {report.get('carry_over_tasks', 0)} tasks\n",
            ]
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in sprint_report: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error generating sprint report: {str(e)}"
            )]
    
    tool_count += 1
    
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
            
            # Get project health
            health = pm_handler.get_project_health(project_id)
            
            if not health:
                return [TextContent(
                    type="text",
                    text=f"No health data available for project {project_id}."
                )]
            
            # Format output
            output_lines = [
                f"# Project Health: {health.get('project_name')}\n\n",
                f"**Overall Health:** {health.get('health_status', 'Unknown')}\n",
                f"**Health Score:** {health.get('health_score', 0)}/100\n\n",
                f"## Indicators\n",
                f"- **On-Time Delivery:** {health.get('on_time_percentage', 0)}%\n",
                f"- **Overdue Tasks:** {health.get('overdue_tasks', 0)}\n",
                f"- **Blocked Tasks:** {health.get('blocked_tasks', 0)}\n",
                f"- **Team Velocity:** {health.get('velocity_trend', 'Stable')}\n",
                f"- **Resource Utilization:** {health.get('resource_utilization', 0)}%\n",
            ]
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in project_health: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error analyzing project health: {str(e)}"
            )]
    
    tool_count += 1
    
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
            
            # Get task distribution
            distribution = pm_handler.get_task_distribution(project_id)
            
            if not distribution:
                return [TextContent(
                    type="text",
                    text=f"No distribution data available for project {project_id}."
                )]
            
            # Format output
            output_lines = [f"# Task Distribution - Project {project_id}\n\n"]
            
            for member in distribution.get("members", []):
                output_lines.append(
                    f"**{member.get('name')}**\n"
                    f"- Open: {member.get('open_tasks', 0)}\n"
                    f"- In Progress: {member.get('in_progress_tasks', 0)}\n"
                    f"- Completed: {member.get('completed_tasks', 0)}\n"
                    f"- Total: {member.get('total_tasks', 0)}\n\n"
                )
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in task_distribution: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error analyzing task distribution: {str(e)}"
            )]
    
    tool_count += 1
    
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
            
            # Get team performance
            performance = pm_handler.get_team_performance(project_id, time_period)
            
            if not performance:
                return [TextContent(
                    type="text",
                    text=f"No performance data available for project {project_id}."
                )]
            
            # Format output
            output_lines = [
                f"# Team Performance - Last {time_period} Days\n\n",
                f"**Project:** {performance.get('project_name')}\n\n",
                f"## Metrics\n",
                f"- **Tasks Completed:** {performance.get('completed_tasks', 0)}\n",
                f"- **Average Completion Time:** {performance.get('avg_completion_time', 0)} days\n",
                f"- **Throughput:** {performance.get('throughput', 0)} tasks/week\n",
                f"- **Quality Score:** {performance.get('quality_score', 0)}/100\n",
                f"- **Collaboration Score:** {performance.get('collaboration_score', 0)}/100\n",
            ]
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in team_performance: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error analyzing team performance: {str(e)}"
            )]
    
    tool_count += 1
    
    logger.info(f"Registered {tool_count} analytics tools")
    return tool_count

