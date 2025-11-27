# Analytics Tools Implementation Plan for MCP Server

## Current Situation

### What We Have

1. **Full Analytics Backend** ✅
   - Location: `src/analytics/`
   - Components:
     - `service.py` - Main analytics service
     - `calculators/` - Burndown, velocity, sprint reports, etc.
     - `adapters/pm_adapter.py` - Integrates with PM providers
     - `models.py` - Data models for charts and reports
   - Status: **Fully implemented and working**

2. **MCP Analytics Tools** ⚠️
   - Location: `mcp_server/tools/analytics.py`
   - Status: **Stub implementations** that just return "not implemented" messages
   - Tools defined: 10 analytics tools (burndown, velocity, sprint_report, etc.)

3. **Backend Analytics Tools** ❌
   - Location: `src/tools/analytics_tools.py`
   - Status: **Broken** - tries to call `get_analytics_service()` which fails
   - Issue: No analytics adapter configured, causing tool execution to fail

### The Problem

When the LLM tries to analyze sprints:
- ❌ Calls broken `src/tools/analytics_tools.py` tools
- ❌ These tools fail because no analytics service is configured
- ✅ MCP PM tools (`list_sprints`, `list_tasks`) work but are ignored
- ✅ Backend analytics service exists but isn't connected to MCP tools

## Solution: Implement Real Analytics in MCP Server

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Agent (Researcher)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              MCP Server Analytics Tools                      │
│  - burndown_chart()                                          │
│  - velocity_chart()                                          │
│  - sprint_report()                                           │
│  - project_health()                                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Backend Analytics Service                       │
│  Location: src/analytics/service.py                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           PM Provider Analytics Adapter                      │
│  Location: src/analytics/adapters/pm_adapter.py              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 PM Provider (OpenProject)                    │
│  - list_sprints()                                            │
│  - list_tasks()                                              │
│  - get_sprint()                                              │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Steps

#### Phase 1: Connect MCP Tools to Analytics Service ⭐ **HIGH PRIORITY**

**File**: `mcp_server/tools/analytics.py`

**Changes Needed**:

1. **Import Analytics Service**
   ```python
   from src.analytics.service import AnalyticsService
   from src.analytics.adapters.pm_adapter import PMProviderAnalyticsAdapter
   from pm_providers.factory import create_pm_provider
   ```

2. **Initialize Analytics Service per Request**
   ```python
   async def _get_analytics_service(project_id: str, pm_handler: MCPPMHandler):
       """Get analytics service for a specific project"""
       # Extract provider_id from composite project_id
       if ":" in project_id:
           provider_id, actual_project_id = project_id.split(":", 1)
       else:
           # Fallback: get first active provider
           providers = pm_handler._get_active_providers()
           if not providers:
               raise ValueError("No active PM providers found")
           provider_id = str(providers[0].id)
           actual_project_id = project_id
       
       # Create PM provider instance
       provider_conn = pm_handler.db.query(PMProviderConnection).filter(
           PMProviderConnection.id == provider_id
       ).first()
       
       if not provider_conn:
           raise ValueError(f"Provider {provider_id} not found")
       
       provider = pm_handler._create_provider_instance(provider_conn)
       
       # Create analytics adapter
       adapter = PMProviderAnalyticsAdapter(provider)
       
       # Create analytics service
       service = AnalyticsService(adapter=adapter)
       
       return service, actual_project_id
   ```

