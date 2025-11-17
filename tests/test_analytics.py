"""
Tests for analytics module.

Tests cover:
- Mock data generation
- Chart calculators (burndown, velocity, sprint report)
- Analytics service
- API endpoints
"""

import pytest
from datetime import date, datetime, timedelta

from src.analytics.mock_data import MockDataGenerator
from src.analytics.models import WorkItemType, TaskStatus, Priority
from src.analytics.calculators.burndown import BurndownCalculator
from src.analytics.calculators.velocity import VelocityCalculator
from src.analytics.calculators.sprint_report import SprintReportCalculator
from src.analytics.service import AnalyticsService


class TestMockDataGenerator:
    """Test mock data generation"""
    
    def test_generate_work_item(self):
        """Test work item generation"""
        generator = MockDataGenerator(seed=42)
        item = generator.generate_work_item()
        
        assert item.id.startswith("TASK-")
        assert item.title
        assert item.type in WorkItemType
        assert item.status in TaskStatus
        assert item.priority in Priority
        assert item.created_at is not None
    
    def test_generate_sprint_data(self):
        """Test sprint data generation"""
        generator = MockDataGenerator(seed=42)
        sprint = generator.generate_sprint_data(
            sprint_number=1,
            start_date=date.today() - timedelta(days=14)
        )
        
        assert sprint.id == "SPRINT-1"
        assert sprint.name == "Sprint 1"
        assert len(sprint.work_items) >= 15
        assert sprint.planned_points >= 0
        assert len(sprint.team_members) >= 4
    
    def test_generate_sprint_history(self):
        """Test sprint history generation"""
        generator = MockDataGenerator(seed=42)
        sprints = generator.generate_sprint_history(num_sprints=6)
        
        assert len(sprints) == 6
        for i, sprint in enumerate(sprints, 1):
            assert sprint.name == f"Sprint {i}"
        
        # Verify sprints are in chronological order
        for i in range(len(sprints) - 1):
            assert sprints[i].start_date < sprints[i + 1].start_date
    
    def test_generate_velocity_data(self):
        """Test velocity data generation"""
        generator = MockDataGenerator(seed=42)
        velocity_data = generator.generate_velocity_data(num_sprints=6)
        
        assert len(velocity_data) == 6
        for vd in velocity_data:
            assert vd.committed > 0
            assert vd.completed >= 0
            assert vd.completed <= vd.committed * 1.1  # Allow slight overcommitment
    
    def test_generate_cycle_time_data(self):
        """Test cycle time data generation"""
        generator = MockDataGenerator(seed=42)
        cycle_times = generator.generate_cycle_time_data(num_items=30)
        
        assert len(cycle_times) == 30
        for ct in cycle_times:
            assert ct.cycle_time_days > 0
            assert ct.started_at < ct.completed_at


class TestBurndownCalculator:
    """Test burndown chart calculator"""
    
    def test_calculate_burndown(self):
        """Test burndown calculation"""
        generator = MockDataGenerator(seed=42)
        sprint_data = generator.generate_sprint_data(
            sprint_number=1,
            start_date=date.today() - timedelta(days=14),
            duration_days=14
        )
        
        # Mark sprint as completed
        sprint_data.status = "completed"
        
        chart = BurndownCalculator.calculate(sprint_data, scope_type="story_points")
        
        assert chart.chart_type == "burndown"
        assert len(chart.series) == 2  # Ideal and Actual
        assert chart.series[0].name == "Ideal"
        assert chart.series[1].name == "Actual"
        
        # Check metadata
        assert "total_scope" in chart.metadata
        assert "remaining" in chart.metadata
        assert "completion_percentage" in chart.metadata
        assert "on_track" in chart.metadata
    
    def test_burndown_with_scope_changes(self):
        """Test burndown handles scope changes"""
        generator = MockDataGenerator(seed=42)
        sprint_data = generator.generate_sprint_data(sprint_number=1)
        
        chart = BurndownCalculator.calculate(sprint_data)
        
        scope_changes = chart.metadata.get("scope_changes", {})
        assert "added" in scope_changes
        assert "removed" in scope_changes
        assert "net" in scope_changes


class TestVelocityCalculator:
    """Test velocity chart calculator"""
    
    def test_calculate_velocity(self):
        """Test velocity calculation"""
        generator = MockDataGenerator(seed=42)
        sprint_history = generator.generate_sprint_history(num_sprints=6)
        
        chart = VelocityCalculator.calculate(sprint_history)
        
        assert chart.chart_type == "velocity"
        assert len(chart.series) == 2  # Committed and Completed
        assert chart.series[0].name == "Committed"
        assert chart.series[1].name == "Completed"
        
        # Check metadata
        assert "average_velocity" in chart.metadata
        assert "trend" in chart.metadata
        assert chart.metadata["trend"] in ["increasing", "decreasing", "stable"]
        assert "predictability_score" in chart.metadata
    
    def test_velocity_trend_detection(self):
        """Test velocity trend is detected correctly"""
        generator = MockDataGenerator(seed=42)
        velocity_data = generator.generate_velocity_data(num_sprints=6)
        
        chart = VelocityCalculator.calculate_from_data(velocity_data)
        
        # Trend should be one of the expected values
        assert chart.metadata["trend"] in ["increasing", "decreasing", "stable"]


