"""
PM MCP Server Tools

This package contains all PM tool registrations for the MCP server.
Each module registers a set of related tools.

Tool Categories:
- projects: Project CRUD and search operations
- tasks: Task management, assignment, and tracking
- sprints: Sprint planning and management
- epics: Epic management and progress tracking
- analytics: Charts, reports, and metrics
- users: User management and workload analysis
- task_interactions: Comments, watchers, and collaboration
- provider_config: PM provider configuration
"""

# Core tools
from .users import register_user_tools
from .task_interactions import register_task_interaction_tools
from .provider_config import register_provider_config_tools

# Refactored tools are registered via their own register modules
# from .analytics.register import register_analytics_tools
# from .projects.register import register_project_tools
# from .tasks.register import register_task_tools
# from .sprints.register import register_sprint_tools
# from .epics.register import register_epic_tools

__all__ = [
    "register_user_tools",
    "register_task_interaction_tools",
    "register_provider_config_tools",
]
