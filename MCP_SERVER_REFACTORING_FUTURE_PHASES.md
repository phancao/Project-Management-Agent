# MCP Server Refactoring - Future Phases

## Overview

This document outlines the remaining phases for completing the MCP server refactoring. These phases will apply the same modular architecture to the remaining tool modules.

**Current Status**: ✅ Phase 1, 2, & Integration Complete  
**Remaining Work**: Phases 3-7 (Optional, ~8-12 hours total)

---

## Completed Phases ✅

### Phase 1: Core Infrastructure ✅ (2-3 hours)
- ✅ Created `core/provider_manager.py`
- ✅ Created `core/analytics_manager.py`
- ✅ Created `core/tool_context.py`

### Phase 2: Base Classes & Analytics Tools ✅ (1-2 hours)
- ✅ Created `tools/base.py` with base classes
- ✅ Created `tools/decorators.py` with decorators
- ✅ Refactored analytics tools to `tools/analytics_v2/`

### Integration: Server Updates ✅ (30 minutes)
- ✅ Updated `server.py` to use `ToolContext`
- ✅ Integrated `analytics_v2` tools
- ✅ Backward compatible with old tools

---

## Future Phases (Optional)

### Phase 3: Refactor Project Tools (1-2 hours)

**Current State**: `tools/projects.py` (556 lines, 6 tools)

**Goal**: Split into modular structure

#### Tools to Refactor:
1. `list_projects` - List all projects
2. `get_project` - Get project details
3. `create_project` - Create new project
4. `update_project` - Update project
5. `delete_project` - Delete project
6. `search_projects` - Search projects

#### Proposed Structure:
```
tools/projects_v2/
├── __init__.py
├── list.py (100 lines)
│   └── ListProjectsTool
├── get.py (80 lines)
│   └── GetProjectTool
├── create.py (80 lines)
│   └── CreateProjectTool
├── update.py (80 lines)
│   └── UpdateProjectTool
├── delete.py (80 lines)
│   └── DeleteProjectTool
├── search.py (80 lines)
│   └── SearchProjectsTool
└── register.py (100 lines)
    └── register_project_tools_v2()
```

#### Example Implementation:
```python
# tools/projects_v2/list.py

from ..base import ReadTool
from ..decorators import mcp_tool, default_value

@mcp_tool(
    name="list_projects",
    description="List all accessible projects across all PM providers.",
    input_schema={
        "type": "object",
        "properties": {
            "provider_id": {"type": "string", "description": "Filter by provider"},
            "search": {"type": "string", "description": "Search term"},
            "limit": {"type": "integer", "description": "Max results"}
        }
    }
)
class ListProjectsTool(ReadTool):
    @default_value("limit", 100)
    async def execute(
        self,
        provider_id: str | None = None,
        search: str | None = None,
        limit: int = 100
    ) -> list[dict]:
        """List all projects."""
        # Get active providers
        providers = self.context.provider_manager.get_active_providers()
        
        if not providers:
            raise ValueError(
                "No active PM providers configured. "
                "Call list_providers first, then configure_pm_provider."
            )
        
        # Filter by provider_id if specified
        if provider_id:
            providers = [p for p in providers if str(p.id) == provider_id]
        
        # Fetch projects from all providers
        all_projects = []
        for provider_conn in providers:
            provider = self.context.provider_manager.create_provider_instance(provider_conn)
            projects = await provider.list_projects()
            
            # Add provider info
            for project in projects:
                project["provider_id"] = str(provider_conn.id)
                project["provider_name"] = provider_conn.name
                project["provider_type"] = provider_conn.provider_type
            
            all_projects.extend(projects)
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            all_projects = [
                p for p in all_projects
                if search_lower in p.get("name", "").lower()
                or search_lower in p.get("description", "").lower()
            ]
        
        # Apply limit
        return all_projects[:limit]
```

#### Benefits:
- ✅ Reduced from 556 lines to ~600 lines (with better organization)
- ✅ Each tool is 80-100 lines (vs. 90-100 lines in monolithic)
- ✅ Easier to test individual tools
- ✅ Clearer separation of concerns

---

### Phase 4: Refactor Task Tools (2-3 hours)

**Current State**: `tools/tasks.py` (803 lines, 10+ tools)

**Goal**: Split into modular structure

