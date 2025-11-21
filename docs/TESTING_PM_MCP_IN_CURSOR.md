# Testing PM MCP Server in Cursor

This guide shows how to test your PM MCP Server connection after configuring it in Cursor.

## 🎯 Quick Verification Steps

### Step 1: Verify Server is Running

First, make sure your PM MCP Server is running:

```bash
# If using Docker (SSE transport)
docker-compose ps pm_mcp_server
# Should show: Up (healthy)

# If running locally (stdio transport)
ps aux | grep run_pm_mcp_server
```

### Step 2: Test Connection from Terminal

Before testing in Cursor, verify the server is accessible:

```bash
# Test health endpoint (if using SSE)
curl http://localhost:8080/health
# Expected: {"status": "healthy", "providers": 3, "tools": 53}

# List tools (if using SSE)
curl -X POST http://localhost:8080/tools/list \
  -H "Content-Type: application/json" \
  -d '{}' | jq '.tools | length'
# Expected: 53 tools
```

### Step 3: Check Cursor MCP Configuration

1. **Open Cursor Settings**
   - Press `Cmd+,` (Mac) or `Ctrl+,` (Windows/Linux)
   - Navigate to **Features** → **MCP**

2. **Verify PM MCP Server is Configured**

   For **stdio transport** (local development):
   ```json
   {
     "mcpServers": {
       "pm-mcp-server": {
         "command": "uv",
         "args": [
           "run",
           "python",
           "/path/to/Project-Management-Agent/scripts/run_pm_mcp_server.py",
           "--transport",
           "stdio"
         ],
         "env": {
           "DATABASE_URL": "postgresql://user:pass@host:port/db"
         }
       }
     }
   }
   ```

   For **SSE transport** (Docker):
   ```json
   {
     "mcpServers": {
       "pm-mcp-server": {
         "transport": "sse",
         "url": "http://localhost:8080/sse"
       }
     }
   }
   ```

3. **Restart Cursor** after making changes to MCP configuration.

---

## 🧪 Testing in Cursor

### Method 1: Test with Natural Language Queries

Open Cursor's chat interface (`Cmd+L` or `Ctrl+L`) and try these queries:

#### Basic Connection Test
```
Can you list all available PM tools?
```

**Expected Result**: 
- ✅ Cursor should recognize MCP tools are available
- ✅ Should list PM-related tools (projects, tasks, sprints, etc.)

#### Test Project Tools
```
List all projects in the PM system
```
or
```
Show me all projects from my project management system
```

**Expected Result**:
- ✅ Should call `list_projects` tool
- ✅ Should return a list of projects from your PM providers
- ✅ Response should show project details

#### Test Task Tools
```
What are my current tasks?
```
or
```
List all tasks assigned to me
```

**Expected Result**:
- ✅ Should call `list_my_tasks` tool
- ✅ Should return your tasks from PM providers

#### Test Sprint Tools
```
Show me all sprints in project [project-name]
```

**Expected Result**:
- ✅ Should call `list_sprints` tool
- ✅ Should return sprint information

### Method 2: Check Available Tools

Ask Cursor directly:
```
What MCP tools are available? Show me the PM MCP Server tools.
```

**Expected**: Should list all 53 PM tools or mention they're available.

### Method 3: Test Specific Tool Calls

```
Use the list_projects tool to show me all projects
```

or

```
Call the PM tool to get my tasks
```

---

## 🔍 Verification Checklist

Use this checklist to verify everything is working:

### Connection Status
- [ ] PM MCP Server is running (Docker or local)
- [ ] Health endpoint returns `200 OK` (if using SSE)
- [ ] Cursor MCP settings show `pm-mcp-server` configured
- [ ] No connection errors in Cursor's MCP logs

### Tool Availability
- [ ] Cursor recognizes PM tools are available
- [ ] Can see tool names when asking about available tools
- [ ] Natural language queries trigger PM tools

