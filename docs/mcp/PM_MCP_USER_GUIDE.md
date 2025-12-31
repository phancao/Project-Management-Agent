# PM MCP Server - User Guide

## 📖 Overview

The PM MCP Server provides comprehensive project management capabilities to DeerFlow agents through the Model Context Protocol (MCP). This guide explains how to use PM MCP features in DeerFlow.

## 🚀 Quick Start

### 1. Start PM MCP Server

```bash
# Start with SSE transport (for web-based agents)
uv run uv run uv run python scripts/run_pm_mcp_server.py --transport sse --port 8080
```

### 2. Auto-Configuration

The frontend automatically detects and configures PM MCP Server when available:
- ✅ Checks `http://localhost:8080` on app load
- ✅ Periodically checks every 5 minutes
- ✅ Adds to settings if detected
- ✅ Enables PM tools for Researcher and Coder agents

### 3. Use PM Features

Simply ask DeerFlow agents to perform PM operations:

```
User: "List my projects"
User: "Show me all my tasks"
User: "What's the status of sprint X?"
User: "Create a task in project Y"
```

---

## 💬 Using PM Features

### Project Management Queries

#### List Projects
```
"List my projects"
"Show me all projects"
"What projects do I have access to?"
```

#### Get Project Details
```
"Show me details of project X"
"What's the status of project ABC?"
"Tell me about project [project_id]"
```

#### List Tasks
```
"List my tasks"
"Show me all my assigned tasks"
"What tasks are assigned to me?"
```

#### List Project Tasks
```
"List all tasks in project X"
"Show tasks in project ABC"
"What tasks are in the current project?"
```

#### List Sprints
```
"List sprints in project X"
"Show me all sprints"
"What sprints are active?"
```

#### List Epics
```
"List epics in project X"
"Show all epics"
"What epics are there?"
```

### Creating and Managing

#### Create Tasks
```
"Create a task 'Fix bug' in project X"
"Add a new task to project ABC"
"Create a task with description 'Implement feature'"
```

#### Update Tasks
```
"Update task [task_id] status to in_progress"
"Mark task X as completed"
"Change task Y priority to high"
```

#### Manage Sprints
```
"Start sprint [sprint_id]"
"Complete sprint X"
"Add task [task_id] to sprint [sprint_id]"
```

---

## 🎯 Advanced Features

### Analytics and Reports

#### Burndown Charts
```
"Show burndown chart for sprint X"
"What's the burndown for current sprint?"
```

#### Velocity Charts
```
"Show velocity chart for project X"
"What's the team velocity?"
```

#### Project Health
```
"Show project health for project X"
"What's the health status of project ABC?"
```

#### Sprint Reports
```
"Generate sprint report for sprint X"
"Show me the sprint summary"
```

---

## ⚙️ Configuration

### Manual Configuration

If auto-configuration doesn't work, you can manually configure PM MCP Server:

1. Go to **Settings** → **MCP** tab
2. Click **Add Server**
3. Enter configuration:

```json
{
  "mcpServers": {
    "pm-server": {
      "transport": "sse",
      "url": "http://localhost:8080"
    }
  }
}
```

4. Click **Add** to query server metadata
5. Enable the server (toggle switch)
6. Select tools you want to use (or leave empty for all tools)
7. Save settings

### Environment Variables

```bash
# Enable MCP server configuration (required)
export ENABLE_MCP_SERVER_CONFIGURATION=true

# PM MCP Server URL (default: http://localhost:8080)
export PM_MCP_SERVER_URL=http://localhost:8080
```

---

## 🔧 Troubleshooting

### PM Tools Not Available

**Problem**: Agents can't use PM tools

**Solutions**:
1. ✅ Check if PM MCP Server is running:
   ```bash
   curl http://localhost:8080/health
   ```

2. ✅ Verify MCP configuration in Settings:
   - Go to Settings → MCP tab
   - Ensure "pm-server" is enabled
   - Check that tools are listed

3. ✅ Check browser console for auto-configuration logs:
   ```
   [PM MCP] Auto-configured: pm-server
   [PM MCP] Tools available: 51
   ```

4. ✅ Verify environment variable:
   ```bash
   echo $ENABLE_MCP_SERVER_CONFIGURATION
   # Should output: true
   ```

### Connection Errors

**Problem**: Cannot connect to PM MCP Server

**Solutions**:
1. ✅ Start PM MCP Server:
   ```bash
   uv run uv run uv run python scripts/run_pm_mcp_server.py --transport sse --port 8080
   ```

2. ✅ Check server logs for errors

3. ✅ Verify port is not in use:
   ```bash
   lsof -i :8080
   ```

4. ✅ Check firewall/network settings

### Auto-Configuration Not Working

**Problem**: PM MCP Server not auto-configured

**Solutions**:
1. ✅ Verify server is accessible:
   ```bash
   curl http://localhost:8080/health
   ```

2. ✅ Check browser console for errors

3. ✅ Manually configure via Settings → MCP tab

4. ✅ Wait 5 minutes (auto-check runs periodically)

---

## 📚 Examples

### Example 1: List My Projects

```
User: "List my projects"

Agent: Uses list_projects tool → Returns all projects
```

### Example 2: Create Task

```
User: "Create a task 'Fix login bug' in project 'Web App'"

Agent: 
  1. Uses list_projects to find 'Web App'
  2. Uses create_task with project_id and subject
  3. Confirms task creation
```

### Example 3: Sprint Status

```
User: "What's the status of sprint 'Sprint 10'?"

Agent:
  1. Uses list_sprints to find sprint
  2. Uses get_sprint to get details
  3. Uses get_sprint_tasks to list tasks
  4. Provides comprehensive sprint status
```

### Example 4: Project Analytics

```
User: "Show me the burndown chart for current sprint"

Agent:
  1. Identifies current sprint
  2. Uses burndown_chart tool
  3. Presents chart data and insights
```

---

## 🎓 Best Practices

### 1. Be Specific
- ✅ "List tasks in project 'Web App'"
- ❌ "Show tasks"

### 2. Use Project Context
- When in a project-specific chat, project context is automatically included
- Mention project name for clarity

### 3. Combine Operations
- Ask for multiple operations in one query:
  - "List my tasks and show me the burndown chart"
  - "Show project status and sprint progress"

### 4. Check Status First
- Verify PM MCP Server is running before complex queries
- Use simple queries like "List my projects" to test

---

## 🔗 Related Documentation

- [PM MCP Server Architecture](PM_MCP_SERVER_ARCHITECTURE.md)
- [PM MCP Server SSE Guide](PM_MCP_SERVER_SSE_GUIDE.md)
- [PM MCP Server HTTP Guide](PM_MCP_SERVER_HTTP_GUIDE.md)
- [PM MCP Server Auth Guide](PM_MCP_SERVER_AUTH_GUIDE.md)
- [DeerFlow MCP Integration](DEERFLOW_MCP_INTEGRATION.md)
- [PM MCP Integration Status](PM_MCP_INTEGRATION_STATUS.md)

---

**Last Updated**: 2025-01-15  
**Version**: 1.0.0

