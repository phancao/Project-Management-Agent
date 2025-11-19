"""
Project Management Tools

MCP tools for project operations across all PM providers.
"""

import logging
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent

from src.server.pm_handler import PMHandler
from ..config import PMServerConfig

logger = logging.getLogger(__name__)


def register_project_tools(
    server: Server,
    pm_handler: PMHandler,
    config: PMServerConfig
) -> int:
    """
    Register project-related MCP tools.
    
    Args:
        server: MCP server instance
        pm_handler: PM handler for multi-provider operations
        config: Server configuration
    
    Returns:
        Number of tools registered
    """
    tool_count = 0
    
    # Tool 1: list_projects
    @server.call_tool()
    async def list_projects(arguments: dict[str, Any]) -> list[TextContent]:
        """
        List all accessible projects across all PM providers.
        
        Args:
            provider_id (optional): Filter projects by provider ID
            search (optional): Search term for project name/description
            limit (optional): Maximum number of projects to return
        
        Returns:
            List of projects with id, name, description, provider info, etc.
        """
        try:
            provider_id = arguments.get("provider_id")
            search = arguments.get("search")
            limit = arguments.get("limit")
            
            logger.info(
                f"list_projects called: provider_id={provider_id}, "
                f"search={search}, limit={limit}"
            )
            
            # Get projects from PM handler
            projects = await pm_handler.list_all_projects()
            
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
                return [TextContent(
                    type="text",
                    text="No projects found."
                )]
            
            # Create formatted output
            output_lines = [f"Found {len(projects)} projects:\n"]
            for i, project in enumerate(projects, 1):
                output_lines.append(
                    f"{i}. **{project.get('name')}** (ID: {project.get('id')})\n"
                    f"   Provider: {project.get('provider_type')} ({project.get('provider_id')})\n"
                    f"   Description: {project.get('description', 'N/A')}\n"
                )
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in list_projects: {error_msg}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return [TextContent(
                type="text",
                text=f"Error listing projects: {error_msg}\n\n"
                     "This might be due to:\n"
                     "- Provider connection issues\n"
                     "- Missing permissions\n"
                     "- Database connection problems\n\n"
                     "Please check the backend logs for more details."
            )]
    
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
            
            # Get project from PM handler
            project = pm_handler.get_project(project_id)
            
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
                f"**Created:** {project.get('created_at', 'N/A')}\n",
                f"**Updated:** {project.get('updated_at', 'N/A')}\n",
            ]
            
            # Add additional fields if available
            if "url" in project:
                output_lines.append(f"**URL:** {project['url']}\n")
            
            if "members_count" in project:
                output_lines.append(f"**Members:** {project['members_count']}\n")
            
            if "tasks_count" in project:
                output_lines.append(f"**Tasks:** {project['tasks_count']}\n")
            
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
            
            # Create project via PM handler
            project = pm_handler.create_project(
                name=name,
                description=description,
                provider_id=provider_id
            )
            
            return [TextContent(
                type="text",
                text=f"✅ Project created successfully!\n\n"
                     f"**Name:** {project.get('name')}\n"
                     f"**ID:** {project.get('id')}\n"
                     f"**Provider:** {project.get('provider_type')}\n"
            )]
            
        except Exception as e:
            logger.error(f"Error in create_project: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error creating project: {str(e)}"
            )]
    
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
            
            # Update project via PM handler
            project = pm_handler.update_project(project_id, **updates)
            
            return [TextContent(
                type="text",
                text=f"✅ Project updated successfully!\n\n"
                     f"**Name:** {project.get('name')}\n"
                     f"**ID:** {project.get('id')}\n"
            )]
            
        except Exception as e:
            logger.error(f"Error in update_project: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error updating project: {str(e)}"
            )]
    
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
            
            # Delete project via PM handler
            pm_handler.delete_project(project_id)
            
            return [TextContent(
                type="text",
                text=f"✅ Project {project_id} deleted successfully!"
            )]
            
        except Exception as e:
            logger.error(f"Error in delete_project: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error deleting project: {str(e)}"
            )]
    
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
    
    tool_count += 1
    
    logger.info(f"Registered {tool_count} project tools")
    return tool_count

