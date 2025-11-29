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
            "sprint_id": {"type": "string", "description": "Sprint ID (numeric ID like '613' or composite like 'provider_id:613')"}
        },
        "required": ["sprint_id"]
    }
)
class GetSprintTool(ReadTool):
    @require_sprint
    async def execute(self, sprint_id: str, **kwargs) -> dict[str, Any]:
        # Extract numeric sprint ID if composite format (provider_id:sprint_id)
        actual_sprint_id = sprint_id
        provider_id = None
        
        if ":" in sprint_id:
            parts = sprint_id.split(":", 1)
            provider_id = parts[0]
            actual_sprint_id = parts[1]
        
        # Get provider
        if provider_id:
            provider = await self.context.provider_manager.get_provider(provider_id)
        else:
            provider = await self._get_first_provider()
        
        return await provider.get_sprint(actual_sprint_id)
    
    async def _get_first_provider(self):
        providers = self.context.provider_manager.get_active_providers()
        if not providers:
            raise ValueError("No active providers")
        return self.context.provider_manager.create_provider_instance(providers[0])

