"""
Mock data generators for analytics testing and development.

Provides realistic mock data for sprints, tasks, and transitions
without needing to connect to real JIRA/OpenProject instances.
"""

import random
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple
from uuid import uuid4

from src.analytics.models import (
    WorkItem, WorkItemType, TaskStatus, Priority,
    SprintData, TaskTransition, VelocityDataPoint,
    CycleTimeDataPoint, TrendDataPoint
)


class MockDataGenerator:
    """Generates realistic mock data for analytics charts"""
    
    # Realistic names for team members
    TEAM_MEMBERS = [
        "Alice Chen", "Bob Smith", "Charlie Johnson", "Diana Martinez",
        "Ethan Brown", "Fiona O'Neill", "George Kim", "Hannah Patel"
    ]
    
    # Component names for a typical project
    COMPONENTS = [
        "Authentication", "API", "Database", "Frontend", "Backend",
        "DevOps", "Documentation", "Testing"
    ]
    
    # Task title templates
    TASK_TEMPLATES = [
        "Implement {feature}",
        "Fix bug in {component}",
        "Refactor {component} module",
        "Add tests for {feature}",
        "Update {component} documentation",
        "Optimize {feature} performance",
        "Design {feature} interface",
        "Review {component} security"
    ]
    
    FEATURES = [
        "user login", "dashboard", "reporting", "notifications",
        "data export", "search", "filtering", "pagination",
        "caching", "logging", "validation", "error handling"
    ]
    
    def __init__(self, seed: int = 42):
        """Initialize with optional random seed for reproducibility"""
        random.seed(seed)
        self.task_counter = 1000
    
    def _generate_task_title(self) -> str:
        """Generate a realistic task title"""
        template = random.choice(self.TASK_TEMPLATES)
        return template.format(
            feature=random.choice(self.FEATURES),
            component=random.choice(self.COMPONENTS)
        )
    
    def generate_work_item(
        self,
        item_type: WorkItemType = None,
        status: TaskStatus = None,
        created_at: datetime = None,
        completed: bool = False
    ) -> WorkItem:
        """Generate a single work item"""
        self.task_counter += 1
        
        if item_type is None:
            item_type = random.choices(
                [WorkItemType.STORY, WorkItemType.BUG, WorkItemType.TASK],
                weights=[0.5, 0.3, 0.2]
            )[0]
        
        if status is None:
            if completed:
                status = TaskStatus.DONE
            else:
                status = random.choice(list(TaskStatus))
        
        if created_at is None:
            created_at = datetime.now() - timedelta(days=random.randint(1, 30))
        
        # Generate story points based on type
        if item_type == WorkItemType.STORY:
            story_points = random.choice([1, 2, 3, 5, 8, 13])
        elif item_type == WorkItemType.BUG:
            story_points = random.choice([1, 2, 3, 5])
        else:
            story_points = random.choice([1, 2, 3])
        
        estimated_hours = story_points * random.uniform(4, 8)
        
        completed_at = None
        actual_hours = None
        if status == TaskStatus.DONE:
            completed_at = created_at + timedelta(days=random.uniform(1, 10))
            actual_hours = estimated_hours * random.uniform(0.7, 1.3)
        
        return WorkItem(
            id=f"TASK-{self.task_counter}",
            title=self._generate_task_title(),
            type=item_type,
            status=status,
            priority=random.choice(list(Priority)),
            story_points=story_points,
            estimated_hours=estimated_hours,
            actual_hours=actual_hours,
            assigned_to=random.choice(self.TEAM_MEMBERS),
            created_at=created_at,
            completed_at=completed_at,
            component=random.choice(self.COMPONENTS)
        )
    
    def generate_sprint_data(
        self,
        sprint_id: str = None,
        sprint_number: int = 1,
        project_id: str = "PROJECT-1",
        start_date: date = None,
        duration_days: int = 14
    ) -> SprintData:
        """Generate complete sprint data with work items"""
        
        if sprint_id is None:
            sprint_id = f"SPRINT-{sprint_number}"
        
        if start_date is None:
            start_date = date.today() - timedelta(days=duration_days)
        
        end_date = start_date + timedelta(days=duration_days)
        
        # Determine sprint status
        today = date.today()
        if today < start_date:
            status = "planning"
        elif start_date <= today <= end_date:
            status = "active"
        else:
            status = "completed"
        
        # Generate work items
        num_items = random.randint(15, 25)
        work_items = []
        
        for i in range(num_items):
            # For completed sprints, most items should be done
            if status == "completed":
                completed = random.random() < 0.85  # 85% completion rate
            elif status == "active":
                completed = random.random() < 0.50  # 50% done mid-sprint
            else:
                completed = False
            
            item = self.generate_work_item(
                created_at=datetime.combine(start_date, datetime.min.time()),
                completed=completed
            )
            work_items.append(item)
        
        # Calculate points
        planned_points = sum(item.story_points or 0 for item in work_items)
        completed_points = sum(
            item.story_points or 0 
            for item in work_items 
            if item.status == TaskStatus.DONE
        )
        
        # Generate scope changes (10-20% of items)
        added_items = []
        removed_items = []
        
        if status in ["active", "completed"]:
            num_added = random.randint(1, 3)
            for _ in range(num_added):
                item = self.generate_work_item(
                    created_at=datetime.combine(
                        start_date + timedelta(days=random.randint(1, 7)),
                        datetime.min.time()
                    )
                )
                added_items.append(item)
            
            num_removed = random.randint(0, 2)
            if num_removed > 0 and len(work_items) >= num_removed:
                removed_items = random.sample(work_items, num_removed)
        
        # Team capacity
        num_team_members = random.randint(4, 8)
        team_members = random.sample(self.TEAM_MEMBERS, num_team_members)
        capacity_hours = num_team_members * duration_days * 6  # 6 hours per person per day
        
        return SprintData(
            id=sprint_id,
            name=f"Sprint {sprint_number}",
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            status=status,
            planned_points=planned_points,
            completed_points=completed_points,
            capacity_hours=capacity_hours,
            work_items=work_items,
            added_items=added_items,
            removed_items=removed_items,
            team_members=team_members
        )
    
    def generate_sprint_history(
        self,
        project_id: str = "PROJECT-1",
        num_sprints: int = 6,
        sprint_duration_days: int = 14
    ) -> List[SprintData]:
        """Generate a history of multiple sprints"""
        sprints = []
        
        # Start from oldest sprint
        current_date = date.today() - timedelta(days=sprint_duration_days * num_sprints)
        
        for i in range(1, num_sprints + 1):
            sprint = self.generate_sprint_data(
                sprint_number=i,
                project_id=project_id,
                start_date=current_date,
                duration_days=sprint_duration_days
            )
            sprints.append(sprint)
            current_date = sprint.end_date + timedelta(days=1)
        
        return sprints
    
    def generate_velocity_data(
        self,
        project_id: str = "PROJECT-1",
        num_sprints: int = 6
    ) -> List[VelocityDataPoint]:
        """Generate velocity data points"""
        velocity_data = []
        
        # Generate with realistic variance
        base_velocity = random.uniform(35, 50)
        
        for i in range(1, num_sprints + 1):
            # Add some trend (slight improvement over time)
            trend = i * 2
            variance = random.uniform(-5, 5)
            
            committed = base_velocity + trend + variance
            # Completion rate typically 80-95%
            completion_rate = random.uniform(0.80, 0.95)
            completed = committed * completion_rate
            
            velocity_data.append(VelocityDataPoint(
                sprint_name=f"Sprint {i}",
                sprint_number=i,
                committed=round(committed, 1),
                completed=round(completed, 1),
                carry_over=round(random.uniform(0, 5), 1) if i > 1 else 0
            ))
        
        return velocity_data
    
    def generate_task_transitions(
        self,
        work_items: List[WorkItem],
        start_date: date,
        end_date: date
    ) -> List[TaskTransition]:
        """Generate realistic task transitions for CFD and cycle time analysis"""
        transitions = []
        
        for item in work_items:
            # Create typical workflow: TODO -> IN_PROGRESS -> IN_REVIEW -> DONE
            current_date = datetime.combine(start_date, datetime.min.time())
            current_status = TaskStatus.TODO
            
            # Initial transition to TODO (implicit)
            
            # Move to IN_PROGRESS
            if item.status in [TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW, TaskStatus.DONE]:
                days_to_start = random.uniform(0, 3)
                transition_date = current_date + timedelta(days=days_to_start)
                transitions.append(TaskTransition(
                    task_id=item.id,
                    from_status=TaskStatus.TODO,
                    to_status=TaskStatus.IN_PROGRESS,
                    transitioned_at=transition_date,
                    transitioned_by=item.assigned_to
                ))
                current_status = TaskStatus.IN_PROGRESS
                current_date = transition_date
            
            # Move to IN_REVIEW (optional)
            if item.status in [TaskStatus.IN_REVIEW, TaskStatus.DONE] and random.random() < 0.7:
                days_in_progress = random.uniform(1, 5)
                transition_date = current_date + timedelta(days=days_in_progress)
                transitions.append(TaskTransition(
                    task_id=item.id,
                    from_status=TaskStatus.IN_PROGRESS,
                    to_status=TaskStatus.IN_REVIEW,
                    transitioned_at=transition_date,
                    transitioned_by=item.assigned_to
                ))
                current_status = TaskStatus.IN_REVIEW
                current_date = transition_date
            
            # Move to DONE
            if item.status == TaskStatus.DONE and item.completed_at:
                # Sometimes items go back to IN_PROGRESS from review
                if current_status == TaskStatus.IN_REVIEW and random.random() < 0.2:
                    rework_date = current_date + timedelta(days=0.5)
                    transitions.append(TaskTransition(
                        task_id=item.id,
                        from_status=TaskStatus.IN_REVIEW,
                        to_status=TaskStatus.IN_PROGRESS,
                        transitioned_at=rework_date,
                        transitioned_by=item.assigned_to
                    ))
                    current_status = TaskStatus.IN_PROGRESS
                    current_date = rework_date
                    
                    # Then back to review
                    review_date = current_date + timedelta(days=random.uniform(0.5, 2))
                    transitions.append(TaskTransition(
                        task_id=item.id,
                        from_status=TaskStatus.IN_PROGRESS,
                        to_status=TaskStatus.IN_REVIEW,
                        transitioned_at=review_date,
                        transitioned_by=item.assigned_to
                    ))
                    current_status = TaskStatus.IN_REVIEW
                    current_date = review_date
                
                # Final transition to DONE
                transitions.append(TaskTransition(
                    task_id=item.id,
                    from_status=current_status,
                    to_status=TaskStatus.DONE,
                    transitioned_at=item.completed_at,
                    transitioned_by=item.assigned_to
                ))
        
        return sorted(transitions, key=lambda t: t.transitioned_at)
    
    def generate_cycle_time_data(
        self,
        num_items: int = 30,
        days_back: int = 30
    ) -> List[CycleTimeDataPoint]:
        """Generate cycle time data for completed work items"""
        cycle_times = []
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        for i in range(num_items):
            # Generate realistic cycle times (mostly 1-7 days with some outliers)
            if random.random() < 0.9:
                cycle_time = random.uniform(1, 7)
            else:
                cycle_time = random.uniform(8, 20)  # Outliers
            
            completed_at = start_date + timedelta(
                days=random.uniform(0, days_back)
            )
            started_at = completed_at - timedelta(days=cycle_time)
            
            cycle_times.append(CycleTimeDataPoint(
                item_id=f"TASK-{self.task_counter + i}",
                item_title=self._generate_task_title(),
                item_type=random.choice([WorkItemType.STORY, WorkItemType.BUG, WorkItemType.TASK]),
                started_at=started_at,
                completed_at=completed_at,
                cycle_time_days=round(cycle_time, 2),
                lead_time_days=round(cycle_time * random.uniform(1.2, 1.8), 2)
            ))
        
        return sorted(cycle_times, key=lambda x: x.completed_at)
    
    def generate_trend_data(
        self,
        project_id: str = "PROJECT-1",
        days_back: int = 90
    ) -> List[TrendDataPoint]:
        """Generate issue trend data (created vs resolved)"""
        trends = []
        
        current_date = date.today() - timedelta(days=days_back)
        open_count = random.randint(20, 40)  # Starting backlog
        
        for day in range(days_back + 1):
            # Daily creation rate (2-8 items, more during weekdays)
            is_weekend = current_date.weekday() >= 5
            if is_weekend:
                created = random.randint(0, 2)
                resolved = random.randint(0, 2)
            else:
                created = random.randint(2, 8)
                resolved = random.randint(2, 9)  # Slightly higher resolution rate
            
            net_change = created - resolved
            open_count = max(0, open_count + net_change)
            
            trends.append(TrendDataPoint(
                date=current_date,
                created=created,
                resolved=resolved,
                open=open_count,
                net_change=net_change
            ))
            
            current_date += timedelta(days=1)
        
        return trends
    
    def generate_distribution_data(
        self,
        work_items: List[WorkItem]
    ) -> Dict[str, Dict[str, int]]:
        """Generate work distribution data across different dimensions"""
        
        distributions = {
            "by_assignee": {},
            "by_priority": {},
            "by_type": {},
            "by_component": {},
            "by_status": {}
        }
        
        for item in work_items:
            # By assignee
            assignee = item.assigned_to or "Unassigned"
            distributions["by_assignee"][assignee] = distributions["by_assignee"].get(assignee, 0) + 1
            
            # By priority
            priority = item.priority.value
            distributions["by_priority"][priority] = distributions["by_priority"].get(priority, 0) + 1
            
            # By type
            item_type = item.type.value
            distributions["by_type"][item_type] = distributions["by_type"].get(item_type, 0) + 1
            
            # By component
            component = item.component or "General"
            distributions["by_component"][component] = distributions["by_component"].get(component, 0) + 1
            
            # By status
            status = item.status.value
            distributions["by_status"][status] = distributions["by_status"].get(status, 0) + 1
        
        return distributions


