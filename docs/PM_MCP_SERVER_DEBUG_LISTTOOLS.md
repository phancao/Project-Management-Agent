# PM MCP Server - ListToolsRequest Debugging

## Issue Summary

The PM MCP Server exits immediately after processing a `ListToolsRequest`. The server:
1. ✅ Starts successfully
2. ✅ Registers 53 tools
3. ✅ Receives `ListToolsRequest`
4. ❌ Exits immediately after processing it

## Log Analysis

From `logs/pm_mcp_server.log`:

```
2025-11-19 15:17:17,764 - mcp.server.lowlevel.server - INFO - Processing request of type ListToolsRequest
2025-11-19 15:17:17,765 - src.mcp_servers.pm_server.server - WARNING - server.run() completed - this shouldn't happen unless connection closed
2025-11-19 15:17:17,765 - src.mcp_servers.pm_server.server - INFO - Cleaning up PM MCP Server...
```

**Key Observations:**
- No error is logged during ListToolsRequest processing
- `server.run()` completes immediately (connection closed)
- Server cleanup happens normally
- This pattern repeats consistently

## Root Cause Analysis

### Possible Causes

1. **Client Closing Connection**
   - Client receives error response from server
   - Client closes connection after receiving response
   - Server detects closed connection and exits

2. **Tool Registration Issue**
   - Tools registered with `@server.call_tool()` but not enumerable
   - Server can't generate proper list_tools response
   - Client receives error/empty response and closes connection

3. **Response Format Issue**
   - Server responds to list_tools but format is incorrect
   - Client rejects response and closes connection

4. **Exception During Processing**
   - Exception occurs but not logged
   - Server exits without proper error handling

## Current Implementation

### Tool Registration Pattern

Tools are registered using `@server.call_tool()` decorator:

```python
@server.call_tool()
async def list_projects(arguments: dict[str, Any]) -> list[TextContent]:
    """List all accessible projects across all PM providers."""
    # ... implementation
```

### Server Setup

```python
# Initialize server
self.server = Server(self.config.server_name)

# Register tools
self._register_all_tools()

# Enable tools capability
init_options.capabilities.tools = ToolsCapability(list_changed=False)

# Run server
await self.server.run(read_stream, write_stream, init_options)
```

## Debugging Steps Taken

1. ✅ Added error handling around `server.run()`
2. ✅ Added logging for connection closure
3. ✅ Verified tools capability is enabled
4. ✅ Checked tool registration count
5. ✅ Added exception handling for CancelledError

## Next Steps to Debug

### 1. Enable Debug Logging

Add more detailed logging to see what happens during list_tools:

```python
# In server.py, add before server.run():
import logging
logging.getLogger("mcp").setLevel(logging.DEBUG)
logging.getLogger("mcp.server").setLevel(logging.DEBUG)
```

### 2. Test with Minimal Client

Create a simple test client to see the actual response:

```python
# test_list_tools.py
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test():
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "scripts/run_pm_mcp_server.py", "--transport", "stdio"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Try to list tools
            try:
                result = await session.list_tools()
                print(f"Tools: {len(result.tools)}")
                for tool in result.tools:
                    print(f"  - {tool.name}")
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()

asyncio.run(test())
```

### 3. Check MCP SDK Version

Verify the MCP SDK version and check for known issues:

```bash
pip show mcp
```

### 4. Verify Tool Registration

Add logging to verify tools are actually registered:

```python
# After _register_all_tools()
if hasattr(self.server, '_tools'):
    tools_dict = getattr(self.server, '_tools', {})
    logger.info(f"Registered tools: {list(tools_dict.keys())}")
else:
    logger.error("Tools not found in server._tools!")
```

### 5. Check for Exceptions in Tool Handlers

The issue might be that a tool handler is raising an exception during registration or listing. Add try-catch around tool registration:

```python
try:
    count = register_func(self.server, self.pm_handler, self.config)
except Exception as e:
    logger.error(f"Failed to register {module_name} tools: {e}", exc_info=True)
    raise
```

## Potential Solutions

### Solution 1: Explicit Tool Definitions

Instead of relying on automatic tool discovery, explicitly define tools:

