# PM Service - Users Tools
"""
User tools using PM Service client.
"""

from typing import Any, Optional

from ..pm_service_base import PMServiceReadTool
from ..decorators import mcp_tool, default_value


@mcp_tool(
    name="list_users",
    description=(
        "List users from PM providers. "
        "Can filter by project to get team members."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Filter by project ID to get team members"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of users to return (default: 100)"
            }
        }
    }
)
class ListUsersTool(PMServiceReadTool):
    """List users."""
    
    async def execute(
        self,
        project_id: Optional[str] = None,
        limit: int = 100
    ) -> dict[str, Any]:
        """
        List users using PM Service.
        
        Note: The PM Service client doesn't support limit parameter.
        All users are fetched and then limited client-side.
        
        If permission errors occur, they will be raised and returned to the agent.
        """
        try:
            async with self.client as client:
                result = await client.list_users(
                    project_id=project_id
                )
            
            # Apply limit client-side (PM Service returns all users)
            all_users = result.get("items", [])
            total = result.get("total", len(all_users))
            limited_users = all_users[:limit] if limit else all_users
            
            # Check if this is a legitimate empty result or if there were permission errors
            # If total is 0 and we have a project_id, it could mean:
            # 1. No users are assigned to the project (legitimate)
            # 2. Permission denied (but we caught it and returned empty)
            # We'll add a note if there were any provider errors
            has_errors = result.get("_has_errors", False)
            
            response = {
                "users": limited_users,
                "total": total,
                "returned": len(limited_users)
            }
            
            # Add informational message if empty result
            if total == 0 and project_id:
                response["message"] = (
                    "No users found in this project. "
                    "This could mean: (1) No team members are assigned to the project, "
                    "or (2) You don't have permission to view project memberships. "
                    "If you expected to see users, please verify project access permissions."
                )
            
            return response
        except PermissionError as e:
            # Re-raise permission errors with clear message
            raise PermissionError(
                f"Permission denied when listing users. {str(e)} "
                "Please contact your administrator or provide a project_id to list users in a specific project."
            ) from e
        except Exception as e:
            # Wrap other errors to provide context
            error_msg = str(e)
            if "403" in error_msg or "Forbidden" in error_msg:
                raise PermissionError(
                    f"Permission denied: {error_msg}. "
                    "Listing users may require administrator permissions. "
                    "If you're trying to list users in a project, make sure the project_id is correct and you have access to it."
                ) from e
            raise


@mcp_tool(
    name="get_user",
    description="Get detailed information about a specific user.",
    input_schema={
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "User ID (format: provider_id:user_id)"
            }
        },
        "required": ["user_id"]
    }
)
class GetUserTool(PMServiceReadTool):
    """Get user details."""
    
    async def execute(self, user_id: str) -> dict[str, Any]:
        """Get user using PM Service."""
        async with self.client as client:
            return await client.get_user(user_id)