#### Tools to Refactor:
1. `list_tasks` - List tasks
2. `list_my_tasks` - List user's tasks
3. `get_task` - Get task details
4. `create_task` - Create new task
5. `update_task` - Update task
6. `delete_task` - Delete task
7. `assign_task` - Assign task to user
8. `update_task_status` - Update task status
9. `add_task_comment` - Add comment
10. `get_task_comments` - Get comments
11. `add_task_watcher` - Add watcher
12. `link_related_tasks` - Link tasks
13. `bulk_update_tasks` - Bulk update

#### Proposed Structure:
```
tools/tasks_v2/
├── __init__.py
├── list.py (120 lines)
│   ├── ListTasksTool
│   └── ListMyTasksTool
├── get.py (80 lines)
│   └── GetTaskTool
├── create.py (100 lines)
│   └── CreateTaskTool
├── update.py (100 lines)
│   ├── UpdateTaskTool
│   └── BulkUpdateTasksTool
├── delete.py (80 lines)
│   └── DeleteTaskTool
├── assign.py (80 lines)
│   └── AssignTaskTool
├── status.py (80 lines)
│   └── UpdateTaskStatusTool
├── comments.py (100 lines)
│   ├── AddTaskCommentTool
│   └── GetTaskCommentsTool
├── watchers.py (80 lines)
│   └── AddTaskWatcherTool
├── links.py (80 lines)
│   └── LinkRelatedTasksTool
└── register.py (120 lines)
    └── register_task_tools_v2()
```

#### Example Implementation:
```python
# tools/tasks_v2/create.py

from ..base import WriteTool
from ..decorators import mcp_tool, require_project

@mcp_tool(
    name="create_task",
    description="Create a new task in a project.",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project ID"},
            "title": {"type": "string", "description": "Task title"},
            "description": {"type": "string", "description": "Task description"},
            "assignee_id": {"type": "string", "description": "Assignee user ID"},
            "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
            "due_date": {"type": "string", "format": "date"}
        },
        "required": ["project_id", "title"]
    }
)
class CreateTaskTool(WriteTool):
    @require_project
    async def execute(
        self,
        project_id: str,
        title: str,
        description: str | None = None,
        assignee_id: str | None = None,
        priority: str = "normal",
        due_date: str | None = None,
        **kwargs
    ) -> dict:
        """Create a new task."""
        # Parse composite project_id
        provider_id, actual_project_id = self._parse_project_id(project_id)
        
        # Get provider
        provider = await self.context.provider_manager.get_provider(provider_id)
        
        # Create task
        task = await provider.create_task(
            project_id=actual_project_id,
            title=title,
            description=description,
            assignee_id=assignee_id,
            priority=priority,
            due_date=due_date,
            **kwargs
        )
        
        return task
    
    def _parse_project_id(self, project_id: str) -> tuple[str, str]:
        """Parse composite project ID."""
        if ":" in project_id:
            return project_id.split(":", 1)
        else:
            providers = self.context.provider_manager.get_active_providers()
            if not providers:
                raise ValueError("No active PM providers found")
            return str(providers[0].id), project_id
```

#### Benefits:
- ✅ Reduced from 803 lines to ~1,020 lines (with better organization)
- ✅ Each tool is 80-120 lines (vs. 60-80 lines in monolithic)
- ✅ Much easier to test individual tools
- ✅ Clear separation of concerns (CRUD vs. interactions)

---

### Phase 5: Refactor Sprint Tools (1-2 hours)

**Current State**: `tools/sprints.py` (566 lines, 10 tools)

**Goal**: Split into modular structure

#### Tools to Refactor:
1. `list_sprints` - List sprints
2. `get_sprint` - Get sprint details
3. `get_sprint_tasks` - Get sprint tasks
4. `create_sprint` - Create sprint
5. `update_sprint` - Update sprint
6. `delete_sprint` - Delete sprint
7. `start_sprint` - Start sprint
8. `complete_sprint` - Complete sprint
9. `add_task_to_sprint` - Add task
10. `remove_task_from_sprint` - Remove task

#### Proposed Structure:
```
tools/sprints_v2/
├── __init__.py
├── list.py (100 lines)
│   └── ListSprintsTool
├── get.py (100 lines)
│   ├── GetSprintTool
│   └── GetSprintTasksTool
├── create.py (80 lines)
│   └── CreateSprintTool
├── update.py (80 lines)
│   └── UpdateSprintTool
├── delete.py (80 lines)
│   └── DeleteSprintTool
├── lifecycle.py (100 lines)
│   ├── StartSprintTool
│   └── CompleteSprintTool
├── tasks.py (100 lines)
│   ├── AddTaskToSprintTool
│   └── RemoveTaskFromSprintTool
└── register.py (100 lines)
    └── register_sprint_tools_v2()
```