# Convenience functions for quick mock data generation

def get_mock_sprint(sprint_number: int = 1) -> SprintData:
    """Get a single mock sprint"""
    generator = MockDataGenerator()
    return generator.generate_sprint_data(sprint_number=sprint_number)


def get_mock_sprint_history(num_sprints: int = 6) -> List[SprintData]:
    """Get mock sprint history"""
    generator = MockDataGenerator()
    return generator.generate_sprint_history(num_sprints=num_sprints)


def get_mock_velocity_data(num_sprints: int = 6) -> List[VelocityDataPoint]:
    """Get mock velocity data"""
    generator = MockDataGenerator()
    return generator.generate_velocity_data(num_sprints=num_sprints)


def get_mock_cycle_times(num_items: int = 30) -> List[CycleTimeDataPoint]:
    """Get mock cycle time data"""
    generator = MockDataGenerator()
    return generator.generate_cycle_time_data(num_items=num_items)


def get_mock_trends(days_back: int = 90) -> List[TrendDataPoint]:
    """Get mock trend data"""
    generator = MockDataGenerator()
    return generator.generate_trend_data(days_back=days_back)


def generate_cfd_data(
    self,
    num_items: int = 50,
    start_date: datetime = None,
    end_date: datetime = None
) -> List[Dict]:
    """
    Generate mock work items with status history for CFD.
    
    Args:
        num_items: Number of work items to generate
        start_date: Start date for the period
        end_date: End date for the period
    
    Returns:
        List of work items with status history
    """
    if start_date is None:
        start_date = datetime.now() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.now()
    
    statuses = ["To Do", "In Progress", "In Review", "Done"]
    work_items = []
    
    for i in range(num_items):
        # Random creation date within the period
        days_offset = random.randint(0, (end_date - start_date).days)
        created_date = start_date + timedelta(days=days_offset)
        
        # Generate status history
        status_history = []
        current_date = created_date
        current_status_index = 0
        
        status_history.append({
            "date": current_date.isoformat(),
            "status": statuses[current_status_index]
        })
        
        # Progress through statuses
        while current_status_index < len(statuses) - 1 and current_date < end_date:
            # Random days to next status (1-7 days)
            days_in_status = random.randint(1, 7)
            current_date += timedelta(days=days_in_status)
            
            if current_date > end_date:
                break
            
            # Sometimes skip a status or stay in current status
            if random.random() < 0.7:  # 70% chance to progress
                current_status_index += 1
                status_history.append({
                    "date": current_date.isoformat(),
                    "status": statuses[current_status_index]
                })
        
        # Determine completion date
        completion_date = None
        if current_status_index == len(statuses) - 1:
            completion_date = current_date.isoformat()
        
        work_items.append({
            "id": f"ITEM-{i+1}",
            "created_date": created_date.isoformat(),
            "completion_date": completion_date,
            "status": statuses[current_status_index],
            "status_history": status_history,
            "start_date": created_date.isoformat()
        })
    
    return work_items


