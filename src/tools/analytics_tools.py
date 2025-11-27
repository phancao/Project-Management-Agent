"""
Analytics tools for AI agents.

⚠️ DEPRECATED: These tools have been moved to MCP server.

These tools are no longer used and have been replaced by MCP analytics tools
in mcp_server/tools/analytics.py which provide the same functionality but
with better integration and reliability.

The MCP analytics tools include:
- burndown_chart: Sprint burndown tracking
- velocity_chart: Team velocity analysis
- sprint_report: Comprehensive sprint reports
- project_health: Project health summary

This file is kept for reference but should not be imported or used.
"""

# DEPRECATED - DO NOT USE
# Use MCP analytics tools instead via the MCP server

from langchain.tools import tool
from typing import Optional, Dict, Any
import json

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
    ⚠️ DEPRECATED: Use MCP burndown_chart tool instead.
    
    This tool has been replaced by the MCP server analytics tools.
    Please use the burndown_chart tool from the MCP server instead.
    """
    return json.dumps({
        "error": "DEPRECATED: This tool has been replaced by MCP analytics tools. "
                 "Use the 'burndown_chart' tool from MCP server instead.",
        "replacement": "burndown_chart",
        "mcp_location": "mcp_server/tools/analytics.py"
    })


@tool
async def get_team_velocity(
    project_id: str,
    sprint_count: int = 6
) -> str:
    """
    ⚠️ DEPRECATED: Use MCP velocity_chart tool instead.
    
    This tool has been replaced by the MCP server analytics tools.
    Please use the velocity_chart tool from the MCP server instead.
    """
    return json.dumps({
        "error": "DEPRECATED: This tool has been replaced by MCP analytics tools. "
                 "Use the 'velocity_chart' tool from MCP server instead.",
        "replacement": "velocity_chart",
        "mcp_location": "mcp_server/tools/analytics.py"
    })


@tool
async def get_sprint_report(
    sprint_id: str,
    project_id: str
) -> str:
    """
    ⚠️ DEPRECATED: Use MCP sprint_report tool instead.
    
    This tool has been replaced by the MCP server analytics tools.
    Please use the sprint_report tool from the MCP server instead.
    """
    return json.dumps({
        "error": "DEPRECATED: This tool has been replaced by MCP analytics tools. "
                 "Use the 'sprint_report' tool from MCP server instead.",
        "replacement": "sprint_report",
        "mcp_location": "mcp_server/tools/analytics.py"
    })


@tool
async def get_project_analytics_summary(project_id: str) -> str:
    """
    ⚠️ DEPRECATED: Use MCP project_health tool instead.
    
    This tool has been replaced by the MCP server analytics tools.
    Please use the project_health tool from the MCP server instead.
    """
    return json.dumps({
        "error": "DEPRECATED: This tool has been replaced by MCP analytics tools. "
                 "Use the 'project_health' tool from MCP server instead.",
        "replacement": "project_health",
        "mcp_location": "mcp_server/tools/analytics.py"
    })


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

