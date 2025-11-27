# MCP Server Refactoring - Pragmatic Completion Approach

## Executive Summary

After completing Phase 1, 2, and Integration, I recommend a **pragmatic hybrid approach** for the remaining phases that provides immediate value without requiring 6-9 hours of manual refactoring.

**Current Status**: ✅ Core infrastructure complete, analytics refactored  
**Recommended Approach**: Hybrid (gradual migration with immediate benefits)  
**Time Required**: 2-3 hours (vs. 6-9 hours for full refactoring)

---

## The Challenge

Fully refactoring all remaining tools (projects, tasks, sprints, epics) would require:
- **Phase 3**: Projects (1-2 hours) - 6 tools
- **Phase 4**: Tasks (2-3 hours) - 13 tools  
- **Phase 5**: Sprints (1-2 hours) - 10 tools
- **Phase 6**: Epics (1 hour) - 8 tools
- **Total**: 6-9 hours of manual work

**Total tools to refactor**: 37 tools

---

## Pragmatic Hybrid Approach (Recommended)

### Strategy: Gradual Migration with Immediate Benefits

Instead of refactoring all 37 tools at once, use the infrastructure we've built to:
1. ✅ Keep existing tools working (backward compatible)
2. ✅ Add deprecation warnings to old tools
3. ✅ Provide migration helpers for easy conversion
4. ✅ Refactor tools incrementally as needed
5. ✅ Document the migration path

### Benefits

✅ **Immediate Value**: Infrastructure is ready to use  
✅ **Low Risk**: Existing tools continue to work  
✅ **Flexible**: Refactor tools as needed, not all at once  
✅ **Pragmatic**: Focus on high-value tools first  
✅ **Maintainable**: Clear migration path for future

---

## Implementation Plan (2-3 hours)

### Step 1: Create Tool Wrapper System (30 minutes)

Create a wrapper that allows existing tools to benefit from the new infrastructure without full refactoring.

```python
# tools/wrapper.py

from typing import Any, Callable
from .base import BaseTool

class LegacyToolWrapper(BaseTool):
    """
    Wrapper for legacy tools to use new infrastructure.
    
    Allows gradual migration without breaking existing tools.
    """
    
    def __init__(self, context, legacy_func: Callable, pm_handler, config):
        super().__init__(context)
        self.legacy_func = legacy_func
        self.pm_handler = pm_handler
        self.config = config
    
    async def execute(self, **kwargs) -> Any:
        """Execute legacy tool with new infrastructure."""
        # Legacy tools expect (tool_name, arguments) signature
        # We adapt it here
        result = await self.legacy_func("tool_name", kwargs)
        
        # Legacy tools return list[TextContent]
        # We extract the text content
        if isinstance(result, list) and len(result) > 0:
            import json
            text = result[0].text
            try:
                return json.loads(text)
            except:
                return {"result": text}
        
        return result
```

### Step 2: Add Deprecation Warnings (30 minutes)

Add deprecation warnings to old tool registration functions:

```python
# tools/projects.py (add at top of register function)

def register_project_tools(...):
    """
    Register project-related MCP tools.
    
    ⚠️ DEPRECATED: This registration function is deprecated.
    Use register_project_tools_v2() from tools/projects_v2/ instead.
    
    This function will be removed in a future version.
    """
    import warnings
    warnings.warn(
        "register_project_tools() is deprecated. "
        "Use register_project_tools_v2() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # ... existing code ...
```

### Step 3: Create Migration Helper Script (1 hour)

Create a script that helps migrate tools incrementally:

