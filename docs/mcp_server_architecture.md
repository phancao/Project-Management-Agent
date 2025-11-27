# MCP Server Architecture - Current vs. Proposed

## Current Architecture Issues

### Problem 1: Large Tool Files
```
Current Tool Files:
├── tasks.py            803 lines ⚠️ Too large
├── analytics.py        758 lines ⚠️ Too large
├── sprints.py          566 lines ⚠️ Too large
├── projects.py         556 lines ⚠️ Too large
├── epics.py            471 lines ⚠️ Too large
└── provider_config.py  435 lines ⚠️ Too large
```

**Impact**: Hard to maintain, test, and understand

### Problem 2: Repetitive Patterns
Every tool file has similar boilerplate:
```python
def register_X_tools(server, pm_handler, config, tool_names, tool_functions):
    tool_count = 0
    
    @server.call_tool()
    async def tool_1(arguments):
        try:
            # Validate arguments
            # Extract parameters
            # Call provider
            # Format response
            # Return result
        except Exception as e:
            logger.error(...)
            return error_response
    
    tool_count += 1
    # Repeat 10+ times...
```

**Impact**: Code duplication, inconsistent error handling

### Problem 3: Analytics Not Using Abstraction Layer
```python
# Current: Custom logic in every analytics tool
async def _get_analytics_service(project_id, pm_handler):
    # 88 lines of custom logic
    if ":" in project_id:
        provider_id, actual_project_id = project_id.split(":", 1)
    else:
        providers = pm_handler._get_active_providers()
        ...
    
    provider_conn = pm_handler.db.query(PMProviderConnection).filter(...)
    provider = pm_handler._create_provider_instance(provider_conn)
    adapter = PMProviderAnalyticsAdapter(provider)
    service = AnalyticsService(adapter=adapter)
    return service, actual_project_id
```

**Impact**: Not leveraging the abstraction layer properly

---

## Proposed Architecture

### New Structure Overview

```
mcp_server/
├── server.py                    # Main server (simplified)
├── config.py                    # Configuration
├── pm_handler.py                # PM Handler (refactored)
│
├── core/                        # NEW: Core business logic
│   ├── provider_manager.py      # Provider lifecycle
│   ├── analytics_manager.py     # Analytics integration
│   └── tool_context.py          # Shared context
│
├── services/                    # Existing services
│   ├── auth_service.py
│   ├── user_context.py
│   └── tool_registry.py
│
├── tools/                       # Refactored tools
│   ├── base.py                  # NEW: Base classes
│   ├── decorators.py            # NEW: Decorators
│   │
│   ├── analytics/               # Split into modules
│   │   ├── burndown.py
│   │   ├── velocity.py
│   │   ├── sprint_report.py
│   │   └── project_health.py
│   │
│   ├── projects/                # Split into modules
│   │   ├── list.py
│   │   ├── get.py
│   │   ├── create.py
│   │   └── update.py
│   │
│   ├── tasks/                   # Split into modules
│   │   ├── list.py
│   │   ├── get.py
│   │   ├── create.py
│   │   ├── update.py
│   │   └── interactions.py
│   │
│   └── ... (sprints, epics, users)
│
└── ... (database, auth, transports)
```

### Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server (server.py)                    │
│  - Tool registration                                         │
│  - Request routing                                           │
│  - Protocol handling                                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Services Layer                             │
│  - AuthService: Authentication                               │
│  - UserContext: User-scoped servers                          │
│  - ToolRegistry: Tool registration                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Core Layer (NEW)                           │
│  - ProviderManager: Provider lifecycle                       │
│  - AnalyticsManager: Analytics integration                   │
│  - ToolContext: Shared context for tools                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Tools Layer                                │
│  - Base classes: BaseTool, ReadTool, WriteTool               │
│  - Decorators: @mcp_tool, @require_project                   │
│  - Tool implementations: analytics, projects, tasks, etc.    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Analytics Abstraction Layer                     │
│  - AnalyticsService                                          │
│  - BaseAnalyticsAdapter                                      │
│  - TaskStatusResolver                                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   PM Providers                               │
│  - BasePMProvider                                            │
│  - OpenProject, JIRA, ClickUp, etc.                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Actual PM Systems                          │
│  - OpenProject API, JIRA API, etc.                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Example: Analytics Tool Refactoring

### Before: `tools/analytics.py` (758 lines)

