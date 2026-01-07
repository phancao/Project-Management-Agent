"""
OpenProject v13 Provider

Connects to OpenProject v13.4.1 (https://www.openproject.org/) API
to manage projects, work packages (tasks), and sprints.

This provider is specifically designed for OpenProject v13.4.1 API.
For OpenProject v16+, use the OpenProjectProvider class.
"""
import base64
import requests
from typing import List, Optional, Dict, Any, Union, AsyncIterator
from datetime import datetime, date

from .base import BasePMProvider
from .models import (
    PMUser, PMProject, PMTask, PMSprint, PMEpic, PMLabel,
    PMProviderConfig
)


class OpenProjectV13Provider(BasePMProvider):
    """
    OpenProject v13.4.1 API integration
    
    OpenProject v13 API documentation:
    https://www.openproject.org/docs/api/
    
    Note: OpenProject v13 may have some API differences from v16:
    - Form validation endpoint may not be available
    - Some response structures may differ
    - Authentication: Uses Basic Auth (apikey:TOKEN)
    """
    
    def __init__(self, config: PMProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url.rstrip('/')
        self.api_key = config.api_key or config.api_token
        
        # Validate API key is present and not just whitespace
        if not self.api_key or not self.api_key.strip():
            raise ValueError(
                "OpenProject requires a non-empty api_key or api_token"
            )
        
        # Strip whitespace from API key
        self.api_key = self.api_key.strip()
        
        # OpenProject v13 uses Basic Auth with "apikey" as username and API key
        # Format: Authorization: Basic <base64(apikey:TOKEN)>
        import logging
        logger = logging.getLogger(__name__)
        
        auth_string = f"apikey:{self.api_key}"
        credentials = base64.b64encode(
            auth_string.encode()
        ).decode()
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {credentials}"
        }
        
        # Log authentication setup (mask token for security)
        token_preview = (
            f"{self.api_key[:4]}...{self.api_key[-4:]}" 
            if len(self.api_key) > 8 
            else "***"
        )
        logger.info(
            f"OpenProject v13: Initialized with base_url={self.base_url}, "
            f"token_length={len(self.api_key)}, token_preview={token_preview}"
        )
    
    # ==================== Project Operations ====================
    
    async def list_projects(self, user_id: Optional[str] = None) -> List[PMProject]:
        """List all projects from OpenProject (handles pagination)"""
        import logging
        import json
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/api/v3/projects"
        all_projects = []
        page_num = 1
        
        try:
            # Use maximum page size for efficiency (OpenProject API supports up to 500 per page)
            # Start with a large page size to minimize API calls
            params = {"pageSize": 500}
            
            # Apply user_id filter if provided
            if user_id:
                # OpenProject JSON filter syntax
                # [{"member":{"operator":"=","values":["<user_id>"]}}]
                filters = [{"member": {"operator": "=", "values": [str(user_id)]}}]
                params["filters"] = json.dumps(filters)
                logger.info(f"OpenProject v13: Filtering projects by user_id={user_id}")
            
            logger.info(f"OpenProject v13: Fetching projects from {url} with params={params}")
            
            request_url = url
            while request_url:
                try:
                    response = requests.get(request_url, headers=self.headers, params=params, timeout=60)
                    
                    # Log response status for debugging
                    logger.info(
                        f"OpenProject v13: Page {page_num} - Response status {response.status_code} for {request_url}"
                    )
                    
                    # Check status code BEFORE calling raise_for_status()
                    # This allows us to provide user-friendly error messages
                    if response.status_code == 401:
                        error_text = response.text[:500] if response.text else "No error message"
                        logger.error(
                            f"OpenProject v13: Authentication failed. Response: {error_text}"
                        )
                        raise ValueError(
                            "OpenProject authentication failed. Please verify your API token is correct. "
                            "For OpenProject v13, use Basic Auth with format: apikey:TOKEN"
                        )
                    elif response.status_code == 403:
                        error_text = response.text[:500] if response.text else "No error message"
                        logger.error(
                            f"OpenProject v13: Access forbidden. Response: {error_text}"
                        )
                        raise ValueError(
                            "OpenProject access forbidden. The API token may not have permission to list projects, "
                            "or the account doesn't have access to any projects. Please check your OpenProject permissions."
                        )
                    elif response.status_code == 404:
                        error_text = response.text[:500] if response.text else "No error message"
                        logger.error(
                            f"OpenProject v13: Endpoint not found. Response: {error_text}"
                        )
                        raise ValueError(
                            "OpenProject endpoint not found. Please verify the base URL is correct."
                        )
                    elif response.status_code != 200:
                        # For other non-200 status codes, log and raise
                        error_text = response.text[:500] if response.text else "No error message"
                        logger.error(
                            f"OpenProject v13: Failed to fetch projects. "
                            f"Status: {response.status_code}, Response: {error_text}"
                        )
                        response.raise_for_status()
                    
                    # Process successful response
                    data = response.json()
                    
                    # Check if response has expected structure
                    if "_embedded" not in data:
                        logger.warning(
                            f"OpenProject v13: Unexpected response structure. "
                            f"Keys: {list(data.keys())}"
                        )
                        # Try to handle different response formats
                        if isinstance(data, list):
                            projects_data = data
                        elif "elements" in data:
                            projects_data = data["elements"]
                        else:
                            logger.error(f"OpenProject v13: Cannot parse response: {data}")
                            break
                    else:
                        projects_data = data.get("_embedded", {}).get("elements", [])
                    
                    total_count = data.get("count", len(all_projects) + len(projects_data))
                    logger.info(
                        f"OpenProject v13: Page {page_num} - Found {len(projects_data)} projects "
                        f"(total so far: {len(all_projects) + len(projects_data)}/{total_count})"
                    )
                    
                    all_projects.extend(projects_data)
                    
                    # Check for next page - OpenProject uses nextByOffset or next
                    links = data.get("_links", {})
                    next_link = links.get("nextByOffset") or links.get("next")
                    
                    if next_link and isinstance(next_link, dict):
                        next_href = next_link.get("href")
                        if next_href:
                            # If it's a relative URL, make it absolute
                            if not next_href.startswith("http"):
                                request_url = f"{self.base_url}{next_href}"
                            else:
                                request_url = next_href
                            # Clear params for subsequent requests (they're in the URL)
                            params = {}
                            page_num += 1
                        else:
                            request_url = None
                    else:
                        # No next link means we've reached the end
                        # Verify we got all projects by checking count
                        if total_count > len(all_projects):
                            logger.warning(
                                f"OpenProject v13: Response indicates {total_count} total projects, "
                                f"but only fetched {len(all_projects)}. "
                                f"This may indicate pagination issues."
                            )
                        request_url = None
                        
                except requests.exceptions.RequestException as e:
                    logger.error(
                        f"OpenProject v13: Request error while fetching projects: {e}"
                    )
                    raise
                except ValueError as e:
                    logger.error(
                        f"OpenProject v13: JSON parsing error: {e}. "
                        f"Response text: {response.text[:500] if hasattr(response, 'text') else 'N/A'}"
                    )
                    raise
                except Exception as e:
                    logger.error(
                        f"OpenProject v13: Unexpected error while fetching projects: {e}",
                        exc_info=True
                    )
                    raise
            
            logger.info(
                f"OpenProject v13: Pagination complete - Total projects fetched: {len(all_projects)} "
                f"from {page_num} page(s)"
            )
            
            # Parse projects with error handling
            parsed_projects = []
            for idx, proj in enumerate(all_projects):
                try:
                    parsed_projects.append(self._parse_project(proj))
                except Exception as e:
                    logger.error(
                        f"OpenProject v13: Failed to parse project at index {idx}: {e}. "
                        f"Project data: {proj}"
                    )
                    # Continue with other projects instead of failing completely
                    continue
            
            logger.info(
                f"OpenProject v13: Successfully parsed {len(parsed_projects)} projects "
                f"(out of {len(all_projects)} raw projects)"
            )
            
            return parsed_projects
            
        except Exception as e:
            logger.error(
                f"OpenProject v13: Failed to list projects: {e}",
                exc_info=True
            )
            raise
    
    async def get_project(self, project_id: str) -> Optional[PMProject]:
        """Get a single project by ID"""
        url = f"{self.base_url}/api/v3/projects/{project_id}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        return self._parse_project(response.json())
    
    async def create_project(self, project: PMProject) -> PMProject:
        """Create a new project"""
        url = f"{self.base_url}/api/v3/projects"
        payload = {
            "name": project.name,
            "description": {
                "raw": project.description or "",
                "format": "plain"
            },
            "_links": {}
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return self._parse_project(response.json())

    async def update_project(
        self,
        project_id: str,
        updates: Dict[str, Any],
    ) -> PMProject:
        """Update an existing project"""
        url = f"{self.base_url}/api/v3/projects/{project_id}"
        payload = {}
        if "name" in updates:
            payload["name"] = updates["name"]
        if "description" in updates:
            payload["description"] = {
                "raw": updates["description"],
                "format": "plain"
            }
        if "status" in updates:
            payload["status"] = updates["status"]
        
        response = requests.patch(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return self._parse_project(response.json())
    
    async def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        url = f"{self.base_url}/api/v3/projects/{project_id}"
        response = requests.delete(url, headers=self.headers)
        return response.status_code == 204
    
    # ==================== Task (Work Package) Operations ====================
    
    async def list_tasks(
        self,
        project_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        sprint_id: Optional[str] = None,
        status: Optional[str] = None  # 'open' = active only, None/'all' = include closed
    ) -> List[PMTask]:
        """List all work packages (tasks) with pagination support"""
        import json as json_lib
        import logging
        import logging
        logger = logging.getLogger(__name__)
        
        # Prepare filters
        filters = []
        
        # Status filter behavior:
        # - status='open': Exclude Done/Closed status (OpenProject default)
        # - status=None or 'all' or '*': Include ALL statuses including closed
        # CHANGED: Default to including all statuses to fix missing tasks issue
        if status == 'open':
            # Don't add status filter - OpenProject will exclude closed by default
            pass
        else:
            # Include ALL statuses (including closed/done) - this is now the default
            filters.append({
                "status": {
                    "operator": "*",  # "*" means "all" - include all statuses
                    "values": []
                }
            })
        
        if project_id:
            # OpenProject IDs must be integers in JSON filters to avoid 400 Bad Request
            val = project_id
            if str(project_id).isdigit():
                val = int(project_id)
                
            filters.append({
                "project": {
                    "operator": "=",
                    "values": [val]
                }
            })
            
        if assignee_id:
            # Handle composite ID format (e.g., "uuid:593") - extract just the numeric part
            val = str(assignee_id)
            if ":" in val:
                val = val.split(":")[-1]  # Get the part after the colon
            if val.isdigit():
                val = int(val)
                
            filters.append({
                "assignee": {
                    "operator": "=",
                    "values": [val]
                }
            })
            
        if sprint_id:
            val = sprint_id
            if str(sprint_id).isdigit():
                val = int(sprint_id)
                
            filters.append({
                "version": {
                    "operator": "=",
                    "values": [val]
                }
            })
        
        # Build initial request parameters
        params = {
            "filters": json_lib.dumps(filters),
            "pageSize": 100,
            "include": "priority,status,assignee,project,version,parent"
        }
        logger.info(f"OpenProject list_tasks with filters: {params}")
        
        # Fetch all pages using pagination (exact pattern from test script)
        all_tasks_data = []
        # CRITICAL FIX: Use project-scoped endpoint when project_id is provided
        # The global /work_packages endpoint rejects version filter even with project filter.
        # The project-scoped endpoint accepts version filter correctly.
        if project_id:
            proj_id_val = int(project_id) if str(project_id).isdigit() else project_id
            request_url = f"{self.base_url}/api/v3/projects/{proj_id_val}/work_packages"
            # Remove project filter from filters array since it's now in the URL
            if filters:
                filters = [f for f in filters if "project" not in f]
                if filters:
                    params["filters"] = json_lib.dumps(filters)
                elif "filters" in params:
                    del params["filters"]
        else:
            request_url = f"{self.base_url}/api/v3/work_packages"
        page_num = 1
        
        while request_url:
            logger.debug(f"Fetching page {page_num} from {request_url}")
            response = requests.get(request_url, headers=self.headers, params=params, timeout=120)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                # OpenProject returns detailed error info in JSON
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message") or error_data.get("_type") or str(e)
                    logger.error(f"OpenProject API Error: {error_msg}")
                except ValueError:
                    # JSON decode failed, allow falls through to raise e or custom error
                    error_msg = str(e)
                    pass
                
                # If status is 400, it's likely invalid filter/ID.
                if response.status_code == 400:
                    raise ValueError(f"OpenProject API Error (400): {error_msg}") from e
                
                raise e
            
            data = response.json()
            tasks_data = data.get("_embedded", {}).get("elements", [])
            all_tasks_data.extend(tasks_data)
            
            total_count = data.get("count", len(all_tasks_data))
            logger.debug(f"Page {page_num}: {len(tasks_data)} tasks (total so far: {len(all_tasks_data)}/{total_count})")
            
            # Check for next page (exact pattern from test script)
            links = data.get("_links", {})
            next_link = links.get("nextByOffset") or links.get("next")
            
            if next_link and isinstance(next_link, dict):
                next_href = next_link.get("href")
                if next_href:
                    if not next_href.startswith("http"):
                        request_url = f"{self.base_url}{next_href}"
                    else:
                        request_url = next_href
                    params = {}  # Clear params for subsequent requests
                    page_num += 1
                else:
                    request_url = None
            else:
                request_url = None
        
        logger.info(
            f"OpenProject list_tasks: Fetched {len(all_tasks_data)} tasks "
            f"from {page_num} page(s) (total reported: {total_count})"
        )
        
        # Log if filter returns no results
        if assignee_id and len(all_tasks_data) == 0:
                    logger.warning(
                f"Assignee filter returned 0 tasks for user_id={assignee_id}"
                    )
        
        return [self._parse_task(task) for task in all_tasks_data]
    
    async def get_task(self, task_id: str) -> Optional[PMTask]:
        """Get a single work package by ID"""
        url = f"{self.base_url}/api/v3/work_packages/{task_id}"
        # Include priority in embedded data
        params = {"include": "priority,status,assignee,project,version,parent"}
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        return self._parse_task(response.json())
    
    async def create_task(self, task: PMTask) -> PMTask:
        """Create a new work package"""
        url = f"{self.base_url}/api/v3/work_packages"
        payload: Dict[str, Any] = {
            "_links": {
                "type": {
                    # Task type - may need to be configurable
                    "href": "/api/v3/types/1"
                }
            }
        }
        
        if task.project_id:
            payload["_links"]["project"] = {
                "href": f"/api/v3/projects/{task.project_id}"
            }
        if task.title:
            payload["subject"] = task.title
        if task.description:
            payload["description"] = {
                "raw": task.description,
                "format": "plain"
            }
        if task.assignee_id:
            payload["_links"]["assignee"] = {
                "href": f"/api/v3/users/{task.assignee_id}"
            }
        if task.status:
            payload["_links"]["status"] = {
                "href": f"/api/v3/statuses/{task.status}"
            }
        
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return self._parse_task(response.json())
    
    async def update_task(
        self, task_id: str, updates: Dict[str, Any]
    ) -> PMTask:
        """Update an existing work package"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Get the original task status before update for comparison
        original_task = await self.get_task(task_id)
        original_status = original_task.status if original_task else None
        if "status" in updates:
            logger.info(f"Updating task {task_id} status from '{original_status}' to '{updates['status']}'")
        
        url = f"{self.base_url}/api/v3/work_packages/{task_id}"
        payload: Dict[str, Any] = {}
        
        # Build the payload first (without lockVersion)
        # We'll get lockVersion and validation from the form endpoint
        
        if "title" in updates or "subject" in updates:
            payload["subject"] = updates.get("title") or updates.get("subject")
        if "description" in updates:
            payload["description"] = {
                "raw": updates["description"],
                "format": "plain"
            }
        if "status" in updates:
            # Status can be either an ID or a name - need to resolve it
            status_value = updates["status"]
            payload["_links"] = payload.get("_links", {})
            # If it's a numeric string or number, use it as ID
            if str(status_value).isdigit():
                # Verify the status exists before trying to use it
                try:
                    statuses_url = f"{self.base_url}/api/v3/statuses"
                    statuses_resp = requests.get(statuses_url, headers=self.headers, timeout=10)
                    if statuses_resp.status_code == 200:
                        statuses = statuses_resp.json().get("_embedded", {}).get("elements", [])
                        status_id_int = int(status_value)
                        matching_status = next((s for s in statuses if s.get("id") == status_id_int), None)
                        if matching_status:
                            logger.info(f"Using status ID {status_value} (name: {matching_status.get('name')})")
                            payload["_links"]["status"] = {
                                "href": f"/api/v3/statuses/{status_value}"
                            }
                        else:
                            available_status_ids = [s.get("id") for s in statuses]
                            logger.warning(f"Status ID {status_value} not found. Available status IDs: {available_status_ids}")
                            # Still try to use it - maybe it's valid but not in the list
                            payload["_links"]["status"] = {
                                "href": f"/api/v3/statuses/{status_value}"
                            }
                    else:
                        logger.warning(f"Failed to fetch statuses for validation: {statuses_resp.status_code}")
                        # Fall back to using the ID directly
                        payload["_links"]["status"] = {
                            "href": f"/api/v3/statuses/{status_value}"
                        }
                except Exception as e:
                    logger.warning(f"Error validating status ID: {e}")
                    # Fall back to using the ID directly
                    payload["_links"]["status"] = {
                        "href": f"/api/v3/statuses/{status_value}"
                    }
            else:
                # Try to look up status by name
                try:
                    statuses_url = f"{self.base_url}/api/v3/statuses"
                    statuses_resp = requests.get(statuses_url, headers=self.headers, timeout=10)
                    if statuses_resp.status_code == 200:
                        statuses = statuses_resp.json().get("_embedded", {}).get("elements", [])
                        # Try to find by name (case-insensitive, also try matching common status names)
                        status_lower = str(status_value).lower().replace("_", " ").replace("-", " ")
                        matching_status = next(
                            (s for s in statuses 
                             if s.get("name", "").lower().replace("_", " ").replace("-", " ") == status_lower
                             or s.get("name", "").lower() == status_lower),
                            None
                        )
                        if matching_status:
                            status_id = matching_status.get("id")
                            payload["_links"]["status"] = {
                                "href": f"/api/v3/statuses/{status_id}"
                            }
                        else:
                            logger.warning(f"Status '{status_value}' not found, skipping status update")
                    else:
                        logger.warning(f"Failed to fetch statuses: {statuses_resp.status_code}")
                except Exception as e:
                    logger.warning(f"Error looking up status: {e}")
        if "priority" in updates:
            # Priority updates - need to look up priority ID by name
            priority_value = updates["priority"]
            payload["_links"] = payload.get("_links", {})
            
            # Priority name mapping from frontend values to common OpenProject names
            priority_name_mapping = {
                "lowest": ["lowest", "trivial", "very low", "very-low"],
                "low": ["low", "minor"],
                "medium": ["medium", "normal", "moderate"],
                "high": ["high", "major", "important"],
                "highest": ["highest", "critical", "urgent", "blocker"],
                "critical": ["critical", "highest", "urgent", "blocker"]
            }
            
            # Try to find priority by name if it's not numeric
            if not str(priority_value).isdigit():
                try:
                    # List priorities and find matching one
                    priorities_url = f"{self.base_url}/api/v3/priorities"
                    priorities_resp = requests.get(priorities_url, headers=self.headers, timeout=10)
                    if priorities_resp.status_code == 200:
                        priorities = priorities_resp.json().get("_embedded", {}).get("elements", [])
                        priority_lower = str(priority_value).lower()
                        
                        # First try exact match
                        matching_priority = next(
                            (p for p in priorities if p.get("name", "").lower() == priority_lower),
                            None
                        )
                        
                        # If no exact match, try mapping
                        if not matching_priority and priority_lower in priority_name_mapping:
                            possible_names = priority_name_mapping[priority_lower]
                            for possible_name in possible_names:
                                matching_priority = next(
                                    (p for p in priorities 
                                     if p.get("name", "").lower() == possible_name.lower()),
                                    None
                                )
                                if matching_priority:
                                    break
                        
                        # If still no match, try partial/fuzzy matching
                        if not matching_priority:
                            for priority in priorities:
                                priority_name = priority.get("name", "").lower()
                                if priority_lower in priority_name or priority_name in priority_lower:
                                    matching_priority = priority
                                    break
                        
                        if matching_priority:
                            priority_id = matching_priority.get("id")
                            priority_name_found = matching_priority.get("name", "unknown")
                            logger.info(f"Found priority match: '{priority_value}' -> '{priority_name_found}' (ID: {priority_id})")
                            payload["_links"]["priority"] = {
                                "href": f"/api/v3/priorities/{priority_id}"
                            }
                        else:
                            available_priorities = [p.get("name") for p in priorities]
                            logger.error(
                                f"Priority '{priority_value}' not found. "
                                f"Available priorities: {available_priorities}. "
                                f"Priority update will be skipped."
                            )
                            # Log all priorities with their IDs for debugging
                            logger.debug(f"All available priorities: {[(p.get('id'), p.get('name')) for p in priorities]}")
                    else:
                        logger.warning(f"Failed to fetch priorities: {priorities_resp.status_code}")
                except Exception as e:
                    logger.error(f"Error looking up priority: {e}", exc_info=True)
            else:
                # Use as ID directly
                logger.info(f"Using priority as ID: {priority_value}")
                payload["_links"]["priority"] = {
                    "href": f"/api/v3/priorities/{priority_value}"
                }
        if "assignee_id" in updates:
            payload["_links"] = payload.get("_links", {})
            assignee_id = updates["assignee_id"]
            if assignee_id:
                payload["_links"]["assignee"] = {
                    "href": f"/api/v3/users/{assignee_id}"
                }
            else:
                payload["_links"]["assignee"] = None
        if "epic_id" in updates:
            # Epic assignment via parent relationship
            epic_id = updates["epic_id"]
            if epic_id:
                payload["_links"] = payload.get("_links", {})
                payload["_links"]["parent"] = {
                    "href": f"/api/v3/work_packages/{epic_id}"
                }
            else:
                # Remove parent (epic) - OpenProject requires using the changeParent action
                # We need to handle this separately, not through the normal update flow
                logger.info(f"Removing parent from task {task_id} using changeParent action")
                try:
                    # Get current work package to access changeParent link
                    current_wp = requests.get(url, headers=self.headers, timeout=10)
                    if current_wp.status_code == 200:
                        current_data = current_wp.json()
                        
                        # Get current lockVersion
                        lock_version = current_data.get('lockVersion')
                        logger.info(f"Current lockVersion: {lock_version}")
                        
                        # According to OpenProject API docs, to remove a link, set href to null
                        # Try: {"lockVersion": X, "_links": {"parent": {"href": null}}}
                        removal_payload = {
                            "lockVersion": lock_version,
                            "_links": {
                                "parent": {"href": None}
                            }
                        }
                        
                        logger.info(f"Attempting removal with payload: {removal_payload}")
                        
                        change_resp = requests.patch(
                            url,  # Use the regular work package URL
                            headers=self.headers,
                            json=removal_payload,
                            timeout=10
                        )
                        
                        if change_resp.status_code in [200, 204]:
                            logger.info(f"Successfully removed parent from task {task_id}")
                            # Return the updated task
                            if change_resp.text:
                                return self._parse_task(change_resp.json())
                            else:
                                # Fetch the updated task
                                updated_task = await self.get_task(task_id)
                                if updated_task:
                                    return updated_task
                        else:
                            error_text = change_resp.text
                            logger.error(f"PATCH failed with status {change_resp.status_code}: {error_text}")
                            raise ValueError(f"Failed to remove parent: {error_text}")
                    else:
                        logger.error(f"Failed to get current task {task_id}: {current_wp.status_code}")
                        raise ValueError(f"Failed to get task for parent removal: {current_wp.status_code}")
                except Exception as e:
                    logger.error(f"Error removing parent: {e}")
                    raise ValueError(f"Failed to remove parent from task: {str(e)}")
        if "sprint_id" in updates:
            # Sprint assignment via version link
            payload["_links"] = payload.get("_links", {})
            sprint_id = updates["sprint_id"]
            if sprint_id:
                payload["_links"]["version"] = {
                    "href": f"/api/v3/versions/{sprint_id}"
                }
            else:
                # Remove from sprint (move to backlog)
                # OpenProject accepts empty dict to remove version link
                # We need to ensure lockVersion is included
                try:
                    # Get current work package to ensure we have lockVersion
                    current_wp = requests.get(url, headers=self.headers, timeout=10)
                    if current_wp.status_code == 200:
                        current_data = current_wp.json()
                        current_lock_version = current_data.get('lockVersion')
                        if current_lock_version is not None:
                            payload["lockVersion"] = current_lock_version
                        payload["_links"]["version"] = {}
                except Exception as e:
                    logger.warning(f"Could not get lockVersion for version removal: {e}")
                    # Try anyway with empty dict
                    payload["_links"]["version"] = {}
        if "estimated_hours" in updates:
            # Convert hours to ISO 8601 duration
            # (e.g., 2.5 -> PT2H30M, 2.0 -> PT2H)
            # Use null/None to delete ETA (set estimated_hours to 0 or None)
            hours = updates["estimated_hours"]
            if hours is None or hours == 0:
                payload["estimatedTime"] = None
            elif hours:
                hours_float = float(hours)
                hours_int = int(hours_float)
                minutes_int = int((hours_float - hours_int) * 60)
                
                if minutes_int > 0:
                    payload["estimatedTime"] = f"PT{hours_int}H{minutes_int}M"
                else:
                    payload["estimatedTime"] = f"PT{hours_int}H"
        
        if "due_date" in updates:
            due_date = updates["due_date"]
            if due_date:
                # OpenProject expects ISO 8601 date format (YYYY-MM-DD)
                if isinstance(due_date, str):
                    payload["dueDate"] = due_date
                elif hasattr(due_date, "isoformat"):
                    payload["dueDate"] = due_date.isoformat()
                else:
                    payload["dueDate"] = str(due_date)
            else:
                payload["dueDate"] = None
        
        if "start_date" in updates:
            start_date = updates["start_date"]
            if start_date:
                # OpenProject expects ISO 8601 date format (YYYY-MM-DD)
                if isinstance(start_date, str):
                    payload["startDate"] = start_date
                elif hasattr(start_date, "isoformat"):
                    payload["startDate"] = start_date.isoformat()
                else:
                    payload["startDate"] = str(start_date)
            else:
                payload["startDate"] = None
        
        if "parent_task_id" in updates:
            # Parent task assignment (for subtasks)
            payload["_links"] = payload.get("_links", {})
            parent_id = updates["parent_task_id"]
            if parent_id:
                payload["_links"]["parent"] = {
                    "href": f"/api/v3/work_packages/{parent_id}"
                }
            else:
                # Remove parent - use changeParent link if available
                try:
                    current_wp = requests.get(url, headers=self.headers, timeout=10)
                    if current_wp.status_code == 200:
                        current_data = current_wp.json()
                        change_parent_link = current_data.get("_links", {}).get("changeParent")
                        if change_parent_link and change_parent_link.get("href"):
                            change_url = change_parent_link["href"]
                            if not change_url.startswith("http"):
                                change_url = f"{self.base_url}{change_url}"
                            change_resp = requests.post(
                                change_url,
                                headers=self.headers,
                                json={"parent": None},
                                timeout=10
                            )
                            if change_resp.status_code in [200, 204]:
                                logger.info(f"Removed parent from work package {task_id}")
                                return self._parse_task(change_resp.json() if change_resp.text else current_data)
                except Exception as e:
                    logger.warning(f"Could not remove parent via changeParent link: {e}")
                # Fallback: try setting parent to empty dict
                payload["_links"]["parent"] = {}
        
        if "label_ids" in updates:
            # Labels in OpenProject are categories
            payload["_links"] = payload.get("_links", {})
            label_ids = updates["label_ids"]
            if label_ids is None:
                payload["_links"]["categories"] = []
            elif isinstance(label_ids, list):
                payload["_links"]["categories"] = [
                    {"href": f"/api/v3/categories/{label_id}"} for label_id in label_ids
                ]
            else:
                payload["_links"]["categories"] = [
                    {"href": f"/api/v3/categories/{label_ids}"}
                ]
        
        if "actual_hours" in updates:
            # Actual hours (spent time) in OpenProject
            # Note: spentTime may be read-only, but we'll try
            hours = updates["actual_hours"]
            if hours is None or hours == 0:
                payload["spentTime"] = None
            elif hours:
                hours_float = float(hours)
                hours_int = int(hours_float)
                minutes_int = int((hours_float - hours_int) * 60)
                
                if minutes_int > 0:
                    payload["spentTime"] = f"PT{hours_int}H{minutes_int}M"
                else:
                    payload["spentTime"] = f"PT{hours_int}H"
        
        # Only send request if there are actual updates
        if not payload:
            logger.warning(f"No updates to apply for task {task_id}")
            # Return current task if no updates
            current_task = await self.get_task(task_id)
            if current_task:
                return current_task
            else:
                raise ValueError(f"Task {task_id} not found")
        
        # For OpenProject v13, form endpoint may not be available
        # Try form endpoint first, but fall back to direct update if 404
        form_url = f"{self.base_url}/api/v3/work_packages/{task_id}/form"
        
        # Get current lockVersion for the update
        current_lock_version = None
        try:
            current_task = await self.get_task(task_id)
            if current_task and hasattr(current_task, 'raw_data') and current_task.raw_data:
                current_lock_version = current_task.raw_data.get('lockVersion')
                if current_lock_version is not None:
                    payload["lockVersion"] = current_lock_version
        except Exception as e:
            logger.warning(f"Could not get current task for lockVersion: {e}")
        
        # Try form endpoint (may not exist in v13)
        form_validated_payload = None
        try:
            form_payload = payload.copy()
            if current_lock_version is not None:
                form_payload["lockVersion"] = current_lock_version
            
            logger.info(f"Attempting form validation (v13 may not support this)...")
            form_response = requests.post(form_url, headers=self.headers, json=form_payload, timeout=10)
            
            if form_response.status_code == 404:
                # Form endpoint doesn't exist in v13 - use direct update
                logger.info("Form endpoint not available (expected for v13), using direct update")
                form_validated_payload = payload.copy()
            elif form_response.ok:
                # Form endpoint exists and succeeded
                form_data = form_response.json()
                validated_payload = form_data.get("_embedded", {}).get("payload", {})
                if validated_payload:
                    form_validated_payload = validated_payload
                else:
                    form_validated_payload = payload.copy()
                logger.info("Form validation successful")
            else:
                # Form endpoint returned error - try direct update anyway
                logger.warning(f"Form endpoint returned {form_response.status_code}, falling back to direct update")
                form_validated_payload = payload.copy()
        except requests.exceptions.RequestException as e:
            # Form endpoint failed - use direct update (expected for v13)
            logger.info(f"Form endpoint not available or failed (expected for v13): {e}")
            form_validated_payload = payload.copy()
        except Exception as e:
            logger.warning(f"Error with form endpoint: {e}, using direct update")
            form_validated_payload = payload.copy()
        
        # Use the validated payload (either from form endpoint or direct)
        validated_payload = form_validated_payload if form_validated_payload else payload.copy()
        
        # Now perform the actual update with validated payload
        logger.info(f"Updating task {task_id} with validated payload: {validated_payload}")
        
        # Retry logic for 409 conflicts (lockVersion mismatch)
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                response = requests.patch(url, headers=self.headers, json=validated_payload, timeout=10)
                
                # Check response status manually instead of using raise_for_status()
                # This gives us better control over error handling
                if not response.ok:
                    error_text = response.text
                    status_code = response.status_code
                    
                    # Handle 409 Conflict (lockVersion mismatch) by retrying with fresh lockVersion
                    if status_code == 409 and attempt < max_retries:
                        logger.warning(f"LockVersion conflict (409) on attempt {attempt + 1}, retrying with fresh lockVersion...")
                        # Get fresh lockVersion from current task and retry
                        try:
                            current_task = await self.get_task(task_id)
                            if current_task and hasattr(current_task, 'raw_data') and current_task.raw_data:
                                fresh_lock_version = current_task.raw_data.get('lockVersion')
                                if fresh_lock_version is not None:
                                    # Update the validated payload with fresh lockVersion
                                    validated_payload = validated_payload.copy()
                                    validated_payload["lockVersion"] = fresh_lock_version
                                    logger.info(f"Retrying with fresh lockVersion: {fresh_lock_version}")
                                    continue  # Retry the update
                        except Exception as retry_error:
                            logger.error(f"Error getting fresh lockVersion for retry: {retry_error}")
                    
                    logger.error(f"OpenProject API error ({status_code}): {error_text}")
                    
                    # Try to parse the error response
                    error_message = None
                    try:
                        error_data = response.json()
                        logger.error(f"OpenProject error response JSON: {error_data}")
                        
                        # Try multiple ways to extract error message from OpenProject error response
                        if "_embedded" in error_data and "errors" in error_data["_embedded"]:
                            errors = error_data["_embedded"]["errors"]
                            if errors and len(errors) > 0:
                                # OpenProject returns errors as array of objects with message and attribute
                                error_parts = []
                                for err in errors:
                                    msg = err.get("message", "")
                                    attr = err.get("_attribute", "")
                                    if msg:
                                        error_parts.append(f"{attr}: {msg}" if attr else msg)
                                if error_parts:
                                    error_message = "; ".join(error_parts)
                        
                        if not error_message:
                            error_message = error_data.get("message") or error_data.get("error", error_text)
                    except (ValueError, KeyError, AttributeError) as parse_error:
                        logger.error(f"Failed to parse OpenProject error response: {parse_error}")
                        error_message = error_text
                    
                    if not error_message:
                        error_message = error_text or f"HTTP {status_code} error"
                    
                    raise ValueError(f"OpenProject validation error ({status_code}): {error_message}")
                
                # Success!
                updated_data = response.json()
                break  # Exit retry loop on success
                
            except ValueError:
                # Re-raise ValueError (our custom errors) - don't retry
                raise
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error when updating task (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    # Retry on network errors
                    logger.warning(f"Retrying after request error...")
                    continue
                raise ValueError(f"Failed to update task: {str(e)}")
        
        # After successful update, fetch the task again with embedded data to get the full status
        # The PATCH response may not include _embedded.status, so we need to fetch it separately
        logger.info(f"Task {task_id} updated successfully. Fetching updated task with embedded data...")
        
        # Wait a moment for OpenProject to process the update
        import asyncio
        await asyncio.sleep(0.5)
        
        # Fetch the updated task
        updated_task = await self.get_task(task_id)
        if updated_task:
            logger.info(f"Task {task_id} status after update: {updated_task.status} (original: {original_status})")
            
            # Verify that the status actually changed if we were trying to update it
            if "status" in updates and original_status is not None:
                expected_status_value = updates["status"]
                # Check if status actually changed
                if updated_task.status == original_status:
                    # Status didn't change - this might be a workflow restriction
                    logger.warning(f"Task {task_id} status did not change after update. Original: {original_status}, After: {updated_task.status}, Attempted: {expected_status_value}")
                    # Raise an error so the frontend knows the update didn't work
                    raise ValueError(f"Status update failed: Task status did not change from '{original_status}' to '{expected_status_value}'. This may be due to workflow restrictions or permissions in OpenProject.")
                else:
                    logger.info(f"Task {task_id} status successfully changed from {original_status} to {updated_task.status}")
            
            return updated_task
        else:
            # Fallback: parse the response data even if it doesn't have embedded status
            logger.warning(f"Could not fetch updated task {task_id}, using PATCH response data")
            return self._parse_task(updated_data)
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete a work package"""
        url = f"{self.base_url}/api/v3/work_packages/{task_id}"
        response = requests.delete(url, headers=self.headers)
        return response.status_code == 204
    
    # ==================== Sprint Operations ====================
    
    async def list_sprints(
        self, project_id: Optional[str] = None, state: Optional[str] = None
    ) -> List[PMSprint]:
        """
        List sprints (iterations) from OpenProject
        
        Note: OpenProject uses "versions" for sprints/iterations.
        Versions have status: "open" or "closed"
        
        State mapping:
        - "active" -> versions with status "open" and current date within start/end dates
        - "closed" -> versions with status "closed" or end date in the past
        - "future" -> versions with status "open" and start date in the future
        - None -> all versions
        
        TESTED: ✅ Works with state filtering based on status and dates
        """
        import logging
        from datetime import date, datetime
        logger = logging.getLogger(__name__)
        
        if project_id:
            # Use project-scoped endpoint which is safer and cleaner than filtering global list
            url = f"{self.base_url}/api/v3/projects/{project_id}/versions"
            # logger.info(f"[list_sprints] Using scoped access: {url}")
        else:
            url = f"{self.base_url}/api/v3/versions"
            
        all_sprints_data = []
        params = {"pageSize": 100}
        
        # NOTE: filters param is not needed for project-scoped endpoint for scoping,
        # but if we wanted to filter global list we would use it.
        # Since we switched to scoped endpoint, we can skip complex filter construction.

        request_url = url
        
        # Fetch all pages using pagination (exact pattern from test script)
        while request_url:
            response = requests.get(request_url, headers=self.headers, params=params, timeout=120)
            response.raise_for_status()
            
            data = response.json()
            sprints_data = data.get("_embedded", {}).get("elements", [])
            all_sprints_data.extend(sprints_data)
            
            # Check for next page
            links = data.get("_links", {})
            next_link = links.get("nextByOffset") or links.get("next")
            
            if next_link and isinstance(next_link, dict):
                next_href = next_link.get("href")
                if next_href:
                    if not next_href.startswith("http"):
                        request_url = f"{self.base_url}{next_href}"
                    else:
                        request_url = next_href
                    params = {}  # Clear params for subsequent requests
                else:
                    request_url = None
            else:
                request_url = None
        
        sprints_data = all_sprints_data
        
        # Client-side filter fallback (if project_id was not filtered server-side)
        # But if we did server-side, this list should be clean already.
        if project_id and "filters" not in params: # Only filter if we didn't use server-side (redundant check)
             pass 
         
        # Still filter again just to be safe (no harm), or simply rely on API.
        # OpenProject versions are strictly scoped.
        if project_id:
            sprints_data = [
                sprint for sprint in sprints_data
                if sprint.get("_links", {})
                .get("definingProject", {})
                .get("href", "")
                .endswith(f"/projects/{project_id}")
            ]
        
        # Filter by state if provided
        if state:
            today = date.today()
            filtered_sprints = []
            
            for sprint in sprints_data:
                sprint_status = sprint.get("status", "open")
                start_date_str = sprint.get("startDate")
                end_date_str = sprint.get("endDate")
                
                # Parse dates if available
                start_date = None
                end_date = None
                if start_date_str:
                    try:
                        start_date = datetime.fromisoformat(
                            start_date_str.replace('Z', '+00:00')
                        ).date()
                    except (ValueError, AttributeError):
                        pass
                if end_date_str:
                    try:
                        end_date = datetime.fromisoformat(
                            end_date_str.replace('Z', '+00:00')
                        ).date()
                    except (ValueError, AttributeError):
                        pass
                
                # Determine sprint state based on status and dates
                sprint_state = None
                
                if sprint_status == "closed":
                    sprint_state = "closed"
                elif sprint_status == "open":
                    if start_date and end_date:
                        if end_date < today:
                            sprint_state = "closed"
                        elif start_date <= today <= end_date:
                            sprint_state = "active"
                        elif start_date > today:
                            sprint_state = "future"
                        else:
                            sprint_state = "active"  # Default for open with dates
                    elif end_date:
                        if end_date < today:
                            sprint_state = "closed"
                        else:
                            sprint_state = "active"
                    elif start_date:
                        if start_date > today:
                            sprint_state = "future"
                        else:
                            sprint_state = "active"
                    else:
                        # No dates, status is "open" -> treat as active
                        sprint_state = "active"
                
                # Match against requested state
                if sprint_state == state:
                    filtered_sprints.append(sprint)
            
            sprints_data = filtered_sprints
            logger.info(
                f"Filtered to {len(sprints_data)} sprints with state '{state}'"
            )
        
        return [self._parse_sprint(sprint) for sprint in sprints_data]
    
    async def get_sprint(self, sprint_id: str) -> Optional[PMSprint]:
        """Get a single version (sprint) by ID"""
        url = f"{self.base_url}/api/v3/versions/{sprint_id}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        return self._parse_sprint(response.json())
    
    async def create_sprint(self, sprint: PMSprint) -> PMSprint:
        """Create a new version (sprint)"""
        url = f"{self.base_url}/api/v3/versions"
        payload = {
            "name": sprint.name,
            "_links": {
                "definingProject": {
                    "href": f"/api/v3/projects/{sprint.project_id}"
                }
            }
        }
        
        if sprint.start_date:
            payload["startDate"] = sprint.start_date.isoformat()
        if sprint.end_date:
            payload["endDate"] = sprint.end_date.isoformat()
        
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return self._parse_sprint(response.json())
    
    async def update_sprint(
        self, sprint_id: str, updates: Dict[str, Any]
    ) -> PMSprint:
        """Update an existing version"""
        url = f"{self.base_url}/api/v3/versions/{sprint_id}"
        payload = {}
        
        if "name" in updates:
            payload["name"] = updates["name"]
        if "start_date" in updates:
            payload["startDate"] = updates["start_date"].isoformat()
        if "end_date" in updates:
            payload["endDate"] = updates["end_date"].isoformat()
        if "status" in updates:
            payload["status"] = updates["status"]
        
        response = requests.patch(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return self._parse_sprint(response.json())
    
    async def delete_sprint(self, sprint_id: str) -> bool:
        """Delete a version"""
        url = f"{self.base_url}/api/v3/versions/{sprint_id}"
        response = requests.delete(url, headers=self.headers)
        return response.status_code == 204
    
    # ==================== User Operations ====================
    
    async def list_users(
        self, project_id: Optional[str] = None
    ) -> List[PMUser]:
        """
        List users with automatic pagination.
        
        If project_id is provided, uses /api/v3/memberships to get project members.
        Otherwise, uses /api/v3/users to get all users (requires admin permissions).
        """
        import logging
        import json as json_lib
        logger = logging.getLogger(__name__)
        
        all_users: List[PMUser] = []
        
        if project_id:
            # Use memberships endpoint to get users in a specific project
            url = f"{self.base_url}/api/v3/memberships"
            
            # Filter by project ID and include principal (user) data
            filters = [{"project": {"operator": "=", "values": [project_id]}}]
            params = {
                "filters": json_lib.dumps(filters),
                "include": "principal",  # Include embedded user data
                "pageSize": 500,
                "offset": 0
            }
            
            offset = 0
            total_count = None
            
            while True:
                params["offset"] = offset
                response = requests.get(url, headers=self.headers, params=params)
                
                # Check for permission errors and raise clear error message
                if response.status_code == 403:
                    raise PermissionError(
                        f"OpenProject API returned 403 Forbidden when trying to list memberships for project {project_id}. "
                        "This may indicate that: "
                        "1) The API token doesn't have permission to view project memberships, "
                        "2) The project doesn't exist or you don't have access to it, "
                        "3) Contact your OpenProject administrator to grant project membership viewing permissions."
                    )
                
                response.raise_for_status()
                
                result = response.json()
                memberships = result.get("_embedded", {}).get("elements", [])
                
                if total_count is None:
                    total_count = result.get("total", 0)
                    logger.info(f"OpenProject list_users (project {project_id}): Total {total_count} memberships to fetch")
                    logger.info(f"[MCP_PROVIDER] Found {len(memberships)} memberships in this page")
                
                # Extract user information from each membership
                for membership in memberships:
                    # First try to get embedded user data (more efficient)
                    principal_data = membership.get("_embedded", {}).get("principal", {})
                    if principal_data:
                        # Use embedded user data if available
                        all_users.append(self._parse_user(principal_data))
                    else:
                        # Fallback: fetch user from link
                        user_link = membership.get("_links", {}).get("principal", {})
                        if user_link and isinstance(user_link, dict):
                            user_href = user_link.get("href", "")
                            if user_href:
                                try:
                                    user_url = f"{self.base_url}{user_href}" if user_href.startswith("/") else user_href
                                    user_response = requests.get(user_url, headers=self.headers)
                                    user_response.raise_for_status()
                                    user_data = user_response.json()
                                    all_users.append(self._parse_user(user_data))
                                except Exception as e:
                                    logger.warning(f"Failed to fetch user from {user_href}: {e}")
                
                if len(memberships) < 500:
                    break
                if total_count and len(all_users) >= total_count:
                    break
                
                offset += 500
                if offset > 10000:  # Safety limit
                    logger.warning(f"OpenProject list_users: Safety limit reached at offset {offset}")
                    break
            
            logger.info(f"OpenProject list_users (project {project_id}): Fetched {len(all_users)} users total")
        else:
            # List all users (requires admin permissions)
            # Fallback for non-admins: List users from all visible projects
            url = f"{self.base_url}/api/v3/users"
            all_users: List[PMUser] = [] # Re-initialize for this branch
            
            # Use larger page size and handle pagination
            params = {"pageSize": 100}
            
            try:
                logger.info("OpenProject list_users: Attempting to list global users (Admin only)")
                while url:
                    response = requests.get(url, headers=self.headers, params=params)
                    
                    # Check for permission errors and trigger fallback
                    if response.status_code == 403:
                        logger.warning("OpenProject list_users: 403 Forbidden. User is likely not an Admin. Switching to Project-Based Fallback.")
                        
                        # FALLBACK: Aggregation Strategy
                        # 1. List all projects the user can see
                        # 2. Iterate and fetch members for each project
                        # 3. Deduplicate
                        
                        projects = await self.list_projects()
                        unique_users = {}
                        
                        for project in projects:
                            try:
                                # Recursive call with project_id (which uses /memberships endpoint)
                                # This endpoint is generally accessible to project members
                                project_users = await self.list_users(project_id=str(project.id))
                                for user in project_users:
                                    if user.id not in unique_users:
                                        unique_users[user.id] = user
                            except Exception as e:
                                logger.warning(f"Fallback: Failed to list users for project {project.id}: {e}")
                                continue
                        
                        logger.info(f"OpenProject list_users (Fallback): Found {len(unique_users)} users across {len(projects)} projects")
                        return list(unique_users.values())

                    response.raise_for_status()
                    
                    result = response.json()
                    users_data = result.get("_embedded", {}).get("elements", [])
                    
                    for user_data in users_data:
                        all_users.append(self._parse_user(user_data))
                    
                    # Check for next page
                    links = result.get("_links", {})
                    next_link = links.get("nextByOffset") or links.get("next")
                    
                    if next_link and isinstance(next_link, dict):
                        next_href = next_link.get("href")
                        if next_href:
                            url = f"{self.base_url}{next_href}" if not next_href.startswith("http") else next_href
                            params = {} # Params are in the URL now
                        else:
                            url = None
                    else:
                        url = None
            except requests.exceptions.HTTPError as e:
                 # Double check if we missed the 403 check above or if raise_for_status caught it
                 if e.response.status_code == 403:
                     # This path might be redundant but safe
                     logger.warning("OpenProject list_users: HTTP 403 caught in exception. Triggering Fallback.")
                     projects = await self.list_projects()
                     unique_users = {}
                     for project in projects:
                         try:
                             project_users = await self.list_users(project_id=str(project.id))
                             for user in project_users:
                                 unique_users[user.id] = user
                         except Exception:
                             continue
                     return list(unique_users.values())
                 raise e
            logger.info(f"OpenProject list_users: Fetched {len(all_users)} users total")
        
        return all_users
    
    async def get_user(self, user_id: str) -> Optional[PMUser]:
        """Get a single user by ID"""
        url = f"{self.base_url}/api/v3/users/{user_id}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        return self._parse_user(response.json())
    
    async def get_current_user(self) -> Optional[PMUser]:
        """Get the current user associated with the API key"""
        url = f"{self.base_url}/api/v3/users/me"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        return self._parse_user(response.json())
    
    # ==================== Health Check ====================
    
    async def health_check(self) -> bool:
        """Check if the OpenProject connection is healthy"""
        try:
            # Use /api/v3/projects endpoint as health check
            response = requests.get(
                f"{self.base_url}/api/v3/projects",
                headers=self.headers,
                timeout=5
            )
            # 200 OK or 403 Forbidden (authenticated but no projects)
            # both indicate healthy connection
            return response.status_code in (200, 403)
        except Exception:
            return False
    
    # ==================== Parser Methods ====================
    
    def _parse_project(self, data: Dict[str, Any]) -> PMProject:
        """Parse OpenProject project data to unified format"""
        return PMProject(
            id=str(data["id"]),
            name=data.get("name", ""),
            description=(
                data.get("description", {}).get("raw")
                if isinstance(data.get("description"), dict)
                else data.get("description")
            ),
            status=data.get("status"),
            created_at=self._parse_datetime(data.get("createdAt")),
            updated_at=self._parse_datetime(data.get("updatedAt")),
            raw_data=data
        )
    
    def _parse_task(self, data: Dict[str, Any]) -> PMTask:
        """Parse OpenProject work package to unified format"""
        links = data.get("_links", {})
        embedded = data.get("_embedded", {})
        
        # Extract priority from embedded data or links
        priority = None
        if embedded.get("priority"):
            priority = embedded.get("priority", {}).get("name")
        elif links.get("priority", {}).get("title"):
            priority = links.get("priority", {}).get("title")
        
        # Extract status from embedded data or links (similar to priority)
        status = None
        if embedded.get("status"):
            status = embedded.get("status", {}).get("name")
        elif links.get("status", {}).get("title"):
            status = links.get("status", {}).get("title")
        
        return PMTask(
            id=str(data["id"]),
            title=data.get("subject", ""),
            description=(
                data.get("description", {}).get("raw")
                if isinstance(data.get("description"), dict)
                else data.get("description")
            ),
            status=status,
            priority=priority,
            project_id=self._extract_id_from_href(
                links.get("project", {}).get("href")
            ),
            assignee_id=self._extract_id_from_href(
                links.get("assignee", {}).get("href")
            ),
            epic_id=self._extract_id_from_href(
                links.get("parent", {}).get("href")
            ) if links.get("parent", {}).get("href") else None,
            sprint_id=self._extract_id_from_href(
                links.get("version", {}).get("href")
            ) if links.get("version", {}).get("href") else None,
            estimated_hours=self._parse_duration_to_hours(
                data.get("estimatedTime")
            ),
            spent_hours=self._parse_duration_to_hours(
                data.get("spentTime")
            ),
            remaining_hours=self._parse_duration_to_hours(
                data.get("remainingTime")
            ),
            actual_hours=self._parse_duration_to_hours(
                data.get("spentTime")  # Usually actual = spent
            ),
            start_date=self._parse_date(data.get("startDate")),
            due_date=self._parse_date(data.get("dueDate")),
            created_at=self._parse_datetime(data.get("createdAt")),
            updated_at=self._parse_datetime(data.get("updatedAt")),
            has_children=len(links.get("children", [])) > 0,
            raw_data=data
        )
    
    def _parse_sprint(self, data: Dict[str, Any]) -> PMSprint:
        """
        Parse OpenProject version to unified format.
        
        Maps OpenProject status ("open"/"closed") to logical states:
        - "closed" if status is "closed" or end date passed
        - "active" if status is "open" and current date within range
        - "future" if status is "open" and start date in future
        """
        from datetime import date
        links = data.get("_links", {})
        
        sprint_status = data.get("status", "open")
        start_date = self._parse_date(data.get("startDate"))
        end_date = self._parse_date(data.get("endDate"))
        today = date.today()
        
        # Determine logical state based on status and dates
        logical_state = "active"  # default
        
        if sprint_status == "closed":
            logical_state = "closed"
        elif sprint_status == "open":
            if start_date and end_date:
                if end_date < today:
                    logical_state = "closed"
                elif start_date <= today <= end_date:
                    logical_state = "active"
                elif start_date > today:
                    logical_state = "future"
            elif end_date:
                if end_date < today:
                    logical_state = "closed"
                else:
                    logical_state = "active"
            elif start_date:
                if start_date > today:
                    logical_state = "future"
                else:
                    logical_state = "active"
            # else: no dates, status is "open" -> "active" (default)
        
        return PMSprint(
            id=str(data["id"]),
            name=data.get("name", ""),
            project_id=self._extract_id_from_href(
                links.get("definingProject", {}).get("href")
            ),
            start_date=start_date,
            end_date=end_date,
            status=logical_state,  # Use logical state instead of raw "open"/"closed"
            raw_data=data
        )
    
    def _parse_user(self, data: Dict[str, Any]) -> PMUser:
        """Parse OpenProject user to unified format"""
        return PMUser(
            id=str(data["id"]),
            name=data.get("name", ""),
            email=data.get("email"),
            avatar_url=data.get("avatar"),
            raw_data=data
        )
    
    # ==================== Helper Methods ====================
    
    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """Parse OpenProject datetime string"""
        if not dt_str:
            return None
        try:
            # OpenProject returns ISO 8601 format
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except Exception:
            return None
    
    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[date]:
        """Parse OpenProject date string"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str).date()
        except Exception:
            return None
    
    @staticmethod
    def _extract_id_from_href(href: Optional[str]) -> Optional[str]:
        """Extract ID from OpenProject HATEOAS href"""
        if not href:
            return None
        try:
            return href.split("/")[-1]
        except Exception:
            return None
    
    # ==================== Time Entry Operations ====================
    
    def _format_hours_to_duration(self, hours: float) -> str:
        """Convert hours to ISO 8601 duration string"""
        hours_int = int(hours)
        minutes_int = int((hours - hours_int) * 60)
        
        if hours_int == 0 and minutes_int == 0:
            return "PT0H"
        elif minutes_int > 0:
            return f"PT{hours_int}H{minutes_int}M"
        else:
            return f"PT{hours_int}H"
    
    async def log_time_entry(
        self, 
        task_id: str, 
        hours: float, 
        comment: Optional[str] = None,
        activity_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a time entry for logging hours worked on a task
        
        Args:
            task_id: The work package (task) ID
            hours: Number of hours to log
            comment: Optional comment describing the work
            activity_id: Optional activity type ID
                (defaults to first available)
            user_id: Optional user ID (defaults to current user)
            
        Returns:
            Created time entry data
        """
        url = f"{self.base_url}/api/v3/time_entries"
        payload: Dict[str, Any] = {
            "hours": self._format_hours_to_duration(hours),
            "_links": {
                "workPackage": {"href": f"/api/v3/work_packages/{task_id}"}
            }
        }
        
        if comment:
            payload["comment"] = {"raw": comment, "format": "plain"}
        
        links: Dict[str, Any] = payload["_links"]
        
        if activity_id:
            links["activity"] = {
                "href": f"/api/v3/time_entries/activities/{activity_id}"
            }
        
        if user_id:
            links["user"] = {"href": f"/api/v3/users/{user_id}"}
        
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()
    
    async def get_time_entries(
        self, 
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Get time entries, optionally filtered by task, user, or project
        
        Args:
            task_id: Filter by work package (task) ID
            user_id: Filter by user ID
            project_id: Filter by project ID
            
        Returns:
            List of time entries
        """
        url = f"{self.base_url}/api/v3/time_entries"
        filters = []
        
        if task_id:
            filters.append({
                "workPackage": {"operator": "=", "values": [task_id]}
            })
        if user_id:
            filters.append({
                "user": {"operator": "=", "values": [user_id]}
            })
        if project_id:
            filters.append({
                "project": {"operator": "=", "values": [project_id]}
            })
            
        # Date filtering
        if start_date and end_date:
            filters.append({
                "spentOn": {
                    "operator": "<>d",
                    "values": [start_date, end_date]
                }
            })
        elif start_date:
            filters.append({
                "spentOn": {
                    "operator": ">=",
                    "values": [start_date]
                }
            })
        elif end_date:
            filters.append({
                "spentOn": {
                    "operator": "<=",
                    "values": [end_date]
                }
            })
        
        # Build initial request parameters
        if filters:
            import json as json_lib
            params = {
                "filters": json_lib.dumps(filters),
                "pageSize": 100
            }
        else:
            params = {"pageSize": 100}
        
        # Fetch all pages using pagination (exact pattern from test script)
        import logging
        logger = logging.getLogger(__name__)
        
        # DEBUG: Log the filters being sent
        if filters:
            logger.info(f"OpenProject get_time_entries filters: {json_lib.dumps(filters)}")
            
        request_url = url
        page_num = 1
        total_entries = 0
        
        while request_url:
            logger.debug(f"Fetching time entries page {page_num} from {request_url}")
            try:
                response = requests.get(request_url, headers=self.headers, params=params, timeout=120)
                
                # Check for permission errors (403) and trigger fallback
                if response.status_code == 403:
                    # Only attempt fallback if we aren't already filtering by a specific project
                    # (If we failed on a specfic project, fallback won't help)
                    if not project_id:
                        logger.warning("OpenProject get_time_entries: 403 Forbidden. Switching to Project-Based Fallback.")
                        
                        projects = await self.list_projects()
                        
                        for project in projects:
                            try:
                                # Recursive call with filtered project_id
                                # Yield from recursive call
                                async for entry in self.get_time_entries(
                                    task_id=task_id,
                                    user_id=user_id,
                                    project_id=str(project.id),
                                    start_date=start_date,
                                    end_date=end_date
                                ):
                                    yield entry
                                    total_entries += 1
                            except Exception as e:
                                # Log but continue to next project
                                logger.debug(f"Fallback: Failed to fetch entries for project {project.id}: {e}")
                                continue
                        
                        logger.info(f"OpenProject get_time_entries (Fallback): Fetched {total_entries} entries across {len(projects)} projects")
                        return
                
                response.raise_for_status()
                
                data = response.json()
                time_entries = data.get("_embedded", {}).get("elements", [])
                
                for entry in time_entries:
                    # Transform entry to include parsed fields
                    transformed = dict(entry)
                    # Parse hours from ISO duration (e.g., "PT8H" -> 8.0)
                    raw_hours = entry.get("hours")
                    if raw_hours:
                        transformed["hours"] = self._parse_duration_to_hours(raw_hours) or 0.0
                    else:
                        transformed["hours"] = 0.0
                    # Extract user_id from _links
                    entry_links = entry.get("_links", {})
                    user_href = entry_links.get("user", {}).get("href")
                    transformed["user_id"] = self._extract_id_from_href(user_href) if user_href else None
                    # Extract task_id from workPackage link
                    wp_href = entry_links.get("workPackage", {}).get("href")
                    transformed["task_id"] = self._extract_id_from_href(wp_href) if wp_href else None
                    # Use spentOn as date
                    transformed["date"] = entry.get("spentOn")
                    yield transformed
                    total_entries += 1
                
                # Check for next page
                links = data.get("_links", {})
                next_link = links.get("nextByOffset") or links.get("next")
                
                if next_link and isinstance(next_link, dict):
                    next_href = next_link.get("href")
                    if next_href:
                        if not next_href.startswith("http"):
                            request_url = f"{self.base_url}{next_href}"
                        else:
                            request_url = next_href
                        params = {}  # Clear params for subsequent requests
                        page_num += 1
                    else:
                        request_url = None
                else:
                    request_url = None
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403 and not project_id:
                     logger.warning("OpenProject get_time_entries: HTTP 403 caught in exception. Triggering Fallback.")
                     projects = await self.list_projects()
                     for project in projects:
                         try:
                             async for entry in self.get_time_entries(
                                 task_id=task_id,
                                 user_id=user_id,
                                 project_id=str(project.id),
                                 start_date=start_date,
                                 end_date=end_date
                             ):
                                 yield entry
                                 total_entries += 1
                         except Exception:
                             continue
                     return
                raise e
        
        logger.info(
            f"OpenProject get_time_entries: Fetched {total_entries} entries "
            f"from {page_num} page(s)"
        )
    
    async def get_total_hours_for_task(self, task_id: str) -> float:
        """
        Get total logged hours for a task by summing all time entries
        
        Args:
            task_id: The work package (task) ID
            
        Returns:
            Total logged hours
        """
        time_entries = await self.get_time_entries(task_id=task_id)
        total_hours = 0.0
        
        for entry in time_entries:
            hours_str = entry.get("hours")
            if hours_str:
                hours = self._parse_duration_to_hours(hours_str)
                if hours:
                    total_hours += hours
        
        return total_hours
    
    @staticmethod
    def _parse_duration_to_hours(
        duration_str: Optional[str]
    ) -> Optional[float]:
        """Parse OpenProject ISO 8601 duration string to hours"""
        if not duration_str:
            return None
        try:
            # OpenProject uses ISO 8601 duration format like
            # "PT1H30M", "P1DT2H", or "P2DT2H" (2 days + 2 hours)
            import re
            # Parse days, hours, and minutes from duration string
            days_match = re.search(r'(\d+)D', duration_str)
            hours_match = re.search(r'(\d+)H', duration_str)
            minutes_match = re.search(r'(\d+)M', duration_str)
            
            total_hours = 0.0
            if days_match:
                total_hours += float(days_match.group(1)) * 24.0
            if hours_match:
                total_hours += float(hours_match.group(1))
            if minutes_match:
                total_hours += float(minutes_match.group(1)) / 60.0
            
            # Return 0.0 for PT0H, None only if parsing failed
            # or no duration provided
            return total_hours if total_hours >= 0 else None
        except Exception:
            return None
    
    # ==================== Epic Operations ====================
    
    async def list_epics(self, project_id: Optional[str] = None) -> List[PMEpic]:
        """
        List all epics, optionally filtered by project.
        
        TESTED: ✅ Works - Uses type ID from /api/v3/types endpoint
        OpenProject requires numeric type ID, not string name
        """
        import logging
        import json as json_lib
        logger = logging.getLogger(__name__)
        
        # First, get Epic type ID from types endpoint
        types_url = f"{self.base_url}/api/v3/types"
        epic_type_id = None
        
        try:
            types_response = requests.get(types_url, headers=self.headers, timeout=10)
            if types_response.status_code == 200:
                types_data = types_response.json()
                elements = types_data.get('_embedded', {}).get('elements', [])
                for t in elements:
                    if 'epic' in t.get('name', '').lower():
                        epic_type_id = str(t.get('id'))
                        logger.info(f"Found Epic type ID: {epic_type_id}")
                        break
        except Exception as e:
            logger.warning(f"Could not fetch types to find Epic ID: {e}")
        
        if not epic_type_id:
            logger.warning("Epic type not found in OpenProject types")
            return []
        
        # Build filters with Epic type ID
        url = f"{self.base_url}/api/v3/work_packages"
        filters = [{
            "type": {"operator": "=", "values": [epic_type_id]}
        }]
        
        if project_id:
            filters.append({
                "project": {"operator": "=", "values": [project_id]}
            })
        
        params = {
            "filters": json_lib.dumps(filters),
            "pageSize": 100,
            "include": "priority,status,assignee,project,version,parent"
        }
        
        try:
            # Fetch all pages using pagination (exact pattern from test script)
            all_work_packages = []
            request_url = url
            
            while request_url:
                response = requests.get(request_url, headers=self.headers, params=params, timeout=120)
                
                if response.status_code == 200:
                    data = response.json()
                    work_packages = data.get('_embedded', {}).get('elements', [])
                    all_work_packages.extend(work_packages)
                    
                    # Check for next page
                    links = data.get("_links", {})
                    next_link = links.get("nextByOffset") or links.get("next")
                    
                    if next_link and isinstance(next_link, dict):
                        next_href = next_link.get("href")
                        if next_href:
                            if not next_href.startswith("http"):
                                request_url = f"{self.base_url}{next_href}"
                            else:
                                request_url = next_href
                            params = {}  # Clear params for subsequent requests
                        else:
                            request_url = None
                    else:
                        request_url = None
                else:
                    break
            
            if response.status_code == 200:
                work_packages = all_work_packages
                
                epics = []
                for wp in work_packages:
                    epic = PMEpic(
                        id=str(wp.get('id')),
                        name=wp.get('subject', ''),
                        description=wp.get('description', {}).get('raw') if isinstance(wp.get('description'), dict) else wp.get('description'),
                        project_id=str(wp.get('_links', {}).get('project', {}).get('href', '').split('/')[-1]) if wp.get('_links', {}).get('project') else None,
                        status=wp.get('_links', {}).get('status', {}).get('title') if wp.get('_links', {}).get('status') else None,
                        priority=wp.get('_links', {}).get('priority', {}).get('title') if wp.get('_links', {}).get('priority') else None,
                        start_date=self._parse_date(wp.get('startDate')),
                        end_date=self._parse_date(wp.get('dueDate')),
                        created_at=self._parse_datetime(wp.get('createdAt')),
                        updated_at=self._parse_datetime(wp.get('updatedAt')),
                        raw_data=wp
                    )
                    epics.append(epic)
                
                logger.info(f"Found {len(epics)} epics from OpenProject")
                return epics
            else:
                logger.error(
                    f"Failed to list epics: {response.status_code}, "
                    f"{response.text[:200]}"
                )
                raise ValueError(
                    f"Failed to list epics: ({response.status_code}) "
                    f"{response.text[:200]}"
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing epics: {e}", exc_info=True)
            raise ValueError(f"Failed to list epics: {str(e)}")
    
    async def get_epic(self, epic_id: str) -> Optional[PMEpic]:
        """
        Get a single epic by ID.
        
        TESTED: ✅ Works via GET /api/v3/work_packages/{id}
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/api/v3/work_packages/{epic_id}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                wp_data = response.json()
                
                # Verify it's an epic by checking type
                wp_type = wp_data.get('_links', {}).get('type', {}).get('title', '').lower()
                if 'epic' not in wp_type:
                    logger.warning(f"Work package {epic_id} is not an epic (type: {wp_type})")
                    return None
                
                epic = PMEpic(
                    id=str(wp_data.get('id')),
                    name=wp_data.get('subject', ''),
                    description=wp_data.get('description', {}).get('raw') if isinstance(wp_data.get('description'), dict) else wp_data.get('description'),
                    project_id=str(wp_data.get('_links', {}).get('project', {}).get('href', '').split('/')[-1]) if wp_data.get('_links', {}).get('project') else None,
                    status=wp_data.get('_links', {}).get('status', {}).get('title') if wp_data.get('_links', {}).get('status') else None,
                    priority=wp_data.get('_links', {}).get('priority', {}).get('title') if wp_data.get('_links', {}).get('priority') else None,
                    start_date=self._parse_date(wp_data.get('startDate')),
                    end_date=self._parse_date(wp_data.get('dueDate')),
                    created_at=self._parse_datetime(wp_data.get('createdAt')),
                    updated_at=self._parse_datetime(wp_data.get('updatedAt')),
                    raw_data=wp_data
                )
                logger.info(f"Retrieved epic {epic_id} from OpenProject")
                return epic
            elif response.status_code == 404:
                logger.warning(f"Epic {epic_id} not found")
                return None
            else:
                logger.error(
                    f"Failed to get epic: {response.status_code}, "
                    f"{response.text[:200]}"
                )
                raise ValueError(
                    f"Failed to get epic: ({response.status_code}) "
                    f"{response.text[:200]}"
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting epic: {e}", exc_info=True)
            raise ValueError(f"Failed to get epic: {str(e)}")
    
    async def create_epic(self, epic: PMEpic) -> PMEpic:
        """
        Create a new epic in OpenProject.
        
        TESTED: ✅ Works via POST /api/v3/work_packages with type Epic
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not epic.project_id:
            raise ValueError("project_id is required to create an epic")
        
        # First, get Epic type ID
        types_url = f"{self.base_url}/api/v3/types"
        epic_type_id = None
        
        try:
            types_response = requests.get(types_url, headers=self.headers, timeout=10)
            if types_response.status_code == 200:
                types_data = types_response.json()
                elements = types_data.get('_embedded', {}).get('elements', [])
                for t in elements:
                    if 'epic' in t.get('name', '').lower():
                        epic_type_id = str(t.get('id'))
                        break
        except Exception as e:
            logger.warning(f"Could not fetch types to find Epic ID: {e}")
        
        if not epic_type_id:
            raise ValueError("Epic type not found in OpenProject. Please ensure Epic type exists.")
        
        url = f"{self.base_url}/api/v3/work_packages"
        
        # Build payload
        payload = {
            "subject": epic.name,
            "_links": {
                "type": {"href": f"/api/v3/types/{epic_type_id}"},
                "project": {"href": f"/api/v3/projects/{epic.project_id}"}
            }
        }
        
        # Add description if provided
        if epic.description:
            payload["description"] = {
                "format": "plain",
                "raw": epic.description
            }
        
        # Add dates if provided
        if epic.start_date:
            payload["startDate"] = epic.start_date.isoformat()
        if epic.end_date:
            payload["dueDate"] = epic.end_date.isoformat()
        
        try:
            response = requests.post(
                url, headers=self.headers, json=payload, timeout=10
            )
            
            if response.status_code == 201:
                created_wp = response.json()
                created_id = str(created_wp.get('id'))
                
                # Fetch the full epic to return complete data
                created_epic = await self.get_epic(created_id)
                if created_epic:
                    logger.info(f"Created epic {created_id} in OpenProject")
                    return created_epic
                else:
                    raise ValueError("Failed to retrieve created epic")
            else:
                logger.error(
                    f"Failed to create epic: {response.status_code}, "
                    f"{response.text[:200]}"
                )
                raise ValueError(
                    f"Failed to create epic: ({response.status_code}) "
                    f"{response.text[:200]}"
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating epic: {e}", exc_info=True)
            raise ValueError(f"Failed to create epic: {str(e)}")
    
    async def update_epic(self, epic_id: str, updates: Dict[str, Any]) -> PMEpic:
        """
        Update an existing epic in OpenProject.
        
        TESTED: ✅ Works via PATCH /api/v3/work_packages/{id}
        Note: OpenProject requires lockVersion for optimistic locking
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/api/v3/work_packages/{epic_id}"
        
        # First, get the current epic to get lockVersion
        current_epic = await self.get_epic(epic_id)
        if not current_epic:
            raise ValueError(f"Epic {epic_id} not found")
        
        # Get lockVersion from raw data
        lock_version = None
        if current_epic.raw_data:
            lock_version = current_epic.raw_data.get('lockVersion')
        
        if lock_version is None:
            logger.warning(f"Could not get lockVersion for epic {epic_id}, trying update anyway")
        
        # Map updates to OpenProject fields
        payload: Dict[str, Any] = {}
        
        # Include lockVersion for optimistic locking
        if lock_version is not None:
            payload["lockVersion"] = lock_version
        
        if "name" in updates:
            payload["subject"] = updates["name"]
        if "description" in updates:
            desc = updates["description"]
            if desc:
                payload["description"] = {
                    "format": "plain",
                    "raw": desc
                }
            else:
                payload["description"] = None
        if "start_date" in updates:
            payload["startDate"] = (
                updates["start_date"].isoformat()
                if updates["start_date"]
                else None
            )
        if "end_date" in updates:
            payload["dueDate"] = (
                updates["end_date"].isoformat()
                if updates["end_date"]
                else None
            )
        if "status" in updates:
            # Status updates require status ID, not name
            # For now, we'll just log a warning
            logger.warning(
                "Status updates require status ID lookup, not implemented yet"
            )
        
        if not payload or (len(payload) == 1 and "lockVersion" in payload):
            # No updates to apply, just return the current epic
            return current_epic
        
        try:
            response = requests.patch(
                url, headers=self.headers, json=payload, timeout=10
            )
            
            if response.status_code == 200:
                # Fetch updated epic
                updated_epic = await self.get_epic(epic_id)
                if updated_epic:
                    logger.info(f"Updated epic {epic_id} in OpenProject")
                    return updated_epic
                else:
                    raise ValueError("Failed to retrieve updated epic")
            elif response.status_code == 409:
                # Conflict - lockVersion mismatch, retry once
                logger.warning(f"Update conflict for epic {epic_id}, retrying...")
                # Get fresh data and retry
                fresh_epic = await self.get_epic(epic_id)
                if fresh_epic and fresh_epic.raw_data:
                    fresh_lock_version = fresh_epic.raw_data.get('lockVersion')
                    if fresh_lock_version is not None:
                        payload["lockVersion"] = fresh_lock_version
                        retry_response = requests.patch(
                            url, headers=self.headers, json=payload, timeout=10
                        )
                        if retry_response.status_code == 200:
                            updated_epic = await self.get_epic(epic_id)
                            if updated_epic:
                                logger.info(f"Updated epic {epic_id} in OpenProject (after retry)")
                                return updated_epic
                raise ValueError(
                    f"Failed to update epic: Update conflict (409). "
                    f"Epic may have been modified by another process."
                )
            else:
                logger.error(
                    f"Failed to update epic: {response.status_code}, "
                    f"{response.text[:200]}"
                )
                raise ValueError(
                    f"Failed to update epic: ({response.status_code}) "
                    f"{response.text[:200]}"
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating epic: {e}", exc_info=True)
            raise ValueError(f"Failed to update epic: {str(e)}")
    
    async def delete_epic(self, epic_id: str) -> bool:
        """
        Delete an epic in OpenProject.
        
        TESTED: ✅ Works via DELETE /api/v3/work_packages/{id}
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/api/v3/work_packages/{epic_id}"
        
        try:
            response = requests.delete(url, headers=self.headers, timeout=10)
            
            if response.status_code == 204:
                logger.info(f"Deleted epic {epic_id} from OpenProject")
                return True
            elif response.status_code == 404:
                logger.warning(f"Epic {epic_id} not found for deletion")
                return False
            else:
                logger.error(
                    f"Failed to delete epic: {response.status_code}, "
                    f"{response.text[:200]}"
                )
                raise ValueError(
                    f"Failed to delete epic: ({response.status_code}) "
                    f"{response.text[:200]}"
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error deleting epic: {e}", exc_info=True)
            raise ValueError(f"Failed to delete epic: {str(e)}")
    
    # ==================== Label Operations ====================
    
    async def list_labels(self, project_id: Optional[str] = None) -> List[PMLabel]:
        """
        List all labels, optionally filtered by project.
        
        TESTED: ✅ Works - Categories from work packages endpoint
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/api/v3/work_packages"
        params = {"pageSize": 100}
        
        if project_id:
            import json as json_lib
            params["filters"] = json_lib.dumps([{
                "project": {"operator": "=", "values": [project_id]}
            }])
        
        try:
            # Fetch all pages using pagination (exact pattern from test script)
            all_work_packages = []
            request_url = url
            
            while request_url:
                response = requests.get(request_url, headers=self.headers, params=params, timeout=120)
                
                if response.status_code == 200:
                    data = response.json()
                    work_packages = data.get('_embedded', {}).get('elements', [])
                    all_work_packages.extend(work_packages)
                    
                    # Check for next page
                    links = data.get("_links", {})
                    next_link = links.get("nextByOffset") or links.get("next")
                    
                    if next_link and isinstance(next_link, dict):
                        next_href = next_link.get("href")
                        if next_href:
                            if not next_href.startswith("http"):
                                request_url = f"{self.base_url}{next_href}"
                            else:
                                request_url = next_href
                            params = {}  # Clear params for subsequent requests
                        else:
                            request_url = None
                    else:
                        request_url = None
                else:
                    break
            
            if response.status_code == 200:
                work_packages = all_work_packages
                
                # Extract unique categories
                categories_map = {}
                for wp in work_packages:
                    categories = wp.get('_links', {}).get('categories', [])
                    if isinstance(categories, list):
                        for cat in categories:
                            if isinstance(cat, dict):
                                cat_href = cat.get('href', '')
                                cat_id = str(cat_href.split('/')[-1]) if cat_href else None
                                cat_name = cat.get('title', '')
                                if cat_id and cat_id not in categories_map:
                                    categories_map[cat_id] = {
                                        'id': cat_id,
                                        'name': cat_name,
                                        'href': cat_href
                                    }
                
                # Convert to PMLabel objects
                labels = []
                for cat_id, cat_data in categories_map.items():
                    label = PMLabel(
                        id=cat_id,
                        name=cat_data['name'],
                        description=None,
                        project_id=project_id,
                        raw_data=cat_data
                    )
                    labels.append(label)
                
                logger.info(f"Found {len(labels)} labels/categories from OpenProject")
                return labels
            else:
                logger.error(
                    f"Failed to list labels: {response.status_code}, "
                    f"{response.text[:200]}"
                )
                raise ValueError(
                    f"Failed to list labels: ({response.status_code}) "
                    f"{response.text[:200]}"
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing labels: {e}", exc_info=True)
            raise ValueError(f"Failed to list labels: {str(e)}")
    
    async def get_label(self, label_id: str) -> Optional[PMLabel]:
        """Get a single label by ID"""
        raise NotImplementedError("Labels not yet implemented for OpenProject")
    
    async def create_label(self, label: PMLabel) -> PMLabel:
        """Create a new label"""
        raise NotImplementedError("Labels not yet implemented for OpenProject")
    
    async def update_label(self, label_id: str, updates: Dict[str, Any]) -> PMLabel:
        """Update an existing label"""
        raise NotImplementedError("Labels not yet implemented for OpenProject")
    
    async def delete_label(self, label_id: str) -> bool:
        """Delete a label"""
        raise NotImplementedError("Labels not yet implemented for OpenProject")
    
    # ==================== Status Operations ====================
    
    async def list_statuses(self, entity_type: str, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of available statuses for an entity type.
        
        TESTED: ✅ Works via /api/v3/statuses endpoint
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/api/v3/statuses"
        all_elements = []
        params = {"pageSize": 100}
        
        try:
            # Fetch all pages using pagination (exact pattern from test script)
            request_url = url
            while request_url:
                response = requests.get(request_url, headers=self.headers, params=params, timeout=120)
                
                if response.status_code == 200:
                    data = response.json()
                    elements = data.get('_embedded', {}).get('elements', [])
                    all_elements.extend(elements)
                    
                    # Check for next page
                    links = data.get("_links", {})
                    next_link = links.get("nextByOffset") or links.get("next")
                    
                    if next_link and isinstance(next_link, dict):
                        next_href = next_link.get("href")
                        if next_href:
                            if not next_href.startswith("http"):
                                request_url = f"{self.base_url}{next_href}"
                            else:
                                request_url = next_href
                            params = {}  # Clear params for subsequent requests
                        else:
                            request_url = None
                    else:
                        request_url = None
                else:
                    break
            
            if response.status_code == 200:
                elements = all_elements
                
                statuses = []
                for status in elements:
                    if isinstance(status, dict):
                        status_id = str(status.get('id', ''))
                        status_name = status.get('name', '')
                        color = status.get('color', '')
                        
                        if status_id and status_name:
                            statuses.append({
                                "id": status_id,
                                "name": status_name,
                                "color": color,
                                "is_closed": status.get('isClosed', False),
                                "is_default": status.get('isDefault', False),
                            })
                
                logger.info(f"Found {len(statuses)} statuses from OpenProject")
                return statuses
            else:
                logger.error(
                    f"Failed to list statuses: {response.status_code}, "
                    f"{response.text[:200]}"
                )
                raise ValueError(
                    f"Failed to list statuses: ({response.status_code}) "
                    f"{response.text[:200]}"
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing statuses: {e}", exc_info=True)
            raise ValueError(f"Failed to list statuses: {str(e)}")
    
    async def list_priorities(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of available priorities.
        
        TESTED: ✅ Works via /api/v3/priorities endpoint
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/api/v3/priorities"
        all_elements = []
        params = {"pageSize": 100}
        
        try:
            # Fetch all pages using pagination (exact pattern from test script)
            request_url = url
            while request_url:
                response = requests.get(request_url, headers=self.headers, params=params, timeout=120)
                
                if response.status_code == 200:
                    data = response.json()
                    elements = data.get('_embedded', {}).get('elements', [])
                    all_elements.extend(elements)
                    
                    # Check for next page
                    links = data.get("_links", {})
                    next_link = links.get("nextByOffset") or links.get("next")
                    
                    if next_link and isinstance(next_link, dict):
                        next_href = next_link.get("href")
                        if next_href:
                            if not next_href.startswith("http"):
                                request_url = f"{self.base_url}{next_href}"
                            else:
                                request_url = next_href
                            params = {}  # Clear params for subsequent requests
                        else:
                            request_url = None
                    else:
                        request_url = None
                else:
                    break
            
            if response.status_code == 200:
                elements = all_elements
                
                priorities = []
                for priority in elements:
                    if isinstance(priority, dict):
                        priority_id = str(priority.get('id', ''))
                        priority_name = priority.get('name', '')
                        color = priority.get('color', '')
                        
                        if priority_id and priority_name:
                            priorities.append({
                                "id": priority_id,
                                "name": priority_name,
                                "color": color,
                                "is_default": priority.get('isDefault', False),
                                "position": priority.get('position', 0),
                            })
                
                logger.info(f"Found {len(priorities)} priorities from OpenProject")
                return priorities
            else:
                logger.error(
                    f"Failed to list priorities: {response.status_code}, "
                    f"{response.text[:200]}"
                )
                raise ValueError(
                    f"Failed to list priorities: ({response.status_code}) "
                    f"{response.text[:200]}"
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing priorities: {e}", exc_info=True)
            raise ValueError(f"Failed to list priorities: {str(e)}")