class TestSprintReportCalculator:
    """Test sprint report calculator"""
    
    def test_calculate_sprint_report(self):
        """Test sprint report generation"""
        generator = MockDataGenerator(seed=42)
        sprint_data = generator.generate_sprint_data(
            sprint_number=1,
            start_date=date.today() - timedelta(days=14)
        )
        sprint_data.status = "completed"
        
        report = SprintReportCalculator.calculate(sprint_data)
        
        assert report.sprint_id == sprint_data.id
        assert report.sprint_name == sprint_data.name
        assert "start" in report.duration
        assert "end" in report.duration
        assert "days" in report.duration
        
        # Check commitment data
        assert "planned_points" in report.commitment
        assert "completed_points" in report.commitment
        assert "completion_rate" in report.commitment
        
        # Check we have highlights and concerns
        assert isinstance(report.highlights, list)
        assert isinstance(report.concerns, list)
    
    def test_sprint_report_work_breakdown(self):
        """Test work breakdown in sprint report"""
        generator = MockDataGenerator(seed=42)
        sprint_data = generator.generate_sprint_data(sprint_number=1)
        
        report = SprintReportCalculator.calculate(sprint_data)
        
        # Should have breakdown by type
        assert len(report.work_breakdown) > 0
        total_items = sum(report.work_breakdown.values())
        assert total_items == len(sprint_data.work_items)


class TestAnalyticsService:
    """Test analytics service"""
    
    def test_service_initialization(self):
        """Test service can be initialized"""
        service = AnalyticsService(data_source="mock")
        assert service.data_source == "mock"
    
    def test_get_burndown_chart(self):
        """Test getting burndown chart via service"""
        service = AnalyticsService(data_source="mock")
        chart = service.get_burndown_chart(
            project_id="PROJECT-1",
            sprint_id="SPRINT-1"
        )
        
        assert chart.chart_type == "burndown"
        assert len(chart.series) == 2
    
    def test_get_velocity_chart(self):
        """Test getting velocity chart via service"""
        service = AnalyticsService(data_source="mock")
        chart = service.get_velocity_chart(
            project_id="PROJECT-1",
            sprint_count=6
        )
        
        assert chart.chart_type == "velocity"
        assert len(chart.series) == 2
    
    def test_get_sprint_report(self):
        """Test getting sprint report via service"""
        service = AnalyticsService(data_source="mock")
        report = service.get_sprint_report(
            sprint_id="SPRINT-1",
            project_id="PROJECT-1"
        )
        
        assert report.sprint_id == "SPRINT-1"
        assert report.sprint_name == "Sprint 1"
    
    def test_get_project_summary(self):
        """Test getting project summary via service"""
        service = AnalyticsService(data_source="mock")
        summary = service.get_project_summary(project_id="PROJECT-1")
        
        assert summary["project_id"] == "PROJECT-1"
        assert "current_sprint" in summary
        assert "velocity" in summary
        assert "overall_stats" in summary
    
    def test_service_caching(self):
        """Test that service caches results"""
        service = AnalyticsService(data_source="mock")
        
        # First call
        chart1 = service.get_burndown_chart("PROJECT-1", "SPRINT-1")
        
        # Second call should be cached
        chart2 = service.get_burndown_chart("PROJECT-1", "SPRINT-1")
        
        # Should be the same object from cache
        assert chart1.generated_at == chart2.generated_at
        
        # Clear cache and get new one
        service.clear_cache()
        chart3 = service.get_burndown_chart("PROJECT-1", "SPRINT-1")
        
        # Should be different (new timestamp)
        assert chart1.generated_at != chart3.generated_at


class TestAnalyticsTools:
    """Test analytics tools for AI agents"""
    
    def test_import_analytics_tools(self):
        """Test that analytics tools can be imported"""
        from src.tools.analytics_tools import (
            get_sprint_burndown,
            get_team_velocity,
            get_sprint_report,
            get_project_analytics_summary,
            get_analytics_tools
        )
        
        tools = get_analytics_tools()
        assert len(tools) == 4
        assert all(hasattr(tool, 'name') for tool in tools)
    
    def test_burndown_tool_execution(self):
        """Test burndown tool can execute"""
        from src.tools.analytics_tools import get_sprint_burndown
        import json
        
        result = get_sprint_burndown.invoke({
            "project_id": "PROJECT-1",
            "sprint_id": "SPRINT-1"
        })
        
        # Should return JSON string
        assert isinstance(result, str)
        data = json.loads(result)
        assert "chart_type" in data or "error" in data
    
    def test_velocity_tool_execution(self):
        """Test velocity tool can execute"""
        from src.tools.analytics_tools import get_team_velocity
        import json
        
        result = get_team_velocity.invoke({
            "project_id": "PROJECT-1",
            "sprint_count": 6
        })
        
        assert isinstance(result, str)
        data = json.loads(result)
        assert "chart_type" in data or "error" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])