```python
# tools/analytics.py (758 lines total)

# Custom helper function (88 lines)
async def _get_analytics_service(project_id, pm_handler):
    # Parse project ID
    if ":" in project_id:
        provider_id, actual_project_id = project_id.split(":", 1)
    else:
        providers = pm_handler._get_active_providers()
        if not providers:
            raise ValueError("No active PM providers found")
        provider_id = str(providers[0].id)
        actual_project_id = project_id
    
    # Get provider from database
    if not pm_handler.db:
        raise ValueError("Database session not available")
    
    provider_conn = pm_handler.db.query(PMProviderConnection).filter(
        PMProviderConnection.id == provider_id
    ).first()
    
    if not provider_conn:
        raise ValueError(f"Provider {provider_id} not found")
    
    # Create provider instance
    provider = pm_handler._create_provider_instance(provider_conn)
    
    # Create analytics adapter
    adapter = PMProviderAnalyticsAdapter(provider)
    
    # Create analytics service
    service = AnalyticsService(adapter=adapter)
    
    return service, actual_project_id


# Tool registration function (670 lines)
def register_analytics_tools(server, pm_handler, config, tool_names, tool_functions):
    tool_count = 0
    
    # Tool 1: burndown_chart (150 lines)
    @server.call_tool()
    async def burndown_chart(arguments: dict[str, Any]) -> list[TextContent]:
        """Generate burndown chart..."""
        try:
            # Validate arguments (10 lines)
            project_id = arguments.get("project_id")
            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required. Please provide the project ID."
                )]
            
            sprint_id = arguments.get("sprint_id")
            scope_type = arguments.get("scope_type", "story_points")
            
            # Log (5 lines)
            logger.info(
                f"[burndown_chart] Called with project_id={project_id}, "
                f"sprint_id={sprint_id}, scope_type={scope_type}"
            )
            
            # Get analytics service (3 lines)
            service, actual_project_id = await _get_analytics_service(project_id, pm_handler)
            
            # Call service (5 lines)
            result = await service.get_burndown_chart(
                project_id=actual_project_id,
                sprint_id=sprint_id,
                scope_type=scope_type
            )
            
            # Format response (20 lines)
            response = {
                "sprint_name": result.get("sprint_name"),
                "start_date": result.get("start_date"),
                # ... 15 more lines
            }
            
            # Return (5 lines)
            logger.info(f"[burndown_chart] Completed successfully")
            return [TextContent(
                type="text",
                text=json.dumps(response, indent=2, default=str)
            )]
        except Exception as e:
            # Error handling (10 lines)
            logger.error(f"[burndown_chart] Error: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error generating burndown chart: {str(e)}"
            )]
    
    tool_count += 1
    tool_names.append("burndown_chart")
    tool_functions["burndown_chart"] = burndown_chart
    
    # Tool 2: velocity_chart (150 lines) - similar structure
    # Tool 3: sprint_report (150 lines) - similar structure
    # Tool 4: project_health (150 lines) - similar structure
    # ... more tools
    
    return tool_count
```

### After: Modular Structure

#### `core/analytics_manager.py` (~100 lines)
```python
"""
Analytics Manager - Integrates analytics service with provider manager.
"""

class AnalyticsManager:
    """
    Manages analytics services for projects.
    
    Handles:
    - Creating analytics services
    - Caching services
    - Managing adapters
    """
    
    def __init__(self, provider_manager: ProviderManager):
        self.provider_manager = provider_manager
        self._service_cache: dict[str, AnalyticsService] = {}
    
    async def get_service(self, project_id: str) -> AnalyticsService:
        """
        Get analytics service for a project.
        
        Args:
            project_id: Project ID (may be composite "provider_id:project_key")
        
        Returns:
            AnalyticsService instance
        """
        # Check cache
        if project_id in self._service_cache:
            return self._service_cache[project_id]
        
        # Parse project ID
        provider_id, actual_project_id = self._parse_project_id(project_id)
        
        # Get provider
        provider = await self.provider_manager.get_provider(provider_id)
        
        # Create adapter
        adapter = PMProviderAnalyticsAdapter(provider)
        
        # Create service
        service = AnalyticsService(adapter=adapter)
        
        # Cache
        self._service_cache[project_id] = service
        
        return service
    
    def _parse_project_id(self, project_id: str) -> tuple[str, str]:
        """Parse composite project ID."""
        if ":" in project_id:
            return project_id.split(":", 1)
        else:
            providers = self.provider_manager.get_active_providers()
            if not providers:
                raise ValueError("No active PM providers found")
            return str(providers[0].id), project_id
```

#### `tools/base.py` (~150 lines)
```python
"""
Base classes for MCP tools.
"""

class BaseTool(ABC):
    """Base class for all MCP tools."""
    
    def __init__(self, context: ToolContext):
        self.context = context
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool."""
        pass
    
    async def __call__(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        MCP tool entry point.
        
        Handles:
        - Argument validation
        - Logging
        - Error handling
        - Response formatting
        """
        try:
            # Log
            logger.info(f"[{self.__class__.__name__}] Called with {arguments}")
            
            # Execute
            result = await self.execute(**arguments)
            
            # Format
            response = self._format_response(result)
            
            # Log success
            logger.info(f"[{self.__class__.__name__}] Completed successfully")
            
            return [TextContent(type="text", text=response)]
        except Exception as e:
            # Log error
            logger.error(f"[{self.__class__.__name__}] Error: {e}", exc_info=True)
            
            # Return error
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    def _format_response(self, result: Any) -> str:
        """Format response as JSON."""
        return json.dumps(result, indent=2, default=str)


class AnalyticsTool(BaseTool):
    """Base class for analytics tools."""
    
    async def get_analytics_service(self, project_id: str) -> AnalyticsService:
        """Get analytics service from context."""
        return await self.context.analytics_manager.get_service(project_id)
```