### Functionality
- [ ] `list_projects` works and returns project data
- [ ] `list_my_tasks` works and returns task data
- [ ] Can get project details using `get_project`
- [ ] Tools return data from your PM providers (OpenProject, JIRA, ClickUp)

### Error Handling
- [ ] Tools handle missing parameters gracefully
- [ ] Error messages are clear and helpful
- [ ] Cursor can recover from tool errors

---

## 🐛 Troubleshooting

### Issue: "No tools found" or "MCP server not connected"

**Check 1**: Verify server is running
```bash
# For Docker
docker-compose logs pm_mcp_server | tail -20

# For local stdio
ps aux | grep run_pm_mcp_server
```

**Check 2**: Verify Cursor MCP configuration
- Settings → Features → MCP
- Check JSON syntax is valid
- Ensure paths are absolute (for stdio transport)

**Check 3**: Restart Cursor
- Close Cursor completely
- Reopen Cursor
- Check if connection establishes

**Check 4**: Check Cursor MCP logs
- Look for MCP-related errors in Cursor's developer console
- Common issues: connection refused, invalid path, missing dependencies

### Issue: "Tools are available but not being called"

**Solution 1**: Be more explicit in your queries
```
Instead of: "show projects"
Use: "List all projects using the PM MCP Server tools"
```

**Solution 2**: Check tool names match
```bash
# List available tools
curl -X POST http://localhost:8080/tools/list \
  -H "Content-Type: application/json" \
  -d '{}' | jq '.tools[].name'
```

**Solution 3**: Verify tool descriptions
- Tools should have clear descriptions
- Cursor uses descriptions to match queries to tools

### Issue: "Connection timeout" or "Server not responding"

**For SSE Transport**:
```bash
# Test connectivity
curl -v http://localhost:8080/health

# Check if port is accessible
netstat -an | grep 8080  # Linux/Mac
netstat -an | findstr 8080  # Windows
```

**For stdio Transport**:
```bash
# Test the command manually
uv run uv run uv run python scripts/run_pm_mcp_server.py --transport stdio

# Check if command exists and is executable
which uv
ls -la scripts/run_pm_mcp_server.py
```

### Issue: "Database connection failed"

**Check**: Database connectivity
```bash
# Test database connection
psql $DATABASE_URL -c "SELECT 1"

# Or check Docker database
docker-compose exec postgres psql -U postgres -c "SELECT 1"
```

**Solution**: Update `DATABASE_URL` in Cursor's MCP config `env` section

### Issue: "Permission denied" or "Command not found"

**Solution**: 
- Ensure `uv` is in PATH or use full path
- Make sure script path is correct and absolute
- Check file permissions: `chmod +x scripts/run_pm_mcp_server.py`

---

## 📊 Advanced Testing

### Test Multiple Tools in Sequence

Ask Cursor:
```
First, list all projects. Then, for the first project, show me all tasks and sprints.
```

### Test Tool with Parameters

```
Get details for project with ID [project-id]
```

```
Show me the burndown chart for sprint [sprint-id]
```

### Test Error Handling

```
Get project with ID invalid-id
```

Should return an error message explaining the issue.

---

## 🔧 Debug Mode

### Enable Debug Logging

For **SSE transport**, start server with debug:
```bash
docker-compose up pm_mcp_server --log-level DEBUG
```

For **stdio transport**, add to Cursor config:
```json
{
  "mcpServers": {
    "pm-mcp-server": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "/path/to/scripts/run_pm_mcp_server.py",
        "--transport",
        "stdio",
        "--log-level",
        "DEBUG"
      ]
    }
  }
}
```

### View Logs

**Docker logs**:
```bash
docker-compose logs -f pm_mcp_server
```

**Local server logs**: Check console output if running manually.

**Cursor MCP logs**: Check Cursor's developer console (Help → Toggle Developer Tools).

---

## 📝 Test Scripts

### Quick Test Script (Python)

Save as `test_cursor_mcp_connection.py`:

