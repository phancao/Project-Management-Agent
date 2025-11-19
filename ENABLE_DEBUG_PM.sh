#!/bin/bash
# Script to enable debug logging for PM-related modules and agent flow
# Usage: source ENABLE_DEBUG_PM.sh
# Then start server: python server.py

# PM Provider modules
export DEBUG_PM_PROVIDER=true
export DEBUG_PM_PROVIDERS=true
export DEBUG_PM_HANDLER=true
export DEBUG_PM_MCP_SERVER=true
export DEBUG_PM_TOOLS=true

# Agent and workflow modules (to see tool calls and agent decisions)
export DEBUG_DEERFLOW=true
export DEBUG_AGENTS=true
export DEBUG_GRAPH=true
export DEBUG_WORKFLOW=true

# MCP client/server (to see MCP tool discovery and calls)
export DEBUG_MCP=true

echo "Debug logging enabled for:"
echo "  PM Modules:"
echo "    - DEBUG_PM_PROVIDER=true"
echo "    - DEBUG_PM_PROVIDERS=true"
echo "    - DEBUG_PM_HANDLER=true"
echo "    - DEBUG_PM_MCP_SERVER=true"
echo "    - DEBUG_PM_TOOLS=true"
echo "  Agent/Workflow Modules:"
echo "    - DEBUG_DEERFLOW=true"
echo "    - DEBUG_AGENTS=true"
echo "    - DEBUG_GRAPH=true"
echo "    - DEBUG_WORKFLOW=true"
echo "  MCP:"
echo "    - DEBUG_MCP=true"
echo ""
echo "Now start the server with: python server.py"
echo ""
echo "This will show debug logs for:"
echo "  1. Agent receiving message and deciding which tools to use"
echo "  2. MCP tool discovery and connection"
echo "  3. MCP tool calls (list_my_tasks, etc.)"
echo "  4. PMHandler processing (list_my_tasks method)"
echo "  5. Provider calls (get_current_user, list_tasks, etc.)"
