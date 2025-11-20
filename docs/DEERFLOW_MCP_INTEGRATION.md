## DeerFlow + PM MCP Server Integration Guide

## 🎯 Overview

This guide explains how to integrate the PM MCP Server with DeerFlow agents, enabling them to access PM operations through a centralized MCP server instead of direct PMHandler integration.

## 🏗️ Architecture

### Before (Direct Integration)
```
DeerFlow Agent → PM Tools → PMHandler → PM Providers
```

### After (MCP Integration)
```
DeerFlow Agent → MCP Client → PM MCP Server → PMHandler → PM Providers
```

### Benefits
- ✅ Centralized PM operations
- ✅ Support for multiple specialized agents (QC, HR, etc.)
- ✅ Better separation of concerns
- ✅ Easier testing and monitoring
- ✅ Backward compatible with existing setup

## 🚀 Quick Start

### 1. Start PM MCP Server

```bash
# Start with SSE transport (recommended for DeerFlow)
uv run uv run uv run python scripts/run_pm_mcp_server.py --transport sse --port 8080
```

### 2. Configure DeerFlow Agents

There are two ways to integrate PM MCP tools:

#### Option A: Programmatic Configuration (Recommended)

```python
from backend.tools import configure_pm_mcp_client, get_pm_mcp_tools

# Configure PM MCP client
configure_pm_mcp_client(
    transport="sse",
    url="http://localhost:8080",
    enabled_tools=None  # None = all tools, or specify list
)

# Get PM tools
pm_tools = await get_pm_mcp_tools()

# Use in agent
tools = [web_search, crawl] + pm_tools
agent = create_agent("researcher", tools)
```

#### Option B: Environment Variables

```bash
# Set environment variables
export PM_MCP_ENABLED=true
export PM_MCP_URL=http://localhost:8080
export PM_MCP_TRANSPORT=sse

# DeerFlow will auto-configure PM MCP client
```

## 📝 Integration Examples

### Example 1: Researcher Agent with PM Tools

```python
# backend/graph/nodes.py

async def researcher_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Researcher node with PM MCP tools."""
    
    configurable = Configuration.from_runnable_config(config)
    
    # Base tools
    tools = [
        get_web_search_tool(configurable.max_search_results),
        crawl_tool
    ]
    
    # Add retriever if available
    retriever_tool = get_retriever_tool(state.get("resources", []))
    if retriever_tool:
        tools.insert(0, retriever_tool)
    
    # Add PM tools via MCP
    try:
        from backend.tools import get_pm_mcp_tools, is_pm_mcp_configured
        
        if is_pm_mcp_configured():
            pm_tools = await get_pm_mcp_tools()
            tools.extend(pm_tools)
            logger.info(f"Added {len(pm_tools)} PM tools via MCP")
        else:
            # Fallback to direct PM tools
            from backend.tools import get_pm_tools
            pm_tools = get_pm_tools()
            if pm_tools:
                tools.extend(pm_tools)
                logger.info(f"Added {len(pm_tools)} PM tools (direct)")
    except Exception as e:
        logger.warning(f"Could not add PM tools: {e}")
    
    return await _setup_and_execute_agent_step(
        state, config, "researcher", tools
    )
```

### Example 2: Selective Tool Loading

```python
# Load only specific PM tools
configure_pm_mcp_client(
    transport="sse",
    url="http://localhost:8080",
    enabled_tools=[
        "list_projects",
        "list_my_tasks",
        "get_project",
        "get_task",
        "create_task",
        "update_task_status"
    ]
)

pm_tools = await get_pm_mcp_tools()
# Only 6 tools loaded instead of all 51
```

### Example 3: QC Agent with PM Tools

```python
async def qc_agent_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """QC agent with defect tracking tools."""
    
    # Configure PM MCP for QC-specific tools
    configure_pm_mcp_client(
        transport="sse",
        url="http://localhost:8080",
        enabled_tools=[
            "list_tasks",           # View tasks
            "create_task",          # Create defects
            "update_task_status",   # Update defect status
            "link_related_tasks",   # Link defects to tasks
            "add_task_comment",     # Add defect comments
        ]
    )
    
    # Get QC-specific tools
    pm_tools = await get_pm_mcp_tools()
    
    # QC-specific tools
    qc_tools = [
        test_execution_tool,
        defect_analysis_tool,
    ]
    
    tools = qc_tools + pm_tools
    
    agent = create_agent("qc_agent", tools)
    return await _execute_agent_step(state, agent, "qc_agent")
```

## 🔧 Configuration Options

### PM MCP Client Configuration

```python
configure_pm_mcp_client(
    transport="sse",              # "sse" or "stdio"
    url="http://localhost:8080",  # MCP server URL (for SSE)
    enabled_tools=None            # None = all, or list of tool names
)
```

### Environment Variables

```bash
# Enable PM MCP integration
PM_MCP_ENABLED=true

# MCP server URL
PM_MCP_URL=http://localhost:8080

# Transport type
PM_MCP_TRANSPORT=sse

# Specific tools (comma-separated, optional)
PM_MCP_ENABLED_TOOLS=list_projects,list_my_tasks,create_task
```

## 🔄 Migration Guide

### Step 1: Keep Existing Setup Working

