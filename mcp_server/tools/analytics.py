"""
Analytics and Reporting Tools

MCP tools for analytics, charts, and reports across all PM providers.
"""

import logging
import json
from typing import Any, Tuple

from mcp.server import Server
from mcp.types import TextContent

from ..pm_handler import MCPPMHandler
from ..config import PMServerConfig
from ..database.models import PMProviderConnection

# Import analytics service and adapter
from src.analytics.service import AnalyticsService
from src.analytics.adapters.pm_adapter import PMProviderAnalyticsAdapter

logger = logging.getLogger(__name__)


async def _get_analytics_service(
    project_id: str,
    pm_handler: MCPPMHandler
) -> Tuple[AnalyticsService, str]:
    """
    Get analytics service for a specific project.
    
    Args:
        project_id: Project ID (may be composite "provider_id:project_key")
        pm_handler: PM handler instance
    
    Returns:
        Tuple of (AnalyticsService, actual_project_id)
    
    Raises:
        ValueError: If provider not found or no active providers
    """
    # Extract provider_id from composite project_id
    if ":" in project_id:
        provider_id, actual_project_id = project_id.split(":", 1)
    else:
        # Fallback: get first active provider
        providers = pm_handler._get_active_providers()
        if not providers:
            raise ValueError("No active PM providers found")
        provider_id = str(providers[0].id)
        actual_project_id = project_id
    
    logger.info(
        f"[_get_analytics_service] Getting analytics for project_id={project_id}, "
        f"provider_id={provider_id}, actual_project_id={actual_project_id}"
    )
    
    # Get provider connection from database
    if not pm_handler.db:
        raise ValueError("Database session not available")
    
    provider_conn = pm_handler.db.query(PMProviderConnection).filter(
        PMProviderConnection.id == provider_id
    ).first()
    
    if not provider_conn:
        raise ValueError(f"Provider {provider_id} not found")
    
    logger.info(
        f"[_get_analytics_service] Found provider: {provider_conn.provider_type} "
        f"at {provider_conn.base_url}"
    )
    
    # Create PM provider instance
    provider = pm_handler._create_provider_instance(provider_conn)
    
    # Create analytics adapter
    adapter = PMProviderAnalyticsAdapter(provider)
    
    # Create analytics service
    service = AnalyticsService(adapter=adapter)
    
    logger.info(
        f"[_get_analytics_service] Created analytics service for "
        f"project {actual_project_id}"
    )
    
    return service, actual_project_id


