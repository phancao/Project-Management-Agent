"""
OpenProject Provider

Connects to OpenProject (https://www.openproject.org/) API
to manage projects, work packages (tasks), and sprints.
"""
import base64
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from .base import BasePMProvider
from .models import (
    PMUser, PMProject, PMTask, PMSprint, PMEpic, PMLabel,
    PMProviderConfig
)


class OpenProjectProvider(BasePMProvider):
    """
    OpenProject API integration
    
    OpenProject API documentation:
    https://www.openproject.org/docs/api/
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
        
        # OpenProject uses Basic auth with "apikey" as username and API key
        auth_string = f"apikey:{self.api_key}"
        credentials = base64.b64encode(
            auth_string.encode()
        ).decode()
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {credentials}"
        }
    
    # ==================== Project Operations ====================
    
    async def list_projects(self) -> List[PMProject]:
        """List all projects from OpenProject (handles pagination)"""
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/api/v3/projects"
        all_projects = []
        page_num = 1
        
        # Use maximum page size for efficiency (OpenProject API supports up to 500 per page)
        params = {"pageSize": 500}
        request_url = url
        
        logger.info(f"OpenProject: Fetching projects from {url} with pageSize=500")
        
        while request_url:
            response = requests.get(request_url, headers=self.headers, params=params, timeout=60)
            
            # Provide user-friendly error messages for common HTTP errors
            if response.status_code == 401:
                raise ValueError(
                    "OpenProject authentication failed. Please verify your API token is correct. "
                    "For OpenProject, use Basic Auth with format: apikey:TOKEN"
                )
            elif response.status_code == 403:
                raise ValueError(
                    "OpenProject access forbidden. The API token may not have permission to list projects, "
                    "or the account doesn't have access to any projects. Please check your OpenProject permissions."
                )
            elif response.status_code == 404:
                raise ValueError(
                    "OpenProject endpoint not found. Please verify the base URL is correct."
                )
            
            response.raise_for_status()
            
            data = response.json()
            projects_data = data.get("_embedded", {}).get("elements", [])
            
            total_count = data.get("count", len(all_projects) + len(projects_data))
            logger.info(
                f"OpenProject: Page {page_num} - Found {len(projects_data)} projects "
                f"(total so far: {len(all_projects) + len(projects_data)}/{total_count})"
            )
            
            all_projects.extend(projects_data)
            
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
                # Verify we got all projects
                if total_count > len(all_projects):
                    logger.warning(
                        f"OpenProject: Response indicates {total_count} total projects, "
                        f"but only fetched {len(all_projects)}. "
                        f"This may indicate pagination issues."
                    )
                request_url = None
        
        logger.info(
            f"OpenProject: Pagination complete - Total projects fetched: {len(all_projects)} "
            f"from {page_num} page(s)"
        )
        
        return [self._parse_project(proj) for proj in all_projects]
    
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
        assignee_id: Optional[str] = None
    ) -> List[PMTask]:
        """
        List all work packages (tasks) with automatic pagination.
        
        OpenProject defaults to 20 items per page. This method fetches
        ALL pages to return the complete task list.
        """
        url = f"{self.base_url}/api/v3/work_packages"
        
        # Build filters for project and/or assignee
        import json as json_lib
        import logging
        logger = logging.getLogger(__name__)
        
        filters = []
        if project_id:
            filters.append({
                "project": {"operator": "=", "values": [project_id]}
            })
        if assignee_id:
            filters.append({
                "assignee": {"operator": "=", "values": [assignee_id]}
            })
        
        # Build base params
        base_params: Dict[str, Any] = {}
        if filters:
            base_params["filters"] = json_lib.dumps(filters)
            logger.info(f"OpenProject list_tasks with filters: {base_params}")
        
        # Include priority in embedded data for better parsing
        base_params["include"] = "priority,status,assignee,project,version,parent"
        
        # Pagination settings
        page_size = 500  # OpenProject max is typically 1000, use 500 for safety
        offset = 0
        all_tasks: List[PMTask] = []
        total_count = None
        
        while True:
            params = {**base_params, "pageSize": page_size, "offset": offset}
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            tasks_data = result.get("_embedded", {}).get("elements", [])
            
            # Get total count on first request
            if total_count is None:
                total_count = result.get("total", 0)
                logger.info(f"OpenProject list_tasks: Total {total_count} work packages to fetch")
            
            # Parse and add tasks
            for task in tasks_data:
                all_tasks.append(self._parse_task(task))
            
            # Check if we've fetched all
            if len(tasks_data) < page_size:
                break
            
            if len(all_tasks) >= total_count:
                break
            
            offset += page_size
            
            # Safety limit to prevent infinite loops
            if offset > 50000:
                logger.warning(f"OpenProject list_tasks: Safety limit reached at offset {offset}")
                break
        
        logger.info(f"OpenProject list_tasks: Fetched {len(all_tasks)} work packages total")
        
        # Log if filter returns no results
        if assignee_id and len(all_tasks) == 0:
            logger.warning(
                f"Assignee filter returned 0 tasks for "
                f"user_id={assignee_id}. Total available: {total_count}"
            )
        
        return all_tasks
    
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
        
        # POST to form endpoint first to get validation and lockVersion
        # This is the recommended OpenProject workflow
        # IMPORTANT: This code path uses form validation - if you see this log, new code is running
        form_url = f"{self.base_url}/api/v3/work_packages/{task_id}/form"
        
        # Get current lockVersion to include in form request (helps with validation)
        current_lock_version = None
        try:
            current_task = await self.get_task(task_id)
            if current_task and hasattr(current_task, 'raw_data') and current_task.raw_data:
                current_lock_version = current_task.raw_data.get('lockVersion')
                if current_lock_version is not None:
                    # Include current lockVersion in payload for form validation
                    form_payload = payload.copy()
                    form_payload["lockVersion"] = current_lock_version
                else:
                    form_payload = payload
            else:
                form_payload = payload
        except Exception as e:
            logger.warning(f"Could not get current task for lockVersion: {e}")
            form_payload = payload
        
        logger.info(f"Validating update via form endpoint with payload: {form_payload}")
        
        # Retry form endpoint if we get 409 (lockVersion conflict)
        form_max_retries = 2
        form_validated_payload = None
        for form_attempt in range(form_max_retries + 1):
            error_text = None
            status_code = None
            try:
                form_response = requests.post(form_url, headers=self.headers, json=form_payload, timeout=10)
                if not form_response.ok:
                    # Form endpoint returned an error
                    error_text = form_response.text
                    status_code = form_response.status_code
                    
                    # Handle 409 Conflict from form endpoint - get fresh lockVersion and retry
                    if status_code == 409 and form_attempt < form_max_retries:
                        logger.warning(f"Form endpoint returned 409 conflict on attempt {form_attempt + 1}, getting fresh lockVersion...")
                        # Get current task to get fresh lockVersion
                        try:
                            current_task = await self.get_task(task_id)
                            if current_task and hasattr(current_task, 'raw_data') and current_task.raw_data:
                                fresh_lock_version = current_task.raw_data.get('lockVersion')
                                if fresh_lock_version is not None:
                                    # Update form payload with fresh lockVersion
                                    form_payload = payload.copy()
                                    form_payload["lockVersion"] = fresh_lock_version
                                    logger.info(f"Retrying form endpoint with fresh lockVersion: {fresh_lock_version}")
                                    continue  # Retry form endpoint
                        except Exception as retry_error:
                            logger.error(f"Error getting fresh lockVersion for form retry: {retry_error}")
                    
                    logger.error(f"Form validation error ({status_code}): {error_text}")
                    
                    # Try to parse the error response
                    error_message = None
                    try:
                        error_data = form_response.json()
                        logger.error(f"Form validation error JSON: {error_data}")
                        
                        if "_embedded" in error_data and "errors" in error_data["_embedded"]:
                            errors = error_data["_embedded"]["errors"]
                            if errors and len(errors) > 0:
                                error_parts = []
                                for err in errors:
                                    msg = err.get("message", "")
                                    attr = err.get("_attribute", "")
                                    if msg:
                                        error_parts.append(f"{attr}: {msg}" if attr else msg)
                                if error_parts:
                                    error_message = "; ".join(error_parts)
                        
                        if not error_message:
                            error_message = error_data.get("message") or error_data.get("error") or (error_text if error_text else "Unknown error")
                    except (ValueError, KeyError, AttributeError) as parse_error:
                        logger.error(f"Failed to parse form validation error: {parse_error}")
                        error_message = error_text if error_text else str(parse_error)
                    
                    if not error_message:
                        error_message = error_text if error_text else (f"HTTP {status_code} error" if status_code else "Unknown error")
                    
                    final_status_code = status_code if status_code else 500
                    raise ValueError(f"OpenProject validation error ({final_status_code}): {error_message}")
                
                # Form endpoint succeeded - get validated payload
                form_data = form_response.json()
                validated_payload = form_data.get("_embedded", {}).get("payload", {})
                lock_version = validated_payload.get("lockVersion")
                
                if not validated_payload:
                    logger.warning("Form endpoint returned empty payload, using original payload")
                    validated_payload = payload.copy()
                    # Still try to get lockVersion from current task
                    current_task = await self.get_task(task_id)
                    if current_task and hasattr(current_task, 'raw_data') and current_task.raw_data:
                        lock_version = current_task.raw_data.get('lockVersion')
                
                # Ensure lockVersion is included
                if lock_version is not None:
                    validated_payload["lockVersion"] = lock_version
                elif "lockVersion" not in validated_payload:
                    # Fallback: get lockVersion from current task
                    current_task = await self.get_task(task_id)
                    if current_task and hasattr(current_task, 'raw_data') and current_task.raw_data:
                        lock_version = current_task.raw_data.get('lockVersion')
                        if lock_version is not None:
                            validated_payload["lockVersion"] = lock_version
                
                logger.info(f"Form validation successful. Using validated payload: {validated_payload}")
                form_validated_payload = validated_payload
                break  # Success - exit retry loop
                
            except ValueError:
                # Re-raise validation errors (don't retry)
                raise
            except requests.exceptions.RequestException as e:
                logger.error(f"Error calling form endpoint (attempt {form_attempt + 1}): {e}")
                if form_attempt < form_max_retries:
                    logger.warning("Retrying form endpoint...")
                    continue
                # Final attempt failed - fallback to getting lockVersion from current task
                logger.warning("Form endpoint failed after retries, falling back to direct update")
                try:
                    current_task = await self.get_task(task_id)
                    if current_task and hasattr(current_task, 'raw_data') and current_task.raw_data:
                        lock_version = current_task.raw_data.get('lockVersion')
                        if lock_version is not None:
                            payload["lockVersion"] = lock_version
                    form_validated_payload = payload
                except Exception as fallback_error:
                    logger.error(f"Error in fallback: {fallback_error}")
                    raise ValueError(f"Failed to update task: Form endpoint failed and fallback also failed: {str(e)}")
                break
            except Exception as e:
                # Catch any other unexpected exceptions
                logger.error(f"Unexpected error in form endpoint (attempt {form_attempt + 1}): {e}")
                if form_attempt < form_max_retries:
                    logger.warning("Retrying form endpoint...")
                    continue
                raise ValueError(f"Failed to update task: Unexpected error: {str(e)}")
        
        # Use the validated payload (either from form endpoint or fallback)
        validated_payload = form_validated_payload
        
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
                        # Get fresh lockVersion from form endpoint and retry
                        try:
                            fresh_form_response = requests.post(form_url, headers=self.headers, json=payload, timeout=10)
                            if fresh_form_response.ok:
                                fresh_form_data = fresh_form_response.json()
                                fresh_validated_payload = fresh_form_data.get("_embedded", {}).get("payload", {})
                                fresh_lock_version = fresh_validated_payload.get("lockVersion")
                                if fresh_lock_version is not None:
                                    # Update the validated payload with fresh lockVersion
                                    validated_payload = fresh_validated_payload.copy()
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
        List sprints (iterations) from OpenProject with automatic pagination.
        
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
        
        url = f"{self.base_url}/api/v3/versions"
        
        # Pagination settings
        page_size = 500
        offset = 0
        sprints_data: List[Dict[str, Any]] = []
        total_count = None
        
        while True:
            params = {"pageSize": page_size, "offset": offset}
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            page_data = result.get("_embedded", {}).get("elements", [])
            
            if total_count is None:
                total_count = result.get("total", 0)
                logger.info(f"OpenProject list_sprints: Total {total_count} versions to fetch")
            
            sprints_data.extend(page_data)
            
            if len(page_data) < page_size:
                break
            if len(sprints_data) >= total_count:
                break
            
            offset += page_size
            if offset > 10000:  # Safety limit
                logger.warning(f"OpenProject list_sprints: Safety limit reached at offset {offset}")
                break
        
        logger.info(f"OpenProject list_sprints: Fetched {len(sprints_data)} versions total")
        
        # Filter by project_id if provided
        # (versions don't have project filter in API)
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
        List all users with automatic pagination.
        
        Note: OpenProject may require admin permissions for user listing.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/api/v3/users"
        
        # Pagination settings
        page_size = 500
        offset = 0
        all_users: List[PMUser] = []
        total_count = None
        
        while True:
            params = {"pageSize": page_size, "offset": offset}
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            users_data = result.get("_embedded", {}).get("elements", [])
            
            if total_count is None:
                total_count = result.get("total", 0)
                logger.info(f"OpenProject list_users: Total {total_count} users to fetch")
            
            for user in users_data:
                all_users.append(self._parse_user(user))
            
            if len(users_data) < page_size:
                break
            if len(all_users) >= total_count:
                break
            
            offset += page_size
            if offset > 10000:  # Safety limit
                logger.warning(f"OpenProject list_users: Safety limit reached at offset {offset}")
                break
        
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
                data.get("estimatedTime") or data.get("derivedEstimatedTime")
            ),
            actual_hours=self._parse_duration_to_hours(
                data.get("spentTime")
            ),
            start_date=self._parse_date(data.get("startDate")),
            due_date=self._parse_date(data.get("dueDate")),
            created_at=self._parse_datetime(data.get("createdAt")),
            updated_at=self._parse_datetime(data.get("updatedAt")),
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
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
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
        
        if filters:
            import json as json_lib
            params = {"filters": json_lib.dumps(filters)}
        else:
            params = {}
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        return data.get("_embedded", {}).get("elements", [])
    
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
                total_hours += float(days_match.group(1)) * 8.0
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
        List all epics with automatic pagination, optionally filtered by project.
        
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
        
        base_params = {
            "filters": json_lib.dumps(filters)
        }
        
        # Pagination settings
        page_size = 500
        offset = 0
        all_epics: List[PMEpic] = []
        total_count = None
        
        try:
            while True:
                params = {**base_params, "pageSize": page_size, "offset": offset}
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                
                if response.status_code != 200:
                    logger.error(
                        f"Failed to list epics: {response.status_code}, "
                        f"{response.text[:200]}"
                    )
                    raise ValueError(
                        f"Failed to list epics: ({response.status_code}) "
                        f"{response.text[:200]}"
                    )
                
                data = response.json()
                work_packages = data.get('_embedded', {}).get('elements', [])
                
                if total_count is None:
                    total_count = data.get("total", 0)
                    logger.info(f"OpenProject list_epics: Total {total_count} epics to fetch")
                
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
                    all_epics.append(epic)
                
                if len(work_packages) < page_size:
                    break
                if len(all_epics) >= total_count:
                    break
                
                offset += page_size
                if offset > 10000:  # Safety limit
                    logger.warning(f"OpenProject list_epics: Safety limit reached at offset {offset}")
                    break
            
            logger.info(f"OpenProject list_epics: Fetched {len(all_epics)} epics total")
            return all_epics
            
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
        List all labels with automatic pagination, optionally filtered by project.
        
        TESTED: ✅ Works - Categories from work packages endpoint
        """
        import logging
        import json as json_lib
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/api/v3/work_packages"
        
        base_params: Dict[str, Any] = {}
        if project_id:
            base_params["filters"] = json_lib.dumps([{
                "project": {"operator": "=", "values": [project_id]}
            }])
        
        # Pagination settings
        page_size = 500
        offset = 0
        categories_map: Dict[str, Dict[str, Any]] = {}
        total_count = None
        
        try:
            while True:
                params = {**base_params, "pageSize": page_size, "offset": offset}
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                
                if response.status_code != 200:
                    logger.error(
                        f"Failed to list labels: {response.status_code}, "
                        f"{response.text[:200]}"
                    )
                    raise ValueError(
                        f"Failed to list labels: ({response.status_code}) "
                        f"{response.text[:200]}"
                    )
                
                data = response.json()
                work_packages = data.get('_embedded', {}).get('elements', [])
                
                if total_count is None:
                    total_count = data.get("total", 0)
                    logger.info(f"OpenProject list_labels: Scanning {total_count} work packages for categories")
                
                # Extract unique categories
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
                
                if len(work_packages) < page_size:
                    break
                if offset + len(work_packages) >= total_count:
                    break
                
                offset += page_size
                if offset > 50000:  # Safety limit
                    logger.warning(f"OpenProject list_labels: Safety limit reached at offset {offset}")
                    break
            
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
            
            logger.info(f"OpenProject list_labels: Found {len(labels)} unique labels/categories")
            return labels
            
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
        Get list of available statuses for an entity type with automatic pagination.
        
        TESTED: ✅ Works via /api/v3/statuses endpoint
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/api/v3/statuses"
        
        # Pagination settings
        page_size = 100
        offset = 0
        statuses: List[Dict[str, Any]] = []
        total_count = None
        
        try:
            while True:
                params = {"pageSize": page_size, "offset": offset}
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                
                if response.status_code != 200:
                    logger.error(
                        f"Failed to list statuses: {response.status_code}, "
                        f"{response.text[:200]}"
                    )
                    raise ValueError(
                        f"Failed to list statuses: ({response.status_code}) "
                        f"{response.text[:200]}"
                    )
                
                data = response.json()
                elements = data.get('_embedded', {}).get('elements', [])
                
                if total_count is None:
                    total_count = data.get("total", 0)
                    logger.info(f"OpenProject list_statuses: Total {total_count} statuses to fetch")
                
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
                
                if len(elements) < page_size:
                    break
                if len(statuses) >= total_count:
                    break
                
                offset += page_size
                if offset > 1000:  # Safety limit for statuses
                    logger.warning(f"OpenProject list_statuses: Safety limit reached at offset {offset}")
                    break
            
            logger.info(f"OpenProject list_statuses: Fetched {len(statuses)} statuses total")
            return statuses
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing statuses: {e}", exc_info=True)
            raise ValueError(f"Failed to list statuses: {str(e)}")
    
    async def list_priorities(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of available priorities with automatic pagination.
        
        TESTED: ✅ Works via /api/v3/priorities endpoint
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/api/v3/priorities"
        
        # Pagination settings
        page_size = 100
        offset = 0
        priorities: List[Dict[str, Any]] = []
        total_count = None
        
        try:
            while True:
                params = {"pageSize": page_size, "offset": offset}
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                
                if response.status_code != 200:
                    logger.error(
                        f"Failed to list priorities: {response.status_code}, "
                        f"{response.text[:200]}"
                    )
                    raise ValueError(
                        f"Failed to list priorities: ({response.status_code}) "
                        f"{response.text[:200]}"
                    )
                
                data = response.json()
                elements = data.get('_embedded', {}).get('elements', [])
                
                if total_count is None:
                    total_count = data.get("total", 0)
                    logger.info(f"OpenProject list_priorities: Total {total_count} priorities to fetch")
                
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
                
                if len(elements) < page_size:
                    break
                if len(priorities) >= total_count:
                    break
                
                offset += page_size
                if offset > 500:  # Safety limit for priorities
                    logger.warning(f"OpenProject list_priorities: Safety limit reached at offset {offset}")
                    break
            
            logger.info(f"OpenProject list_priorities: Fetched {len(priorities)} priorities total")
            return priorities
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing priorities: {e}", exc_info=True)
            raise ValueError(f"Failed to list priorities: {str(e)}")

