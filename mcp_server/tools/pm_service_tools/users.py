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
    
    @default_value("limit", 100)
    async def execute(
        self,
        project_id: Optional[str] = None,
        limit: int = 100
    ) -> dict[str, Any]:
        """List users using PM Service."""
        async with self.client as client:
            result = await client.list_users(
                project_id=project_id,
                limit=limit
            )
        
        return {
            "users": result.get("items", []),
            "total": result.get("total", 0),
            "returned": result.get("returned", 0)
        }


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