#### `tools/decorators.py` (~100 lines)
```python
"""
Decorators for MCP tools.
"""

def mcp_tool(name: str, description: str):
    """
    Decorator for MCP tool registration.
    
    Usage:
        @mcp_tool(name="my_tool", description="My tool description")
        class MyTool(BaseTool):
            async def execute(self, **kwargs):
                ...
    """
    def decorator(cls):
        cls._mcp_name = name
        cls._mcp_description = description
        return cls
    return decorator


def require_project(func):
    """
    Decorator to require project_id argument.
    
    Usage:
        @require_project
        async def execute(self, project_id: str, **kwargs):
            ...
    """
    @wraps(func)
    async def wrapper(self, **kwargs):
        if "project_id" not in kwargs:
            raise ValueError("project_id is required")
        return await func(self, **kwargs)
    return wrapper
```

#### `tools/analytics/burndown.py` (~50 lines)
```python
"""
Burndown chart tool.
"""

from ..base import AnalyticsTool
from ..decorators import mcp_tool, require_project


@mcp_tool(
    name="burndown_chart",
    description="Generate burndown chart data for a sprint to track progress."
)
class BurndownChartTool(AnalyticsTool):
    """
    Burndown chart tool.
    
    Shows how much work remains in a sprint over time.
    """
    
    @require_project
    async def execute(
        self,
        project_id: str,
        sprint_id: str | None = None,
        scope_type: str = "story_points"
    ) -> dict[str, Any]:
        """
        Generate burndown chart.
        
        Args:
            project_id: Project ID (format: "provider_uuid:project_key")
            sprint_id: Sprint ID (uses current/active sprint if not provided)
            scope_type: What to measure - "story_points", "tasks", or "hours"
        
        Returns:
            Burndown chart data
        """
        # Get analytics service (from context)
        service = await self.get_analytics_service(project_id)
        
        # Call analytics service
        result = await service.get_burndown_chart(
            project_id=project_id,
            sprint_id=sprint_id,
            scope_type=scope_type
        )
        
        return result
```

---

## Benefits Comparison

### Before: Monolithic File (758 lines)
- ❌ Hard to navigate
- ❌ Repetitive code
- ❌ Custom logic in every tool
- ❌ Difficult to test
- ❌ Hard to maintain

### After: Modular Structure (50-150 lines per file)
- ✅ Easy to navigate
- ✅ DRY (Don't Repeat Yourself)
- ✅ Reuses abstraction layer
- ✅ Easy to test
- ✅ Easy to maintain

---

## File Size Comparison

### Before
```
tools/analytics.py:        758 lines (monolithic)
```

### After
```
core/analytics_manager.py: 100 lines (reusable)
tools/base.py:             150 lines (reusable)
tools/decorators.py:       100 lines (reusable)
tools/analytics/
  ├── burndown.py:          50 lines
  ├── velocity.py:          50 lines
  ├── sprint_report.py:     50 lines
  └── project_health.py:    50 lines
─────────────────────────────────────
Total:                     550 lines (vs. 758)
Reusable infrastructure:   350 lines (benefits all tools)
Per-tool code:              50 lines (vs. 150-200)
```

**Reduction**: ~27% less code, much more maintainable!

---

## Refactoring Timeline

### Phase 1: Core Infrastructure (2-3 hours) - HIGH PRIORITY
- Create `core/provider_manager.py`
- Create `core/analytics_manager.py`
- Create `core/tool_context.py`
- Create `tools/base.py`
- Create `tools/decorators.py`

### Phase 2: Analytics Tools (1-2 hours) - HIGH PRIORITY
- Split `tools/analytics.py` into modules
- Use `AnalyticsManager` instead of custom logic
- Test with real data

### Phase 3-6: Other Tools (5-8 hours) - MEDIUM PRIORITY
- Refactor projects, tasks, sprints, epics
- Can be done incrementally

### Phase 7: Simplify Server (1 hour) - MEDIUM PRIORITY
- Use `ToolRegistry` service
- Simplify routing logic

### Phase 8: Testing & Docs (1-2 hours) - HIGH PRIORITY
- Test all refactored tools
- Update documentation

**Total**: 10-17 hours

---

## Recommendation

✅ **Proceed with Phase 1 & 2 (3-5 hours)**

**Rationale**:
1. Analytics tools are already causing issues
2. Core infrastructure benefits all future development
3. Immediate value with minimal risk
4. Clear path to completion

**Defer Phases 3-6** until needed (not urgent).

---

## Next Steps

If approved:
1. Create `core/` directory structure
2. Implement `ProviderManager`, `AnalyticsManager`, `ToolContext`
3. Create base classes and decorators
4. Refactor analytics tools
5. Test with real OpenProject data
6. Document changes

**Ready to proceed?** 🚀