The new MCP integration is **backward compatible**. Your existing setup will continue to work:

```python
# Existing code (still works)
from backend.tools import get_pm_tools

pm_tools = get_pm_tools()  # Uses direct PMHandler
```

### Step 2: Start PM MCP Server

```bash
# Terminal 1: Start PM MCP Server
uv run uv run uv run python scripts/run_pm_mcp_server.py --transport sse --port 8080
```

### Step 3: Update Agent Code (Gradual)

Update one agent at a time:

```python
# Before
from backend.tools import get_pm_tools
pm_tools = get_pm_tools()

# After
from backend.tools import configure_pm_mcp_client, get_pm_mcp_tools

configure_pm_mcp_client(
    transport="sse",
    url="http://localhost:8080"
)
pm_tools = await get_pm_mcp_tools()
```

### Step 4: Test Thoroughly

```bash
# Test with existing queries
curl -X POST http://localhost:3000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"list my projects"}]}'
```

### Step 5: Monitor and Optimize

```bash
# Check PM MCP Server logs
tail -f logs/pm_mcp_server.log

# Monitor tool usage
curl http://localhost:8080/health
```

## 🧪 Testing

### Test PM MCP Integration

```python
# tests/test_pm_mcp_integration.py

import pytest
from backend.tools import (
    configure_pm_mcp_client,
    get_pm_mcp_tools,
    is_pm_mcp_configured,
    reset_pm_mcp_client
)

@pytest.fixture
def pm_mcp_server():
    """Start PM MCP server for testing."""
    # Start server
    # ... server startup code ...
    yield
    # Cleanup

@pytest.mark.asyncio
async def test_pm_mcp_tools_loading(pm_mcp_server):
    """Test loading PM tools from MCP server."""
    
    # Configure client
    configure_pm_mcp_client(
        transport="sse",
        url="http://localhost:8080"
    )
    
    assert is_pm_mcp_configured()
    
    # Load tools
    tools = await get_pm_mcp_tools()
    
    assert len(tools) > 0
    assert any(tool.name == "list_projects" for tool in tools)
    assert any(tool.name == "list_my_tasks" for tool in tools)
    
    # Cleanup
    reset_pm_mcp_client()

@pytest.mark.asyncio
async def test_selective_tool_loading(pm_mcp_server):
    """Test loading specific PM tools."""
    
    configure_pm_mcp_client(
        transport="sse",
        url="http://localhost:8080",
        enabled_tools=["list_projects", "list_my_tasks"]
    )
    
    tools = await get_pm_mcp_tools()
    
    assert len(tools) == 2
    tool_names = [tool.name for tool in tools]
    assert "list_projects" in tool_names
    assert "list_my_tasks" in tool_names
```

## 🐛 Troubleshooting

### Issue: "PM MCP client not configured"

```python
# Solution: Configure before using
from backend.tools import configure_pm_mcp_client

configure_pm_mcp_client(
    transport="sse",
    url="http://localhost:8080"
)
```

### Issue: "Connection refused"

```bash
# Check if PM MCP Server is running
curl http://localhost:8080/health

# Start server if not running
uv run uv run uv run python scripts/run_pm_mcp_server.py --transport sse --port 8080
```

### Issue: Tools not loading

```python
# Check configuration
from backend.tools import get_pm_mcp_config, is_pm_mcp_configured

print(f"Configured: {is_pm_mcp_configured()}")
print(f"Config: {get_pm_mcp_config()}")

# Check server health
import httpx
response = httpx.get("http://localhost:8080/health")
print(response.json())
```

### Issue: Slow tool calls

- **Check network latency** between DeerFlow and PM MCP Server
- **Use localhost** for best performance
- **Enable caching** in PM MCP Server config
- **Consider stdio transport** for same-machine deployment

## 📊 Performance Comparison

| Metric | Direct PMHandler | PM MCP (SSE) | PM MCP (stdio) |
|--------|------------------|--------------|----------------|
| Latency | ~50ms | ~100ms | ~60ms |
| Setup | Complex | Simple | Simple |
| Monitoring | Limited | Excellent | Good |
| Multi-agent | Difficult | Easy | Easy |
| Scalability | Limited | High | Medium |

## 🔗 Related Documentation

- [PM MCP Server Architecture](PM_MCP_SERVER_ARCHITECTURE.md)
- [PM MCP Server SSE Guide](PM_MCP_SERVER_SSE_GUIDE.md)
- [PM MCP Server HTTP Guide](PM_MCP_SERVER_HTTP_GUIDE.md)
- [PM MCP Server Status](PM_MCP_SERVER_STATUS.md)

## 📝 Best Practices

1. **Start with SSE transport** for web-based deployments
2. **Use selective tool loading** for specialized agents
3. **Monitor PM MCP Server health** regularly
4. **Keep fallback to direct PM tools** during migration
5. **Test thoroughly** before full migration
6. **Use environment variables** for configuration
7. **Enable logging** for debugging

## 🎯 Next Steps

1. Start PM MCP Server
2. Configure one agent with MCP tools
3. Test with existing queries
4. Monitor performance
5. Gradually migrate other agents
6. Remove direct PM tool dependencies
7. Create specialized agents (QC, HR, etc.)

---

**Last Updated**: 2025-01-15  
**Version**: 1.0.0

