"""
PM MCP Server Tools

This package contains all PM tool registrations for the MCP server.
Each module registers a set of related tools.

Tool Categories:
- projects_v2: Project CRUD and search operations (refactored)
- tasks_v2: Task management, assignment, and tracking (refactored)
- sprints_v2: Sprint planning and management (refactored)
- epics_v2: Epic management and progress tracking (refactored)
- analytics_v2: Charts, reports, and metrics (refactored)
- users: User management and workload analysis
- task_interactions: Comments, watchers, and collaboration
- provider_config: PM provider configuration
"""

# Core tools (still using old pattern but updated for context)
from .users import register_user_tools
from .task_interactions import register_task_interaction_tools
from .provider_config import register_provider_config_tools

# V2 Tools are registered via their own register modules
# from .analytics_v2.register import register_analytics_tools_v2
# from .projects_v2.register import register_project_tools_v2
# from .tasks_v2.register import register_task_tools_v2
# from .sprints_v2.register import register_sprint_tools_v2
# from .epics_v2.register import register_epic_tools_v2

__all__ = [
    "register_user_tools",
    "register_task_interaction_tools",
    "register_provider_config_tools",
]

