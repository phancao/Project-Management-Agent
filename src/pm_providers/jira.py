"""
JIRA Provider

Connects to Atlassian JIRA API to manage projects, issues, and sprints.
"""
import base64
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base import BasePMProvider
from .models import PMUser, PMProject, PMTask, PMSprint, PMProviderConfig


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
        
        Uses the 'recent' parameter to get projects accessible to the user.
        """
        url = f"{self.base_url}/rest/api/3/project"
        
        # JIRA API v3: Use 'recent' parameter to get accessible projects
        params = {
            "recent": 50,  # Get up to 50 recent projects
            "expand": "description,lead,url,projectKeys"  # Get more details
        }
        
        response = requests.get(
            url, headers=self.headers, params=params, timeout=10
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
            return []
        
        # Response is a list of projects
        if not isinstance(projects_data, list):
            # Handle unexpected format
            if isinstance(projects_data, dict) and 'values' in projects_data:
                projects_data = projects_data['values']
            else:
                return []
        
        return [self._parse_project(proj) for proj in projects_data]
    
    def _parse_project(self, proj_data: Dict[str, Any]) -> PMProject:
        """Parse JIRA project data to PMProject"""
        # For Next-Gen projects, try different ID fields
        project_id = (
            proj_data.get("key") or 
            proj_data.get("id") or 
            proj_data.get("simplifiedId") or
            str(proj_data.get("id", ""))
        )
        
        return PMProject(
            id=project_id,
            name=proj_data.get("name", ""),
            description=proj_data.get("description", ""),
            status=None,  # JIRA projects don't have a simple status field
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
            dt_str = dt_str.replace("+0000", "+00:00").replace("Z", "+00:00")
            return datetime.fromisoformat(dt_str)
        except (ValueError, AttributeError):
            return None
    
    async def get_project(self, project_id: str) -> Optional[PMProject]:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def create_project(self, project: PMProject) -> PMProject:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def update_project(self, project_id: str, updates: Dict) -> PMProject:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def delete_project(self, project_id: str) -> bool:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def list_tasks(
        self,
        project_id: Optional[str] = None,
        assignee_id: Optional[str] = None
    ) -> List[PMTask]:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def get_task(self, task_id: str) -> Optional[PMTask]:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def create_task(self, task: PMTask) -> PMTask:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def update_task(self, task_id: str, updates: Dict) -> PMTask:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def delete_task(self, task_id: str) -> bool:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def list_sprints(self, project_id: Optional[str] = None) -> List[PMSprint]:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def get_sprint(self, sprint_id: str) -> Optional[PMSprint]:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def create_sprint(self, sprint: PMSprint) -> PMSprint:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def update_sprint(self, sprint_id: str, updates: Dict) -> PMSprint:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def delete_sprint(self, sprint_id: str) -> bool:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def list_users(self, project_id: Optional[str] = None) -> List[PMUser]:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def get_user(self, user_id: str) -> Optional[PMUser]:
        raise NotImplementedError("JIRA provider not yet implemented")
    
    async def health_check(self) -> bool:
        raise NotImplementedError("JIRA provider not yet implemented")

