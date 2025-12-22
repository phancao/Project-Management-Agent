# PM Backend - AI Context

## When to Use This Module
- Modifying PM agent behavior
- Adding new agent types
- Changing workflow graph
- Updating PM provider integrations
- Modifying analytics calculations

## Quick Reference

### Key Directories
| Path | Purpose |
|------|---------|
| `agents/` | PM, Planner, React agents |
| `graph/` | Workflow graph builder |
| `pm_providers/` | OpenProject, Jira integrations |
| `analytics/` | Burndown, velocity calculations |
| `tools/` | Agent tools |
| `prompts/` | LLM prompts |

### Agent Flow
```
User Query → Intent Detection → Route to Agent
                                    ↓
            PM Agent ← Planner Agent → React Agent
                 ↓           ↓            ↓
             Direct     Complex      Multi-step
             Query      Planning     Execution
```

### Add a New PM Tool
```python
# backend/tools/my_tool.py
from backend.tools.base import PMTool

class MyTool(PMTool):
    name = "my_tool"
    description = "Does something"
    
    async def execute(self, **kwargs):
        # Implementation
        return result
```

### Graph Nodes
Main nodes in `graph/nodes.py`:
- `detect_intent` - Route query
- `pm_agent` - Direct PM queries
- `planner` - Create execution plans
- `executor` - Execute plan steps

## Don't Forget
- Agents use LangGraph for state management
- PM providers are in `pm_providers/`
- Config in `shared/config/`
- Prompts in `prompts/` folder

## Related Modules
- `shared/` - Base handlers, analytics models
- `mcp_server/` - MCP tool exposures
- `web/` - Frontend UI