# Add method to MockDataGenerator class
MockDataGenerator.generate_cfd_data = generate_cfd_data


def generate_cycle_time_data(
    self,
    num_items: int = 50,
    start_date: datetime = None,
    end_date: datetime = None
) -> List[Dict]:
    """
    Generate mock work items with cycle time data.
    
    Args:
        num_items: Number of work items to generate
        start_date: Start date for the period
        end_date: End date for the period
    
    Returns:
        List of work items with start_date, completion_date, and cycle time
    """
    if start_date is None:
        start_date = datetime.now() - timedelta(days=60)
    if end_date is None:
        end_date = datetime.now()
    
    work_items = []
    item_types = ["story", "bug", "task", "feature"]
    
    task_titles = [
        "Implement user authentication",
        "Fix API endpoint bug",
        "Update database schema",
        "Refactor UI component",
        "Add error handling",
        "Remove deprecated code",
        "Optimize database query",
        "Fix performance issue",
        "Update documentation",
        "Add test coverage",
        "Implement data validation",
        "Fix security vulnerability",
        "Update dependencies",
        "Refactor business logic",
        "Add logging",
    ]
    
    for i in range(num_items):
        # Random completion date within the range
        days_offset = random.randint(0, (end_date - start_date).days)
        completion_date = start_date + timedelta(days=days_offset)
        
        # Generate cycle time with realistic distribution
        # Most items: 1-7 days, some outliers: 8-30 days
        if random.random() < 0.8:  # 80% normal items
            cycle_time_days = random.randint(1, 7)
        else:  # 20% slower items
            cycle_time_days = random.randint(8, 30)
        
        item_start_date = completion_date - timedelta(days=cycle_time_days)
        
        # Ensure start date is not before the period start
        if item_start_date < start_date:
            item_start_date = start_date
            cycle_time_days = (completion_date - item_start_date).days
        
        item_type = random.choice(item_types)
        title = random.choice(task_titles)
        
        work_items.append({
            "id": f"ITEM-{i+1}",
            "title": f"{title} #{i+1}",
            "type": item_type,
            "start_date": item_start_date.isoformat(),
            "completion_date": completion_date.isoformat(),
            "cycle_time_days": cycle_time_days,
        })
    
    # Sort by completion date
    work_items.sort(key=lambda x: x["completion_date"])
    
    return work_items


# Add method to MockDataGenerator class
MockDataGenerator.generate_cycle_time_data = generate_cycle_time_data

