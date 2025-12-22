# Project Management Agent - Module Index

## Overview
This repository contains multiple interconnected modules for PM and Meeting AI agents.

## Modules

| Module | Purpose | Summary Doc |
|--------|---------|-------------|
| `shared/` | Reusable base classes | [CODEBASE_SUMMARY.md](shared/CODEBASE_SUMMARY.md) |
| `backend/` | PM Agent core | [BACKEND_CODEBASE_SUMMARY.md](backend/BACKEND_CODEBASE_SUMMARY.md) |
| `mcp_server/` | PM MCP Server | [ARCHITECTURE.md](mcp_server/ARCHITECTURE.md) |
| `meeting_agent/` | Meeting Notes Agent | [CODEBASE_SUMMARY.md](meeting_agent/CODEBASE_SUMMARY.md) |
| `mcp_meeting_server/` | Meeting MCP Server | [CODEBASE_SUMMARY.md](mcp_meeting_server/CODEBASE_SUMMARY.md) |
| `web/` | Frontend | [CODEBASE_SUMMARY.md](web/CODEBASE_SUMMARY.md) |

## Quick Start

### Working on a Specific Module
Read the module's AI context file first:
```
<module>/.agent/context.md
```

### Module Dependencies
```
shared/ ─────────────────────────────────────────
   ↑                    ↑                    ↑
backend/           meeting_agent/        mcp_server/
   ↑                    ↑                    
mcp_server/      mcp_meeting_server/     
```

## AI Assistant Tips

1. **Start with module docs** - Read CODEBASE_SUMMARY.md first
2. **Use .agent/context.md** - Contains quick patterns and gotchas
3. **Focus on one module** - Reduces context token usage
4. **Check related modules** - Listed in each context.md

## Running Services

```bash
# PM Backend
python server.py

# PM MCP Server  
python -m mcp_server.main

# Meeting MCP Server
python scripts/run_meeting_mcp_server.py

# Frontend
cd web && npm run dev
```
