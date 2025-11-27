# MCP Server Refactoring Plan

## Executive Summary

After analyzing the MCP server codebase, I've identified several areas for improvement to enhance maintainability, reduce complexity, and improve the abstraction layer integration.

**Current State**:
- ✅ Good: Service layer exists (`services/`)
- ✅ Good: Analytics abstraction layer is comprehensive
- ⚠️ Issue: Tool files are very large (800+ lines)
- ⚠️ Issue: Repetitive tool registration patterns
- ⚠️ Issue: Analytics tools don't fully leverage the abstraction layer
- ⚠️ Issue: Server.py has complex tool routing logic (190 lines)
- ⚠️ Issue: PM Handler mixes provider management with business logic

**Proposed Refactoring**: Modular, layered architecture with clear separation of concerns.

---

## Current Architecture Analysis

### File Sizes (Lines of Code)
```
mcp_server/tools/
  - tasks.py:            803 lines ⚠️ Too large
  - analytics.py:        758 lines ⚠️ Too large
  - sprints.py:          566 lines ⚠️ Too large
  - projects.py:         556 lines ⚠️ Too large
  - epics.py:            471 lines ⚠️ Too large
  - provider_config.py:  435 lines ⚠️ Too large
  - task_interactions.py: 271 lines ⚠️ Moderate
  - users.py:            254 lines ✅ Acceptable
```

### Issues Identified

#### 1. **Large Tool Files** (High Priority)
- **Problem**: Tool files are 400-800 lines, mixing concerns
- **Impact**: Hard to maintain, test, and understand
- **Solution**: Split into smaller, focused modules

#### 2. **Repetitive Tool Registration** (Medium Priority)
- **Problem**: Each tool file has similar registration patterns
- **Impact**: Code duplication, inconsistent error handling
- **Solution**: Create tool registration decorators/helpers

#### 3. **Analytics Integration** (Medium Priority)
- **Problem**: Analytics tools have custom `_get_analytics_service()` logic
- **Impact**: Not fully leveraging the abstraction layer
- **Solution**: Integrate analytics service into PM Handler

#### 4. **Complex Tool Routing** (Medium Priority)
- **Problem**: `server.py` has 190 lines of tool routing logic
- **Impact**: Hard to understand, maintain
- **Solution**: Simplify using tool registry service

#### 5. **PM Handler Responsibilities** (Low Priority)
- **Problem**: PM Handler mixes provider management with business logic
- **Impact**: Tight coupling, hard to test
- **Solution**: Split into ProviderManager and BusinessLogic layers

---

## Proposed Architecture

### New Structure

```
mcp_server/
├── server.py                    # Main server (simplified)
├── config.py                    # Configuration
├── pm_handler.py                # PM Handler (refactored)
│
├── core/                        # NEW: Core business logic
│   ├── __init__.py
│   ├── provider_manager.py      # Provider lifecycle management
│   ├── analytics_manager.py     # Analytics service integration
│   └── tool_context.py          # Shared context for tools
│
├── services/                    # Existing service layer
│   ├── auth_service.py          # Authentication
│   ├── user_context.py          # User-scoped servers
│   └── tool_registry.py         # Tool registration
│
├── tools/                       # Refactored tools
│   ├── __init__.py
│   ├── base.py                  # NEW: Base tool classes
│   ├── decorators.py            # NEW: Tool registration decorators
│   │
│   ├── projects/                # NEW: Project tools (split)
│   │   ├── __init__.py
│   │   ├── list.py              # list_projects
│   │   ├── get.py               # get_project
│   │   ├── create.py            # create_project
│   │   ├── update.py            # update_project
│   │   └── search.py            # search_projects
│   │
│   ├── tasks/                   # NEW: Task tools (split)
│   │   ├── __init__.py
│   │   ├── list.py              # list_tasks, list_my_tasks
│   │   ├── get.py               # get_task
│   │   ├── create.py            # create_task
│   │   ├── update.py            # update_task
│   │   ├── assign.py            # assign_task
│   │   ├── status.py            # update_task_status
│   │   └── interactions.py      # comments, watchers, links
│   │
│   ├── sprints/                 # NEW: Sprint tools (split)
│   │   ├── __init__.py
│   │   ├── list.py              # list_sprints
│   │   ├── get.py               # get_sprint, get_sprint_tasks
│   │   ├── create.py            # create_sprint
│   │   ├── update.py            # update_sprint
│   │   ├── lifecycle.py         # start_sprint, complete_sprint
│   │   └── tasks.py             # add_task_to_sprint, remove_task_from_sprint
│   │
│   ├── epics/                   # NEW: Epic tools (split)
│   │   ├── __init__.py
│   │   ├── list.py              # list_epics
│   │   ├── get.py               # get_epic, get_epic_progress
│   │   ├── create.py            # create_epic
│   │   ├── update.py            # update_epic
│   │   └── tasks.py             # link_task_to_epic, unlink_task_from_epic
│   │
│   ├── analytics/               # NEW: Analytics tools (split)
│   │   ├── __init__.py
│   │   ├── burndown.py          # burndown_chart
│   │   ├── velocity.py          # velocity_chart
│   │   ├── sprint_report.py     # sprint_report
│   │   ├── project_health.py    # project_health
│   │   ├── task_distribution.py # task_distribution
│   │   └── team_performance.py  # team_performance
│   │
│   ├── users/                   # Users tools (keep as is)
│   │   ├── __init__.py
│   │   └── users.py
│   │
│   └── provider_config/         # Provider config tools
│       ├── __init__.py
│       └── config.py
│
├── database/                    # Database layer
│   ├── connection.py
│   └── models.py
│
├── auth/                        # Authentication
│   └── ...
│
└── transports/                  # Transport layers
    ├── http.py
    ├── sse.py
    └── stdio.py
```

