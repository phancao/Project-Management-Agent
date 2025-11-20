"""
JIRA Provider

Connects to Atlassian JIRA API to manage projects, issues, and sprints.
"""
import base64
import logging
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from .base import BasePMProvider
from .models import (
    PMUser, PMProject, PMTask, PMSprint, PMEpic, PMLabel,
    PMProviderConfig
)

logger = logging.getLogger(__name__)


class JIRAProvider(BasePMProvider):
    """
    JIRA Cloud API integration
    
    JIRA Cloud API documentation:
    https://developer.atlassian.com/cloud/jira/platform/rest/v3/
    """
    
    def __init__(self, config: PMProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url.rstrip('/')
        
        # JIRA uses email + API token for authentication
        api_token = config.api_token
        email = config.username  # For JIRA, username is the email
        
        if not api_token:
            raise ValueError("JIRA requires api_token for authentication")
        
        if not email:
            raise ValueError(
                "JIRA requires email (username) for authentication. "
                "For JIRA Cloud, use your email address."
            )
        
        # JIRA Basic Auth: base64(email:API_TOKEN)
        auth_string = f"{email}:{api_token}"
        auth_bytes = auth_string.encode('utf-8')
        auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_b64}",
            "Accept": "application/json"
        }
    
    async def list_projects(self) -> List[PMProject]:
        """
        List all projects from JIRA.
        
        Fetches all accessible projects. Without the 'recent' parameter,
        JIRA returns all accessible projects (may be paginated internally).
        """
        url = f"{self.base_url}/rest/api/3/project"
        all_projects = []
        start_at = 0
        max_results = 50  # JIRA API default page size
        
        while True:
            # JIRA API v3: Remove 'recent' parameter to get ALL projects
            # Use pagination to fetch all pages
            params: Dict[str, Any] = {
                "startAt": start_at,
                "maxResults": max_results,
                # Get more details
                "expand": "description,lead,url,projectKeys"
            }
            
            response = requests.get(
                url, headers=self.headers, params=params, timeout=30
            )
            
            # Provide better error messages for common issues
            if response.status_code == 401:
                raise ValueError(
                    "JIRA authentication failed. Please verify your email and "
                    "API token are correct. "
                    "For JIRA Cloud, use: email:API_TOKEN for Basic Auth."
                )
            elif response.status_code == 403:
                raise ValueError(
                    "JIRA access forbidden. The API token may not have "
                    "permission to list projects, or the account doesn't "
                    "have access to any projects."
                )
            
            response.raise_for_status()
            
            projects_data = response.json()
            
            # Handle empty response
            if not projects_data:
                break
            
            # Response is typically a list of projects
            if isinstance(projects_data, list):
                # Direct list response - parse all projects
                for proj in projects_data:
                    all_projects.append(self._parse_project(proj))
                
                # If we got fewer than max_results, we're done
                if len(projects_data) < max_results:
                    break
                
                # Continue to next page
                start_at += len(projects_data)
            else:
                # Unexpected format - try to handle gracefully
                if isinstance(projects_data, dict):
                    if "values" in projects_data:
                        # Paginated response format
                        projects_list = projects_data["values"]
                        for proj in projects_list:
                            all_projects.append(self._parse_project(proj))
                        
                        # Check if there are more pages
                        total = projects_data.get("total", 0)
                        start_at = projects_data.get("startAt", 0) + len(projects_list)
                        if start_at >= total or projects_data.get("isLast", True):
                            break
                    else:
                        # Single project object
                        all_projects.append(self._parse_project(projects_data))
                        break
                else:
                    # Unknown format
                    logger.warning(f"Unexpected JIRA projects response format: {type(projects_data)}")
                    break
        
        return all_projects
    
    def _parse_project(self, proj_data: Dict[str, Any]) -> PMProject:
        """Parse JIRA project data to PMProject"""
        # For Next-Gen projects, try different ID fields
        project_id = (
            proj_data.get("key") or
            proj_data.get("id") or
            proj_data.get("simplifiedId") or
            str(proj_data.get("id", ""))
        )
        
        # JIRA projects don't have a simple status field
        return PMProject(
            id=project_id,
            name=proj_data.get("name", ""),
            description=proj_data.get("description", ""),
            status=None,
            priority=None,
            created_at=self._parse_datetime(proj_data.get("created")),
            updated_at=self._parse_datetime(proj_data.get("updated")),
            raw_data=proj_data
        )
    
    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """Parse JIRA datetime string"""
        if not dt_str:
            return None
        try:
            # JIRA format: "2023-01-15T10:30:00.000+0000"
            dt_str = (
                dt_str.replace("+0000", "+00:00")
                .replace("Z", "+00:00")
            )
            return datetime.fromisoformat(dt_str)
        except (ValueError, AttributeError):
            return None
    
    async def get_project(self, project_id: str) -> Optional[PMProject]:
        """
        Get a specific project by ID or key.
        
        Tries to fetch project using JIRA API /rest/api/3/project endpoint.
        """
        # Try project key first (most common)
        url = f"{self.base_url}/rest/api/3/project/{project_id}"
        
        response = requests.get(
            url, headers=self.headers, timeout=10
        )
        
        if response.status_code == 200:
            project_data = response.json()
            return self._parse_project(project_data)
        elif response.status_code == 404:
            # Project not found
            return None
        elif response.status_code == 410:
            # Project gone/deleted/archived
            return None
        else:
            # Log other errors but don't fail completely
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                "Failed to get project %s: HTTP %d",
                project_id, response.status_code
            )
            return None
    
    async def create_project(self, project: PMProject) -> PMProject:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def update_project(
        self, project_id: str, updates: Dict
    ) -> PMProject:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def delete_project(self, project_id: str) -> bool:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def list_tasks(
        self,
        project_id: Optional[str] = None,
        assignee_id: Optional[str] = None
    ) -> List[PMTask]:
        """
        List all issues (tasks) from JIRA.
        
        Uses JIRA Search API with JQL to filter by project and/or assignee.
        """
        # First, verify the project exists if project_id is provided
        # This helps provide a clearer error message
        actual_project_key = None
        project_numeric_id = None
        if project_id:
            project = await self.get_project(project_id)
            if project is None:
                # Try to get more information about why it failed
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    "Project '%s' verification failed. "
                    "This might indicate the project is archived, deleted, "
                    "or you don't have permission to access it.",
                    project_id
                )
                # Still try the search - sometimes the project exists but
                # the get_project endpoint fails for other reasons
                actual_project_key = project_id
            else:
                # Use the verified project key (might be different format)
                actual_project_key = project.id
                # Try to get numeric ID from raw_data for alternative queries
                if project.raw_data:
                    project_numeric_id = (
                        project.raw_data.get("id") or
                        project.raw_data.get("simplifiedId")
                    )
        else:
            actual_project_key = project_id
        
        # JIRA deprecated /rest/api/3/search and requires /rest/api/3/search/jql
        # See: https://developer.atlassian.com/changelog/#CHANGE-2046
        url = f"{self.base_url}/rest/api/3/search/jql"
        
        # Build JQL query
        jql_parts = []
        if actual_project_key:
            # JIRA project can be identified by key (e.g., "SCRUM") or ID
            # Quote the project_id to handle special characters and ensure
            # proper JQL syntax. JIRA JQL requires quotes for project keys.
            # Also try without quotes as fallback for some JIRA instances
            jql_parts.append(f'project = "{actual_project_key}"')
        if assignee_id:
            # JIRA JQL supports currentUser() function for current user's tasks
            # Try using currentUser() first, then fall back to accountId/email if needed
            # For JIRA, we can use currentUser() if the assignee_id matches the current user
            # Otherwise, use accountId, email, or username
            jql_parts.append(f'assignee = "{assignee_id}"')
        
        # Default: return all issues if no filters
        if not jql_parts:
            jql = "ORDER BY created DESC"
        else:
            jql = " AND ".join(jql_parts) + " ORDER BY created DESC"
        
        # JIRA default is 50, max is 1000
        params: Dict[str, Any] = {
            "jql": jql,
            "maxResults": 1000,
            "fields": [
                "summary",           # title
                "description",       # description
                "status",            # status
                "priority",          # priority
                "assignee",          # assignee
                "project",           # project info
                "parent",            # parent task
                "customfield_10020", # sprint field (for Scrum/Kanban boards)
                # estimated hours (seconds)
                "timeoriginalestimate",
                "timespent",         # actual hours (seconds)
                "created",           # created date
                "updated",           # updated date
                "resolutiondate",    # completed date
                "duedate",           # due date
                "startdate",         # start date
            ],
            "expand": "names,schema"
        }
        
        # Comprehensive logging for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=" * 80)
        logger.info("JIRA API REQUEST TRACE")
        logger.info("=" * 80)
        logger.info("Project ID provided: %s", project_id)
        logger.info("Actual project key used: %s", actual_project_key)
        logger.info("Project numeric ID: %s", project_numeric_id)
        logger.info("JQL Query: %s", jql)
        logger.info("Request URL: %s", url)
        logger.info("Request params: %s", params)
        logger.info("Request headers: %s", {k: v for k, v in self.headers.items() if k != 'Authorization'})
        
        # The new /rest/api/3/search/jql endpoint uses POST with JSON body
        # instead of GET with query parameters
        response = requests.post(
            url, headers=self.headers, json=params, timeout=30
        )
        
        # Log response details
        logger.info("=" * 80)
        logger.info("JIRA API RESPONSE TRACE")
        logger.info("=" * 80)
        logger.info("Response status code: %d", response.status_code)
        logger.info("Response headers: %s", dict(response.headers))
        logger.info("Response text (first 1000 chars): %s", response.text[:1000])
        try:
            response_json = response.json()
            logger.info("Response JSON keys: %s", list(response_json.keys()) if isinstance(response_json, dict) else "Not a dict")
            if isinstance(response_json, dict):
                if "errorMessages" in response_json:
                    logger.error("JIRA Error Messages: %s", response_json.get("errorMessages"))
                if "errors" in response_json:
                    logger.error("JIRA Errors: %s", response_json.get("errors"))
        except Exception as e:
            logger.warning("Could not parse response as JSON: %s", str(e))
        logger.info("=" * 80)
        
        # Provide better error messages
        if response.status_code == 401:
            raise ValueError(
                "JIRA authentication failed. Please verify your email and "
                "API token are correct."
            )
        elif response.status_code == 400:
            # JQL syntax error or invalid project
            try:
                error_data = response.json()
                error_messages = error_data.get("errorMessages", [])
                raise ValueError(
                    f"JIRA query error: {'; '.join(error_messages)}"
                )
            except ValueError:
                raise
            except Exception:
                raise ValueError("JIRA query error: Invalid request")
        elif response.status_code == 403:
            raise ValueError(
                "JIRA access forbidden. The API token may not have "
                "permission to search issues."
            )
        elif response.status_code == 410:
            # 410 Gone - resource no longer available
            # Try to get more details from response
            error_detail = ""
            try:
                error_data = response.json()
                error_messages = error_data.get("errorMessages", [])
                if error_messages:
                    error_detail = f" Details: {'; '.join(error_messages)}"
            except Exception:
                pass
            
            # Try alternative JQL formats if the quoted format fails
            # Some JIRA instances have issues with quoted project keys
            if actual_project_key or project_numeric_id:
                logger.info(
                    "JIRA search API returned 410 for project '%s'. "
                    "Trying alternative JQL formats...",
                    actual_project_key or project_numeric_id
                )
                try:
                    # Try 1: Without quotes (for numeric IDs or certain formats)
                    if actual_project_key:
                        alt_jql = f"project = {actual_project_key}"
                        alt_params = params.copy()
                        alt_params["jql"] = alt_jql
                        alt_response = requests.post(
                            url, headers=self.headers, json=alt_params,
                            timeout=30
                        )
                        if alt_response.status_code == 200:
                            logger.info(
                                "Successfully retrieved issues using "
                                "unquoted project key format"
                            )
                            alt_data = alt_response.json()
                            alt_issues = alt_data.get("issues", [])
                            return [
                                self._parse_task(issue)
                                for issue in alt_issues
                            ]
                    
                    # Try 2: Using numeric project ID if available
                    if project_numeric_id:
                        alt_jql2 = f'project = {project_numeric_id}'
                        alt_params2 = params.copy()
                        alt_params2["jql"] = alt_jql2
                        alt_response2 = requests.post(
                            url, headers=self.headers, json=alt_params2,
                            timeout=30
                        )
                        if alt_response2.status_code == 200:
                            logger.info(
                                "Successfully retrieved issues using "
                                "numeric project ID"
                            )
                            alt_data2 = alt_response2.json()
                            alt_issues2 = alt_data2.get("issues", [])
                            return [
                                self._parse_task(issue)
                                for issue in alt_issues2
                            ]
                    
                    # Try 3: Search without project filter, then filter
                    # (as last resort - may be slow but works)
                    logger.info("Trying search without project filter...")
                    alt_jql3 = "ORDER BY created DESC"
                    alt_params3 = params.copy()
                    alt_params3["jql"] = alt_jql3
                    alt_params3["maxResults"] = 1000  # Get more results
                    alt_response3 = requests.post(
                        url, headers=self.headers, json=alt_params3,
                        timeout=30
                    )
                    if alt_response3.status_code == 200:
                        alt_data3 = alt_response3.json()
                        all_issues = alt_data3.get("issues", [])
                        # Filter by project client-side
                        filtered_issues = [
                            issue for issue in all_issues
                            if (
                                issue.get("fields", {}).get("project", {})
                                .get("key") == actual_project_key
                                or issue.get("fields", {}).get("project", {})
                                .get("id") == str(project_numeric_id)
                            )
                        ]
                        if filtered_issues:
                            logger.info(
                                "Successfully retrieved issues using "
                                "client-side filtering"
                            )
                            return [
                                self._parse_task(issue)
                                for issue in filtered_issues
                            ]
                except Exception as alt_error:
                    logger.warning(
                        "Alternative JQL formats also failed: %s",
                        str(alt_error)
                    )
            
            # All methods failed - provide detailed error with full response
            response_text = response.text if response.text else 'No response body'
            logger.error(
                "JIRA 410 error for project '%s' (tried key: %s, numeric ID: %s). "
                "Original JQL query was: %s. "
                "Full response: %s",
                project_id,
                actual_project_key,
                project_numeric_id,
                jql,
                response_text[:500]  # Log first 500 chars
            )
            
            error_msg = (
                f"JIRA project '{actual_project_key or project_id}' not "
                f"accessible (410 Gone). This could mean: (1) The project "
                f"was deleted or archived, (2) The project key doesn't match "
                f"the actual key in JIRA (check case sensitivity and "
                f"spelling), (3) You don't have permission to access this "
                f"project, or (4) The JIRA API endpoint is deprecated. "
                f"Please verify the project exists in JIRA and the project "
                f"key is correct.{error_detail}"
            )
            raise ValueError(error_msg)
        elif response.status_code == 404:
            raise ValueError(
                "JIRA project not found. Please verify the project key or "
                "ID is correct."
            )
        
        response.raise_for_status()
        
        try:
            data = response.json()
            logger.info("Parsed response JSON successfully")
            logger.info("Number of issues in response: %d", len(data.get("issues", [])))
            
            issues = data.get("issues", [])
            
            logger.info("Parsing %d issues...", len(issues))
            parsed_tasks = []
            for idx, issue in enumerate(issues):
                try:
                    task = self._parse_task(issue)
                    parsed_tasks.append(task)
                    if idx < 3:  # Log first 3 for debugging
                        logger.debug("Parsed issue %d: id=%s, title=%s", idx, task.id, task.title[:50])
                except Exception as parse_error:
                    logger.error("Error parsing issue %d: %s", idx, str(parse_error))
                    logger.error("Issue data: %s", str(issue)[:500])
                    raise
            
            logger.info("Successfully parsed %d tasks", len(parsed_tasks))
            return parsed_tasks
        except ValueError as json_error:
            logger.error("JSON parsing error: %s", str(json_error))
            logger.error("Response text: %s", response.text[:2000])
            raise
        except Exception as parse_error:
            logger.error("Error parsing response: %s", str(parse_error))
            logger.error("Response status: %d", response.status_code)
            logger.error("Response text: %s", response.text[:2000])
            raise
    
    def _parse_task(self, issue_data: Dict[str, Any]) -> PMTask:
        """Parse JIRA issue data to PMTask"""
        fields = issue_data.get("fields", {})
        
        # Extract task ID (issue key like "SCRUM-123")
        issue_key = issue_data.get("key", "")
        issue_id = issue_data.get("id", "")
        
        # Parse status
        status_obj = fields.get("status", {})
        status_name = (
            status_obj.get("name", "").lower() if status_obj else None
        )
        
        # Map JIRA status to unified status
        status_mapping = {
            "to do": "todo",
            "in progress": "in_progress",
            "done": "done",
            "completed": "completed",
            "closed": "completed",
            "resolved": "completed",
            "blocked": "blocked",
            "on hold": "on_hold",
        }
        unified_status = None
        if status_name:
            for jira_status, unified_status_value in status_mapping.items():
                if jira_status in status_name:
                    unified_status = unified_status_value
                    break
            if not unified_status:
                unified_status = status_name
        
        # Parse priority
        priority_obj = fields.get("priority", {})
        priority_name = (
            priority_obj.get("name", "").lower()
            if priority_obj else None
        )
        
        # Map JIRA priority to unified priority
        # Note: Check for longer matches first to avoid "high" matching "highest"
        priority_mapping = {
            "blocker": "highest",
            "highest": "highest",
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "low": "low",
            "lowest": "lowest",
            "trivial": "lowest",
        }
        unified_priority = None
        if priority_name:
            # Check for exact match first
            priority_name_lower = priority_name.lower()
            if priority_name_lower in priority_mapping:
                unified_priority = priority_mapping[priority_name_lower]
            else:
                # Try partial matching (check longer matches first to avoid "high" matching "highest")
                # Sort by length descending to check longer matches first
                sorted_mappings = sorted(priority_mapping.items(), key=lambda x: len(x[0]), reverse=True)
                for jira_priority, unified_priority_value in sorted_mappings:
                    if jira_priority in priority_name_lower:
                        unified_priority = unified_priority_value
                        break
            if not unified_priority:
                unified_priority = priority_name
        
        # Parse assignee
        assignee_obj = fields.get("assignee")
        assignee_id = None
        if assignee_obj:
            assignee_id = (
                assignee_obj.get("accountId") or
                assignee_obj.get("key") or
                assignee_obj.get("id")
            )
        
        # Parse project
        project_obj = fields.get("project", {})
        project_id = project_obj.get("key") or project_obj.get("id")
        
        # Parse labels
        labels = fields.get("labels", [])
        label_ids = labels if labels else None
        
        # Parse parent task (for subtasks) and epic (if parent is an epic)
        parent_obj = fields.get("parent")
        parent_task_id = None
        epic_id = None
        if parent_obj:
            parent_key = parent_obj.get("key")
            parent_id = parent_obj.get("id")
            # Check if parent is an epic
            parent_type = parent_obj.get("fields", {}).get("issuetype", {})
            parent_type_name = parent_type.get("name", "").lower()
            
            if parent_type_name == "epic":
                # Parent is an epic, set epic_id
                epic_id = parent_key or parent_id
            else:
                # Parent is a regular task/subtask, set parent_task_id
                parent_task_id = parent_key or parent_id
        
        # Parse sprint (customfield_10020)
        sprint_field = fields.get("customfield_10020")  # Sprint field
        sprint_id = None
        if sprint_field:
            # Sprint field is an array of sprint objects
            if isinstance(sprint_field, list) and len(sprint_field) > 0:
                # Take the first sprint (most recent)
                sprint_obj = sprint_field[0]
                sprint_id = str(sprint_obj.get("id")) if sprint_obj.get("id") else None
            elif isinstance(sprint_field, dict):
                # Single sprint object
                sprint_id = str(sprint_field.get("id")) if sprint_field.get("id") else None
        
        # Parse time estimates (JIRA stores in seconds)
        time_original_estimate = fields.get("timeoriginalestimate")
        estimated_hours = None
        if time_original_estimate:
            # Convert seconds to hours
            estimated_hours = time_original_estimate / 3600.0
        
        time_spent = fields.get("timespent")
        actual_hours = None
        if time_spent:
            # Convert seconds to hours
            actual_hours = time_spent / 3600.0
        
        # Parse dates
        created_str = fields.get("created")
        updated_str = fields.get("updated")
        resolution_date_str = fields.get("resolutiondate")
        due_date_str = fields.get("duedate")
        start_date_str = fields.get("startdate")
        
        # Parse description (can be plain text or ADF format)
        description = fields.get("description")
        if isinstance(description, dict):
            # ADF (Atlassian Document Format) - extract plain text if possible
            description_text = description.get("content", [])
            if description_text:
                # Try to extract text from ADF structure
                def extract_adf_text(content):
                    if isinstance(content, list):
                        return " ".join(
                            extract_adf_text(item) for item in content
                        )
                    elif isinstance(content, dict):
                        if content.get("type") == "text":
                            return content.get("text", "")
                        elif "content" in content:
                            return extract_adf_text(content["content"])
                    return ""
                description = extract_adf_text(description_text)
            else:
                description = None
        elif not description:
            description = None
        
        return PMTask(
            # Prefer key (e.g., "SCRUM-123") over numeric ID
            id=issue_key or issue_id,
            title=fields.get("summary", ""),
            description=description,
            status=unified_status,
            priority=unified_priority,
            project_id=project_id,
            parent_task_id=parent_task_id,
            epic_id=epic_id,  # Set epic_id if parent is an epic
            sprint_id=sprint_id,  # Set sprint_id from customfield_10020
            assignee_id=assignee_id,
            label_ids=label_ids,
            estimated_hours=estimated_hours,
            actual_hours=actual_hours,
            start_date=self._parse_date(start_date_str),
            due_date=self._parse_date(due_date_str),
            created_at=self._parse_datetime(created_str),
            updated_at=self._parse_datetime(updated_str),
            completed_at=self._parse_datetime(resolution_date_str),
            raw_data=issue_data
        )
    
    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[date]:
        """Parse JIRA date string (YYYY-MM-DD) to date object"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str).date()
        except (ValueError, AttributeError):
            return None
    
    async def get_task(self, task_id: str) -> Optional[PMTask]:
        """
        Get a single task by ID (key or numeric ID).
        
        TESTED: ✅ Works via /rest/api/3/issue/{key}
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/rest/api/3/issue/{task_id}"
        
        try:
            response = requests.get(
                url,
                headers=self.headers,
                params={"expand": "names,schema"},
                timeout=10
            )
            
            if response.status_code == 200:
                issue_data = response.json()
                task = self._parse_task(issue_data)
                logger.info(f"Retrieved task {task_id} from JIRA")
                return task
            elif response.status_code == 404:
                logger.warning(f"Task {task_id} not found in JIRA")
                return None
            else:
                logger.error(
                    f"Failed to get task: {response.status_code}, "
                    f"{response.text[:200]}"
                )
                response.raise_for_status()
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting task: {e}", exc_info=True)
            raise ValueError(f"Failed to get task: {str(e)}")
    
    async def create_task(self, task: PMTask) -> PMTask:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> PMTask:
        """
        Update an existing task in JIRA.
        
        Supports updating epic_id via parent field:
        - If epic_id is set, uses parent field to link to epic
        - If epic_id is None, removes parent relationship
        
        TESTED: ✅ Works via PUT /rest/api/3/issue/{key} with parent field
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/rest/api/3/issue/{task_id}"
        
        # Map updates to JIRA fields
        fields: Dict[str, Any] = {}
        
        if "title" in updates or "summary" in updates:
            fields["summary"] = updates.get("title") or updates.get("summary")
        if "description" in updates:
            desc = updates["description"]
            if desc:
                fields["description"] = {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": desc}]
                        }
                    ]
                }
            else:
                fields["description"] = None
        if "status" in updates:
            # Status updates require transitions API
            status_value = updates["status"]
            try:
                # Get available transitions
                transitions_url = f"{self.base_url}/rest/api/3/issue/{task_id}/transitions"
                trans_resp = requests.get(transitions_url, headers=self.headers, timeout=10)
                if trans_resp.status_code == 200:
                    transitions = trans_resp.json().get("transitions", [])
                    # Try to find transition by name (case-insensitive)
                    status_lower = str(status_value).lower().replace("_", " ").replace("-", " ")
                    matching_transition = None
                    for trans in transitions:
                        trans_name = trans.get("name", "").lower()
                        if trans_name == status_lower or status_lower in trans_name:
                            matching_transition = trans
                            break
                    
                    if matching_transition:
                        transition_id = matching_transition.get("id")
                        # Execute transition
                        transition_url = f"{self.base_url}/rest/api/3/issue/{task_id}/transitions"
                        transition_payload = {"transition": {"id": transition_id}}
                        transition_resp = requests.post(
                            transition_url, headers=self.headers, json=transition_payload, timeout=10
                        )
                        if transition_resp.status_code == 204:
                            logger.info(f"Status transition successful: {status_value}")
                        else:
                            logger.warning(
                                f"Failed to transition status: {transition_resp.status_code}, "
                                f"{transition_resp.text[:200]}"
                            )
                    else:
                        logger.warning(
                            f"Status transition '{status_value}' not found. "
                            f"Available: {[t.get('name') for t in transitions]}"
                        )
                else:
                    logger.warning(f"Failed to get transitions: {trans_resp.status_code}")
            except Exception as e:
                logger.warning(f"Error updating status: {e}")
        if "priority" in updates:
            # Priority updates
            priority_value = updates["priority"]
            if priority_value:
                # Try to get priority by name or ID
                try:
                    priorities_url = f"{self.base_url}/rest/api/3/priority"
                    prio_resp = requests.get(priorities_url, headers=self.headers, timeout=10)
                    if prio_resp.status_code == 200:
                        priorities = prio_resp.json()
                        # Priority name mapping
                        # Note: Order matters - check longer names first to avoid "high" matching "highest"
                        priority_name_mapping = {
                            "lowest": ["lowest", "trivial"],
                            "low": ["low", "minor"],
                            "medium": ["medium", "normal"],
                            "highest": ["highest", "critical", "blocker"],  # Check "highest" before "high"
                            "high": ["high", "major"],
                            "critical": ["critical", "highest", "blocker"]
                        }
                        
                        priority_lower = str(priority_value).lower()
                        matching_priority = None
                        
                        # First try exact match by name (case-insensitive)
                        # IMPORTANT: Sort by name length (longest first) to prefer "Highest" over "High"
                        sorted_priorities_exact = sorted(priorities, key=lambda p: len(p.get("name", "")), reverse=True)
                        for prio in sorted_priorities_exact:
                            prio_name_lower = prio.get("name", "").lower()
                            if prio_name_lower == priority_lower:
                                matching_priority = prio
                                break
                        
                        # If no exact match, try mapping
                        # IMPORTANT: When checking priorities, we need to ensure longer names are checked first
                        # to avoid "high" matching when we're looking for "highest"
                        if not matching_priority and priority_lower in priority_name_mapping:
                            possible_names = priority_name_mapping[priority_lower]
                            
                            # For "highest", check priorities in order: "highest" first, then "critical", then "blocker"
                            # This ensures we don't accidentally match "high" if it exists
                            if priority_lower == "highest":
                                # Sort priorities by name length (longest first) to prefer "highest" over "high"
                                sorted_priorities = sorted(priorities, key=lambda p: len(p.get("name", "")), reverse=True)
                                for possible_name in possible_names:
                                    for prio in sorted_priorities:
                                        prio_name_lower = prio.get("name", "").lower()
                                        # Exact match only
                                        if prio_name_lower == possible_name.lower():
                                            matching_priority = prio
                                            break
                                    if matching_priority:
                                        break
                            else:
                                # For other priorities, use normal matching
                                for possible_name in possible_names:
                                    for prio in priorities:
                                        prio_name_lower = prio.get("name", "").lower()
                                        if prio_name_lower == possible_name.lower():
                                            matching_priority = prio
                                            break
                                    if matching_priority:
                                        break
                        
                        # If still no match, try partial/fuzzy matching (but be careful with "high" vs "highest")
                        if not matching_priority:
                            # For "highest", avoid matching "high" by checking for longer match first
                            if priority_lower == "highest":
                                # Try to find priorities that contain "highest" (not just "high")
                                for prio in priorities:
                                    prio_name_lower = prio.get("name", "").lower()
                                    if "highest" in prio_name_lower or prio_name_lower == "highest":
                                        matching_priority = prio
                                        break
                            else:
                                # For other priorities, try partial matching
                                # But avoid matching shorter strings when looking for longer ones
                                # (e.g., don't match "high" when looking for "highest")
                                for prio in priorities:
                                    prio_name_lower = prio.get("name", "").lower()
                                    # Only match if the priority name is at least as long as what we're looking for
                                    # This prevents "high" from matching when we're looking for "highest"
                                    if len(prio_name_lower) >= len(priority_lower):
                                        if priority_lower in prio_name_lower:
                                            matching_priority = prio
                                            break
                                    elif len(priority_lower) >= len(prio_name_lower):
                                        # If what we're looking for is longer, check if the priority name is contained in it
                                        if prio_name_lower in priority_lower:
                                            matching_priority = prio
                                            break
                        
                        if matching_priority:
                            fields["priority"] = {"id": str(matching_priority.get("id"))}
                        elif str(priority_value).isdigit():
                            # Use as ID directly
                            fields["priority"] = {"id": str(priority_value)}
                        else:
                            available_priorities = [p.get("name") for p in priorities]
                            logger.warning(
                                f"Priority '{priority_value}' not found. "
                                f"Available priorities: {available_priorities}. "
                                f"Tried: exact match, mapping, and partial match."
                            )
                    else:
                        # If can't fetch priorities, try using as ID
                        if str(priority_value).isdigit():
                            fields["priority"] = {"id": str(priority_value)}
                except Exception as e:
                    logger.warning(f"Error looking up priority: {e}")
                    # Fallback: try using as ID
                    if str(priority_value).isdigit():
                        fields["priority"] = {"id": str(priority_value)}
            else:
                fields["priority"] = None
        if "assignee_id" in updates:
            assignee_id = updates["assignee_id"]
            if assignee_id:
                fields["assignee"] = {"accountId": assignee_id}
            else:
                fields["assignee"] = None
        if "epic_id" in updates:
            # Epic assignment via parent field
            epic_id = updates["epic_id"]
            if epic_id:
                fields["parent"] = {"key": epic_id}
            else:
                fields["parent"] = None
        if "sprint_id" in updates:
            # Sprint assignment uses Agile API, not direct field update
            # We'll handle this separately after the standard update
            sprint_id = updates["sprint_id"]
            sprint_updates_applied = False
            if sprint_id:
                # Assign to sprint using Agile API
                try:
                    sprint_url = f"{self.base_url}/rest/agile/1.0/sprint/{sprint_id}/issue"
                    sprint_payload = {"issues": [task_id]}
                    sprint_resp = requests.post(
                        sprint_url, headers=self.headers, json=sprint_payload, timeout=10
                    )
                    if sprint_resp.status_code == 204:
                        sprint_updates_applied = True
                        logger.info(f"Assigned task {task_id} to sprint {sprint_id}")
                    else:
                        logger.warning(
                            f"Failed to assign to sprint via Agile API: "
                            f"{sprint_resp.status_code}, {sprint_resp.text[:200]}"
                        )
                except Exception as e:
                    logger.warning(f"Error assigning to sprint: {e}")
            else:
                # Move to backlog using Agile API
                try:
                    backlog_url = f"{self.base_url}/rest/agile/1.0/backlog/issue"
                    backlog_payload = {"issues": [task_id]}
                    backlog_resp = requests.post(
                        backlog_url, headers=self.headers, json=backlog_payload, timeout=10
                    )
                    if backlog_resp.status_code == 204:
                        sprint_updates_applied = True
                        logger.info(f"Moved task {task_id} to backlog")
                    else:
                        logger.warning(
                            f"Failed to move to backlog: "
                            f"{backlog_resp.status_code}, {backlog_resp.text[:200]}"
                        )
                except Exception as e:
                    logger.warning(f"Error moving to backlog: {e}")
            
            if sprint_updates_applied:
                # If sprint update was successful, fetch updated task
                updated_task = await self.get_task(task_id)
                if updated_task:
                    return updated_task
                else:
                    raise ValueError("Failed to retrieve updated task after sprint assignment")
        
        if "due_date" in updates:
            due_date = updates["due_date"]
            if due_date:
                # JIRA expects YYYY-MM-DD format
                if isinstance(due_date, str):
                    fields["duedate"] = due_date
                elif hasattr(due_date, "isoformat"):
                    fields["duedate"] = due_date.isoformat()
                else:
                    fields["duedate"] = str(due_date)
            else:
                fields["duedate"] = None
        
        if "start_date" in updates:
            start_date = updates["start_date"]
            if start_date:
                # JIRA expects YYYY-MM-DD format
                if isinstance(start_date, str):
                    fields["startdate"] = start_date
                elif hasattr(start_date, "isoformat"):
                    fields["startdate"] = start_date.isoformat()
                else:
                    fields["startdate"] = str(start_date)
            else:
                fields["startdate"] = None
        
        if "estimated_hours" in updates:
            hours = updates["estimated_hours"]
            if hours is None or hours == 0:
                fields["timeoriginalestimate"] = None
            elif hours:
                # Convert hours to seconds
                seconds = int(float(hours) * 3600)
                fields["timeoriginalestimate"] = seconds
        
        if "actual_hours" in updates:
            hours = updates["actual_hours"]
            if hours is None or hours == 0:
                fields["timespent"] = None
            elif hours:
                # Convert hours to seconds
                # Note: timespent may be read-only, but we'll try
                seconds = int(float(hours) * 3600)
                fields["timespent"] = seconds
        
        if "parent_task_id" in updates:
            parent_id = updates["parent_task_id"]
            if parent_id:
                fields["parent"] = {"key": parent_id}
            else:
                fields["parent"] = None
        
        if "label_ids" in updates:
            labels = updates["label_ids"]
            if labels is None:
                fields["labels"] = []
            elif isinstance(labels, list):
                # JIRA labels are just strings
                fields["labels"] = [str(label) for label in labels]
            else:
                fields["labels"] = [str(labels)]
        
        if not fields:
            # No updates to apply, just return the current task
            task = await self.get_task(task_id)
            if task:
                return task
            else:
                raise ValueError(f"Task {task_id} not found")
        
        payload = {"fields": fields}
        logger.info(f"[JIRA update_task] Sending payload with fields: {list(fields.keys())}")
        
        try:
            response = requests.put(
                url, headers=self.headers, json=payload, timeout=10
            )
            
            if response.status_code == 204:
                # Fetch updated task
                updated_task = await self.get_task(task_id)
                if updated_task:
                    return updated_task
                else:
                    raise ValueError("Failed to retrieve updated task")
            else:
                logger.error(
                    f"Failed to update task: {response.status_code}, "
                    f"{response.text[:200]}"
                )
                raise ValueError(
                    f"Failed to update task: ({response.status_code}) "
                    f"{response.text[:200]}"
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating task: {e}", exc_info=True)
            raise ValueError(f"Failed to update task: {str(e)}")
    
    async def delete_task(self, task_id: str) -> bool:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def list_sprints(
        self, project_id: Optional[str] = None, state: Optional[str] = None
    ) -> List[PMSprint]:
        """
        List all sprints for a project, optionally filtered by state.
        
        JIRA API: /rest/agile/1.0/board/{boardId}/sprint
        Supports state filter: "active", "closed", "future", or None for all
        
        TESTED: ✅ Works with state filtering
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # First, get boards for the project
            boards_url = f"{self.base_url}/rest/agile/1.0/board"
            params = {}
            
            if project_id:
                # Try to use project_id as projectKeyOrId
                # Could be numeric ID or project key (e.g., "SCRUM")
                params['projectKeyOrId'] = project_id
            
            response = requests.get(boards_url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                boards = data.get('values', [])
                
                if not boards:
                    logger.warning(f"No boards found for project: {project_id}")
                    return []
                
                # Get sprints from the first board (or all boards if project_id not specified)
                all_sprints = []
                
                for board in boards:
                    board_id = board.get('id')
                    if not board_id:
                        continue
                    
                    sprints_url = f"{self.base_url}/rest/agile/1.0/board/{board_id}/sprint"
                    
                    # Add state filter if specified
                    sprint_params = {}
                    if state:
                        sprint_params['state'] = state
                    
                    sprint_response = requests.get(
                        sprints_url, 
                        headers=self.headers, 
                        params=sprint_params if sprint_params else None,
                        timeout=10
                    )
                    
                    if sprint_response.status_code == 200:
                        sprint_data = sprint_response.json()
                        board_sprints = sprint_data.get('values', [])
                        all_sprints.extend(board_sprints)
                        logger.info(
                            f"Found {len(board_sprints)} sprints from board {board_id} "
                            f"(state={state or 'all'})"
                        )
                    else:
                        logger.warning(
                            f"Failed to get sprints from board {board_id}: "
                            f"{sprint_response.status_code}"
                        )
                
                # Convert to PMSprint objects
                sprints = []
                for s in all_sprints:
                    sprint = PMSprint(
                        id=str(s.get('id')),
                        name=s.get('name', ''),
                        project_id=project_id,
                        start_date=self._parse_date(s.get('startDate')),
                        end_date=self._parse_date(s.get('endDate')),
                        status=s.get('state'),  # active, closed, future
                        goal=s.get('goal'),
                        created_at=self._parse_datetime(s.get('createdDate')),
                        updated_at=self._parse_datetime(s.get('updatedDate')),
                        raw_data=s
                    )
                    sprints.append(sprint)
                
                logger.info(f"Returning {len(sprints)} sprints (state={state or 'all'})")
                return sprints
            else:
                logger.error(
                    f"Failed to get boards: {response.status_code}, "
                    f"{response.text[:200]}"
                )
                raise ValueError(
                    f"Failed to get boards: ({response.status_code}) "
                    f"{response.text[:200]}"
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing sprints: {e}", exc_info=True)
            raise ValueError(f"Failed to list sprints: {str(e)}")
    
    async def get_sprint(self, sprint_id: str) -> Optional[PMSprint]:
        """
        Fetch a single sprint by ID using the JIRA Agile API.

        JIRA API: /rest/agile/1.0/sprint/{sprintId}
        """
        import logging

        logger = logging.getLogger(__name__)
        url = f"{self.base_url}/rest/agile/1.0/sprint/{sprint_id}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
        except requests.exceptions.RequestException as exc:
            logger.error("Error retrieving JIRA sprint %s: %s", sprint_id, exc, exc_info=True)
            raise ValueError(f"Failed to fetch sprint {sprint_id}: {exc}") from exc

        if response.status_code == 404:
            logger.info("JIRA sprint %s not found", sprint_id)
            return None

        response.raise_for_status()
        sprint_data = response.json()

        # Attempt to enrich with project context by inspecting the origin board.
        project_id: Optional[str] = None
        origin_board_id = sprint_data.get("originBoardId")

        if origin_board_id:
            board_url = f"{self.base_url}/rest/agile/1.0/board/{origin_board_id}"
            try:
                board_resp = requests.get(board_url, headers=self.headers, timeout=10)
                if board_resp.status_code == 200:
                    board_data = board_resp.json()
                    location = board_data.get("location") or {}
                    project_id = (
                        location.get("projectKey")
                        or location.get("projectId")
                        or board_data.get("location", {}).get("projectKey")
                    )
                    if not project_id:
                        project_keys = board_data.get("projectKeys")
                        if isinstance(project_keys, list) and project_keys:
                            project_id = project_keys[0]
                else:
                    logger.warning(
                        "Unable to resolve project for sprint %s via board %s: status=%s",
                        sprint_id,
                        origin_board_id,
                        board_resp.status_code,
                    )
            except requests.exceptions.RequestException as exc:
                logger.warning(
                    "Failed to fetch board %s for sprint %s: %s",
                    origin_board_id,
                    sprint_id,
                    exc,
                )

        return PMSprint(
            id=str(sprint_data.get("id")),
            name=sprint_data.get("name", ""),
            project_id=str(project_id) if project_id else None,
            start_date=self._parse_date(sprint_data.get("startDate")),
            end_date=self._parse_date(sprint_data.get("endDate")),
            status=sprint_data.get("state"),
            goal=sprint_data.get("goal"),
            created_at=self._parse_datetime(sprint_data.get("createdDate")),
            updated_at=self._parse_datetime(sprint_data.get("updatedDate")),
            raw_data=sprint_data,
        )
    
    async def create_sprint(self, sprint: PMSprint) -> PMSprint:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def update_sprint(self, sprint_id: str, updates: Dict) -> PMSprint:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def delete_sprint(self, sprint_id: str) -> bool:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def list_users(
        self, project_id: Optional[str] = None
    ) -> List[PMUser]:
        """
        List users from JIRA.
        If project_id is provided, lists assignable users for that project.
        Otherwise, lists all users (requires admin permissions).
        """
        import logging
        _logger = logging.getLogger(__name__)
        
        try:
            if project_id:
                # List assignable users for a project
                # JIRA API: GET /rest/api/3/user/assignable/search?project={projectKey}
                url = f"{self.base_url}/rest/api/3/user/assignable/search"
                params = {"project": project_id}
            else:
                # List all users (requires admin permissions)
                # JIRA API: GET /rest/api/3/users/search
                url = f"{self.base_url}/rest/api/3/users/search"
                params = {}
            
            _logger.info("Fetching users from JIRA: %s (project_id=%s)", url, project_id)
            
            response = requests.get(
                url, headers=self.headers, params=params, timeout=10
            )
            
            _logger.info("JIRA list_users response: status=%d", response.status_code)
            
            if response.status_code == 200:
                users_data = response.json()
                _logger.info("JIRA users data: %d users found", len(users_data))
                
                users = []
                for user_data in users_data:
                    # JIRA returns user info with accountId as the unique identifier
                    account_id = user_data.get("accountId") or user_data.get("key")
                    email = user_data.get("emailAddress")
                    display_name = user_data.get("displayName") or user_data.get("name", "")
                    avatar_url = user_data.get("avatarUrls", {}).get("48x48") if user_data.get("avatarUrls") else None
                    
                    user_id = account_id or email or display_name
                    if not user_id:
                        _logger.warning("JIRA user data missing all ID fields. User data: %s", str(user_data)[:200])
                        continue
                    
                    users.append(PMUser(
                        id=user_id,
                        name=display_name,
                        email=email,
                        username=user_data.get("name") or email,
                        avatar_url=avatar_url,
                        raw_data=user_data
                    ))
                
                return users
            elif response.status_code == 401:
                _logger.error("JIRA authentication failed (401)")
                raise ValueError("JIRA authentication failed. Please check your credentials.")
            elif response.status_code == 403:
                _logger.error("JIRA permission denied (403)")
                raise ValueError("JIRA permission denied. You may need admin permissions to list users.")
            else:
                _logger.error("JIRA list_users failed: status=%d, response=%s", response.status_code, response.text[:500])
                response.raise_for_status()
                return []
        except requests.exceptions.RequestException as e:
            _logger.error("JIRA list_users request failed: %s", str(e))
            raise ValueError(f"Failed to fetch users from JIRA: {str(e)}")
    
    async def get_user(self, user_id: str) -> Optional[PMUser]:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def get_current_user(self) -> Optional[PMUser]:
        """
        Get the current authenticated user from JIRA.
        Uses the /rest/api/3/myself endpoint.
        """
        import logging
        _logger = logging.getLogger(__name__)
        
        try:
            url = f"{self.base_url}/rest/api/3/myself"
            
            _logger.info("Fetching current user from JIRA: %s", url)
            
            response = requests.get(
                url, headers=self.headers, timeout=10
            )
            
            _logger.info("JIRA get_current_user response: status=%d", response.status_code)
            
            if response.status_code == 200:
                user_data = response.json()
                _logger.info("JIRA user data: %s", str(user_data)[:200])
                
                # JIRA returns user info with accountId as the unique identifier
                account_id = user_data.get("accountId") or user_data.get("key")
                email = user_data.get("emailAddress")
                display_name = user_data.get("displayName") or user_data.get("name", "")
                
                user_id = account_id or email or display_name
                if not user_id:
                    _logger.warning("JIRA user data missing all ID fields. User data: %s", str(user_data)[:200])
                    return None
                
                _logger.info("JIRA current user: id=%s, name=%s, email=%s", user_id, display_name, email)
                
                return PMUser(
                    id=user_id,
                    name=display_name,
                    email=email,
                    raw_data=user_data
                )
            elif response.status_code == 401:
                _logger.warning(
                    "JIRA authentication failed when getting current user. "
                    "Status: %d, Response: %s",
                    response.status_code,
                    response.text[:200]
                )
                return None
            else:
                _logger.warning(
                    "Failed to get current user from JIRA. Status: %d, Response: %s",
                    response.status_code,
                    response.text[:200]
                )
                return None
        except Exception as e:
            _logger.error(
                "Error getting current user from JIRA: %s",
                str(e),
                exc_info=True
            )
            return None
    
    async def health_check(self) -> bool:
        """Check if JIRA connection is healthy"""
        try:
            url = f"{self.base_url}/rest/api/3/myself"
            response = requests.get(url, headers=self.headers, timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    # ==================== Epic Operations ====================
    
    async def list_epics(self, project_id: Optional[str] = None) -> List[PMEpic]:
        """
        List all epics, optionally filtered by project.
        
        TESTED: ✅ Works via /rest/api/3/search/jql with issuetype = Epic
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/rest/api/3/search/jql"
        
        # Build JQL query for epics
        jql_parts = ['issuetype = Epic']
        if project_id:
            # Verify project and get actual key
            project = await self.get_project(project_id)
            if project:
                actual_project_key = project.id
            else:
                actual_project_key = project_id
            
            jql_parts.append(f'project = "{actual_project_key}"')
        
        jql = " AND ".join(jql_parts)
        
        params = {
            "jql": jql,
            "maxResults": 1000,
            "fields": [
                "summary", "description", "status", "priority",
                "project", "created", "updated", "duedate", "startdate"
            ],
            "expand": "names,schema"
        }
        
        try:
            response = requests.post(
                url, headers=self.headers, json=params, timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                issues = data.get('issues', [])
                
                epics = []
                for issue in issues:
                    fields = issue.get('fields', {})
                    status_obj = fields.get('status', {})
                    priority_obj = fields.get('priority', {})
                    
                    # Parse description (can be ADF format or string)
                    description = fields.get('description')
                    if isinstance(description, dict):
                        # ADF (Atlassian Document Format) - extract plain text if possible
                        description_text = description.get("content", [])
                        if description_text:
                            def extract_adf_text(content):
                                if isinstance(content, list):
                                    return " ".join(
                                        extract_adf_text(item) for item in content
                                    )
                                elif isinstance(content, dict):
                                    if content.get("type") == "text":
                                        return content.get("text", "")
                                    elif "content" in content:
                                        return extract_adf_text(content["content"])
                                return ""
                            description = extract_adf_text(description_text)
                        else:
                            description = None
                    elif not description:
                        description = None
                    
                    epic = PMEpic(
                        id=issue.get('key'),
                        name=fields.get('summary', ''),
                        description=description,
                        project_id=fields.get('project', {}).get('key'),
                        status=status_obj.get('name') if status_obj else None,
                        priority=priority_obj.get('name') if priority_obj else None,
                        start_date=self._parse_date(fields.get('startdate')),
                        end_date=self._parse_date(fields.get('duedate')),
                        created_at=self._parse_datetime(fields.get('created')),
                        updated_at=self._parse_datetime(fields.get('updated')),
                        raw_data=issue
                    )
                    epics.append(epic)
                
                logger.info(f"Found {len(epics)} epics from JIRA")
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
        Get a single epic by ID (key or numeric ID).
        
        TESTED: ✅ Works via /rest/api/3/issue/{key}
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/rest/api/3/issue/{epic_id}"
        
        try:
            response = requests.get(
                url,
                headers=self.headers,
                params={"expand": "names,schema"},
                timeout=10
            )
            
            if response.status_code == 200:
                issue = response.json()
                fields = issue.get('fields', {})
                status_obj = fields.get('status', {})
                priority_obj = fields.get('priority', {})
                
                # Parse description (can be ADF format or string)
                description = fields.get('description')
                if isinstance(description, dict):
                    # ADF (Atlassian Document Format) - extract plain text if possible
                    description_text = description.get("content", [])
                    if description_text:
                        def extract_adf_text(content):
                            if isinstance(content, list):
                                return " ".join(
                                    extract_adf_text(item) for item in content
                                )
                            elif isinstance(content, dict):
                                if content.get("type") == "text":
                                    return content.get("text", "")
                                elif "content" in content:
                                    return extract_adf_text(content["content"])
                            return ""
                        description = extract_adf_text(description_text)
                    else:
                        description = None
                elif not description:
                    description = None
                
                epic = PMEpic(
                    id=issue.get('key'),
                    name=fields.get('summary', ''),
                    description=description,
                    project_id=fields.get('project', {}).get('key'),
                    status=status_obj.get('name') if status_obj else None,
                    priority=priority_obj.get('name') if priority_obj else None,
                    start_date=self._parse_date(fields.get('startdate')),
                    end_date=self._parse_date(fields.get('duedate')),
                    created_at=self._parse_datetime(fields.get('created')),
                    updated_at=self._parse_datetime(fields.get('updated')),
                    raw_data=issue
                )
                
                logger.info(f"Retrieved epic {epic_id} from JIRA")
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
        Create a new epic in JIRA.
        
        TESTED: ✅ Works via /rest/api/3/issue with issuetype = Epic
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not epic.project_id:
            raise ValueError("project_id is required to create an epic")
        
        url = f"{self.base_url}/rest/api/3/issue"
        
        # Build fields payload
        fields: Dict[str, Any] = {
            "project": {"key": epic.project_id},
            "summary": epic.name,
            "issuetype": {"name": "Epic"}
        }
        
        # Add description if provided
        if epic.description:
            # JIRA uses ADF (Atlassian Document Format) for rich text
            # For simplicity, we'll use plain text wrapped in ADF format
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": epic.description
                            }
                        ]
                    }
                ]
            }
        
        # Add dates if provided (only if fields are available for epics)
        # Note: Some JIRA instances may not have startdate/duedate for epics
        # We'll try to set them, but if they fail, we'll continue without them
        if epic.end_date:
            fields["duedate"] = epic.end_date.isoformat()
        # startdate is often not available for epics, so we skip it
        
        payload = {"fields": fields}
        
        try:
            response = requests.post(
                url, headers=self.headers, json=payload, timeout=10
            )
            
            if response.status_code == 201:
                created_issue = response.json()
                epic_key = created_issue.get('key')
                
                # Fetch the full epic to return complete data
                created_epic = await self.get_epic(epic_key)
                if created_epic:
                    logger.info(f"Created epic {epic_key} in JIRA")
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
        Update an existing epic in JIRA.
        
        TESTED: ✅ Works via PUT /rest/api/3/issue/{key}
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/rest/api/3/issue/{epic_id}"
        
        # Map updates to JIRA fields
        fields: Dict[str, Any] = {}
        
        if "name" in updates:
            fields["summary"] = updates["name"]
        if "description" in updates:
            desc = updates["description"]
            if desc:
                fields["description"] = {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": desc}]
                        }
                    ]
                }
            else:
                fields["description"] = None
        if "start_date" in updates:
            fields["startdate"] = (
                updates["start_date"].isoformat()
                if updates["start_date"]
                else None
            )
        if "end_date" in updates:
            fields["duedate"] = (
                updates["end_date"].isoformat()
                if updates["end_date"]
                else None
            )
        if "status" in updates:
            # Status transition requires special handling
            # For now, we'll just log a warning
            logger.warning(
                "Status updates require transitions API, not implemented yet"
            )
        
        if not fields:
            # No updates to apply, just return the current epic
            return await self.get_epic(epic_id) or PMEpic()
        
        payload = {"fields": fields}
        
        try:
            response = requests.put(
                url, headers=self.headers, json=payload, timeout=10
            )
            
            if response.status_code == 204:
                # Fetch updated epic
                updated_epic = await self.get_epic(epic_id)
                if updated_epic:
                    logger.info(f"Updated epic {epic_id} in JIRA")
                    return updated_epic
                else:
                    raise ValueError("Failed to retrieve updated epic")
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
        Delete an epic in JIRA.
        
        TESTED: ✅ Works via DELETE /rest/api/3/issue/{key}
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/rest/api/3/issue/{epic_id}"
        
        try:
            response = requests.delete(url, headers=self.headers, timeout=10)
            
            if response.status_code == 204:
                logger.info(f"Deleted epic {epic_id} from JIRA")
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
        
        TESTED: ✅ Works via /rest/api/3/search/jql with labels IS NOT EMPTY
        Returns empty list if project has no labels (endpoint works correctly)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/rest/api/3/search/jql"
        
        # Build JQL query to find issues with labels
        jql_parts = ['labels IS NOT EMPTY']
        if project_id:
            project = await self.get_project(project_id)
            if project:
                actual_project_key = project.id
            else:
                actual_project_key = project_id
            
            jql_parts.append(f'project = "{actual_project_key}"')
        
        jql = " AND ".join(jql_parts)
        
        params = {
            "jql": jql,
            "maxResults": 1000,
            "fields": ["labels"],
            "expand": "names"
        }
        
        try:
            response = requests.post(
                url, headers=self.headers, json=params, timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                issues = data.get('issues', [])
                
                # Extract unique labels
                labels_set = set()
                for issue in issues:
                    fields = issue.get('fields', {})
                    labels = fields.get('labels', [])
                    if isinstance(labels, list):
                        for label_name in labels:
                            if label_name:
                                labels_set.add(label_name)
                
                # Convert to PMLabel objects
                labels = []
                for label_name in sorted(labels_set):
                    label = PMLabel(
                        id=label_name,
                        name=label_name,
                        color=None,
                        description=None,
                        project_id=project_id if project_id else None,
                        raw_data={"name": label_name}
                    )
                    labels.append(label)
                
                logger.info(f"Found {len(labels)} unique labels from JIRA")
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
        raise NotImplementedError("Labels not yet implemented for JIRA")
    
    async def create_label(self, label: PMLabel) -> PMLabel:
        """Create a new label"""
        raise NotImplementedError("Labels not yet implemented for JIRA")
    
    async def update_label(self, label_id: str, updates: Dict[str, Any]) -> PMLabel:
        """Update an existing label"""
        raise NotImplementedError("Labels not yet implemented for JIRA")
    
    async def delete_label(self, label_id: str) -> bool:
        """Delete a label"""
        raise NotImplementedError("Labels not yet implemented for JIRA")
    
    # ==================== Status Operations ====================
    
    async def list_statuses(self, entity_type: str, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of available statuses for an entity type.
        
        TESTED: ✅ Works via /rest/api/3/status endpoint
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Use global statuses endpoint (tested and working)
        url = f"{self.base_url}/rest/api/3/status"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                statuses = []
                for status in data:
                    if isinstance(status, dict):
                        status_id = str(status.get('id', ''))
                        status_name = status.get('name', '')
                        # Get color from statusCategory
                        status_category = status.get('statusCategory', {})
                        color_name = status_category.get('colorName', '')
                        # Map color names to hex codes
                        color_map = {
                            'blue-gray': '#6b778c',
                            'yellow': '#f4c430',
                            'green': '#00b894',
                            'red': '#d04437',
                            'medium-gray': '#97a0af'
                        }
                        color = color_map.get(color_name.lower(), '')
                        
                        if status_id and status_name:
                            statuses.append({
                                "id": status_id,
                                "name": status_name,
                                "color": color,
                                "description": status.get('description', ''),
                                "category": status_category.get('name', ''),
                            })
                
                logger.info(f"Found {len(statuses)} statuses from JIRA")
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
        
        TESTED: ✅ Works via /rest/api/3/priority endpoint
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/rest/api/3/priority"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                priorities = []
                for priority in data:
                    if isinstance(priority, dict):
                        priority_id = str(priority.get('id', ''))
                        priority_name = priority.get('name', '')
                        color = priority.get('statusColor', '')
                        
                        if priority_id and priority_name:
                            priorities.append({
                                "id": priority_id,
                                "name": priority_name,
                                "color": color,
                                "description": priority.get('description', ''),
                            })
                
                logger.info(f"Found {len(priorities)} priorities from JIRA")
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