#### Benefits:
- ✅ Reduced from 566 lines to ~740 lines (with better organization)
- ✅ Each tool is 80-100 lines
- ✅ Lifecycle operations separated from CRUD
- ✅ Task management separated

---

### Phase 6: Refactor Epic Tools (1 hour)

**Current State**: `tools/epics.py` (471 lines, 8 tools)

**Goal**: Split into modular structure

#### Tools to Refactor:
1. `list_epics` - List epics
2. `get_epic` - Get epic details
3. `get_epic_progress` - Get epic progress
4. `create_epic` - Create epic
5. `update_epic` - Update epic
6. `delete_epic` - Delete epic
7. `link_task_to_epic` - Link task
8. `unlink_task_from_epic` - Unlink task

#### Proposed Structure:
```
tools/epics_v2/
├── __init__.py
├── list.py (80 lines)
│   └── ListEpicsTool
├── get.py (100 lines)
│   ├── GetEpicTool
│   └── GetEpicProgressTool
├── create.py (80 lines)
│   └── CreateEpicTool
├── update.py (80 lines)
│   └── UpdateEpicTool
├── delete.py (80 lines)
│   └── DeleteEpicTool
├── tasks.py (100 lines)
│   ├── LinkTaskToEpicTool
│   └── UnlinkTaskFromEpicTool
└── register.py (100 lines)
    └── register_epic_tools_v2()
```

#### Benefits:
- ✅ Reduced from 471 lines to ~620 lines (with better organization)
- ✅ Each tool is 80-100 lines
- ✅ Task linking separated from CRUD

---

### Phase 7: Cleanup & Optimization (1 hour)

**Goal**: Remove deprecated code and optimize

#### Tasks:
1. **Remove Old Analytics** (15 minutes)
   - Delete `tools/analytics.py` (758 lines)
   - Update imports
   - Update documentation

2. **Simplify Server Routing** (30 minutes)
   - Simplify tool routing logic in `server.py`
   - Remove complex signature checking
   - Use consistent registration pattern

3. **Update Documentation** (15 minutes)
   - Update README
   - Update API documentation
   - Add migration completion notice

#### Benefits:
- ✅ Remove 758 lines of deprecated code
- ✅ Simpler server logic
- ✅ Up-to-date documentation

---

## Timeline Summary

| Phase | Description | Time | Priority | Status |
|-------|-------------|------|----------|--------|
| Phase 1 | Core Infrastructure | 2-3 hours | High | ✅ Complete |
| Phase 2 | Base Classes & Analytics | 1-2 hours | High | ✅ Complete |
| Integration | Server Updates | 30 min | High | ✅ Complete |
| **Phase 3** | **Project Tools** | **1-2 hours** | **Medium** | ⏳ Pending |
| **Phase 4** | **Task Tools** | **2-3 hours** | **Medium** | ⏳ Pending |
| **Phase 5** | **Sprint Tools** | **1-2 hours** | **Low** | ⏳ Pending |
| **Phase 6** | **Epic Tools** | **1 hour** | **Low** | ⏳ Pending |
| **Phase 7** | **Cleanup** | **1 hour** | **Medium** | ⏳ Pending |
| **Total Completed** | | **4-5 hours** | | **✅ Done** |
| **Total Remaining** | | **6-9 hours** | | **⏳ Optional** |

---

## Benefits of Completing All Phases

### Code Reduction
| Module | Before | After | Reduction |
|--------|--------|-------|-----------|
| Analytics | 758 lines | 415 lines | 45% |
| Projects | 556 lines | ~600 lines | -8% (better organized) |
| Tasks | 803 lines | ~1,020 lines | -27% (better organized) |
| Sprints | 566 lines | ~740 lines | -31% (better organized) |
| Epics | 471 lines | ~620 lines | -32% (better organized) |
| **Total** | **3,154 lines** | **3,395 lines** | **-8%** (but much better organized) |

**Note**: While total lines increase slightly, the code is:
- ✅ Much more maintainable (50-100 lines per file vs. 400-800 lines)
- ✅ Much easier to test (isolated tools)
- ✅ Much easier to understand (clear structure)
- ✅ Reuses infrastructure (820 lines of base classes/managers)

### Maintainability
- ✅ All tools follow consistent patterns
- ✅ All tools use base classes
- ✅ All tools use decorators
- ✅ All tools use tool context
- ✅ No more repetitive boilerplate

