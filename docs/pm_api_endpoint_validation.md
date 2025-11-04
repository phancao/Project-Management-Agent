# PM API Endpoint Validation Guide

## Overview

Before implementing new features (Epics, Components, Labels, Workflows) in PM providers, we need to validate that the API endpoints exist, are accessible, and are not deprecated.

## Usage

### Test JIRA Endpoints

```bash
python test_pm_api_endpoints.py jira <base_url> <email> <api_token> [project_key]

# Example:
python test_pm_api_endpoints.py jira https://your-domain.atlassian.net email@example.com your_token SCRUM
```

### Test OpenProject Endpoints

```bash
python test_pm_api_endpoints.py openproject <base_url> <api_key> [project_id]

# Example:
python test_pm_api_endpoints.py openproject https://your-openproject.com apikey123 123
```

## What the Script Tests

### 1. Epics
- **JIRA**: `/rest/api/3/search/jql` with `issuetype = Epic`
- **OpenProject**: `/api/v3/work_packages` with type filter for Epic

### 2. Components
- **JIRA**: `/rest/api/3/project/{projectKey}/components`
- **OpenProject**: `/api/v3/categories` or `/api/v3/projects/{id}/categories`

### 3. Labels
- **JIRA**: Labels field in issue search results
- **OpenProject**: Categories field in work packages

### 4. Workflows
- **JIRA**: `/rest/api/3/workflowscheme` and `/rest/api/3/issue/{key}/transitions`
- **OpenProject**: `/api/v3/statuses` and `/api/v3/types`

## Expected Results

The script will:
- ✅ Mark endpoints as "working" if they return 200 OK
- ❌ Mark endpoints as "deprecated" if they return 410 Gone
- ⚠️ Mark endpoints as "not tested" if they fail or aren't accessible

## Next Steps After Validation

1. **If endpoints work**: Proceed with implementation
2. **If endpoints are deprecated**: Find alternative endpoints or document limitations
3. **If endpoints don't exist**: Use fallback implementations (e.g., custom fields, categories)

## Implementation Priority

Based on validation results:
1. Implement working endpoints first
2. Document deprecated endpoints with alternatives
3. Create fallback implementations for missing features

