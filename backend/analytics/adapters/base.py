# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Base Analytics Adapter

Defines the interface for fetching real data from PM providers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime


class BaseAnalyticsAdapter(ABC):
    """
    Abstract base class for analytics data adapters.
    
    Adapters are responsible for fetching data from PM providers
    and transforming it into formats suitable for analytics calculators.
    """
    
    @abstractmethod
    async def get_burndown_data(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        scope_type: str = "story_points"
    ) -> Dict[str, Any]:
        """
        Fetch data for burndown chart.
        
        Returns:
            Dict with:
                - sprint: Sprint info (name, start_date, end_date, etc.)
                - tasks: List of tasks with story_points/count, status, completion dates
                - scope_changes: List of scope changes during sprint
        """
        pass
    
    @abstractmethod
    async def get_velocity_data(
        self,
        project_id: str,
        num_sprints: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Fetch data for velocity chart.
        
        Returns:
            List of sprints with:
                - name: Sprint name
                - start_date, end_date
                - planned_points, completed_points
                - planned_count, completed_count
        """
        pass
    
    @abstractmethod
    async def get_sprint_report_data(
        self,
        sprint_id: str,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch data for sprint report.
        
        Returns:
            Dict with:
                - sprint: Sprint info
                - tasks: All tasks in sprint with details
                - team_members: List of team members
                - completed_tasks, incomplete_tasks, added_tasks, removed_tasks
        """
        pass
    
    @abstractmethod
    async def get_cfd_data(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Fetch data for CFD chart.
        
        Returns:
            Dict with:
                - work_items: List of items with status_history
                - start_date, end_date
                - statuses: List of status names in order
        """
        pass
    
    @abstractmethod
    async def get_cycle_time_data(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        days_back: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Fetch data for cycle time chart.
        
        Returns:
            List of completed work items with:
                - id, title, type
                - start_date, completion_date
                - cycle_time_days
        """
        pass
    
    @abstractmethod
    async def get_work_distribution_data(
        self,
        project_id: str,
        sprint_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch data for work distribution chart.
        
        Returns:
            List of work items with:
                - assignee, priority, type, status
                - story_points
        """
        pass
    
    @abstractmethod
    async def get_issue_trend_data(
        self,
        project_id: str,
        days_back: int = 30,
        sprint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch data for issue trend chart.
        
        Returns:
            Dict with:
                - work_items: List with created_date, completion_date, type
                - start_date, end_date
        """
        pass