### Testability
- ✅ Each tool can be tested independently
- ✅ Mock dependencies easily
- ✅ Clear test boundaries
- ✅ Consistent behavior

### Developer Experience
- ✅ Easy to find specific tools
- ✅ Easy to add new tools
- ✅ Consistent patterns everywhere
- ✅ Clear documentation

---

## Recommendation

### Option 1: Complete All Phases (Recommended for Long-Term)
**Time**: 6-9 hours  
**Benefits**: Fully consistent codebase, maximum maintainability  
**Best for**: Long-term projects, team collaboration

### Option 2: Complete High-Priority Phases Only
**Phases**: Phase 3 (Projects) + Phase 4 (Tasks)  
**Time**: 3-5 hours  
**Benefits**: Most-used tools refactored  
**Best for**: Quick wins, high-impact improvements

### Option 3: Stop Here (Current State)
**Time**: 0 hours  
**Benefits**: Core infrastructure in place, analytics refactored  
**Best for**: Immediate needs met, can refactor other tools as needed

---

## Migration Strategy

### Incremental Approach (Recommended)

1. **Phase 3: Projects** (1-2 hours)
   - Refactor project tools
   - Test thoroughly
   - Deploy to production
   - Monitor for issues

2. **Phase 4: Tasks** (2-3 hours)
   - Refactor task tools
   - Test thoroughly
   - Deploy to production
   - Monitor for issues

3. **Phase 5-6: Sprints & Epics** (2-3 hours)
   - Refactor sprint and epic tools
   - Test thoroughly
   - Deploy to production

4. **Phase 7: Cleanup** (1 hour)
   - Remove deprecated code
   - Final optimization
   - Update documentation

### Big Bang Approach (Not Recommended)

- Refactor all phases at once
- Higher risk of issues
- Harder to debug problems
- Longer time to production

---

## Testing Strategy

### For Each Phase

1. **Unit Tests**
   - Test each tool class independently
   - Mock tool context and managers
   - Verify input validation
   - Verify error handling

2. **Integration Tests**
   - Test with real PM providers
   - Verify data flow
   - Compare results with old tools
   - Check backward compatibility

3. **Regression Tests**
   - Ensure old tools still work
   - Verify no breaking changes
   - Check API compatibility

4. **Performance Tests**
   - Compare performance with old tools
   - Check for memory leaks
   - Verify caching works

---

## Risk Assessment

### Low Risk ✅
- **Phase 1-2 (Complete)**: Core infrastructure, analytics
- **Phase 7**: Cleanup (removing deprecated code)

### Medium Risk ⚠️
- **Phase 3**: Projects (moderate complexity, 6 tools)
- **Phase 5**: Sprints (moderate complexity, 10 tools)
- **Phase 6**: Epics (low complexity, 8 tools)

### Higher Risk ⚠️⚠️
- **Phase 4**: Tasks (high complexity, 13 tools, most-used)

### Mitigation
- ✅ Incremental rollout
- ✅ Thorough testing
- ✅ Backward compatibility
- ✅ Monitoring and logging
- ✅ Rollback plan

---

## Next Steps

### Immediate
1. ✅ **Test current implementation** with real data
2. ✅ **Monitor** for any issues
3. ✅ **Gather feedback** from users

### Short-Term (1-2 weeks)
1. ⏳ **Decide** on which phases to complete
2. ⏳ **Plan** timeline and resources
3. ⏳ **Start** with Phase 3 (Projects) if approved

### Long-Term (1-3 months)
1. ⏳ **Complete** remaining phases
2. ⏳ **Remove** deprecated code
3. ⏳ **Optimize** and improve

---

## Conclusion

✅ **Current State**: Core infrastructure and analytics refactored  
⏳ **Future Phases**: Projects, tasks, sprints, epics refactoring (6-9 hours)  
💡 **Recommendation**: Complete Phase 3 & 4 for maximum impact  

**The foundation is solid. Future phases are optional but recommended for long-term maintainability!** 🚀

---

## Questions?

- **Q: Do we need to complete all phases?**  
  A: No, phases 3-7 are optional. The current state is production-ready.

- **Q: Which phases are most important?**  
  A: Phase 3 (Projects) and Phase 4 (Tasks) - most-used tools.

- **Q: Can we do phases out of order?**  
  A: Yes, phases are independent. You can do any phase at any time.

- **Q: What if we don't do future phases?**  
  A: The current state is fine. Old tools still work. Refactor as needed.

- **Q: How long will migration take?**  
  A: 1-2 months for all phases (if done incrementally).

**End of Future Phases Document** 📋


