# Merged Debug Logs - 2026-01-11T12:11

---

## Full Timeline (All Sources Merged by Timestamp)

```
05:06:15.690 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
05:06:45.741 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
05:07:15.791 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
05:07:45.846 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
05:08:15.904 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
05:08:45.962 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
05:09:16.017 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
05:09:46.061 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
05:10:16.119 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
05:10:46.191 [MCP] mcp_server.core.provider_manager - INFO - [ProviderManager] Found 1 active provider(s)
 [MCP] INFO:     127.0.0.1:36072 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:42062 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:49438 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:49978 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:60286 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:38166 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:58070 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:36188 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:39502 - "GET /health HTTP/1.1" 200 OK
 [MCP] INFO:     127.0.0.1:57104 - "GET /health HTTP/1.1" 200 OK
```

---

## Browser Console Logs

```
[BROWSER] listTasks called - filters: {assignee_ids: Array(1), status: open}
[BROWSER] listTasks called - filters: {assignee_ids: Array(1), status: open}
[BROWSER] listTasks called - filters: {assignee_ids: Array(1), status: open}
[BROWSER] listTasks called - filters: {assignee_ids: Array(1), status: open}
[BROWSER] listTasks called - filters: {assignee_ids: Array(1), status: open}
[BROWSER] listTasks called - filters: {assignee_ids: Array(1), status: open}
[BROWSER] listTasks called - filters: {assignee_ids: Array(1), status: open}
[BROWSER] listTasks called - filters: {assignee_ids: Array(1), status: open}
[BROWSER] listTasks called - filters: {assignee_ids: Array(1), status: open}
[BROWSER] warning: The width(-1) and height(-1) of chart should be greater than 0...
[BROWSER] warning: Skipping auto-scroll behavior due to position: sticky or position: fixed on element
```

---

## Analysis

**ISSUE IDENTIFIED**: `listTasks` is called **9 times** in rapid succession during navigation.
This excessive API call pattern is causing the 20+ second loading delay.

**Root Cause**: Multiple components are independently calling the same API endpoint without proper deduplication or caching.

**Potential Locations**:
1. TeamOverview component
2. MemberMatrix component  
3. Other team components that render simultaneously
