# Merged Debug Logs - 2026-01-13T01:41

---

## Full Timeline (All Sources Merged by Timestamp)

```
18:36:55.873 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
18:37:25.923 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
18:37:55.990 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
18:38:26.051 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
18:38:56.112 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
18:39:23.492 [MCP] __main__ - INFO - ============================================================
18:39:23.492 [MCP] __main__ - INFO - PM MCP Server Starting
18:39:23.492 [MCP] __main__ - INFO - ============================================================
18:39:23.492 [MCP] __main__ - INFO - Transport: sse
18:39:23.493 [MCP] __main__ - INFO - Address: 0.0.0.0:8080
18:39:23.493 [MCP] __main__ - INFO - Log Level: INFO
18:39:23.493 [MCP] __main__ - INFO - Authentication: Disabled
18:39:23.493 [MCP] __main__ - INFO - RBAC: Disabled
18:39:23.494 [MCP] __main__ - INFO - ============================================================
18:39:23.494 [MCP] mcp_server.server - INFO - PM MCP Server initialized: pm-server v0.1.0
18:39:23.494 [MCP] mcp_server.server - INFO - Starting PM MCP Server with SSE transport on 0.0.0.0:8080...
18:39:23.494 [MCP] mcp_server.server - INFO - Initializing Tool Context...
18:39:23.494 [MCP] mcp_server.database.connection - INFO - Initializing MCP Server database: mcp-postgres:5432/mcp_server
18:39:23.518 [MCP] mcp_server.database.connection - INFO - MCP Server database tables created/verified
18:39:23.518 [MCP] mcp_server.database.connection - INFO - MCP Server database connection initialized
18:39:23.518 [MCP] mcp_server.core.tool_context - INFO - [ToolContext] Initialized (PM Service: http://pm-service:8001)
18:39:23.575 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
18:39:23.575 [MCP] mcp_server.server - INFO - Tool Context initialized with 1 active provider(s) (all users)
18:39:23.576 [MCP] mcp_server.server - INFO - Registering PM tools...
18:39:23.576 [MCP] mcp_server.server - INFO - [provider_config] Registering with context
18:39:23.576 [MCP] mcp_server.tools.provider_config - INFO - Registered 2 provider configuration tool(s)
18:39:23.576 [MCP] mcp_server.server - INFO - Registered 2 provider_config tools
18:39:23.576 [MCP] mcp_server.server - INFO - [task_interactions] Registering with context
18:39:23.577 [MCP] mcp_server.tools.task_interactions - INFO - Registered 5 task interaction tools
18:39:23.577 [MCP] mcp_server.server - INFO - Registered 5 task_interactions tools
18:39:23.578 [MCP] mcp_server.server - INFO - [analytics] Registering with context
18:39:23.578 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered tool: burndown_chart
18:39:23.578 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered tool: velocity_chart
18:39:23.578 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered tool: sprint_report
18:39:23.579 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered tool: project_health
18:39:23.579 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered tool: cfd_chart
18:39:23.579 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered tool: cycle_time_chart
18:39:23.580 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered tool: work_distribution_chart
18:39:23.580 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered tool: issue_trend_chart
18:39:23.581 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered tool: capacity_chart
18:39:23.581 [MCP] mcp_server.tools.analytics.register - INFO - [Analytics] Registered 9 analytics tools
18:39:23.581 [MCP] mcp_server.server - INFO - Registered 9 analytics tools
18:39:23.581 [MCP] mcp_server.server - INFO - [projects] Registering with context
18:39:23.582 [MCP] mcp_server.tools.projects.register - INFO - [Projects] Registered tool: list_projects
18:39:23.582 [MCP] mcp_server.tools.projects.register - INFO - [Projects] Registered tool: get_project
18:39:23.582 [MCP] mcp_server.tools.projects.register - INFO - [Projects] Registered tool: create_project
18:39:23.582 [MCP] mcp_server.tools.projects.register - INFO - [Projects] Registered tool: update_project
18:39:23.583 [MCP] mcp_server.tools.projects.register - INFO - [Projects] Registered tool: delete_project
18:39:23.583 [MCP] mcp_server.tools.projects.register - INFO - [Projects] Registered tool: search_projects
18:39:23.584 [MCP] mcp_server.tools.projects.register - INFO - [Projects] Registered 6 project tools
18:39:23.584 [MCP] mcp_server.server - INFO - Registered 6 projects tools
18:39:23.584 [MCP] mcp_server.server - INFO - [tasks] Registering with context
18:39:23.585 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: list_tasks
18:39:23.585 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: list_my_tasks
18:39:23.585 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: list_tasks_by_assignee
18:39:23.586 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: list_unassigned_tasks
18:39:23.586 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: list_tasks_in_sprint
18:39:23.586 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: get_task
18:39:23.586 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: create_task
18:39:23.587 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: update_task
18:39:23.587 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: delete_task
18:39:23.587 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: assign_task
18:39:23.587 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: update_task_status
18:39:23.588 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered tool: search_tasks
18:39:23.588 [MCP] mcp_server.tools.tasks.register - INFO - [Tasks] Registered 12 task tools
18:39:23.588 [MCP] mcp_server.server - INFO - Registered 12 tasks tools
18:39:23.589 [MCP] mcp_server.server - INFO - [sprints] Registering with context
18:39:23.589 [MCP] mcp_server.tools.sprints.register - INFO - [Sprints] Registered tool: list_sprints
18:39:23.589 [MCP] mcp_server.tools.sprints.register - INFO - [Sprints] Registered tool: get_sprint
18:39:23.589 [MCP] mcp_server.tools.sprints.register - INFO - [Sprints] Registered tool: create_sprint
18:39:23.589 [MCP] mcp_server.tools.sprints.register - INFO - [Sprints] Registered tool: update_sprint
18:39:23.590 [MCP] mcp_server.tools.sprints.register - INFO - [Sprints] Registered tool: delete_sprint
18:39:23.590 [MCP] mcp_server.tools.sprints.register - INFO - [Sprints] Registered tool: start_sprint
18:39:23.590 [MCP] mcp_server.tools.sprints.register - INFO - [Sprints] Registered tool: complete_sprint
18:39:23.590 [MCP] mcp_server.tools.sprints.register - INFO - [Sprints] Registered tool: get_sprint_tasks
18:39:23.591 [MCP] mcp_server.tools.sprints.register - INFO - [Sprints] Registered 8 sprint tools
18:39:23.591 [MCP] mcp_server.server - INFO - Registered 8 sprints tools
18:39:23.591 [MCP] mcp_server.server - INFO - [epics] Registering with context
18:39:23.591 [MCP] mcp_server.tools.epics.register - INFO - [Epics] Registered tool: list_epics
18:39:23.592 [MCP] mcp_server.tools.epics.register - INFO - [Epics] Registered tool: get_epic
18:39:23.592 [MCP] mcp_server.tools.epics.register - INFO - [Epics] Registered tool: create_epic
18:39:23.592 [MCP] mcp_server.tools.epics.register - INFO - [Epics] Registered tool: update_epic
18:39:23.593 [MCP] mcp_server.tools.epics.register - INFO - [Epics] Registered tool: delete_epic
18:39:23.593 [MCP] mcp_server.tools.epics.register - INFO - [Epics] Registered tool: link_task_to_epic
18:39:23.593 [MCP] mcp_server.tools.epics.register - INFO - [Epics] Registered tool: unlink_task_from_epic
18:39:23.594 [MCP] mcp_server.tools.epics.register - INFO - [Epics] Registered 7 epic tools
18:39:23.594 [MCP] mcp_server.server - INFO - Registered 7 epics tools
18:39:23.594 [MCP] mcp_server.server - INFO - [pm_service_users] Registering with context
18:39:23.595 [MCP] mcp_server.tools.pm_service_tools.register - INFO - [PM Service Tools] Registered tool: list_users
18:39:23.595 [MCP] mcp_server.tools.pm_service_tools.register - INFO - [PM Service Tools] Registered tool: get_user
18:39:23.595 [MCP] mcp_server.tools.pm_service_tools.register - INFO - [PM Service Tools] Registered tool: list_worklogs
18:39:23.596 [MCP] mcp_server.tools.pm_service_tools.register - INFO - [PM Service Tools] Registered 3 user tools
18:39:23.596 [MCP] mcp_server.server - INFO - Registered 3 pm_service_users tools
18:39:23.597 [MCP] mcp_server.server - INFO - [meeting_tools] Registering with context
18:39:23.597 [MCP] mcp_server.server - INFO - Registered 7 meeting_tools tools
18:39:23.598 [MCP] mcp_server.server - INFO - Total tools registered: 9
18:39:23.598 [MCP] mcp_server.server - INFO - Creating single routing handler for all tool calls...
18:39:23.598 [MCP] mcp_server.server - INFO - ✅ Routing handler created. 54 tools available for routing.
18:39:23.598 [MCP] mcp_server.server - INFO - Registering list_tools handler...
18:39:23.599 [MCP] mcp_server.server - INFO - ✅ list_tools handler registered successfully
18:39:23.599 [MCP] mcp_server.server - INFO -    Handler type: <class 'function'>
18:39:23.599 [MCP] mcp_server.server - INFO -    Handler: <function Server.list_tools.<locals>.decorator.<locals>.handler at 0xffff9107ee80>
18:39:23.752 [MCP] mcp_server.server - INFO - SSE transport initialized - 59 tools available via MCP server
18:39:23.752 [MCP] mcp_server.server - INFO - PM MCP Server (SSE) starting on http://0.0.0.0:8080
18:39:23.752 [MCP] mcp_server.server - INFO - SSE endpoint: http://0.0.0.0:8080/sse
18:39:23.752 [MCP] mcp_server.server - INFO - Tools endpoint: http://0.0.0.0:8080/tools/list
18:39:23.752 [MCP] mcp_server.server - INFO - Call tool: http://0.0.0.0:8080/tools/call
18:39:23.752 [MCP] mcp_server.server - INFO - Stream tool: http://0.0.0.0:8080/tools/call/stream
18:39:27.440 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
18:39:57.496 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
18:40:27.541 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
18:40:57.613 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
18:41:27.662 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
 [MCP] INFO:     127.0.0.1:52274 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:34696 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:60296 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:43172 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:46668 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:40928 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:44392 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:36562 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:39872 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:60756 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     Shutting down
 [MCP] INFO:     Waiting for application shutdown.
 [MCP] INFO:     Application shutdown complete.
 [MCP] INFO:     Finished server process [9]
 [MCP] INFO:     Started server process [9]
 [MCP] INFO:     Waiting for application startup.
 [MCP] INFO:     Application startup complete.
 [MCP] INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```
