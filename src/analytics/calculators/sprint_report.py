"""
Sprint report calculator.

Generates comprehensive sprint summary reports.
"""

from typing import List, Dict, Any
from datetime import datetime

from src.analytics.models import (
    SprintData, SprintReport, WorkItemType, TaskStatus
)


class SprintReportCalculator:
    """Generates sprint summary reports"""
    
    @staticmethod
    def calculate(sprint_data: SprintData) -> SprintReport:
        """
        Generate a comprehensive sprint report.
        
        Args:
            sprint_data: Sprint data with all work items
        
        Returns:
            SprintReport with summary and key metrics
        """
        
        # Duration info
        duration_days = (sprint_data.end_date - sprint_data.start_date).days
        duration = {
            "start": sprint_data.start_date.isoformat(),
            "end": sprint_data.end_date.isoformat(),
            "days": duration_days,
            "working_days": duration_days  # Simplified; could exclude weekends
        }
        
        # Commitment and completion
        planned_points = sprint_data.planned_points or 0
        completed_points = sprint_data.completed_points or 0
        completion_rate = (completed_points / planned_points) if planned_points > 0 else 0
        
        commitment = {
            "planned_points": round(planned_points, 1),
            "completed_points": round(completed_points, 1),
            "completion_rate": round(completion_rate, 2),
            "planned_items": len(sprint_data.work_items),
            "completed_items": sum(
                1 for item in sprint_data.work_items 
                if item.status == TaskStatus.DONE
            )
        }
        
        # Scope changes
        added_count = len(sprint_data.added_items)
        removed_count = len(sprint_data.removed_items)
        added_points = sum(item.story_points or 0 for item in sprint_data.added_items)
        removed_points = sum(item.story_points or 0 for item in sprint_data.removed_items)
        
        scope_changes = {
            "added": added_count,
            "removed": removed_count,
            "net_change": added_count - removed_count,
            "added_points": round(added_points, 1),
            "removed_points": round(removed_points, 1),
            "net_points": round(added_points - removed_points, 1),
            "scope_stability": round(1 - (abs(added_points - removed_points) / planned_points), 2) 
                               if planned_points > 0 else 1.0
        }
        
        # Work breakdown by type
        work_breakdown = {}
        for item_type in WorkItemType:
            count = sum(1 for item in sprint_data.work_items if item.type == item_type)
            if count > 0:
                work_breakdown[item_type.value] = count
        
        # Team performance
        capacity_used = sum(
            item.actual_hours or 0 
            for item in sprint_data.work_items 
            if item.status == TaskStatus.DONE
        )
        
        capacity_utilization = (capacity_used / sprint_data.capacity_hours) \
                              if sprint_data.capacity_hours else 0
        
        team_performance = {
            "velocity": round(completed_points, 1),
            "capacity_hours": round(sprint_data.capacity_hours or 0, 1),
            "capacity_used": round(capacity_used, 1),
            "capacity_utilized": round(capacity_utilization, 2),
            "team_size": len(sprint_data.team_members)
        }
        
        # Generate highlights
        highlights = SprintReportCalculator._generate_highlights(
            sprint_data, completion_rate, capacity_utilization
        )
        
        # Generate concerns
        concerns = SprintReportCalculator._generate_concerns(
            sprint_data, completion_rate, scope_changes, capacity_utilization
        )
        
        # Additional metadata
        metadata = {
            "status": sprint_data.status,
            "project_id": sprint_data.project_id,
            "generated_at": datetime.now().isoformat(),
            "priority_breakdown": SprintReportCalculator._get_priority_breakdown(sprint_data),
            "team_members": sprint_data.team_members
        }
        
        return SprintReport(
            sprint_id=sprint_data.id,
            sprint_name=sprint_data.name,
            duration=duration,
            commitment=commitment,
            scope_changes=scope_changes,
            work_breakdown=work_breakdown,
            team_performance=team_performance,
            highlights=highlights,
            concerns=concerns,
            metadata=metadata
        )
    
    @staticmethod
    def _generate_highlights(
        sprint_data: SprintData,
        completion_rate: float,
        capacity_utilization: float
    ) -> List[str]:
        """Generate positive highlights for the sprint"""
        highlights = []
        
        if completion_rate >= 0.90:
            highlights.append(f"✅ Excellent sprint completion: {completion_rate*100:.0f}% of committed work delivered")
        elif completion_rate >= 0.80:
            highlights.append(f"✅ Good sprint completion: {completion_rate*100:.0f}% of committed work delivered")
        
        if capacity_utilization >= 0.85 and capacity_utilization <= 0.95:
            highlights.append(f"✅ Optimal team capacity utilization: {capacity_utilization*100:.0f}%")
        
        # Count high-priority completed items
        high_priority_completed = sum(
            1 for item in sprint_data.work_items
            if item.status == TaskStatus.DONE and item.priority.value in ['critical', 'high']
        )
        if high_priority_completed > 0:
            highlights.append(f"✅ Completed {high_priority_completed} high-priority items")
        
        # Check if any blockers were cleared
        # (This would require tracking state changes, simplified here)
        
        if not highlights:
            highlights.append("Sprint completed")
        
        return highlights
    
    @staticmethod
    def _generate_concerns(
        sprint_data: SprintData,
        completion_rate: float,
        scope_changes: Dict[str, Any],
        capacity_utilization: float
    ) -> List[str]:
        """Generate concerns and issues from the sprint"""
        concerns = []
        
        if completion_rate < 0.70:
            concerns.append(f"⚠️ Low completion rate: Only {completion_rate*100:.0f}% of committed work delivered")
        
        if scope_changes["net_change"] > 3:
            concerns.append(f"⚠️ High scope volatility: {scope_changes['net_change']} net items added during sprint")
        
        if capacity_utilization < 0.60:
            concerns.append(f"⚠️ Low capacity utilization: {capacity_utilization*100:.0f}% - team may be blocked or overestimating")
        elif capacity_utilization > 1.10:
            concerns.append(f"⚠️ Over-capacity: {capacity_utilization*100:.0f}% - team may be overworked")
        
        # Check for blocked items
        blocked_count = sum(
            1 for item in sprint_data.work_items
            if item.status == TaskStatus.BLOCKED
        )
        if blocked_count > 0:
            concerns.append(f"⚠️ {blocked_count} items currently blocked")
        
        # Check for items in progress at sprint end
        if sprint_data.status == "completed":
            in_progress_count = sum(
                1 for item in sprint_data.work_items
                if item.status in [TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW]
            )
            if in_progress_count > 0:
                concerns.append(f"⚠️ {in_progress_count} items incomplete at sprint end")
        
        return concerns
    
    @staticmethod
    def _get_priority_breakdown(sprint_data: SprintData) -> Dict[str, int]:
        """Get breakdown of work items by priority"""
        breakdown = {}
        for item in sprint_data.work_items:
            priority = item.priority.value
            breakdown[priority] = breakdown.get(priority, 0) + 1
        return breakdown







