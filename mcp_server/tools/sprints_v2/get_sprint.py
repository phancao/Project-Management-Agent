"""Get Sprint Tool"""
from typing import Any
from ..base import ReadTool
from ..decorators import mcp_tool, require_sprint

@mcp_tool(
    name="get_sprint",
    description="Get detailed information about a sprint.",
    input_schema={
        "type": "object",
        "properties": {
            "sprint_id": {"type": "string", "description": "Sprint ID"}
        },
        "required": ["sprint_id"]
    }
)
class GetSprintTool(ReadTool):
    @require_sprint
    async def execute(self, sprint_id: str, **kwargs) -> dict[str, Any]:
        provider = await self._get_first_provider()
        return await provider.get_sprint(sprint_id)
    
    async def _get_first_provider(self):
        providers = self.context.provider_manager.get_active_providers()
        if not providers:
            raise ValueError("No active providers")
        return self.context.provider_manager.create_provider_instance(providers[0])

