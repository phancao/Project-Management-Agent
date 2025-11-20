# Plan: Enable Agent to Auto-Configure PM Providers

## Goal
Teach the LLM agent to automatically:
1. **Check for active providers** using `list_providers` tool
2. **Configure a provider** using `configure_pm_provider` if none exist
3. **List projects** using `list_projects` after provider is configured

## Current Problem
- Agent calls `list_projects` directly
- Returns 0 projects because no providers are configured
- Agent doesn't know to check/configure providers first

## Solution: Multi-Step Approach

### Step 1: Create `list_providers` MCP Tool
**File**: `mcp_server/tools/provider_config.py`

Add a new tool that:
- Lists all configured PM providers (active and inactive)
- Shows provider type, name, status, and configuration status
- Returns empty list if no providers exist
- Helps agent understand current provider state

**Tool Signature**:
```python
async def list_providers(arguments: dict[str, Any]) -> list[TextContent]:
    """
    List all configured PM providers (both active and inactive).
    
    Use this tool FIRST before attempting to list projects. If this returns
    no active providers, you must configure a provider using configure_pm_provider
    before you can retrieve projects.
    
    Args:
        active_only (optional): If True, only return active providers (default: False)
    
    Returns:
        List of providers with:
        - id: Provider ID
        - name: Provider name
        - provider_type: Type (jira, openproject, clickup, mock)
        - is_active: Whether provider is active
        - base_url: Provider base URL
        - status: Configuration status
    """
```

### Step 2: Update `list_projects` Tool Description
**File**: `mcp_server/tools/projects.py`

Modify the tool description to guide the agent:

```python
async def list_projects(tool_name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """
    List all accessible projects across all PM providers.
    
    **IMPORTANT WORKFLOW**:
    Before calling this tool, you MUST:
    1. First call `list_providers` to check if any providers are configured
    2. If no active providers exist, call `configure_pm_provider` to set up a provider
    3. Only then call `list_projects` to retrieve projects
    
    If this tool returns 0 projects, it likely means:
    - No providers are configured (check with list_providers first)
    - Providers are configured but have no projects
    - Provider connection failed (check provider status)
    
    Args:
        provider_id (optional): Filter projects by provider ID
        search (optional): Search term for project name/description
        limit (optional): Maximum number of projects to return
    
    Returns:
        List of projects with id, name, description, provider info, etc.
        Returns empty list if no providers are configured or no projects exist.
    """
```

### Step 3: Update `configure_pm_provider` Tool Description
**File**: `mcp_server/tools/provider_config.py`

Enhance the description to guide the workflow:

```python
async def configure_pm_provider(arguments: dict[str, Any]) -> list[TextContent]:
    """
    Configure a PM provider (JIRA, OpenProject, ClickUp, Mock) for the current user.
    
    **WHEN TO USE THIS TOOL**:
    - After calling `list_providers` and finding no active providers
    - When user asks to "list my projects" but no providers are configured
    - When you need to set up a provider before retrieving project data
    
    **WORKFLOW**:
    1. Call `list_providers` first to check current provider status
    2. If no active providers exist, use this tool to configure one
    3. For demo/testing: Use provider_type="mock" (no credentials needed)
    4. For real providers: User must provide credentials (api_key, api_token, etc.)
    
    Args:
        provider_type (required): Type of provider - "jira", "openproject", "clickup", "mock"
        base_url (required): Base URL of the provider
        api_token (optional): API token for JIRA
        api_key (optional): API key for OpenProject or ClickUp
        username (optional): Username/email - required for JIRA
        organization_id (optional): Organization/Team ID for ClickUp
        workspace_id (optional): Workspace ID for OpenProject
        name (optional): Custom name for this provider connection
    
    Returns:
        Success message with provider ID, or error message if configuration fails
    
    Example for Mock provider (demo data, no credentials):
        configure_pm_provider({
            "provider_type": "mock",
            "base_url": "http://localhost",
            "name": "Mock Provider (Demo Data)"
        })
    """
```

### Step 4: Update Agent Prompts
**Files**: 
- `src/prompts/researcher.md`
- `src/prompts/coder.md`

Add a new section about PM Provider Workflow:

```markdown
## Project Management Provider Workflow

**CRITICAL**: Before querying project data, you MUST follow this workflow:

1. **Check Providers First**: Always call `list_providers` tool first to see if any PM providers are configured
2. **Configure if Needed**: If `list_providers` returns no active providers:
   - For demo/testing: Configure a Mock provider using `configure_pm_provider` with provider_type="mock"
   - For real data: Ask user for provider credentials, then configure using `configure_pm_provider`
3. **Then Query Data**: Only after confirming active providers exist, call tools like `list_projects`, `list_tasks`, etc.

**Example Workflow**:
- User: "list my projects"
- Agent: 
  1. Call `list_providers()` → Returns empty list
  2. Call `configure_pm_provider({"provider_type": "mock", "base_url": "http://localhost", "name": "Demo"})`
  3. Call `list_projects()` → Returns projects

**Why This Matters**:
- `list_projects` will return 0 projects if no providers are configured
- You must configure at least one provider before project data is available
- Mock provider is perfect for demo/testing scenarios (no credentials needed)
```

### Step 5: Update Tool Registration
**File**: `mcp_server/server.py` or wherever tools are registered

Ensure `list_providers` tool is:
- Registered with the MCP server
- Included in the tool list for agents
- Has proper error handling

### Step 6: Add Helper Logic (Optional)
**File**: `mcp_server/tools/projects.py`

Add logic to automatically suggest provider configuration if 0 projects are returned:

```python
if not projects:
    # Check if it's because no providers exist
    providers = await pm_handler._get_active_providers()
    if not providers:
        return [TextContent(
            type="text",
            text="No projects found. No active PM providers are configured. "
                 "Please use the 'list_providers' tool to check provider status, "
                 "then use 'configure_pm_provider' to set up a provider before listing projects."
        )]
```

## Implementation Order

1. ✅ Create `list_providers` tool in `provider_config.py`
2. ✅ Update `list_projects` tool description
3. ✅ Update `configure_pm_provider` tool description  
4. ✅ Update agent prompts (researcher.md, coder.md)
5. ✅ Register `list_providers` tool in server
6. ✅ Test the complete workflow

## Testing Plan

1. **Test Case 1**: Fresh system (no providers)
   - Agent receives: "list my projects"
   - Expected: Calls `list_providers` → `configure_pm_provider(mock)` → `list_projects`

2. **Test Case 2**: Provider already configured
   - Agent receives: "list my projects"
   - Expected: Calls `list_providers` → (sees provider exists) → `list_projects`

3. **Test Case 3**: Provider configured but no projects
   - Agent receives: "list my projects"
   - Expected: Calls `list_providers` → `list_projects` → Returns empty (but provider exists)

## Files to Modify

1. `mcp_server/tools/provider_config.py` - Add `list_providers` tool
2. `mcp_server/tools/projects.py` - Update `list_projects` description
3. `mcp_server/tools/provider_config.py` - Update `configure_pm_provider` description
4. `src/prompts/researcher.md` - Add provider workflow section
5. `src/prompts/coder.md` - Add provider workflow section
6. `mcp_server/server.py` - Register `list_providers` tool (if needed)

