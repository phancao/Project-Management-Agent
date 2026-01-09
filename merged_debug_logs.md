# Merged Debug Logs - 2026-01-10T01:16

---

## Full Timeline (All Sources Merged by Timestamp)

```
18:13:29.305 [MCP] __main__ - INFO - ============================================================
18:13:29.306 [MCP] __main__ - INFO - PM MCP Server Starting
18:13:29.306 [MCP] __main__ - INFO - ============================================================
18:13:29.306 [MCP] __main__ - INFO - Transport: sse
18:13:29.306 [MCP] __main__ - INFO - Address: 0.0.0.0:8080
18:13:29.306 [MCP] __main__ - INFO - Log Level: INFO
18:13:29.307 [MCP] __main__ - INFO - Authentication: Disabled
18:13:29.307 [MCP] __main__ - INFO - RBAC: Disabled
18:13:29.307 [MCP] __main__ - INFO - ============================================================
18:13:29.307 [MCP] mcp_server.server - INFO - PM MCP Server initialized: pm-server v0.1.0
18:13:29.307 [MCP] mcp_server.server - INFO - Starting PM MCP Server with SSE transport on 0.0.0.0:8080...
18:13:29.308 [MCP] mcp_server.server - INFO - Initializing Tool Context...
18:13:29.308 [MCP] mcp_server.database.connection - INFO - Initializing MCP Server database: mcp-postgres:5432/mcp_server
18:13:29.333 [MCP] mcp_server.database.connection - INFO - MCP Server database tables created/verified
18:13:29.334 [MCP] mcp_server.database.connection - INFO - MCP Server database connection initialized
18:13:29.334 [MCP] mcp_server.core.tool_context - INFO - [ToolContext] Initialized (PM Service: http://pm-service:8001)
18:13:29.352 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
18:13:29.352 [MCP] mcp_server.server - INFO - Tool Context initialized with 1 active provider(s) (all users)
18:13:29.353 [MCP] mcp_server.server - INFO - Registering PM tools...
18:13:29.353 [MCP] mcp_server.server - INFO - [provider_config] Registering with context
18:13:29.353 [MCP] mcp_server.tools.provider_config - INFO - Registered 2 provider configuration tool(s)
18:13:29.353 [MCP] mcp_server.server - INFO - Registered 2 provider_config tools
18:13:29.353 [MCP] mcp_server.server - INFO - [task_interactions] Registering with context
18:13:29.354 [MCP] mcp_server.tools.task_interactions - INFO - Registered 5 task interaction tools
18:13:29.354 [MCP] mcp_server.server - INFO - Registered 5 task_interactions tools
18:13:29.354 [MCP] mcp_server.server - INFO - [analytics_v2] Registering with context
18:13:29.354 [MCP] mcp_server.tools.analytics_v2.register - INFO - [Analytics V2] Registered tool: burndown_chart
18:13:29.354 [MCP] mcp_server.tools.analytics_v2.register - INFO - [Analytics V2] Registered tool: velocity_chart
18:13:29.355 [MCP] mcp_server.tools.analytics_v2.register - INFO - [Analytics V2] Registered tool: sprint_report
18:13:29.355 [MCP] mcp_server.tools.analytics_v2.register - INFO - [Analytics V2] Registered tool: project_health
18:13:29.355 [MCP] mcp_server.tools.analytics_v2.register - INFO - [Analytics V2] Registered tool: cfd_chart
18:13:29.355 [MCP] mcp_server.tools.analytics_v2.register - INFO - [Analytics V2] Registered tool: cycle_time_chart
18:13:29.355 [MCP] mcp_server.tools.analytics_v2.register - INFO - [Analytics V2] Registered tool: work_distribution_chart
18:13:29.355 [MCP] mcp_server.tools.analytics_v2.register - INFO - [Analytics V2] Registered tool: issue_trend_chart
18:13:29.355 [MCP] mcp_server.tools.analytics_v2.register - INFO - [Analytics V2] Registered tool: capacity_chart
18:13:29.356 [MCP] mcp_server.tools.analytics_v2.register - INFO - [Analytics V2] Registered 9 analytics tools
18:13:29.356 [MCP] mcp_server.server - INFO - Registered 9 analytics_v2 tools
18:13:29.356 [MCP] mcp_server.server - INFO - [projects_v2] Registering with context
18:13:29.356 [MCP] mcp_server.tools.projects_v2.register - INFO - [Projects V2] Registered tool: list_projects
18:13:29.357 [MCP] mcp_server.tools.projects_v2.register - INFO - [Projects V2] Registered tool: get_project
18:13:29.357 [MCP] mcp_server.tools.projects_v2.register - INFO - [Projects V2] Registered tool: create_project
18:13:29.357 [MCP] mcp_server.tools.projects_v2.register - INFO - [Projects V2] Registered tool: update_project
18:13:29.357 [MCP] mcp_server.tools.projects_v2.register - INFO - [Projects V2] Registered tool: delete_project
18:13:29.358 [MCP] mcp_server.tools.projects_v2.register - INFO - [Projects V2] Registered tool: search_projects
18:13:29.358 [MCP] mcp_server.tools.projects_v2.register - INFO - [Projects V2] Registered 6 project tools (fully independent)
18:13:29.358 [MCP] mcp_server.server - INFO - Registered 6 projects_v2 tools
18:13:29.358 [MCP] mcp_server.server - INFO - [tasks_v2] Registering with context
18:13:29.358 [MCP] mcp_server.tools.tasks_v2.register - INFO - [Tasks V2] Registered tool: list_tasks
18:13:29.359 [MCP] mcp_server.tools.tasks_v2.register - INFO - [Tasks V2] Registered tool: list_my_tasks
18:13:29.359 [MCP] mcp_server.tools.tasks_v2.register - INFO - [Tasks V2] Registered tool: list_tasks_by_assignee
18:13:29.359 [MCP] mcp_server.tools.tasks_v2.register - INFO - [Tasks V2] Registered tool: list_unassigned_tasks
18:13:29.359 [MCP] mcp_server.tools.tasks_v2.register - INFO - [Tasks V2] Registered tool: list_tasks_in_sprint
18:13:29.359 [MCP] mcp_server.tools.tasks_v2.register - INFO - [Tasks V2] Registered tool: get_task
18:13:29.359 [MCP] mcp_server.tools.tasks_v2.register - INFO - [Tasks V2] Registered tool: create_task
18:13:29.359 [MCP] mcp_server.tools.tasks_v2.register - INFO - [Tasks V2] Registered tool: update_task
18:13:29.360 [MCP] mcp_server.tools.tasks_v2.register - INFO - [Tasks V2] Registered tool: delete_task
18:13:29.360 [MCP] mcp_server.tools.tasks_v2.register - INFO - [Tasks V2] Registered tool: assign_task
18:13:29.360 [MCP] mcp_server.tools.tasks_v2.register - INFO - [Tasks V2] Registered tool: update_task_status
18:13:29.360 [MCP] mcp_server.tools.tasks_v2.register - INFO - [Tasks V2] Registered tool: search_tasks
18:13:29.360 [MCP] mcp_server.tools.tasks_v2.register - INFO - [Tasks V2] Registered 12 task tools (fully independent)
18:13:29.360 [MCP] mcp_server.server - INFO - Registered 12 tasks_v2 tools
18:13:29.361 [MCP] mcp_server.server - INFO - [sprints_v2] Registering with context
18:13:29.361 [MCP] mcp_server.tools.sprints_v2.register - INFO - [Sprints V2] Registered tool: list_sprints
18:13:29.361 [MCP] mcp_server.tools.sprints_v2.register - INFO - [Sprints V2] Registered tool: get_sprint
18:13:29.361 [MCP] mcp_server.tools.sprints_v2.register - INFO - [Sprints V2] Registered tool: create_sprint
18:13:29.361 [MCP] mcp_server.tools.sprints_v2.register - INFO - [Sprints V2] Registered tool: update_sprint
18:13:29.362 [MCP] mcp_server.tools.sprints_v2.register - INFO - [Sprints V2] Registered tool: delete_sprint
18:13:29.362 [MCP] mcp_server.tools.sprints_v2.register - INFO - [Sprints V2] Registered tool: start_sprint
18:13:29.362 [MCP] mcp_server.tools.sprints_v2.register - INFO - [Sprints V2] Registered tool: complete_sprint
18:13:29.362 [MCP] mcp_server.tools.sprints_v2.register - INFO - [Sprints V2] Registered tool: get_sprint_tasks
18:13:29.362 [MCP] mcp_server.tools.sprints_v2.register - INFO - [Sprints V2] Registered 8 sprint tools (fully independent)
18:13:29.362 [MCP] mcp_server.server - INFO - Registered 8 sprints_v2 tools
18:13:29.362 [MCP] mcp_server.server - INFO - [epics_v2] Registering with context
18:13:29.363 [MCP] mcp_server.tools.epics_v2.register - INFO - [Epics V2] Registered tool: list_epics
18:13:29.364 [MCP] mcp_server.tools.epics_v2.register - INFO - [Epics V2] Registered tool: get_epic
18:13:29.364 [MCP] mcp_server.tools.epics_v2.register - INFO - [Epics V2] Registered tool: create_epic
18:13:29.364 [MCP] mcp_server.tools.epics_v2.register - INFO - [Epics V2] Registered tool: update_epic
18:13:29.365 [MCP] mcp_server.tools.epics_v2.register - INFO - [Epics V2] Registered tool: delete_epic
18:13:29.365 [MCP] mcp_server.tools.epics_v2.register - INFO - [Epics V2] Registered tool: link_task_to_epic
18:13:29.365 [MCP] mcp_server.tools.epics_v2.register - INFO - [Epics V2] Registered tool: unlink_task_from_epic
18:13:29.365 [MCP] mcp_server.tools.epics_v2.register - INFO - [Epics V2] Registered 7 epic tools (fully independent)
18:13:29.365 [MCP] mcp_server.server - INFO - Registered 7 epics_v2 tools
18:13:29.365 [MCP] mcp_server.server - INFO - [epics_v2] Registering with context
18:13:29.366 [MCP] mcp_server.tools.epics_v2.register - INFO - [Epics V2] Registered tool: list_epics
18:13:29.366 [MCP] mcp_server.tools.epics_v2.register - INFO - [Epics V2] Registered tool: get_epic
18:13:29.366 [MCP] mcp_server.tools.epics_v2.register - INFO - [Epics V2] Registered tool: create_epic
18:13:29.366 [MCP] mcp_server.tools.epics_v2.register - INFO - [Epics V2] Registered tool: update_epic
18:13:29.366 [MCP] mcp_server.tools.epics_v2.register - INFO - [Epics V2] Registered tool: delete_epic
18:13:29.367 [MCP] mcp_server.tools.epics_v2.register - INFO - [Epics V2] Registered tool: link_task_to_epic
18:13:29.367 [MCP] mcp_server.tools.epics_v2.register - INFO - [Epics V2] Registered tool: unlink_task_from_epic
18:13:29.367 [MCP] mcp_server.tools.epics_v2.register - INFO - [Epics V2] Registered 7 epic tools (fully independent)
18:13:29.367 [MCP] mcp_server.server - INFO - Registered 7 epics_v2 tools
18:13:29.367 [MCP] mcp_server.server - INFO - [pm_service_users] Registering with context
18:13:29.368 [MCP] mcp_server.tools.pm_service_tools.register - INFO - [PM Service Tools] Registered tool: list_users
18:13:29.368 [MCP] mcp_server.tools.pm_service_tools.register - INFO - [PM Service Tools] Registered tool: get_user
18:13:29.368 [MCP] mcp_server.tools.pm_service_tools.register - INFO - [PM Service Tools] Registered tool: list_worklogs
18:13:29.368 [MCP] mcp_server.tools.pm_service_tools.register - INFO - [PM Service Tools] Registered 3 user tools
18:13:29.368 [MCP] mcp_server.server - INFO - Registered 3 pm_service_users tools
18:13:29.368 [MCP] mcp_server.server - INFO - [meeting_tools] Registering with context
18:13:29.369 [MCP] mcp_server.server - INFO - Registered 7 meeting_tools tools
18:13:29.369 [MCP] mcp_server.server - INFO - Total tools registered: 10
18:13:29.369 [MCP] mcp_server.server - INFO - Creating single routing handler for all tool calls...
18:13:29.369 [MCP] mcp_server.server - INFO - ✅ Routing handler created. 54 tools available for routing.
18:13:29.369 [MCP] mcp_server.server - INFO - Registering list_tools handler...
18:13:29.369 [MCP] mcp_server.server - INFO - ✅ list_tools handler registered successfully
18:13:29.369 [MCP] mcp_server.server - INFO -    Handler type: <class 'function'>
18:13:29.369 [MCP] mcp_server.server - INFO -    Handler: <function Server.list_tools.<locals>.decorator.<locals>.handler at 0xffff9e999580>
18:13:29.570 [MCP] mcp_server.server - INFO - SSE transport initialized - 66 tools available via MCP server
18:13:29.570 [MCP] mcp_server.server - INFO - PM MCP Server (SSE) starting on http://0.0.0.0:8080
18:13:29.570 [MCP] mcp_server.server - INFO - SSE endpoint: http://0.0.0.0:8080/sse
18:13:29.570 [MCP] mcp_server.server - INFO - Tools endpoint: http://0.0.0.0:8080/tools/list
18:13:29.570 [MCP] mcp_server.server - INFO - Call tool: http://0.0.0.0:8080/tools/call
18:13:29.570 [MCP] mcp_server.server - INFO - Stream tool: http://0.0.0.0:8080/tools/call/stream
18:13:31.040 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
18:14:01.172 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
18:14:31.241 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
18:15:01.305 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
18:15:31.365 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
18:16:01.415 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
18:16:31.472 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
 [MCP] INFO:     127.0.0.1:38322 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:45624 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:44024 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:60872 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:51138 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:57686 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:38384 - "GET /health HTTP/1.1" 200 OK
 [MCP] Building deer-flow @ file:///app
 [MCP] Built deer-flow @ file:///app
 [MCP] Uninstalled 1 package in 7ms
 [MCP] Installed 1 package in 0.71ms
 [MCP] INFO:     Started server process [19]
 [MCP] INFO:     Waiting for application startup.
 [MCP] INFO:     Application startup complete.
 [MCP] INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

---

## Browser Console Logs

```
[BROWSER] Failed to load resource: the server responded with a status of 401 (Unauthorized) - /api/auth/me
[BROWSER] [Fast Refresh] rebuilding
[BROWSER] [Fast Refresh] done in 1339ms
[BROWSER] [Fast Refresh] rebuilding
[BROWSER] [Fast Refresh] done in 112ms
[BROWSER] [Fast Refresh] rebuilding
[BROWSER] [Fast Refresh] done in 698ms
[BROWSER] [Fast Refresh] rebuilding
[BROWSER] [Fast Refresh] done in 101ms
[BROWSER] grid.svg: Failed to load resource: 404 (Not Found)
[BROWSER] CSS preload warning - resource not used within timeout
[BROWSER] layout-router.tsx:139 Skipping auto-scroll behavior due to position: sticky/fixed
```
