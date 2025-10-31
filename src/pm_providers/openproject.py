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
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.api_key}"  # OpenProject uses Basic auth with API key
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
    
    async def list_tasks(self, project_id: Optional[str] = None) -> List[PMTask]:
        """List all work packages (tasks)"""
        url = f"{self.base_url}/api/v3/work_packages"
        
        if project_id:
            url += f"/projects/{project_id}"
        
        response = requests.get(url, headers=self.headers)
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
        
        if project_id:
            url += f"/projects/{project_id}"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        sprints_data = response.json()["_embedded"]["elements"]
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
    
    # ==================== Health Check ====================
    
    async def health_check(self) -> bool:
        """Check if the OpenProject connection is healthy"""
        try:
            response = requests.get(f"{self.base_url}/api/v3/status", headers=self.headers, timeout=5)
            return response.status_code == 200
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