---

## Refactoring Steps

### Phase 1: Core Infrastructure (2-3 hours)

#### Step 1.1: Create Core Modules
- [ ] Create `core/provider_manager.py`
  - Extract provider management from PM Handler
  - Methods: `get_active_providers()`, `create_provider_instance()`, `get_provider_by_id()`
  
- [ ] Create `core/analytics_manager.py`
  - Integrate analytics service with provider manager
  - Methods: `get_analytics_service()`, `get_burndown()`, `get_velocity()`, etc.
  
- [ ] Create `core/tool_context.py`
  - Shared context for all tools
  - Contains: `provider_manager`, `analytics_manager`, `db_session`, `user_id`

#### Step 1.2: Create Tool Base Classes
- [ ] Create `tools/base.py`
  - `BaseTool`: Abstract base class for all tools
  - `ReadTool`: For read-only operations (list, get)
  - `WriteTool`: For write operations (create, update, delete)
  - `AnalyticsTool`: For analytics operations

#### Step 1.3: Create Tool Decorators
- [ ] Create `tools/decorators.py`
  - `@mcp_tool`: Decorator for tool registration
  - `@require_project`: Decorator for tools requiring project_id
  - `@require_provider`: Decorator for tools requiring provider_id
  - Automatic error handling, logging, validation

### Phase 2: Refactor Analytics Tools (1-2 hours)

#### Step 2.1: Split Analytics Tools
- [ ] Create `tools/analytics/burndown.py`
  - Move `burndown_chart` tool
  - Use `AnalyticsManager` instead of custom logic
  
- [ ] Create `tools/analytics/velocity.py`
  - Move `velocity_chart` tool
  
- [ ] Create `tools/analytics/sprint_report.py`
  - Move `sprint_report` tool
  
- [ ] Create `tools/analytics/project_health.py`
  - Move `project_health` tool

#### Step 2.2: Integrate with Analytics Manager
- [ ] Update tools to use `context.analytics_manager`
- [ ] Remove custom `_get_analytics_service()` logic
- [ ] Simplify error handling

### Phase 3: Refactor Project Tools (1-2 hours)

#### Step 3.1: Split Project Tools
- [ ] Create `tools/projects/list.py` - `list_projects`
- [ ] Create `tools/projects/get.py` - `get_project`
- [ ] Create `tools/projects/create.py` - `create_project`
- [ ] Create `tools/projects/update.py` - `update_project`
- [ ] Create `tools/projects/search.py` - `search_projects`

#### Step 3.2: Use Base Classes
- [ ] Inherit from `ReadTool` or `WriteTool`
- [ ] Use decorators for common patterns
- [ ] Simplify error handling

### Phase 4: Refactor Task Tools (2-3 hours)

#### Step 4.1: Split Task Tools
- [ ] Create `tools/tasks/list.py` - `list_tasks`, `list_my_tasks`
- [ ] Create `tools/tasks/get.py` - `get_task`
- [ ] Create `tools/tasks/create.py` - `create_task`
- [ ] Create `tools/tasks/update.py` - `update_task`
- [ ] Create `tools/tasks/assign.py` - `assign_task`
- [ ] Create `tools/tasks/status.py` - `update_task_status`
- [ ] Create `tools/tasks/interactions.py` - `add_task_comment`, `add_task_watcher`, `link_related_tasks`

