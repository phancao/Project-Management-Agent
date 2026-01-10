"""Get Epic Tool"""
from typing import Any
from ..base import ReadTool
from ..decorators import mcp_tool

@mcp_tool(
    name="get_epic",
    description="Get detailed information about an epic.",
    input_schema={
        "type": "object",
        "properties": {
            "epic_id": {"type": "string", "description": "Epic ID"}
        },
        "required": ["epic_id"]
    }
)
class GetEpicTool(ReadTool):
    async def execute(self, epic_id: str, **kwargs) -> dict[str, Any]:
        provider = await self._get_first_provider()
        return await provider.get_epic(epic_id)
    
    async def _get_first_provider(self):
        providers = self.context.provider_manager.get_active_providers()
        if not providers:
            raise ValueError("No active providers")
        return self.context.provider_manager.create_provider_instance(providers[0])

