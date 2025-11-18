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
    config: PMServerConfig
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
            
            # Add comment via PM handler
            result = pm_handler.add_task_comment(task_id, comment)
            
            return [TextContent(
                type="text",
                text=f"✅ Comment added to task {task_id}!"
            )]
            
        except Exception as e:
            logger.error(f"Error in add_task_comment: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error adding comment: {str(e)}"
            )]
    
    tool_count += 1
    
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
            
            # Get comments from PM handler
            comments = pm_handler.get_task_comments(task_id)
            
            # Apply limit
            if limit:
                comments = comments[:int(limit)]
            
            if not comments:
                return [TextContent(
                    type="text",
                    text=f"No comments found for task {task_id}."
                )]
            
            # Format output
            output_lines = [f"Found {len(comments)} comments:\n\n"]
            for i, comment in enumerate(comments, 1):
                output_lines.append(
                    f"{i}. **{comment.get('author_name', 'Unknown')}** "
                    f"({comment.get('created_at', 'N/A')})\n"
                    f"   {comment.get('text', '')}\n\n"
                )
            
            return [TextContent(
                type="text",
                text="".join(output_lines)
            )]
            
        except Exception as e:
            logger.error(f"Error in get_task_comments: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error getting comments: {str(e)}"
            )]
    
    tool_count += 1
    
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
            
            # Add watcher via PM handler
            pm_handler.add_task_watcher(task_id, user_id)
            
            return [TextContent(
                type="text",
                text=f"✅ User {user_id} added as watcher to task {task_id}!"
            )]
            
        except Exception as e:
            logger.error(f"Error in add_task_watcher: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error adding watcher: {str(e)}"
            )]
    
    tool_count += 1
    
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
            
            # Bulk update via PM handler
            results = pm_handler.bulk_update_tasks(task_ids, updates)
            
            success_count = len([r for r in results if r.get("success")])
            
            return [TextContent(
                type="text",
                text=f"✅ Bulk update complete!\n\n"
                     f"**Updated:** {success_count}/{len(task_ids)} tasks\n"
                     f"**Fields:** {', '.join(updates.keys())}\n"
            )]
            
        except Exception as e:
            logger.error(f"Error in bulk_update_tasks: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error in bulk update: {str(e)}"
            )]
    
    tool_count += 1
    
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
            
            # Link tasks via PM handler
            pm_handler.link_related_tasks(task_id, related_task_id, relationship_type)
            
            return [TextContent(
                type="text",
                text=f"✅ Tasks linked successfully!\n\n"
                     f"**Relationship:** Task {task_id} {relationship_type} Task {related_task_id}\n"
            )]
            
        except Exception as e:
            logger.error(f"Error in link_related_tasks: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error linking tasks: {str(e)}"
            )]
    
    tool_count += 1
    
    logger.info(f"Registered {tool_count} task interaction tools")
    return tool_count