3. **Implement Real Tool Functions**

   **burndown_chart**:
   ```python
   @server.call_tool()
   async def burndown_chart(arguments: dict[str, Any]) -> list[TextContent]:
       """Generate burndown chart data for a sprint."""
       try:
           project_id = arguments.get("project_id")
           sprint_id = arguments.get("sprint_id")
           scope_type = arguments.get("scope_type", "story_points")
           
           if not project_id:
               return [TextContent(type="text", text="Error: project_id is required")]
           
           # Get analytics service
           service, actual_project_id = await _get_analytics_service(project_id, pm_handler)
           
           # Get burndown data
           chart_data = await service.get_burndown_chart(
               project_id=actual_project_id,
               sprint_id=sprint_id,
               scope_type=scope_type
           )
           
           # Format for LLM consumption
           result = {
               "sprint": chart_data.title,
               "total_scope": chart_data.metadata.get("total_scope"),
               "remaining": chart_data.metadata.get("remaining"),
               "completed": chart_data.metadata.get("completed"),
               "completion_percentage": chart_data.metadata.get("completion_percentage"),
               "on_track": chart_data.metadata.get("on_track"),
               "status": chart_data.metadata.get("status"),
               "scope_changes": chart_data.metadata.get("scope_changes", {})
           }
           
           return [TextContent(type="text", text=json.dumps(result, indent=2))]
           
       except Exception as e:
           logger.error(f"Error in burndown_chart: {e}", exc_info=True)
           return [TextContent(type="text", text=f"Error: {str(e)}")]
   ```

   **velocity_chart**:
   ```python
   @server.call_tool()
   async def velocity_chart(arguments: dict[str, Any]) -> list[TextContent]:
       """Calculate team velocity over recent sprints."""
       try:
           project_id = arguments.get("project_id")
           sprint_count = arguments.get("sprint_count", 5)
           
           if not project_id:
               return [TextContent(type="text", text="Error: project_id is required")]
           
           service, actual_project_id = await _get_analytics_service(project_id, pm_handler)
           
           chart_data = await service.get_velocity_chart(
               project_id=actual_project_id,
               sprint_count=sprint_count
           )
           
           result = {
               "average_velocity": chart_data.metadata.get("average_velocity"),
               "median_velocity": chart_data.metadata.get("median_velocity"),
               "latest_velocity": chart_data.metadata.get("latest_velocity"),
               "trend": chart_data.metadata.get("trend"),
               "predictability_score": chart_data.metadata.get("predictability_score"),
               "sprint_count": chart_data.metadata.get("sprint_count"),
               "velocity_range": chart_data.metadata.get("velocity_range", {}),
               "sprints": [
                   {
                       "name": point.label,
                       "committed": committed_series.data[i].value,
                       "completed": completed_series.data[i].value
                   }
                   for i, point in enumerate(chart_data.series[0].data)
               ] if len(chart_data.series) >= 2 else []
           }
           
           return [TextContent(type="text", text=json.dumps(result, indent=2))]
           
       except Exception as e:
           logger.error(f"Error in velocity_chart: {e}", exc_info=True)
           return [TextContent(type="text", text=f"Error: {str(e)}")]
   ```

   **sprint_report**:
   ```python
   @server.call_tool()
   async def sprint_report(arguments: dict[str, Any]) -> list[TextContent]:
       """Generate comprehensive sprint report."""
       try:
           project_id = arguments.get("project_id")
           sprint_id = arguments.get("sprint_id")
           
           if not project_id or not sprint_id:
               return [TextContent(
                   type="text",
                   text="Error: Both project_id and sprint_id are required"
               )]
           
           service, actual_project_id = await _get_analytics_service(project_id, pm_handler)
           
           report = await service.get_sprint_report(
               sprint_id=sprint_id,
               project_id=actual_project_id
           )
           
           # Convert to dict for JSON serialization
           result = {
               "sprint_id": report.sprint_id,
               "sprint_name": report.sprint_name,
               "duration": {
                   "start": report.duration.start.isoformat() if report.duration.start else None,
                   "end": report.duration.end.isoformat() if report.duration.end else None,
                   "days": report.duration.days
               },
               "commitment": {
                   "planned_points": report.commitment.planned_points,
                   "completed_points": report.commitment.completed_points,
                   "completion_rate": report.commitment.completion_rate,
                   "planned_items": report.commitment.planned_items,
                   "completed_items": report.commitment.completed_items
               },
               "scope_changes": {
                   "added": report.scope_changes.added,
                   "removed": report.scope_changes.removed,
                   "net_change": report.scope_changes.net_change,
                   "scope_stability": report.scope_changes.scope_stability
               },
               "work_breakdown": report.work_breakdown,
               "team_performance": {
                   "velocity": report.team_performance.velocity,
                   "capacity_hours": report.team_performance.capacity_hours,
                   "capacity_used": report.team_performance.capacity_used,
                   "capacity_utilized": report.team_performance.capacity_utilized,
                   "team_size": report.team_performance.team_size
               },
               "highlights": report.highlights,
               "concerns": report.concerns
           }
           
           return [TextContent(type="text", text=json.dumps(result, indent=2))]
           
       except Exception as e:
           logger.error(f"Error in sprint_report: {e}", exc_info=True)
           return [TextContent(type="text", text=f"Error: {str(e)}")]
   ```

