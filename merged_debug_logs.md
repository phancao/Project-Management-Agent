# Merged Debug Logs - 2026-01-11T13:20

---

## Full Timeline (All Sources Merged by Timestamp)

```
06:17:55.299 [MCP] __main__ - INFO - ============================================================
06:17:55.299 [MCP] __main__ - INFO - PM MCP Server Starting
06:17:55.299 [MCP] __main__ - INFO - ============================================================
06:17:55.299 [MCP] __main__ - INFO - Transport: sse
06:17:55.299 [MCP] __main__ - INFO - Address: 0.0.0.0:8080
06:17:55.299 [MCP] __main__ - INFO - Log Level: INFO
06:17:55.300 [MCP] __main__ - INFO - Authentication: Disabled
06:17:55.300 [MCP] __main__ - INFO - RBAC: Disabled
06:17:55.300 [MCP] __main__ - INFO - ============================================================
06:17:55.300 [MCP] mcp_server.server - INFO - PM MCP Server initialized: pm-server v0.1.0
06:17:55.301 [MCP] mcp_server.server - INFO - Starting PM MCP Server with SSE transport on 0.0.0.0:8080...
06:17:55.301 [MCP] mcp_server.server - INFO - Initializing Tool Context...
06:17:55.301 [MCP] mcp_server.database.connection - INFO - Initializing MCP Server database: mcp-postgres:5432/mcp_server
06:17:55.318 [MCP] mcp_server.database.connection - INFO - MCP Server database tables created/verified
06:17:55.319 [MCP] mcp_server.database.connection - INFO - MCP Server database connection initialized
06:17:55.319 [MCP] mcp_server.core.tool_context - INFO - [ToolContext] Initialized (PM Service: http://pm-service:8001)
06:17:55.336 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
06:17:55.336 [MCP] mcp_server.server - INFO - Tool Context initialized with 1 active provider(s) (all users)
06:17:55.336 [MCP] mcp_server.server - INFO - Registering PM tools...
06:17:55.337 [MCP] mcp_server.server - INFO - [provider_config] Registering with context
06:17:55.337 [MCP] mcp_server.tools.provider_config - INFO - Registered 2 provider configuration tool(s)
06:17:55.337 [MCP] mcp_server.server - INFO - Registered 2 provider_config tools
06:17:55.337 [MCP] mcp_server.server - INFO - [task_interactions] Registering with context
06:17:55.338 [MCP] mcp_server.tools.task_interactions - INFO - Registered 5 task interaction tools
06:17:55.338 [MCP] mcp_server.server - INFO - Registered 5 task_interactions tools
06:17:55.338 [MCP] mcp_server.server - INFO - [analytics] Registering with context
06:17:55.339 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered tool: burndown_chart
06:17:55.339 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered tool: velocity_chart
06:17:55.339 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered tool: sprint_report
06:17:55.339 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered tool: project_health
06:17:55.339 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered tool: cfd_chart
06:17:55.339 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered tool: cycle_time_chart
06:17:55.340 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered tool: work_distribution_chart
06:17:55.340 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered tool: issue_trend_chart
06:17:55.340 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered tool: capacity_chart
06:17:55.340 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered 9 analytics tools
06:17:55.340 [MCP] mcp_server.server - INFO - Registered 9 analytics tools
06:17:55.341 [MCP] mcp_server.server - INFO - [projects] Registering with context
06:17:55.341 [MCP] mcp_server.tools.projects.register - INFO - [Projects] Registered tool: list_projects
06:17:55.341 [MCP] mcp_server.tools.projects.register - INFO - [Projects] Registered tool: get_project
06:17:55.341 [MCP] mcp_server.tools.projects.register - INFO - [Projects] Registered tool: create_project
06:17:55.341 [MCP] mcp_server.tools.projects.register - INFO - [Projects] Registered tool: update_project
06:17:55.341 [MCP] mcp_server.tools.projects.register - INFO - [Projects] Registered tool: delete_project
06:17:55.342 [MCP] mcp_server.tools.projects.register - INFO - [Projects] Registered tool: search_projects
06:17:55.342 [MCP] mcp_server.tools.projects.register - INFO - [Projects] Registered 6 project tools
06:17:55.342 [MCP] mcp_server.server - INFO - Registered 6 projects tools
06:17:55.342 [MCP] mcp_server.server - INFO - [tasks] Registering with context
06:17:55.342 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: list_tasks
06:17:55.342 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: list_my_tasks
06:17:55.342 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: list_tasks_by_assignee
06:17:55.343 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: list_unassigned_tasks
06:17:55.343 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: list_tasks_in_sprint
06:17:55.343 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: get_task
06:17:55.343 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: create_task
06:17:55.344 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: update_task
06:17:55.344 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: delete_task
06:17:55.344 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: assign_task
06:17:55.344 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: update_task_status
06:17:55.344 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: search_tasks
06:17:55.345 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered 12 task tools
06:17:55.345 [MCP] mcp_server.server - INFO - Registered 12 tasks tools
06:17:55.345 [MCP] mcp_server.server - INFO - [sprints] Registering with context
06:17:55.345 [MCP] mcp_server.tools.sprints.register - INFO - [Sprints] Registered tool: list_sprints
06:17:55.346 [MCP] mcp_server.tools.sprints.register - INFO - [Sprints] Registered tool: get_sprint
06:17:55.346 [MCP] mcp_server.tools.sprints.register - INFO - [Sprints] Registered tool: create_sprint
06:17:55.346 [MCP] mcp_server.tools.sprints.register - INFO - [Sprints] Registered tool: update_sprint
06:17:55.346 [MCP] mcp_server.tools.sprints.register - INFO - [Sprints] Registered tool: delete_sprint
06:17:55.346 [MCP] mcp_server.tools.sprints.register - INFO - [Sprints] Registered tool: start_sprint
06:17:55.346 [MCP] mcp_server.tools.sprints.register - INFO - [Sprints] Registered tool: complete_sprint
06:17:55.347 [MCP] mcp_server.tools.sprints.register - INFO - [Sprints] Registered tool: get_sprint_tasks
06:17:55.347 [MCP] mcp_server.tools.sprints.register - INFO - [Sprints] Registered 8 sprint tools
06:17:55.347 [MCP] mcp_server.server - INFO - Registered 8 sprints tools
06:17:55.347 [MCP] mcp_server.server - INFO - [epics] Registering with context
06:17:55.347 [MCP] mcp_server.tools.epics.register - INFO - [Epics] Registered tool: list_epics
06:17:55.348 [MCP] mcp_server.tools.epics.register - INFO - [Epics] Registered tool: get_epic
06:17:55.348 [MCP] mcp_server.tools.epics.register - INFO - [Epics] Registered tool: create_epic
06:17:55.348 [MCP] mcp_server.tools.epics.register - INFO - [Epics] Registered tool: update_epic
06:17:55.349 [MCP] mcp_server.tools.epics.register - INFO - [Epics] Registered tool: delete_epic
06:17:55.349 [MCP] mcp_server.tools.epics.register - INFO - [Epics] Registered tool: link_task_to_epic
06:17:55.350 [MCP] mcp_server.tools.epics.register - INFO - [Epics] Registered tool: unlink_task_from_epic
06:17:55.350 [MCP] mcp_server.tools.epics.register - INFO - [Epics] Registered 7 epic tools
06:17:55.350 [MCP] mcp_server.server - INFO - Registered 7 epics tools
06:17:55.350 [MCP] mcp_server.server - INFO - [pm_service_users] Registering with context
06:17:55.350 [MCP] mcp_server.tools.pm_service_tools.register - INFO - [PM Service Tools] Registered tool: list_users
06:17:55.351 [MCP] mcp_server.tools.pm_service_tools.register - INFO - [PM Service Tools] Registered tool: get_user
06:17:55.351 [MCP] mcp_server.tools.pm_service_tools.register - INFO - [PM Service Tools] Registered tool: list_worklogs
06:17:55.351 [MCP] mcp_server.tools.pm_service_tools.register - INFO - [PM Service Tools] Registered 3 user tools
06:17:55.352 [MCP] mcp_server.server - INFO - Registered 3 pm_service_users tools
06:17:55.352 [MCP] mcp_server.server - INFO - [meeting_tools] Registering with context
06:17:55.352 [MCP] mcp_server.server - INFO - Registered 7 meeting_tools tools
06:17:55.353 [MCP] mcp_server.server - INFO - Total tools registered: 9
06:17:55.353 [MCP] mcp_server.server - INFO - Creating single routing handler for all tool calls...
06:17:55.354 [MCP] mcp_server.server - INFO - ✅ Routing handler created. 54 tools available for routing.
06:17:55.354 [MCP] mcp_server.server - INFO - Registering list_tools handler...
06:17:55.354 [MCP] mcp_server.server - INFO - ✅ list_tools handler registered successfully
06:17:55.355 [MCP] mcp_server.server - INFO -    Handler type: <class 'function'>
06:17:55.355 [MCP] mcp_server.server - INFO -    Handler: <function Server.list_tools.<locals>.decorator.<locals>.handler at 0xffff7ed15300>
06:17:55.558 [MCP] mcp_server.server - INFO - SSE transport initialized - 59 tools available via MCP server
06:17:55.559 [MCP] mcp_server.server - INFO - PM MCP Server (SSE) starting on http://0.0.0.0:8080
06:17:55.559 [MCP] mcp_server.server - INFO - SSE endpoint: http://0.0.0.0:8080/sse
06:17:55.559 [MCP] mcp_server.server - INFO - Tools endpoint: http://0.0.0.0:8080/tools/list
06:17:55.559 [MCP] mcp_server.server - INFO - Call tool: http://0.0.0.0:8080/tools/call
06:17:55.559 [MCP] mcp_server.server - INFO - Stream tool: http://0.0.0.0:8080/tools/call/stream
06:17:57.460 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
06:18:27.499 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
06:18:57.561 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
06:19:27.620 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
06:19:57.676 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
 [MCP] INFO:     127.0.0.1:56276 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:49068 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:60398 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:53658 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:42004 - "GET /health HTTP/1.1" 200 OK
 [MCP] Building deer-flow @ file:///app
 [MCP] Built deer-flow @ file:///app
 [MCP] Uninstalled 1 package in 3ms
 [MCP] Installed 1 package in 0.39ms
 [MCP] INFO:     Started server process [20]
 [MCP] INFO:     Waiting for application startup.
 [MCP] INFO:     Application startup complete.
 [MCP] INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```
