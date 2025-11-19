# Smart Debug Logging Guide

The smart debug logging system allows you to enable/disable debug logs for specific modules before running, helping you focus on the areas you need to debug while reducing noise in the logs.

## Quick Start

### Using Environment Variables

Set environment variables before starting the server:

```bash
# Enable debug for PM Provider module
DEBUG_PM_PROVIDER=true python server.py

# Enable debug for multiple modules
DEBUG_PM_PROVIDER=true DEBUG_ANALYTICS=true DEBUG_MCP=true python server.py

# Enable debug for all DeerFlow components
DEBUG_DEERFLOW=true python server.py
```

### Available Modules

#### Core Modules
- `DEBUG_DEERFLOW` - DeerFlow workflow, graph, and agents
- `DEBUG_PM_PROVIDER` - PM providers, PM handler, PM MCP server
- `DEBUG_ANALYTICS` - Analytics service, adapters, calculators
- `DEBUG_CONVERSATION` - Conversation flow manager
- `DEBUG_TOOLS` - All tools (search, crawl, retriever, etc.)
- `DEBUG_RAG` - RAG retriever and builders
- `DEBUG_CRAWLER` - Web crawler

#### Granular Sub-Modules

**PM Provider:**
- `DEBUG_PM_PROVIDERS` - Individual PM providers (JIRA, OpenProject, etc.)
- `DEBUG_PM_MCP_SERVER` - PM MCP server specifically
- `DEBUG_PM_HANDLER` - PM handler abstraction layer

**Analytics:**
- `DEBUG_ANALYTICS_SERVICE` - Analytics service
- `DEBUG_ANALYTICS_ADAPTERS` - Analytics adapters
- `DEBUG_ANALYTICS_CALCULATORS` - Analytics calculators

**Agents & Workflow:**
- `DEBUG_AGENTS` - Agent creation and execution
- `DEBUG_GRAPH` - Graph nodes and execution
- `DEBUG_WORKFLOW` - Workflow orchestration

**Tools:**
- `DEBUG_SEARCH_TOOLS` - Search tools (Tavily, etc.)
- `DEBUG_PM_TOOLS` - PM tools
- `DEBUG_ANALYTICS_TOOLS` - Analytics tools

**MCP:**
- `DEBUG_MCP` - MCP client and server connections

## Examples

### Debug PM Provider Issues

```bash
DEBUG_PM_PROVIDER=true python server.py
```

This enables debug for:
- PM providers (JIRA, OpenProject, etc.)
- PM handler
- PM MCP server

### Debug Analytics Only

```bash
DEBUG_ANALYTICS=true python server.py
```

This enables debug for:
- Analytics service
- Analytics adapters
- Analytics calculators

### Debug MCP Connection Issues

```bash
DEBUG_MCP=true DEBUG_PM_MCP_SERVER=true python server.py
```

### Debug Everything in DeerFlow

```bash
DEBUG_DEERFLOW=true DEBUG_AGENTS=true DEBUG_GRAPH=true DEBUG_WORKFLOW=true python server.py
```

## Programmatic Usage

You can also configure debug logging programmatically:

```python
from src.config.debug_config import DebugConfig, set_debug_config

# Create custom configuration
debug_config = DebugConfig(
    pm_provider=True,
    analytics=True,
    mcp=True
)

# Apply it
set_debug_config(debug_config)
```

## How It Works

1. The `DebugConfig` class defines which modules should have debug logging enabled
2. When `apply()` is called, it sets the logging level to `DEBUG` for the specified module loggers
3. Modules use standard Python logging, so enabling debug will show all `logger.debug()` calls
4. The configuration is applied automatically on server startup if environment variables are set

## Tips

- **Start specific**: Enable debug only for the module you're debugging to reduce noise
- **Use granular options**: If you only need to debug PM MCP server, use `DEBUG_PM_MCP_SERVER=true` instead of `DEBUG_PM_PROVIDER=true`
- **Combine modules**: You can enable multiple modules at once
- **Check logs**: Look for the message "🔍 Debug logging enabled for modules: ..." to confirm which modules have debug enabled

## Module Logger Names

The system maps module names to Python logger names:

- `deerflow` → `src.workflow`, `src.graph`, `src.agents`
- `pm_provider` → `src.pm_providers`, `src.server.pm_handler`, `src.mcp_servers.pm_server`
- `analytics` → `src.analytics`
- `conversation` → `src.conversation`
- `tools` → `src.tools`
- `rag` → `src.rag`
- `crawler` → `src.crawler`

And more granular mappings for sub-modules.