#### Phase 2: Update Tool Registration

**File**: `mcp_server/server.py`

Ensure analytics tools are registered and enabled by default:

```python
# Register analytics tools
from .tools.analytics import register_analytics_tools

analytics_count = register_analytics_tools(
    server, 
    pm_handler, 
    config,
    tool_names
)
logger.info(f"Registered {analytics_count} analytics tools")
```

#### Phase 3: Remove Broken Backend Analytics Tools

**File**: `src/tools/analytics_tools.py`

**Option A**: Delete the file entirely (recommended)
**Option B**: Add deprecation notice and redirect to MCP tools

```python
# DEPRECATED: These tools are replaced by MCP analytics tools
# Use the MCP server analytics tools instead:
# - burndown_chart (MCP)
# - velocity_chart (MCP)
# - sprint_report (MCP)
# - project_health (MCP)
```

#### Phase 4: Update Agent Configuration

**File**: `src/graph/nodes.py`

Keep analytics tools disabled in researcher_node (already done):

```python
# Analytics tools are now provided via MCP server
# No need to add them here - they're loaded via MCP configuration
```

### Testing Plan

#### Test 1: Burndown Chart
```
Query: "Show me the burndown chart for Sprint 4 in project d7e300c6-d6c0-4c08-bc8d-e41967458d86:478"

Expected:
- Agent calls burndown_chart MCP tool
- Returns actual burndown data with completion percentage
- Shows if sprint is on track
```

#### Test 2: Velocity Chart
```
Query: "What's our team velocity for the last 5 sprints?"

Expected:
- Agent calls velocity_chart MCP tool
- Returns average, median, latest velocity
- Shows trend (increasing/decreasing/stable)
- Shows predictability score
```

#### Test 3: Sprint Report
```
Query: "Give me a comprehensive report for Sprint 4"

Expected:
- Agent calls sprint_report MCP tool
- Returns full sprint analysis with:
  - Commitment vs delivery
  - Scope changes
  - Work breakdown
  - Team performance
  - Highlights and concerns
```

### Benefits

1. **Single Source of Truth** ✅
   - All analytics logic in `src/analytics/`
   - No duplicate implementations

2. **Reusable Components** ✅
   - Same analytics service used by:
     - MCP tools (for AI agents)
     - REST API (for frontend)
     - Direct Python usage

3. **Provider Agnostic** ✅
   - Works with any PM provider (OpenProject, JIRA, etc.)
   - Adapter pattern handles provider differences

4. **Better Tool Descriptions** ✅
   - MCP tools have clear, specific descriptions
   - LLM knows exactly when to use each tool

5. **Real Data** ✅
   - Fetches actual data from PM systems
   - No more "missing data" errors

### Timeline

- **Phase 1**: Implement core analytics tools (burndown, velocity, sprint_report) - **2-3 hours**
- **Phase 2**: Update tool registration - **30 minutes**
- **Phase 3**: Clean up broken backend tools - **30 minutes**
- **Phase 4**: Testing and validation - **1 hour**

**Total**: ~4-5 hours of development work

### Priority

**HIGH PRIORITY** ⭐⭐⭐

This directly fixes the sprint analysis issue and provides the analytics capabilities that users expect.

### Next Steps

1. Implement Phase 1 (core analytics tools in MCP server)
2. Test with real sprint data
3. Verify LLM uses the new tools correctly
4. Clean up old broken tools
5. Document the new analytics capabilities

## Alternative: Quick Fix (Already Done)

We've already implemented a quick fix by disabling the broken analytics tools. This allows the LLM to use the basic MCP PM tools (`list_sprints`, `list_tasks`) directly.

**Pros**:
- ✅ Works immediately
- ✅ No broken tools
- ✅ LLM gets real data

**Cons**:
- ❌ No high-level analytics (burndown, velocity, etc.)
- ❌ LLM has to manually calculate metrics
- ❌ Less sophisticated analysis

The full implementation above provides the best long-term solution with proper analytics capabilities.