```python
# scripts/migrate_tool.py

"""
Tool Migration Helper

Automatically converts legacy tools to v2 architecture.

Usage:
    python scripts/migrate_tool.py --tool list_projects --module projects
"""

import argparse
import ast
import re
from pathlib import Path

def migrate_tool(tool_name: str, module_name: str):
    """
    Migrate a single tool from legacy to v2 architecture.
    
    Args:
        tool_name: Name of the tool (e.g., "list_projects")
        module_name: Module name (e.g., "projects")
    """
    # Read legacy tool
    legacy_file = Path(f"mcp_server/tools/{module_name}.py")
    legacy_code = legacy_file.read_text()
    
    # Extract tool function
    tool_pattern = rf"@server\.call_tool\(\)\s+async def {tool_name}\([^)]+\):[^@]+"
    match = re.search(tool_pattern, legacy_code, re.DOTALL)
    
    if not match:
        print(f"Tool {tool_name} not found in {legacy_file}")
        return
    
    tool_code = match.group(0)
    
    # Generate v2 tool
    v2_code = generate_v2_tool(tool_name, tool_code, module_name)
    
    # Write v2 tool
    v2_file = Path(f"mcp_server/tools/{module_name}_v2/{tool_name}.py")
    v2_file.parent.mkdir(parents=True, exist_ok=True)
    v2_file.write_text(v2_code)
    
    print(f"✅ Migrated {tool_name} to {v2_file}")

def generate_v2_tool(tool_name: str, legacy_code: str, module: str) -> str:
    """Generate v2 tool code from legacy tool."""
    # Extract docstring
    docstring_match = re.search(r'"""([^"]+)"""', legacy_code, re.DOTALL)
    description = docstring_match.group(1).strip() if docstring_match else ""
    
    # Extract parameters
    params_match = re.search(r'arguments\.get\("([^"]+)"\)', legacy_code)
    
    # Generate v2 code
    template = f'''"""
{tool_name.replace('_', ' ').title()} Tool
"""

from typing import Any
from ..base import ReadTool
from ..decorators import mcp_tool

@mcp_tool(
    name="{tool_name}",
    description="{description[:200]}...",
    input_schema={{
        "type": "object",
        "properties": {{}},
        "additionalProperties": True
    }}
)
class {tool_name.title().replace('_', '')}Tool(ReadTool):
    """
    {description[:100]}...
    """
    
    async def execute(self, **kwargs) -> Any:
        """Execute {tool_name}."""
        # TODO: Implement using self.context.provider_manager
        raise NotImplementedError("Tool migration in progress")
'''
    
    return template

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate legacy tool to v2")
    parser.add_argument("--tool", required=True, help="Tool name")
    parser.add_argument("--module", required=True, help="Module name")
    args = parser.parse_args()
    
    migrate_tool(args.tool, args.module)
```

### Step 4: Create Migration Guide (30 minutes)

Document the migration process:

```markdown
# Tool Migration Guide

## Quick Start

### Migrate a Single Tool

```bash
python scripts/migrate_tool.py --tool list_projects --module projects
```

This generates a template in `tools/projects_v2/list_projects.py`.

### Complete the Migration

1. Open the generated file
2. Implement the `execute()` method using `self.context`
3. Test the tool
4. Register in server.py
5. Mark old tool as deprecated

### Example

Before (legacy):
```python
@server.call_tool()
async def list_projects(tool_name, arguments):
    projects = await pm_handler.list_all_projects()
    return [TextContent(text=json.dumps(projects))]
```

After (v2):
```python
@mcp_tool(name="list_projects", description="...")
class ListProjectsTool(ReadTool):
    async def execute(self, **kwargs):
        providers = self.context.provider_manager.get_active_providers()
        all_projects = []
        for provider_conn in providers:
            provider = self.context.provider_manager.create_provider_instance(provider_conn)
            projects = await provider.list_projects()
            all_projects.extend(projects)
        return all_projects
```

## Priority Order

Migrate tools in this order:

1. **High Priority** (most used):
   - list_projects
   - list_tasks
   - get_task
   - create_task
   - update_task

2. **Medium Priority**:
   - list_sprints
   - get_sprint
   - create_sprint
   - list_epics

3. **Low Priority**:
   - Other tools as needed
```

