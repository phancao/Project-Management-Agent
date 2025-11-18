"""
PM MCP Server Tools

This package contains all PM tool registrations for the MCP server.
Each module registers a set of related tools.

Tool Categories:
- projects: Project CRUD and search operations
- tasks: Task management, assignment, and tracking
- sprints: Sprint planning and management
- epics: Epic management and progress tracking
- users: User management and workload analysis
- analytics: Charts, reports, and metrics
- task_interactions: Comments, watchers, and collaboration
"""

from .projects import register_project_tools
from .tasks import register_task_tools
from .sprints import register_sprint_tools
from .epics import register_epic_tools
from .users import register_user_tools
from .analytics import register_analytics_tools
from .task_interactions import register_task_interaction_tools

__all__ = [
    "register_project_tools",
    "register_task_tools",
    "register_sprint_tools",
    "register_epic_tools",
    "register_user_tools",
    "register_analytics_tools",
    "register_task_interaction_tools",
]

