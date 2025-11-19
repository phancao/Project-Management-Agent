"""
Task Interaction Tools

MCP tools for task comments, attachments, and collaboration.
"""

import logging
from typing import Any

from mcp.server import Server
from mcp.types import TextContent

from src.server.pm_handler import PMHandler
from ..config import PMServerConfig

logger = logging.getLogger(__name__)


def register_task_interaction_tools(
    server: Server,
    pm_handler: PMHandler,
    config: PMServerConfig,
    tool_names: list[str] | None = None
) -> int:
    """
    Register task interaction tools (comments, watchers, etc.).
    
    Args:
        server: MCP server instance
        pm_handler: PM handler for multi-provider operations
        config: Server configuration
    
    Returns:
        Number of tools registered
    """
    tool_count = 0
    
    # Tool 1: add_task_comment
    @server.call_tool()
    async def add_task_comment(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Add a comment to a task.
        
        Args:
            task_id (required): Task ID
            comment (required): Comment text
        
        Returns:
            Confirmation message
        """
        try:
            task_id = arguments.get("task_id")
            comment = arguments.get("comment")
            
            if not task_id or not comment:
                return [TextContent(
                    type="text",
                    text="Error: task_id and comment are required"
                )]
            
            logger.info(f"add_task_comment called: task_id={task_id}")
            
            # Task comments are not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"Task comments are not yet implemented. "
                     f"Please add comments directly in your PM provider (JIRA, OpenProject, etc.)."
            )]
            
        except Exception as e:
            logger.error(f"Error in add_task_comment: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error adding comment: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("add_task_comment")
    
    # Tool 2: get_task_comments
    @server.call_tool()
    async def get_task_comments(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Get all comments for a task.
        
        Args:
            task_id (required): Task ID
            limit (optional): Maximum number of comments
        
        Returns:
            List of task comments
        """
        try:
            task_id = arguments.get("task_id")
            if not task_id:
                return [TextContent(
                    type="text",
                    text="Error: task_id is required"
                )]
            
            limit = arguments.get("limit")
            
            logger.info(f"get_task_comments called: task_id={task_id}")
            
            # Task comments are not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"Task comments are not yet implemented. "
                     f"Please view comments directly in your PM provider (JIRA, OpenProject, etc.)."
            )]
            
        except Exception as e:
            logger.error(f"Error in get_task_comments: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error getting comments: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("get_task_comments")
    
    # Tool 3: add_task_watcher
    @server.call_tool()
    async def add_task_watcher(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Add a watcher to a task (for notifications).
        
        Args:
            task_id (required): Task ID
            user_id (required): User ID to add as watcher
        
        Returns:
            Confirmation message
        """
        try:
            task_id = arguments.get("task_id")
            user_id = arguments.get("user_id")
            
            if not task_id or not user_id:
                return [TextContent(
                    type="text",
                    text="Error: task_id and user_id are required"
                )]
            
            logger.info(
                f"add_task_watcher called: task_id={task_id}, user_id={user_id}"
            )
            
            # Task watchers are not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"Task watchers are not yet implemented. "
                     f"Please add watchers directly in your PM provider (JIRA, OpenProject, etc.)."
            )]
            
        except Exception as e:
            logger.error(f"Error in add_task_watcher: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error adding watcher: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("add_task_watcher")
    
    # Tool 4: bulk_update_tasks
    @server.call_tool()
    async def bulk_update_tasks(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Update multiple tasks at once.
        
        Args:
            task_ids (required): List of task IDs
            updates (required): Dictionary of fields to update
        
        Returns:
            Summary of updates
        """
        try:
            task_ids = arguments.get("task_ids")
            updates = arguments.get("updates")
            
            if not task_ids or not updates:
                return [TextContent(
                    type="text",
                    text="Error: task_ids and updates are required"
                )]
            
            if not isinstance(task_ids, list):
                return [TextContent(
                    type="text",
                    text="Error: task_ids must be a list"
                )]
            
            logger.info(
                f"bulk_update_tasks called: {len(task_ids)} tasks, updates={updates}"
            )
            
            # Bulk task updates are not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"Bulk task updates are not yet implemented. "
                     f"Please update tasks individually or use your PM provider's bulk update feature."
            )]
            
        except Exception as e:
            logger.error(f"Error in bulk_update_tasks: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error in bulk update: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("bulk_update_tasks")
    
    # Tool 5: link_related_tasks
    @server.call_tool()
    async def link_related_tasks(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Link two tasks as related (blocks, depends on, etc.).
        
        Args:
            task_id (required): Source task ID
            related_task_id (required): Related task ID
            relationship_type (optional): Type of relationship (blocks, depends_on, relates_to)
        
        Returns:
            Confirmation message
        """
        try:
            task_id = arguments.get("task_id")
            related_task_id = arguments.get("related_task_id")
            
            if not task_id or not related_task_id:
                return [TextContent(
                    type="text",
                    text="Error: task_id and related_task_id are required"
                )]
            
            relationship_type = arguments.get("relationship_type", "relates_to")
            
            logger.info(
                f"link_related_tasks called: task_id={task_id}, "
                f"related_task_id={related_task_id}, type={relationship_type}"
            )
            
            # Task linking is not yet implemented in PMHandler
            return [TextContent(
                type="text",
                text=f"Task linking is not yet implemented. "
                     f"Please link tasks directly in your PM provider (JIRA, OpenProject, etc.)."
            )]
            
        except Exception as e:
            logger.error(f"Error in link_related_tasks: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error linking tasks: {str(e)}"
            )]
    
    tool_count += 1
    if tool_names is not None:
        tool_names.append("link_related_tasks")
    
    logger.info(f"Registered {tool_count} task interaction tools")
    return tool_count

