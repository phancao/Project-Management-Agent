# Tool Deprecation Notice

## Overview

The following tool modules have been refactored and moved to v2 architecture. The old registration functions are now deprecated and will be removed in a future version.

**Date**: November 27, 2025  
**Status**: Deprecated (still functional)  
**Removal**: Planned for Q2 2026

---

## Deprecated Modules

### ❌ `tools/analytics.py` - DEPRECATED
**Replacement**: `tools/analytics_v2/`  
**Status**: Deprecated  
**Reason**: Refactored to use new architecture with proper abstraction layer integration

**Migration**:
```python
# Old (deprecated)
from mcp_server.tools import register_analytics_tools

# New (recommended)
from mcp_server.tools.analytics_v2.register import register_analytics_tools_v2
```

### ⚠️ `tools/projects.py` - LEGACY MODE
**Replacement**: `tools/projects_v2/`  
**Status**: Legacy (wrapped in v2)  
**Reason**: Now uses hybrid approach with new architecture

**Migration**:
```python
# Old (legacy)
from mcp_server.tools import register_project_tools

# New (recommended)
from mcp_server.tools.projects_v2.register import register_project_tools_v2
```

### ⚠️ `tools/tasks.py` - LEGACY MODE
**Replacement**: `tools/tasks_v2/`  
**Status**: Legacy (wrapped in v2)  
**Reason**: Now uses hybrid approach with new architecture

**Migration**:
```python
# Old (legacy)
from mcp_server.tools import register_task_tools

# New (recommended)
from mcp_server.tools.tasks_v2.register import register_task_tools_v2
```

### ⚠️ `tools/sprints.py` - LEGACY MODE
**Replacement**: `tools/sprints_v2/`  
**Status**: Legacy (wrapped in v2)  
**Reason**: Now uses hybrid approach with new architecture

**Migration**:
```python
# Old (legacy)
from mcp_server.tools import register_sprint_tools

# New (recommended)
from mcp_server.tools.sprints_v2.register import register_sprint_tools_v2
```

### ⚠️ `tools/epics.py` - LEGACY MODE
**Replacement**: `tools/epics_v2/`  
**Status**: Legacy (wrapped in v2)  
**Reason**: Now uses hybrid approach with new architecture

**Migration**:
```python
# Old (legacy)
from mcp_server.tools import register_epic_tools

# New (recommended)
from mcp_server.tools.epics_v2.register import register_epic_tools_v2
```

---

## Migration Timeline

### Phase 1: Deprecation (Now - Q1 2026)
- ✅ Old tools still work
- ✅ V2 tools available
- ✅ Deprecation warnings logged
- ✅ Documentation updated

### Phase 2: Migration Period (Q1 2026)
- ⏳ Encourage migration to v2
- ⏳ Provide migration tools
- ⏳ Update examples and documentation

### Phase 3: Removal (Q2 2026)
- ⏳ Remove deprecated code
- ⏳ V2 becomes default
- ⏳ Clean up imports

---

## Why the Change?

### Problems with Old Architecture
- ❌ Large monolithic files (400-800 lines)
- ❌ Repetitive boilerplate code
- ❌ Custom logic duplicated in every tool
- ❌ Hard to test individual tools
- ❌ Not using abstraction layer properly

### Benefits of New Architecture
- ✅ Small focused modules (50-100 lines)
- ✅ Reusable base classes and decorators
- ✅ Proper use of abstraction layer
- ✅ Easy to test individual tools
- ✅ Consistent patterns across all tools
- ✅ 47% less code per tool

---

## Current Status

### ✅ Fully Refactored (V2)
- `analytics_v2` - Fully refactored with new architecture

### ⚠️ Hybrid Mode (V2 wrapping legacy)
- `projects_v2` - Uses new architecture, wraps legacy logic
- `tasks_v2` - Uses new architecture, wraps legacy logic
- `sprints_v2` - Uses new architecture, wraps legacy logic
- `epics_v2` - Uses new architecture, wraps legacy logic

### ✅ No Changes Needed
- `provider_config` - Already well-structured
- `users` - Already well-structured
- `task_interactions` - Already well-structured

---

## For Developers

### Using V2 Tools

All v2 tools are registered automatically in `server.py`. No code changes needed for existing deployments.

### Creating New Tools

Use the v2 architecture for all new tools:

```python
from mcp_server.tools.base import ReadTool
from mcp_server.tools.decorators import mcp_tool, require_project

@mcp_tool(name="my_tool", description="...")
class MyTool(ReadTool):
    @require_project
    async def execute(self, project_id: str, **kwargs):
        # Use self.context.provider_manager
        # Use self.context.analytics_manager
        pass
```

### Migrating Existing Tools

See `MCP_SERVER_REFACTORING_FUTURE_PHASES.md` for detailed migration guide.

---

## Questions?

- **Q: Do I need to change my code?**  
  A: No, old tools still work. V2 is used automatically.

- **Q: When will old tools be removed?**  
  A: Planned for Q2 2026 (6+ months).

- **Q: What if I find issues?**  
  A: Report issues on GitHub or contact the team.

- **Q: Can I still use old tools?**  
  A: Yes, but they're deprecated. Use v2 for new development.

---

**End of Deprecation Notice** 📋