#### Step 4.2: Use Base Classes
- [ ] Inherit from `ReadTool` or `WriteTool`
- [ ] Use decorators for validation
- [ ] Simplify error handling

### Phase 5: Refactor Sprint Tools (1-2 hours)

#### Step 5.1: Split Sprint Tools
- [ ] Create `tools/sprints/list.py` - `list_sprints`
- [ ] Create `tools/sprints/get.py` - `get_sprint`, `get_sprint_tasks`
- [ ] Create `tools/sprints/create.py` - `create_sprint`
- [ ] Create `tools/sprints/update.py` - `update_sprint`
- [ ] Create `tools/sprints/lifecycle.py` - `start_sprint`, `complete_sprint`
- [ ] Create `tools/sprints/tasks.py` - `add_task_to_sprint`, `remove_task_from_sprint`

### Phase 6: Refactor Epic Tools (1 hour)

#### Step 6.1: Split Epic Tools
- [ ] Create `tools/epics/list.py` - `list_epics`
- [ ] Create `tools/epics/get.py` - `get_epic`, `get_epic_progress`
- [ ] Create `tools/epics/create.py` - `create_epic`
- [ ] Create `tools/epics/update.py` - `update_epic`
- [ ] Create `tools/epics/tasks.py` - `link_task_to_epic`, `unlink_task_from_epic`

### Phase 7: Simplify Server (1 hour)

#### Step 7.1: Use Tool Registry
- [ ] Refactor `server.py` to use `ToolRegistry` service
- [ ] Simplify tool routing logic
- [ ] Remove manual tool tracking

#### Step 7.2: Clean Up
- [ ] Remove old tool files
- [ ] Update imports
- [ ] Update documentation

### Phase 8: Testing & Documentation (1-2 hours)

#### Step 8.1: Testing
- [ ] Test all refactored tools
- [ ] Verify analytics integration
- [ ] Test with real PM providers

#### Step 8.2: Documentation
- [ ] Update README
- [ ] Document new architecture
- [ ] Create migration guide

---

## Benefits of Refactoring

### 1. **Maintainability** ✅
- Smaller files (50-150 lines each)
- Single responsibility per module
- Easier to understand and modify

### 2. **Testability** ✅
- Each tool can be tested independently
- Mock dependencies easily
- Clear test boundaries

### 3. **Extensibility** ✅
- Easy to add new tools
- Consistent patterns
- Reusable base classes

### 4. **Performance** ✅
- Better code organization
- Easier to optimize
- Clear dependency graph

### 5. **Developer Experience** ✅
- Easier onboarding
- Clear structure
- Consistent patterns

---

## Example: Before vs. After

### Before: `tools/analytics.py` (758 lines)

```python
# tools/analytics.py (758 lines)

async def _get_analytics_service(project_id, pm_handler):
    # 88 lines of custom logic
    if ":" in project_id:
        provider_id, actual_project_id = project_id.split(":", 1)
    else:
        providers = pm_handler._get_active_providers()
        if not providers:
            raise ValueError("No active PM providers found")
        provider_id = str(providers[0].id)
        actual_project_id = project_id
    
    # Get provider from database
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


def register_analytics_tools(server, pm_handler, config, tool_names, tool_functions):
    tool_count = 0
    
    @server.call_tool()
    async def burndown_chart(arguments: dict[str, Any]) -> list[TextContent]:
        # 50+ lines
        try:
            project_id = arguments.get("project_id")
            if not project_id:
                return [TextContent(type="text", text="Error: project_id is required")]
            
            sprint_id = arguments.get("sprint_id")
            scope_type = arguments.get("scope_type", "story_points")
            
            service, actual_project_id = await _get_analytics_service(project_id, pm_handler)
            
            result = await service.get_burndown_chart(
                project_id=actual_project_id,
                sprint_id=sprint_id,
                scope_type=scope_type
            )
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            logger.error(f"Error in burndown_chart: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    tool_count += 1
    # ... repeat for 10+ more tools
    
    return tool_count
```

### After: `tools/analytics/burndown.py` (~50 lines)

```python
# tools/analytics/burndown.py (~50 lines)

from ..base import AnalyticsTool
from ..decorators import mcp_tool, require_project

@mcp_tool(
    name="burndown_chart",
    description="Generate burndown chart data for a sprint to track progress."
)
@require_project
class BurndownChartTool(AnalyticsTool):
    """
    Burndown chart tool.
    
    Shows how much work remains in a sprint over time, comparing actual progress 
    against an ideal burndown line.
    """
    
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
        # Get analytics service from context (managed by AnalyticsManager)
        service = await self.context.analytics_manager.get_service(project_id)
        
        # Call analytics service
        result = await service.get_burndown_chart(
            project_id=project_id,
            sprint_id=sprint_id,
            scope_type=scope_type
        )
        
        return result
```