def register_analytics_tools(
    server: Server,
    pm_handler: MCPPMHandler,
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
        Generate burndown chart data for a sprint to track progress.
        
        Shows how much work remains in a sprint over time, comparing actual progress 
        against an ideal burndown line. Use this to check if a sprint is on track, 
        identify if the team is ahead or behind schedule, and forecast sprint completion.
        
        Args:
            project_id (required): Project ID (format: "provider_uuid:project_key")
            sprint_id (optional): Sprint ID (uses current/active sprint if not provided)
            scope_type (optional): What to measure - "story_points", "tasks", or "hours" (default: "story_points")
        
        Returns:
            JSON with burndown data including total scope, remaining work, completion 
            percentage, and whether the sprint is on track.
        
        Example usage:
            - "Show me the burndown for Sprint 4"
            - "Is our current sprint on track?"
            - "How much work is remaining in this sprint?"
        """
        try:
            project_id = arguments.get("project_id")
            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required. Please provide the project ID."
                )]
            
            sprint_id = arguments.get("sprint_id")
            scope_type = arguments.get("scope_type", "story_points")
            
            logger.info(
                f"[burndown_chart] Called with project_id={project_id}, "
                f"sprint_id={sprint_id}, scope_type={scope_type}"
            )
            
            # Get analytics service
            service, actual_project_id = await _get_analytics_service(project_id, pm_handler)
            
            # Get burndown data
            chart_data = await service.get_burndown_chart(
                project_id=actual_project_id,
                sprint_id=sprint_id,
                scope_type=scope_type
            )
            
            # Format for LLM consumption
            result = {
                "sprint": chart_data.title,
                "scope_type": scope_type,
                "total_scope": chart_data.metadata.get("total_scope"),
                "remaining": chart_data.metadata.get("remaining"),
                "completed": chart_data.metadata.get("completed"),
                "completion_percentage": chart_data.metadata.get("completion_percentage"),
                "on_track": chart_data.metadata.get("on_track"),
                "status": chart_data.metadata.get("status"),
                "scope_changes": chart_data.metadata.get("scope_changes", {}),
                "days_elapsed": chart_data.metadata.get("days_elapsed"),
                "days_remaining": chart_data.metadata.get("days_remaining")
            }
            
            logger.info(
                f"[burndown_chart] Success: {result['completion_percentage']}% complete, "
                f"on_track={result['on_track']}"
            )
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
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
        Get team velocity data showing performance over recent sprints.
        
        Velocity measures how much work a team completes in each sprint. Use this to 
        forecast future capacity for sprint planning, track team performance trends over 
        time, identify if velocity is increasing/decreasing/stable, and assess team 
        predictability (how often they deliver what they commit to).
        
        Args:
            project_id (required): Project ID (format: "provider_uuid:project_key")
            sprint_count (optional): Number of recent sprints to analyze (default: 5, recommended: 3-10)
        
        Returns:
            JSON with velocity data including committed vs completed story points per sprint, 
            average velocity, trend, and predictability score.
        
        Example usage:
            - "What's our team's velocity?"
            - "Show me velocity for the last 10 sprints"
            - "Is our velocity improving?"
            - "How many story points should we commit to in the next sprint?"
        """
        try:
            project_id = arguments.get("project_id")
            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required. Please provide the project ID."
                )]
            
            sprint_count = arguments.get("sprint_count", 5)
            
            logger.info(
                f"[velocity_chart] Called with project_id={project_id}, "
                f"sprint_count={sprint_count}"
            )
            
            # Get analytics service
            service, actual_project_id = await _get_analytics_service(project_id, pm_handler)
            
            # Get velocity data
            chart_data = await service.get_velocity_chart(
                project_id=actual_project_id,
                sprint_count=sprint_count
            )
            
            # Extract sprint data from series
            sprints_data = []
            if len(chart_data.series) >= 2:
                committed_series = chart_data.series[0]
                completed_series = chart_data.series[1]
                
                for i, point in enumerate(committed_series.data):
                    sprints_data.append({
                        "sprint": point.label,
                        "committed": point.value,
                        "completed": completed_series.data[i].value if i < len(completed_series.data) else 0,
                        "completion_rate": (
                            (completed_series.data[i].value / point.value * 100)
                            if point.value > 0 and i < len(completed_series.data)
                            else 0
                        )
                    })
            
            # Format for LLM consumption
            result = {
                "average_velocity": chart_data.metadata.get("average_velocity"),
                "median_velocity": chart_data.metadata.get("median_velocity"),
                "latest_velocity": chart_data.metadata.get("latest_velocity"),
                "trend": chart_data.metadata.get("trend"),
                "predictability_score": chart_data.metadata.get("predictability_score"),
                "sprint_count": chart_data.metadata.get("sprint_count"),
                "velocity_range": chart_data.metadata.get("velocity_range", {}),
                "sprints": sprints_data
            }
            
            logger.info(
                f"[velocity_chart] Success: avg={result['average_velocity']}, "
                f"trend={result['trend']}, predictability={result['predictability_score']}"
            )
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
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
        Get a comprehensive sprint summary report with key metrics and insights.
        
        This report provides a complete overview of a sprint's performance, including:
        - Sprint duration and dates
        - Commitment vs actual delivery
        - Scope changes during the sprint
        - Work breakdown by type (stories, bugs, tasks)
        - Team capacity and utilization
        - Key highlights and concerns
        
        Use this for sprint reviews, retrospectives, or to understand sprint outcomes.
        
        Args:
            project_id (required): Project ID (format: "provider_uuid:project_key")
            sprint_id (required): Sprint ID
        
        Returns:
            JSON with comprehensive sprint report including metrics, achievements, 
            and areas of concern.
        
        Example usage:
            - "Give me a summary of Sprint 4"
            - "How did our last sprint go?"
            - "What were the key achievements in Sprint 4?"
            - "Prepare a sprint review for Sprint 4"
        """
        try:
            project_id = arguments.get("project_id")
            sprint_id = arguments.get("sprint_id")
            
            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required. Please provide the project ID."
                )]
            
            if not sprint_id:
                return [TextContent(
                    type="text",
                    text="Error: sprint_id is required. Please provide the sprint ID."
                )]
            
            logger.info(
                f"[sprint_report] Called with project_id={project_id}, "
                f"sprint_id={sprint_id}"
            )
            
            # Get analytics service
            service, actual_project_id = await _get_analytics_service(project_id, pm_handler)
            
            # Get sprint report
            report = await service.get_sprint_report(
                sprint_id=sprint_id,
                project_id=actual_project_id
            )
            
            # Convert to dict for JSON serialization
            # Handle both dict and object return types
            if isinstance(report, dict):
                result = report
            else:
                result = {
                    "sprint_id": getattr(report, "sprint_id", None),
                    "sprint_name": getattr(report, "sprint_name", None),
                    "duration": {
                        "start": (
                            getattr(report.duration, "start", None).isoformat()
                            if hasattr(report, "duration") and getattr(report.duration, "start", None)
                            else None
                        ),
                        "end": (
                            getattr(report.duration, "end", None).isoformat()
                            if hasattr(report, "duration") and getattr(report.duration, "end", None)
                            else None
                        ),
                        "days": (
                            getattr(report.duration, "days", None)
                            if hasattr(report, "duration")
                            else None
                        )
                    } if hasattr(report, "duration") else {},
                    "commitment": {
                        "planned_points": getattr(report.commitment, "planned_points", 0),
                        "completed_points": getattr(report.commitment, "completed_points", 0),
                        "completion_rate": getattr(report.commitment, "completion_rate", 0),
                        "planned_items": getattr(report.commitment, "planned_items", 0),
                        "completed_items": getattr(report.commitment, "completed_items", 0)
                    } if hasattr(report, "commitment") else {},
                    "scope_changes": {
                        "added": getattr(report.scope_changes, "added", 0),
                        "removed": getattr(report.scope_changes, "removed", 0),
                        "net_change": getattr(report.scope_changes, "net_change", 0),
                        "scope_stability": getattr(report.scope_changes, "scope_stability", 0)
                    } if hasattr(report, "scope_changes") else {},
                    "work_breakdown": getattr(report, "work_breakdown", {}),
                    "team_performance": {
                        "velocity": getattr(report.team_performance, "velocity", 0),
                        "capacity_hours": getattr(report.team_performance, "capacity_hours", 0),
                        "capacity_used": getattr(report.team_performance, "capacity_used", 0),
                        "capacity_utilized": getattr(report.team_performance, "capacity_utilized", 0),
                        "team_size": getattr(report.team_performance, "team_size", 0)
                    } if hasattr(report, "team_performance") else {},
                    "highlights": getattr(report, "highlights", []),
                    "concerns": getattr(report, "concerns", [])
                }
            
            completion_rate = result.get("commitment", {}).get("completion_rate", 0)
            velocity = result.get("team_performance", {}).get("velocity", 0)
            sprint_name = result.get("sprint_name", "Unknown")
            
            logger.info(
                f"[sprint_report] Success: {sprint_name}, "
                f"completion={completion_rate:.1%}, velocity={velocity}"
            )
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
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
        Get a high-level analytics summary for a project.
        
        Provides a quick overview of project health, including:
        - Current sprint status and progress
        - Team velocity trends
        - Overall completion statistics
        - Team size
        
        Use this for project status updates or quick health checks.
        
        Args:
            project_id (required): Project ID (format: "provider_uuid:project_key")
        
        Returns:
            JSON with project summary including current sprint info, velocity metrics, 
            and overall statistics.
        
        Example usage:
            - "How is the project going?"
            - "Give me a project status update"
            - "What's the current sprint progress?"
            - "Show me project health metrics"
        """
        try:
            project_id = arguments.get("project_id")
            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required. Please provide the project ID."
                )]
            
            logger.info(f"[project_health] Called with project_id={project_id}")
            
            # Get analytics service
            service, actual_project_id = await _get_analytics_service(project_id, pm_handler)
            
            # Get project summary
            summary = await service.get_project_summary(project_id=actual_project_id)
            
            logger.info(
                f"[project_health] Success: current_sprint={summary.get('current_sprint', {}).get('name')}, "
                f"velocity={summary.get('velocity', {}).get('average')}"
            )
            
            return [TextContent(
                type="text",
                text=json.dumps(summary, indent=2)
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