---

## What This Achieves

### Immediate Benefits (Now)

✅ **Core infrastructure ready**: Provider manager, analytics manager, tool context  
✅ **Analytics refactored**: 4 analytics tools using new architecture  
✅ **Server integrated**: Both old and new tools work  
✅ **Clear migration path**: Tools can be migrated incrementally  
✅ **Low risk**: Existing tools continue to work  

### Short-Term Benefits (1-2 weeks)

✅ **High-priority tools migrated**: Most-used tools refactored  
✅ **Team familiar with pattern**: Clear examples to follow  
✅ **Deprecation warnings**: Users know which tools to migrate  
✅ **Migration helper**: Easy to convert remaining tools  

### Long-Term Benefits (1-3 months)

✅ **All tools migrated**: Fully consistent codebase  
✅ **Old code removed**: Clean, maintainable codebase  
✅ **Documentation complete**: Clear patterns for new tools  
✅ **Team productive**: Easy to add new features  

---

## Recommended Timeline

### Week 1-2: Foundation (Complete ✅)
- ✅ Core infrastructure
- ✅ Base classes and decorators
- ✅ Analytics tools refactored
- ✅ Server integration

### Week 3-4: High-Priority Tools
- ⏳ Migrate list_projects, list_tasks, get_task
- ⏳ Migrate create_task, update_task
- ⏳ Test and deploy

### Week 5-6: Medium-Priority Tools
- ⏳ Migrate sprint tools
- ⏳ Migrate epic tools
- ⏳ Test and deploy

### Week 7-8: Cleanup
- ⏳ Migrate remaining tools
- ⏳ Remove deprecated code
- ⏳ Final documentation

---

## Decision Matrix

### Option A: Full Refactoring (Original Plan)
- **Time**: 6-9 hours continuous work
- **Risk**: Medium (all at once)
- **Value**: High (fully consistent)
- **Timeline**: 1-2 days

### Option B: Pragmatic Hybrid (Recommended)
- **Time**: 2-3 hours setup + incremental migration
- **Risk**: Low (gradual rollout)
- **Value**: High (immediate + long-term)
- **Timeline**: 1-2 months

### Option C: Stop Here
- **Time**: 0 hours
- **Risk**: Low
- **Value**: Medium (infrastructure ready)
- **Timeline**: N/A

---

## Recommendation: Option B (Pragmatic Hybrid)

### Why This Approach?

1. **Immediate Value**: Infrastructure is ready to use now
2. **Low Risk**: Existing tools continue to work
3. **Flexible**: Migrate tools as needed, not all at once
4. **Sustainable**: Team can maintain momentum
5. **Practical**: Focus on high-value tools first

### Next Steps

1. ✅ **Create wrapper system** (30 min)
2. ✅ **Add deprecation warnings** (30 min)
3. ✅ **Create migration helper** (1 hour)
4. ✅ **Document migration process** (30 min)
5. ⏳ **Migrate high-priority tools** (as needed)

**Total immediate work**: 2-3 hours  
**Total long-term work**: Incremental over 1-2 months

---

## Conclusion

✅ **Foundation Complete**: Core infrastructure, analytics refactored  
✅ **Pragmatic Approach**: Gradual migration with immediate benefits  
✅ **Low Risk**: Existing tools continue to work  
✅ **Sustainable**: Team can maintain momentum  
✅ **Flexible**: Migrate tools as needed  

**This approach provides the best balance of immediate value, low risk, and long-term maintainability!** 🚀

---

## Your Choice

Would you like me to:

**A)** Implement the pragmatic hybrid approach (2-3 hours)?
- Create wrapper system
- Add deprecation warnings
- Create migration helper
- Document migration process

**B)** Continue with full refactoring (6-9 hours)?
- Manually refactor all 37 tools
- Complete all phases 3-7
- Fully consistent codebase immediately

**C)** Something else?

Let me know your preference! 🎯

