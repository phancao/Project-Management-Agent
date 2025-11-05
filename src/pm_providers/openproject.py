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
        """List all projects from OpenProject"""
        url = f"{self.base_url}/api/v3/projects"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        projects_data = response.json()["_embedded"]["elements"]
        return [self._parse_project(proj) for proj in projects_data]
    
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
        """List all work packages (tasks)"""
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
        
        if filters:
            params = {"filters": json_lib.dumps(filters)}
            logger.info(f"OpenProject list_tasks with filters: {params}")
        else:
            params = {}
        
        response = requests.get(url, headers=self.headers, params=params)
        
        # Log if filter returns no results
        if assignee_id:
            try:
                result = response.json()
                task_count = len(
                    result.get("_embedded", {}).get("elements", [])
                )
                if task_count == 0:
                    logger.warning(
                        f"Assignee filter returned 0 tasks for "
                        f"user_id={assignee_id}. Response: "
                        f"{result.get('count', 'N/A')} total"
                    )
            except Exception:
                pass
        
        response.raise_for_status()
        
        tasks_data = response.json()["_embedded"]["elements"]
        return [self._parse_task(task) for task in tasks_data]
    
    async def get_task(self, task_id: str) -> Optional[PMTask]:
        """Get a single work package by ID"""
        url = f"{self.base_url}/api/v3/work_packages/{task_id}"
        response = requests.get(url, headers=self.headers)
        
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
        url = f"{self.base_url}/api/v3/work_packages/{task_id}"
        payload: Dict[str, Any] = {}
        
        # Get lockVersion from form to prevent conflicts
        form_url = f"{self.base_url}/api/v3/work_packages/{task_id}/form"
        form_response = requests.post(form_url, headers=self.headers)
        form_response.raise_for_status()
        lock_version = (
            form_response.json()
            .get("_embedded", {})
            .get("payload", {})
            .get("lockVersion")
        )
        if lock_version is not None:
            payload["lockVersion"] = lock_version
        
        if "title" in updates or "subject" in updates:
            payload["subject"] = updates.get("title") or updates.get("subject")
        if "description" in updates:
            payload["description"] = {
                "raw": updates["description"],
                "format": "plain"
            }
        if "status" in updates:
            payload["_links"] = {
                "status": {
                    "href": f"/api/v3/statuses/{updates['status']}"
                }
            }
        if "assignee_id" in updates:
            payload["_links"] = {
                **payload.get("_links", {}),
                "assignee": {
                    "href": f"/api/v3/users/{updates['assignee_id']}"
                }
            }
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
        
        response = requests.patch(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return self._parse_task(response.json())
    
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
        
        url = f"{self.base_url}/api/v3/versions"
        
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        
        sprints_data = response.json()["_embedded"]["elements"]
        
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
        """List all users"""
        url = f"{self.base_url}/api/v3/users"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        users_data = response.json()["_embedded"]["elements"]
        return [self._parse_user(user) for user in users_data]
    
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
        
        return PMTask(
            id=str(data["id"]),
            title=data.get("subject", ""),
            description=(
                data.get("description", {}).get("raw")
                if isinstance(data.get("description"), dict)
                else data.get("description")
            ),
            status=(
                embedded.get("status", {}).get("name")
                if embedded.get("status") else None
            ),
            project_id=self._extract_id_from_href(
                links.get("project", {}).get("href")
            ),
            assignee_id=self._extract_id_from_href(
                links.get("assignee", {}).get("href")
            ),
            estimated_hours=self._parse_duration_to_hours(
                data.get("estimatedTime")
            ),
            actual_hours=self._parse_duration_to_hours(
                data.get("derivedRemainingTime")
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
            "pageSize": 100
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                work_packages = data.get('_embedded', {}).get('elements', [])
                
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
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/api/v3/work_packages/{epic_id}"
        
        # Map updates to OpenProject fields
        payload: Dict[str, Any] = {}
        
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
        
        if not payload:
            # No updates to apply, just return the current epic
            return await self.get_epic(epic_id) or PMEpic()
        
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
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                work_packages = data.get('_embedded', {}).get('elements', [])
                
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
    
    async def list_statuses(self, entity_type: str, project_id: Optional[str] = None) -> List[str]:
        """
        Get list of available statuses for an entity type.
        
        TESTED: ✅ Works via /api/v3/statuses endpoint
        """
        import logging
        logger = logging.getLogger(__name__)
        
        url = f"{self.base_url}/api/v3/statuses"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                elements = data.get('_embedded', {}).get('elements', [])
                
                statuses = []
                for status in elements:
                    if isinstance(status, dict):
                        status_name = status.get('name')
                        if status_name:
                            statuses.append(status_name)
                
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

