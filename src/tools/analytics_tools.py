"""
Analytics tools for AI agents.

Provides tools for agents to query project analytics, charts, and metrics.
"""

from langchain.tools import tool
from typing import Optional, Dict, Any
import json

from src.analytics.service import AnalyticsService
from src.analytics.adapters.pm_adapter import PMProviderAnalyticsAdapter

# Analytics service will be initialized on-demand based on project_id
# No default mock provider - analytics tools require real project data
_analytics_service = None


@tool
async def get_sprint_burndown(
    project_id: str,
    sprint_id: Optional[str] = None,
    scope_type: str = "story_points"
) -> str:
    """
    Get burndown chart data for a sprint to track progress.
    
    This tool shows how much work remains in a sprint over time, comparing
    actual progress against an ideal burndown line. Use this to:
    - Check if a sprint is on track
    - Identify if the team is ahead or behind schedule
    - Forecast sprint completion
    
    Args:
        project_id: The project identifier (format: "provider_uuid:project_key")
        sprint_id: The sprint identifier (optional, uses current sprint if not provided)
        scope_type: What to measure - "story_points", "tasks", or "hours" (default: "story_points")
    
    Returns:
        JSON string with burndown chart data including ideal and actual lines,
        completion percentage, and whether the sprint is on track.
    
    Example usage:
        - "Show me the burndown for sprint 1"
        - "Is our current sprint on track?"
        - "How much work is remaining in this sprint?"
    """
    try:
        # Get analytics service for this project
        from database.connection import get_db_session
        from src.server.app import get_analytics_service
        
        db_gen = get_db_session()
        db = next(db_gen)
        try:
            analytics_service = get_analytics_service(project_id, db)
            chart_data = await analytics_service.get_burndown_chart(
                project_id=project_id,
                sprint_id=sprint_id,
                scope_type=scope_type
            )
        finally:
            db.close()
        
        # Return simplified version for AI agent
        result = {
            "chart_type": chart_data.chart_type,
            "title": chart_data.title,
            "summary": {
                "total_scope": chart_data.metadata.get("total_scope"),
                "remaining": chart_data.metadata.get("remaining"),
                "completed": chart_data.metadata.get("completed"),
                "completion_percentage": chart_data.metadata.get("completion_percentage"),
                "on_track": chart_data.metadata.get("on_track"),
                "status": chart_data.metadata.get("status")
            },
            "scope_changes": chart_data.metadata.get("scope_changes", {}),
            "data_points": len(chart_data.series[0].data) if chart_data.series else 0
        }
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
async def get_team_velocity(
    project_id: str,
    sprint_count: int = 6
) -> str:
    """
    Get team velocity data showing performance over recent sprints.
    
    Velocity measures how much work a team completes in each sprint. Use this to:
    - Forecast future capacity for sprint planning
    - Track team performance trends over time
    - Identify if velocity is increasing, decreasing, or stable
    - Assess team predictability (how often they deliver what they commit to)
    
    Args:
        project_id: The project identifier (e.g., "PROJECT-1")
        sprint_count: Number of recent sprints to analyze (default: 6, recommended: 3-10)
    
    Returns:
        JSON string with velocity chart data including committed vs completed
        story points per sprint, average velocity, trend, and predictability score.
    
    Example usage:
        - "What's our team's velocity?"
        - "Show me velocity for the last 10 sprints"
        - "Is our velocity improving?"
        - "How many story points should we commit to in the next sprint?"
    """
    try:
        # Get analytics service for this project
        from database.connection import get_db_session
        from src.server.app import get_analytics_service
        
        db_gen = get_db_session()
        db = next(db_gen)
        try:
            analytics_service = get_analytics_service(project_id, db)
            chart_data = await analytics_service.get_velocity_chart(
                project_id=project_id,
                sprint_count=sprint_count
            )
        finally:
            db.close()
        
        # Return simplified version for AI agent
        result = {
            "chart_type": chart_data.chart_type,
            "title": chart_data.title,
            "summary": {
                "average_velocity": chart_data.metadata.get("average_velocity"),
                "median_velocity": chart_data.metadata.get("median_velocity"),
                "latest_velocity": chart_data.metadata.get("latest_velocity"),
                "trend": chart_data.metadata.get("trend"),
                "predictability_score": chart_data.metadata.get("predictability_score"),
                "sprint_count": chart_data.metadata.get("sprint_count")
            },
            "velocity_range": chart_data.metadata.get("velocity_range", {}),
            "completion_rates": chart_data.metadata.get("completion_rates", [])
        }
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
async def get_sprint_report(
    sprint_id: str,
    project_id: str
) -> str:
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
        sprint_id: The sprint identifier (e.g., "SPRINT-1")
        project_id: The project identifier (e.g., "PROJECT-1")
    
    Returns:
        JSON string with comprehensive sprint report including metrics,
        achievements, and areas of concern.
    
    Example usage:
        - "Give me a summary of sprint 1"
        - "How did our last sprint go?"
        - "What were the key achievements in sprint 2?"
        - "Prepare a sprint review for sprint 3"
    """
    try:
        # Get analytics service for this project
        from database.connection import get_db_session
        from src.server.app import get_analytics_service
        
        db_gen = get_db_session()
        db = next(db_gen)
        try:
            analytics_service = get_analytics_service(project_id, db)
            report = await analytics_service.get_sprint_report(
                sprint_id=sprint_id,
                project_id=project_id
            )
        finally:
            db.close()
        
        # Return full report (it's already structured for consumption)
        result = {
            "sprint_id": report.sprint_id,
            "sprint_name": report.sprint_name,
            "duration": report.duration,
            "commitment": report.commitment,
            "scope_changes": report.scope_changes,
            "work_breakdown": report.work_breakdown,
            "team_performance": report.team_performance,
            "highlights": report.highlights,
            "concerns": report.concerns
        }
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
async def get_project_analytics_summary(project_id: str) -> str:
    """
    Get a high-level analytics summary for a project.
    
    Provides a quick overview of project health, including:
    - Current sprint status and progress
    - Team velocity trends
    - Overall completion statistics
    - Team size
    
    Use this for project status updates or quick health checks.
    
    Args:
        project_id: The project identifier (e.g., "PROJECT-1")
    
    Returns:
        JSON string with project summary including current sprint info,
        velocity metrics, and overall statistics.
    
    Example usage:
        - "How is the project going?"
        - "Give me a project status update"
        - "What's the current sprint progress?"
        - "Show me project health metrics"
    """
    try:
        # Get analytics service for this project
        from database.connection import get_db_session
        from src.server.app import get_analytics_service
        
        db_gen = get_db_session()
        db = next(db_gen)
        try:
            analytics_service = get_analytics_service(project_id, db)
            summary = await analytics_service.get_project_summary(project_id=project_id)
            return json.dumps(summary, indent=2)
        finally:
            db.close()
    except Exception as e:
        return json.dumps({"error": str(e)})


# List of all analytics tools for easy registration
ANALYTICS_TOOLS = [
    get_sprint_burndown,
    get_team_velocity,
    get_sprint_report,
    get_project_analytics_summary
]


def get_analytics_tools():
    """
    Get all analytics tools for agent registration.
    
    Returns:
        List of analytics tool functions
    """
    return ANALYTICS_TOOLS