```python
from mcp.types import Tool

@server.call_tool()
async def list_projects(arguments: dict[str, Any]) -> list[TextContent]:
    # ... implementation

# Explicitly register with metadata
tool = Tool(
    name="list_projects",
    description="List all accessible projects",
    inputSchema={
        "type": "object",
        "properties": {
            "provider_id": {"type": "string"},
            "search": {"type": "string"},
            "limit": {"type": "integer"}
        }
    }
)
```

### Solution 2: Custom list_tools Handler

Add a custom handler to ensure proper response:

```python
@self.server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List all available tools."""
    tools = []
    # Manually collect tools from registered handlers
    # Return proper Tool objects
    return tools
```

### Solution 3: Fix Response Format

Ensure the server returns proper MCP response format for list_tools.

## Testing

Run the test script to verify the fix:

```bash
# Test core functionality
uv run python scripts/test_pm_mcp_server.py

# Test with actual client
uv run python test_list_tools.py
```

## Related Issues

- MCP Python SDK issues: https://github.com/modelcontextprotocol/python-sdk/issues
- Similar issues reported: https://github.com/modelcontextprotocol/python-sdk/issues/396

## Root Cause Found! ✅

**Issue Identified**: The code was checking for tools in `_tools` attribute, but the MCP SDK (version 1.12.2) stores tools in `_tool_cache` instead.

**Evidence from logs**:
- Line 342: `Server attributes: ['_tool_cache']` - Tools are in `_tool_cache`, not `_tools`
- Line 344: `❌ Cannot enable tools capability: No tools registered!` - Code found 0 tools because it checked wrong attribute
- Line 346: `❌ Tools capability is NOT enabled` - Because tools_count was 0, capability wasn't enabled
- Line 351: `Response sent` - Server responded to ListToolsRequest but with empty/error response, client closed connection

**Fix Applied**:
1. ✅ Updated code to check multiple possible attributes (`_tools`, `_tool_cache`, `_call_tool_handlers`)
2. ✅ Always enable tools capability even if we can't verify count (MCP SDK handles enumeration automatically)
3. ✅ Added better logging to identify where tools are stored

## Critical Finding! 🔍

**Root Cause Identified**: `_tool_cache` is **EMPTY** (0 items) even though tools are being "registered"

**Evidence from latest logs**:
- Line 433: `_tool_cache is a dict with 0 items` - Cache exists but is empty!
- Line 447: `_tool_cache: dict with length 0` - Confirmed empty
- Tools are being decorated with `@server.call_tool()` but not appearing in cache
- Server responds to ListToolsRequest but with empty tool list
- Client closes connection because response is empty

**The Problem**:
The `@server.call_tool()` decorator is being used inside functions (`register_project_tools()`, etc.), but tools are NOT being stored in `_tool_cache`. This suggests:
1. The decorator might need to be applied at module level
2. Tools might need explicit names/metadata
3. There might be a version mismatch in MCP SDK
4. The decorator pattern might have changed

## Update: MCP SDK Upgraded! ✅

**Action Taken**: Updated MCP SDK from 1.12.2 → 1.21.2

**Changes Made**:
- Updated `pyproject.toml`: `mcp>=1.11.0` → `mcp>=1.21.2`
- Ran `uv sync` to install new version
- Verified installation: MCP SDK version 1.21.2 confirmed

**New Features in 1.21.2** (from release notes):
- Support for structured tool outputs
- OAuth-based authorization
- Improved security best practices
- Various bug fixes and improvements

## Status

- **Issue**: Server exits after ListToolsRequest
- **Root Cause**: `_tool_cache` is empty - tools decorated with `@server.call_tool()` are not being registered
- **Status**: ✅ MCP SDK Updated - Ready for Testing
- **Priority**: Critical (blocks all MCP server functionality)
- **Next Action**: 
  1. ✅ **DONE**: Updated MCP SDK to 1.21.2
  2. **TEST**: Run the server again and check if tools are now registered
  3. **VERIFY**: Check logs to see if `_tool_cache` now has tools
  4. **IF STILL EMPTY**: Check if new SDK version requires different registration pattern

---

**Last Updated**: 2025-11-19  
**Investigator**: AI Assistant