```python
#!/usr/bin/env python3
"""Test PM MCP Server connection for Cursor."""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.client.sse import sse_client
from mcp import ClientSession
from datetime import timedelta

async def test_connection():
    """Test PM MCP Server connection."""
    print("Testing PM MCP Server connection...")
    
    # Test SSE connection (for Docker)
    url = "http://localhost:8080/sse"
    
    try:
        async with sse_client(url=url, timeout=30) as (read, write):
            async with ClientSession(
                read, write, 
                read_timeout_seconds=timedelta(seconds=30)
            ) as session:
                print("✅ Connected to PM MCP Server")
                
                # Initialize
                await session.initialize()
                print("✅ Session initialized")
                
                # List tools
                result = await session.list_tools()
                print(f"✅ Found {len(result.tools)} tools")
                
                # List first 10 tool names
                tool_names = [tool.name for tool in result.tools[:10]]
                print(f"   Sample tools: {', '.join(tool_names)}")
                
                # Test a simple tool call
                if result.tools:
                    try:
                        tool_result = await session.call_tool("list_projects", {})
                        print("✅ Successfully called list_projects tool")
                        print(f"   Result type: {type(tool_result)}")
                    except Exception as e:
                        print(f"⚠️  Tool call failed: {e}")
                
                print("\n✅ All tests passed! Server is ready for Cursor.")
                return True
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Is the server running? (docker-compose ps pm_mcp_server)")
        print("2. Is the URL correct? (http://localhost:8080/sse)")
        print("3. Check server logs: docker-compose logs pm_mcp_server")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
```

Run it:
```bash
uv run python test_cursor_mcp_connection.py
```

---

## ✅ Success Indicators

Your PM MCP Server is working correctly in Cursor if:

1. ✅ **Connection**: No connection errors in Cursor
2. ✅ **Tools Available**: Can see PM tools when asking about available tools
3. ✅ **Queries Work**: Natural language queries trigger appropriate PM tools
4. ✅ **Data Returns**: Tools return actual data from your PM providers
5. ✅ **Multiple Tools**: Can use different tools (projects, tasks, sprints)
6. ✅ **Error Handling**: Errors are clear and helpful

---

## 🎯 Example Test Session

Here's a complete test session you can try in Cursor:

```
You: What PM tools are available from the MCP server?

Cursor: I can see the following PM tools available:
- list_projects
- get_project
- create_project
- list_my_tasks
- list_tasks
... (53 total tools)

You: List all my projects

Cursor: [Calls list_projects tool]
Here are your projects:
1. Project A - OpenProject
2. Project B - JIRA
...

You: What tasks do I have?

Cursor: [Calls list_my_tasks tool]
Your current tasks:
1. Task 1 - In Progress
2. Task 2 - To Do
...

You: Show me sprints in Project A

Cursor: [Calls list_sprints tool]
Sprints for Project A:
- Sprint 1 (Jan 1-15)
- Sprint 2 (Jan 16-31)
...
```

---

## 📚 Additional Resources

- [PM MCP Server Testing Guide](./PM_MCP_SERVER_TESTING_GUIDE.md) - Comprehensive testing guide
- [MCP Client Alternatives](./MCP_CLIENT_ALTERNATIVES.md) - Other MCP clients you can use
- [Cursor Documentation](https://docs.cursor.com) - Official Cursor docs
- [MCP Protocol Documentation](https://modelcontextprotocol.io/) - MCP specification

---

## 💡 Tips

1. **Be Specific**: Use clear, specific queries for better tool matching
2. **Check Logs**: If something doesn't work, check both server and Cursor logs
3. **Start Simple**: Test basic queries first, then try more complex ones
4. **Restart if Needed**: Sometimes restarting Cursor helps establish connections
5. **Test One Thing at a Time**: Verify each tool category separately

---

If you encounter issues not covered here, check the main [PM MCP Server Testing Guide](./PM_MCP_SERVER_TESTING_GUIDE.md) or the [Troubleshooting section](./PM_MCP_SERVER_TESTING_GUIDE.md#-common-issues).











