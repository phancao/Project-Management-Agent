"""
OpenProject Provider

Connects to OpenProject (https://www.openproject.org/) API
to manage projects, work packages (tasks), and sprints.
"""
import os
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from .base import BasePMProvider
from .models import (
    PMUser, PMProject, PMTask, PMSprint,
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
        
        if not self.api_key:
            raise ValueError("OpenProject requires api_key or api_token")
        
        # OpenProject requires Basic auth with base64(apikey:API_KEY)
        import base64
        auth_string = f"apikey:{self.api_key}"
        auth_bytes = auth_string.encode('utf-8')
        auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_b64}"
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
    
    async def update_project(self, project_id: str, updates: Dict[str, Any]) -> PMProject:
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
    
    async def list_tasks(self, project_id: Optional[str] = None, assignee_id: Optional[str] = None) -> List[PMTask]:
        """List all work packages (tasks)"""
        url = f"{self.base_url}/api/v3/work_packages"
        
        # Build filters for project and/or assignee
        import json as json_lib
        import logging
        logger = logging.getLogger(__name__)
        
        filters = []
        if project_id:
            filters.append({"project": {"operator": "=", "values": [project_id]}})
        if assignee_id:
            filters.append({"assignee": {"operator": "=", "values": [assignee_id]}})
        
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
                task_count = len(result.get("_embedded", {}).get("elements", []))
                if task_count == 0:
                    logger.warning(f"Assignee filter returned 0 tasks for user_id={assignee_id}. Response: {result.get('count', 'N/A')} total")
            except:
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
        payload = {
            "_links": {
                "type": {
                    "href": "/api/v3/types/1"  # Task type - may need to be configurable
                }
            }
        }
        
        if task.project_id:
            payload["_links"]["project"] = {"href": f"/api/v3/projects/{task.project_id}"}
        if task.title:
            payload["subject"] = task.title
        if task.description:
            payload["description"] = {
                "raw": task.description,
                "format": "plain"
            }
        if task.assignee_id:
            payload["_links"]["assignee"] = {"href": f"/api/v3/users/{task.assignee_id}"}
        if task.status:
            payload["_links"]["status"] = {"href": f"/api/v3/statuses/{task.status}"}
        
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return self._parse_task(response.json())
    
    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> PMTask:
        """Update an existing work package"""
        url = f"{self.base_url}/api/v3/work_packages/{task_id}"
        payload = {}
        
        # Get lockVersion from form to prevent conflicts
        form_url = f"{self.base_url}/api/v3/work_packages/{task_id}/form"
        form_response = requests.post(form_url, headers=self.headers)
        form_response.raise_for_status()
        lock_version = form_response.json().get("_embedded", {}).get("payload", {}).get("lockVersion")
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
            payload["_links"] = {"status": {"href": f"/api/v3/statuses/{updates['status']}"}}
        if "assignee_id" in updates:
            payload["_links"] = {
                **payload.get("_links", {}),
                "assignee": {"href": f"/api/v3/users/{updates['assignee_id']}"}
            }
        if "estimated_hours" in updates:
            # Convert hours to ISO 8601 duration (e.g., 2.5 -> PT2H30M, 2.0 -> PT2H)
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
    
    async def list_sprints(self, project_id: Optional[str] = None) -> List[PMSprint]:
        """
        List sprints (iterations) from OpenProject
        
        Note: OpenProject uses "versions" for sprints/iterations
        """
        url = f"{self.base_url}/api/v3/versions"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        sprints_data = response.json()["_embedded"]["elements"]
        
        # Filter by project_id if provided (versions don't have project filter in API)
        if project_id:
            sprints_data = [
                sprint for sprint in sprints_data
                if sprint.get("_links", {}).get("definingProject", {}).get("href", "").endswith(f"/projects/{project_id}")
            ]
        
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
    
    async def update_sprint(self, sprint_id: str, updates: Dict[str, Any]) -> PMSprint:
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
    
    async def list_users(self, project_id: Optional[str] = None) -> List[PMUser]:
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
            response = requests.get(f"{self.base_url}/api/v3/projects", headers=self.headers, timeout=5)
            # 200 OK or 403 Forbidden (authenticated but no projects) both indicate healthy connection
            return response.status_code in (200, 403)
        except:
            return False
    
    # ==================== Parser Methods ====================
    
    def _parse_project(self, data: Dict[str, Any]) -> PMProject:
        """Parse OpenProject project data to unified format"""
        return PMProject(
            id=str(data["id"]),
            name=data.get("name", ""),
            description=data.get("description", {}).get("raw") if isinstance(data.get("description"), dict) else data.get("description"),
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
            description=data.get("description", {}).get("raw") if isinstance(data.get("description"), dict) else data.get("description"),
            status=embedded.get("status", {}).get("name") if embedded.get("status") else None,
            project_id=self._extract_id_from_href(links.get("project", {}).get("href")),
            assignee_id=self._extract_id_from_href(links.get("assignee", {}).get("href")),
            estimated_hours=self._parse_duration_to_hours(data.get("estimatedTime")),
            actual_hours=self._parse_duration_to_hours(data.get("derivedRemainingTime")),
            start_date=self._parse_date(data.get("startDate")),
            due_date=self._parse_date(data.get("dueDate")),
            created_at=self._parse_datetime(data.get("createdAt")),
            updated_at=self._parse_datetime(data.get("updatedAt")),
            raw_data=data
        )
    
    def _parse_sprint(self, data: Dict[str, Any]) -> PMSprint:
        """Parse OpenProject version to unified format"""
        links = data.get("_links", {})
        
        return PMSprint(
            id=str(data["id"]),
            name=data.get("name", ""),
            project_id=self._extract_id_from_href(links.get("definingProject", {}).get("href")),
            start_date=self._parse_date(data.get("startDate")),
            end_date=self._parse_date(data.get("endDate")),
            status=data.get("status"),
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
        except:
            return None
    
    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[date]:
        """Parse OpenProject date string"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str).date()
        except:
            return None
    
    @staticmethod
    def _extract_id_from_href(href: Optional[str]) -> Optional[str]:
        """Extract ID from OpenProject HATEOAS href"""
        if not href:
            return None
        try:
            return href.split("/")[-1]
        except:
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
            activity_id: Optional activity type ID (defaults to first available)
            user_id: Optional user ID (defaults to current user)
            
        Returns:
            Created time entry data
        """
        url = f"{self.base_url}/api/v3/time_entries"
        payload = {
            "hours": self._format_hours_to_duration(hours),
            "_links": {
                "workPackage": {"href": f"/api/v3/work_packages/{task_id}"}
            }
        }
        
        if comment:
            payload["comment"] = {"raw": comment, "format": "plain"}
        
        if activity_id:
            payload["_links"]["activity"] = {"href": f"/api/v3/time_entries/activities/{activity_id}"}
        
        if user_id:
            payload["_links"]["user"] = {"href": f"/api/v3/users/{user_id}"}
        
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
            filters.append({"workPackage": {"operator": "=", "values": [task_id]}})
        if user_id:
            filters.append({"user": {"operator": "=", "values": [user_id]}})
        if project_id:
            filters.append({"project": {"operator": "=", "values": [project_id]}})
        
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
    def _parse_duration_to_hours(duration_str: Optional[str]) -> Optional[float]:
        """Parse OpenProject ISO 8601 duration string to hours"""
        if not duration_str:
            return None
        try:
            # OpenProject uses ISO 8601 duration format like "PT1H30M", "P1DT2H", or "P2DT2H" (2 days + 2 hours)
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
            
            # Return 0.0 for PT0H, None only if parsing failed or no duration provided
            return total_hours if total_hours >= 0 else None
        except:
            return None

