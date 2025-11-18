# JIRA "Spaces" (Next-Gen Projects) Support

## ✅ Updates Made

### 1. Terminology Documentation
- Added clear comments explaining that:
  - **UI Terminology**: Next-Gen projects are called "spaces" in JIRA UI
  - **API Terminology**: API still uses "projects" endpoint (`/rest/api/3/project`)
  - **Provider Support**: Works with both Classic and Next-Gen projects

### 2. Enhanced Project Parsing
- Updated `_parse_project()` method to handle Next-Gen project structure:
  - Checks for `simplifiedId` field (Next-Gen specific)
  - Falls back to standard `key` or `id` fields
  - Maintains backward compatibility with Classic projects

### 3. Next-Gen Detection Helper
- Added `_is_next_gen_project()` method to detect Next-Gen projects
- Checks for indicators like:
  - `style` field containing "next-gen" or "simplified"
  - Different `projectTypeKey` values

### 4. Updated Method Documentation
- All project-related methods now document Next-Gen/spaces support
- Clear indication that "spaces" refer to Next-Gen projects

## 📋 Next Steps

1. **Test with Your JIRA Instance**:
   - Update email in `.env` or via UI/API
   - Verify that your space appears in the projects list
   - Check that backlog and sprints are accessible

2. **Verify Email Auto-Retrieval**:
   - Try adding JIRA provider without email (just API token)
   - System will attempt to retrieve email automatically
   - If it fails, you'll get a helpful error message

3. **Test Features**:
   - List projects/spaces ✅
   - View backlog (via `list_tasks()` with project filter)
   - List sprints (via `list_sprints()`)
   - Create/update tasks
   - Assign tasks to users

## 🔍 Testing Commands

```bash
# Test provider connection
curl http://localhost:8000/api/pm/providers

# Test listing projects/spaces
curl http://localhost:8000/api/pm/providers/{provider_id}/projects

# Update provider with correct email
python3 scripts/utils/update_jira_provider.py your-email@example.com
```

## 📝 Notes

- The API endpoint remains `/rest/api/3/project` for both Classic and Next-Gen
- UI may show "spaces" but internally we use "projects" to match API
- Next-Gen projects have additional fields like `simplifiedId` that we now handle
- Sprints and backlog features work the same for both project types