### After: `core/analytics_manager.py` (~100 lines)

```python
# core/analytics_manager.py (~100 lines)

class AnalyticsManager:
    """
    Analytics Manager - Integrates analytics service with provider manager.
    
    Handles:
    - Creating analytics services for projects
    - Caching analytics services
    - Managing analytics adapters
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
        
        # Parse composite project ID
        provider_id, actual_project_id = self._parse_project_id(project_id)
        
        # Get provider from provider manager
        provider = await self.provider_manager.get_provider(provider_id)
        
        # Create analytics adapter
        adapter = PMProviderAnalyticsAdapter(provider)
        
        # Create analytics service
        service = AnalyticsService(adapter=adapter)
        
        # Cache service
        self._service_cache[project_id] = service
        
        return service
    
    def _parse_project_id(self, project_id: str) -> tuple[str, str]:
        """Parse composite project ID into provider_id and project_key."""
        if ":" in project_id:
            provider_id, actual_project_id = project_id.split(":", 1)
            return provider_id, actual_project_id
        else:
            # Fallback: get first active provider
            providers = self.provider_manager.get_active_providers()
            if not providers:
                raise ValueError("No active PM providers found")
            return str(providers[0].id), project_id
```

---

## Migration Strategy

### Approach: Incremental Refactoring

1. **Phase 1**: Create core infrastructure (no breaking changes)
2. **Phase 2**: Refactor analytics tools (test thoroughly)
3. **Phase 3-6**: Refactor other tools one module at a time
4. **Phase 7**: Simplify server (final integration)
5. **Phase 8**: Clean up old code

### Backward Compatibility

- Keep old tool files during migration
- Deprecate old imports gradually
- Provide migration guide
- Test both old and new implementations

### Testing Strategy

1. **Unit Tests**: Test each tool independently
2. **Integration Tests**: Test with real PM providers
3. **Regression Tests**: Ensure no breaking changes
4. **Performance Tests**: Verify no performance degradation

---

## Timeline Estimate

| Phase | Description | Time | Priority |
|-------|-------------|------|----------|
| Phase 1 | Core Infrastructure | 2-3 hours | High |
| Phase 2 | Analytics Tools | 1-2 hours | High |
| Phase 3 | Project Tools | 1-2 hours | Medium |
| Phase 4 | Task Tools | 2-3 hours | Medium |
| Phase 5 | Sprint Tools | 1-2 hours | Medium |
| Phase 6 | Epic Tools | 1 hour | Low |
| Phase 7 | Simplify Server | 1 hour | Medium |
| Phase 8 | Testing & Docs | 1-2 hours | High |
| **Total** | | **10-17 hours** | |

---

## Risks & Mitigation

### Risk 1: Breaking Changes
- **Mitigation**: Incremental refactoring, keep old code during migration
- **Testing**: Comprehensive regression tests

### Risk 2: Performance Degradation
- **Mitigation**: Profile before/after, optimize hot paths
- **Testing**: Performance benchmarks

### Risk 3: Incomplete Migration
- **Mitigation**: Clear checklist, automated tests
- **Testing**: Integration tests for all tools

### Risk 4: Developer Confusion
- **Mitigation**: Clear documentation, migration guide
- **Communication**: Team review, pair programming

---

## Decision: Proceed with Refactoring?

### Recommendation: **YES - Proceed with Phase 1 & 2**

**Rationale**:
1. Analytics tools are already causing issues (as seen in sprint analysis failure)
2. Core infrastructure will benefit all future development
3. Incremental approach minimizes risk
4. Clear benefits in maintainability and extensibility

**Start with**:
- Phase 1: Core Infrastructure (2-3 hours)
- Phase 2: Analytics Tools (1-2 hours)
- **Total**: 3-5 hours for immediate value

**Defer**:
- Phases 3-6 can be done later as needed
- Not urgent, but beneficial for long-term maintainability

---

## Next Steps

If approved, I will:

1. ✅ Create `core/` directory structure
2. ✅ Implement `ProviderManager`
3. ✅ Implement `AnalyticsManager`
4. ✅ Implement `ToolContext`
5. ✅ Create `tools/base.py` with base classes
6. ✅ Create `tools/decorators.py` with decorators
7. ✅ Refactor analytics tools to use new structure
8. ✅ Test with real OpenProject data
9. ✅ Document changes

**Estimated time for Phase 1 & 2**: 3-5 hours

Shall I proceed with the refactoring?


