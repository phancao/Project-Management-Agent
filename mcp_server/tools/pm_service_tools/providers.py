# PM Service - Providers Tools
"""
Provider tools using PM Service client.
"""

from typing import Any

from ..pm_service_base import PMServiceReadTool
from ..decorators import mcp_tool


@mcp_tool(
    name="list_providers",
    description="List all configured PM providers and their status.",
    input_schema={
        "type": "object",
        "properties": {}
    }
)
class ListProvidersTool(PMServiceReadTool):
    """List configured providers."""
    
    async def execute(self) -> dict[str, Any]:
        """List providers using PM Service."""
        async with self.client as client:
            result = await client.list_providers()
        
        return {
            "providers": result.get("items", []),
            "total": result.get("total", 0)
        }

