"""
Project Management Tools

MCP tools for project operations across all PM providers.
"""

import logging
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent

from ..pm_handler import MCPPMHandler
from ..config import PMServerConfig

logger = logging.getLogger(__name__)


def register_project_tools(
    server: Server,
    pm_handler: MCPPMHandler,
    config: PMServerConfig,
    tool_names: list[str] | None = None,
    tool_functions: dict[str, Any] | None = None
) -> int:
    """
    Register project-related MCP tools.
    
    Args:
        server: MCP server instance
        pm_handler: PM handler for multi-provider operations
        config: Server configuration
        tool_names: Optional list to track tool names for list_tools
    
    Returns:
        Number of tools registered
    """
    tool_count = 0
    
    # Tool 1: list_projects
    @server.call_tool()
    async def list_projects(tool_name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """
        List all accessible projects across all PM providers.
        
        **IMPORTANT WORKFLOW - READ THIS FIRST**:
        Before calling this tool, you MUST follow this sequence:
        1. **First**: Call `list_providers` to check if any providers are configured
        2. **If no active providers exist**: Call `configure_pm_provider` to set up a provider
           - For demo/testing: Use provider_type="mock" (no credentials needed, has demo data)
           - For real data: User must provide credentials
        3. **Then**: Call `list_projects` to retrieve projects
        
        **Why This Matters**:
        - This tool will return 0 projects if no providers are configured
        - You cannot retrieve projects without at least one active provider
        - Always check provider status first using `list_providers`
        
        **If This Tool Returns 0 Projects**:
        - Check if providers exist: Call `list_providers` first
        - If no providers: Configure one using `configure_pm_provider`
        - If providers exist but no projects: The providers may not have any projects yet
        
        Args:
            provider_id (optional): Filter projects by provider ID
            search (optional): Search term for project name/description
            limit (optional): Maximum number of projects to return
        
        Returns:
            List of projects with id, name, description, provider info, etc.
            Returns empty list if no providers are configured or no projects exist.
        """
        try:
            logger.info("=" * 80)
            logger.info("[MCP-TOOL] list_projects called")
            logger.info(f"[MCP-TOOL] Raw arguments: {arguments}")
            logger.info(f"[MCP-TOOL] Arguments type: {type(arguments)}")
            logger.info("=" * 80)
            
            # Validate arguments is a dict
            if not isinstance(arguments, dict):
                logger.error(f"[list_projects] Invalid arguments type: {type(arguments)}, expected dict")
                return [TextContent(
                    type="text",
                    text=f"Error: Invalid arguments format. Expected dictionary, got {type(arguments).__name__}."
                )]
            
            provider_id = arguments.get("provider_id")
            search = arguments.get("search")
            limit = arguments.get("limit")
            
            logger.info(
                f"[MCP-TOOL] Extracted parameters: provider_id={provider_id}, "
                f"search={search}, limit={limit}"
            )
            
            # Get projects from PM handler
            logger.info("[MCP-TOOL] Calling pm_handler.list_all_projects()...")
            projects = await pm_handler.list_all_projects()
            provider_errors = getattr(pm_handler, '_last_provider_errors', [])
            logger.info(f"[MCP-TOOL] Retrieved {len(projects)} projects from PMHandler")
            if provider_errors:
                logger.warning(f"[MCP-TOOL] {len(provider_errors)} provider(s) failed to retrieve projects")
            
            # Apply provider_id filter if specified
            if provider_id:
                projects = [p for p in projects if p.get("provider_id") == provider_id]
            
            # Apply search filter
            if search:
                search_lower = search.lower()
                projects = [
                    p for p in projects
                    if search_lower in p.get("name", "").lower()
                    or search_lower in p.get("description", "").lower()
                ]
            
            # Apply limit
            if limit:
                projects = projects[:int(limit)]
            
            logger.info(f"Returning {len(projects)} projects")
            
            # Format response
            if not projects:
                # Check if it's because no providers exist
                active_providers = pm_handler._get_active_providers()
                if not active_providers:
                    return [TextContent(
                        type="text",
                        text="❌ ERROR: Cannot list projects - No active PM providers configured!\n\n"
                             "**REQUIRED ACTION:** You MUST call `list_providers` FIRST before calling `list_projects`.\n\n"
                             "**Correct Workflow:**\n"
                             "1. ⚠️ STOP - Do not call list_projects again until providers are configured\n"
                             "2. ✅ Call `list_providers` to check provider status\n"
                             "3. ✅ If no providers exist, call `configure_pm_provider` with:\n"
                             "   - provider_type='mock' (for demo/testing, no credentials needed)\n"
                             "   - base_url='http://localhost'\n"
                             "   - name='Demo Provider'\n"
                             "4. ✅ Then call `list_projects` again\n\n"
                             "**Why this happened:** You called `list_projects` without checking if providers exist first. "
                             "Always call `list_providers` before any project-related operations."
                    )]
                else:
                    # Build detailed provider status report
                    output_lines = [
                        f"📊 **Provider Status Report** ({len(active_providers)} active provider(s)):\n\n"
                    ]
                    
                    # Get provider info for all providers
                    provider_status = {}
                    for provider in active_providers:
                        provider_status[str(provider.id)] = {
                            "name": provider.name or f"{provider.provider_type} ({provider.base_url})",
                            "type": provider.provider_type,
                            "base_url": provider.base_url,
                            "projects_count": 0,
                            "status": "success"
                        }
                    
                    # Count projects per provider
                    for project in projects:
                        provider_id = project.get('provider_id')
                        if provider_id in provider_status:
                            provider_status[provider_id]["projects_count"] += 1
                    
                    # Mark failed providers
                    for err in provider_errors:
                        provider_id = err['provider_id']
                        if provider_id in provider_status:
                            provider_status[provider_id]["status"] = "failed"
                            provider_status[provider_id]["error"] = err['error']
                    
                    # Output provider status
                    for provider_id, status in provider_status.items():
                        if status["status"] == "failed":
                            output_lines.append(
                                f"❌ **{status['name']}** ({status['type']}):\n"
                                f"   Status: Failed to retrieve projects\n"
                                f"   Error: {status.get('error', 'Unknown error')}\n\n"
                            )
                        else:
                            output_lines.append(
                                f"✅ **{status['name']}** ({status['type']}):\n"
                                f"   Projects: {status['projects_count']} project(s)\n"
                                f"   URL: {status['base_url']}\n\n"
                            )
                    
                    # Add summary
                    successful_providers = [s for s in provider_status.values() if s["status"] == "success"]
                    total_projects = sum(s["projects_count"] for s in successful_providers)
                    
                    if total_projects == 0:
                        output_lines.append(
                            f"**Summary:** No projects found across all providers.\n"
                            f"- {len(successful_providers)} provider(s) connected successfully but have no projects\n"
                            f"- {len(provider_errors)} provider(s) failed to connect\n\n"
                        )
                        if provider_errors:
                            output_lines.append(
                                "**Troubleshooting:**\n"
                                "- Check provider connection settings (base_url, API key)\n"
                                "- Verify API credentials are correct\n"
                                "- Ensure provider services are accessible\n"
                                "- Use `configure_pm_provider` to update provider settings if needed\n"
                            )
                    
                    return [TextContent(
                        type="text",
                        text="".join(output_lines)
                    )]
            
            # Create formatted output
            output_lines = [f"✅ Found {len(projects)} project(s) from {len(set(p.get('provider_id') for p in projects))} provider(s):\n\n"]
            
            # Group projects by provider
            projects_by_provider = {}
            for project in projects:
                provider_id = project.get('provider_id')
                if provider_id not in projects_by_provider:
                    projects_by_provider[provider_id] = []
                projects_by_provider[provider_id].append(project)
            
            # Output projects grouped by provider
            project_num = 1
            for provider_id, provider_projects in projects_by_provider.items():
                provider_type = provider_projects[0].get('provider_type', 'unknown')
                output_lines.append(f"**Provider: {provider_type}** ({len(provider_projects)} project(s)):\n")
                for project in provider_projects:
                    output_lines.append(
                        f"{project_num}. **{project.get('name')}** (ID: {project.get('id')})\n"
                        f"   Description: {project.get('description', 'N/A')}\n"
                        f"   Status: {project.get('status', 'N/A')}\n"
                    )
                    project_num += 1
                output_lines.append("\n")
            
            # Add provider errors if any
            if provider_errors:
                error_lines = [
                    f"\n⚠️ **Note: {len(provider_errors)} provider(s) failed to retrieve projects:**\n"
                ]
                for err in provider_errors:
                    error_lines.append(
                        f"- **{err['provider_name']}** ({err['provider_type']}): {err['error']}\n"
                    )
                output_lines.extend(error_lines)
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            error_msg = str(e)
            logger.error("=" * 80)
            logger.error(f"[MCP-TOOL] Error in list_projects: {error_msg}")
            logger.error(f"[MCP-TOOL] Error type: {type(e).__name__}")
            import traceback
            logger.error(f"[MCP-TOOL] Full traceback:\n{traceback.format_exc()}")
            logger.error("=" * 80)
            return [TextContent(
                type="text",
                text=f"Error listing projects: {error_msg}\n\n"
                     "This might be due to:\n"
                     "- Provider connection issues\n"
                     "- Missing permissions\n"
                     "- Database connection problems\n"
                     "- Invalid arguments passed to the tool\n\n"
                     "Please check the backend logs for more details."
            )]
    
    # Track tool name and store function reference after function is defined
    if tool_names is not None:
        tool_names.append("list_projects")
    if tool_functions is not None:
        tool_functions["list_projects"] = list_projects
    tool_count += 1
    
    # Tool 2: get_project
    @server.call_tool()
    async def get_project(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Get detailed information about a specific project.
        
        Args:
            project_id (required): Project ID
        
        Returns:
            Detailed project information including tasks, sprints, members, etc.
        """
        try:
            project_id = arguments.get("project_id")
            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required"
                )]
            
            logger.info(f"get_project called: project_id={project_id}")
            
            # Get project from list_all_projects
            projects = await pm_handler.list_all_projects()
            project = next((p for p in projects if p.get("id") == project_id), None)
            
            if not project:
                return [TextContent(
                    type="text",
                    text=f"Project with ID {project_id} not found."
                )]
            
            # Format detailed output
            output_lines = [
                f"# Project: {project.get('name')}\n\n",
                f"**ID:** {project.get('id')}\n",
                f"**Provider:** {project.get('provider_type')} ({project.get('provider_id')})\n",
                f"**Description:** {project.get('description', 'N/A')}\n",
                f"**Status:** {project.get('status', 'N/A')}\n",
            ]
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in get_project: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error getting project: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("get_project")
    tool_count += 1
    
    # Tool 3: create_project
    @server.call_tool()
    async def create_project(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Create a new project.
        
        Args:
            name (required): Project name
            description (optional): Project description
            provider_id (optional): Provider to create project in (defaults to first available)
        
        Returns:
            Created project information
        """
        try:
            name = arguments.get("name")
            if not name:
                return [TextContent(
                    type="text",
                    text="Error: name is required"
                )]
            
            description = arguments.get("description")
            provider_id = arguments.get("provider_id")
            
            logger.info(
                f"create_project called: name={name}, provider_id={provider_id}"
            )
            
            # Project creation is not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"Project creation is not yet implemented. "
                     f"Please create projects directly in your PM provider (JIRA, OpenProject, etc.) "
                     f"and they will be available via list_projects."
            )]
            
        except Exception as e:
            logger.error(f"Error in create_project: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error creating project: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("create_project")
    tool_count += 1
    
    # Tool 4: update_project
    @server.call_tool()
    async def update_project(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Update an existing project.
        
        Args:
            project_id (required): Project ID
            name (optional): New project name
            description (optional): New project description
            status (optional): New project status
        
        Returns:
            Updated project information
        """
        try:
            project_id = arguments.get("project_id")
            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required"
                )]
            
            updates = {
                k: v for k, v in arguments.items()
                if k != "project_id" and v is not None
            }
            
            if not updates:
                return [TextContent(
                    type="text",
                    text="Error: At least one field to update is required"
                )]
            
            logger.info(
                f"update_project called: project_id={project_id}, updates={updates}"
            )
            
            # Project update is not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"Project update is not yet implemented. "
                     f"Please update projects directly in your PM provider (JIRA, OpenProject, etc.)."
            )]
            
        except Exception as e:
            logger.error(f"Error in update_project: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error updating project: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("update_project")
    tool_count += 1
    
    # Tool 5: delete_project
    @server.call_tool()
    async def delete_project(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Delete a project.
        
        Args:
            project_id (required): Project ID
        
        Returns:
            Confirmation message
        """
        try:
            project_id = arguments.get("project_id")
            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required"
                )]
            
            logger.info(f"delete_project called: project_id={project_id}")
            
            # Project deletion is not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"Project deletion is not yet implemented. "
                     f"Please delete projects directly in your PM provider (JIRA, OpenProject, etc.)."
            )]
            
        except Exception as e:
            logger.error(f"Error in delete_project: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error deleting project: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("delete_project")
    tool_count += 1
    
    # Tool 6: search_projects
    @server.call_tool()
    async def search_projects(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Search projects by name or description.
        
        Args:
            query (required): Search query
            provider_id (optional): Filter by provider
            limit (optional): Maximum results
        
        Returns:
            List of matching projects
        """
        try:
            query = arguments.get("query")
            if not query:
                return [TextContent(
                    type="text",
                    text="Error: query is required"
                )]
            
            provider_id = arguments.get("provider_id")
            limit = arguments.get("limit", 10)
            
            logger.info(
                f"search_projects called: query={query}, provider_id={provider_id}"
            )
            
            # Search via list_projects with filter
            projects = await pm_handler.list_all_projects()
            
            # Apply provider_id filter if specified
            if provider_id:
                projects = [p for p in projects if p.get("provider_id") == provider_id]
            
            # Filter by query
            query_lower = query.lower()
            matching = [
                p for p in projects
                if query_lower in p.get("name", "").lower()
                or query_lower in p.get("description", "").lower()
            ][:int(limit)]
            
            if not matching:
                return [TextContent(
                    type="text",
                    text=f"No projects found matching '{query}'"
                )]
            
            output_lines = [f"Found {len(matching)} projects matching '{query}':\n\n"]
            for i, project in enumerate(matching, 1):
                output_lines.append(
                    f"{i}. **{project.get('name')}** (ID: {project.get('id')})\n"
                    f"   {project.get('description', 'No description')}\n"
                )
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in search_projects: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error searching projects: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("search_projects")
    tool_count += 1
    
    logger.info(f"Registered {tool_count} project tools")
    return tool_count

