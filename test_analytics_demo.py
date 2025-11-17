#!/usr/bin/env python3
"""
Demo script to test analytics module functionality.

This script demonstrates:
- Mock data generation
- Chart calculations
- Analytics service usage
- JSON serialization for API responses
"""

import json
from datetime import date, timedelta

from src.analytics.service import AnalyticsService
from src.analytics.mock_data import MockDataGenerator


def print_section(title: str):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def test_mock_data_generation():
    """Test mock data generation"""
    print_section("1. Mock Data Generation")
    
    generator = MockDataGenerator(seed=42)
    
    # Generate a sprint
    sprint = generator.generate_sprint_data(
        sprint_number=1,
        start_date=date.today() - timedelta(days=14),
        duration_days=14
    )
    
    print(f"Sprint ID: {sprint.id}")
    print(f"Sprint Name: {sprint.name}")
    print(f"Status: {sprint.status}")
    print(f"Work Items: {len(sprint.work_items)}")
    print(f"Planned Points: {sprint.planned_points}")
    print(f"Completed Points: {sprint.completed_points}")
    print(f"Team Members: {len(sprint.team_members)}")
    print(f"Team: {', '.join(sprint.team_members[:3])}...")
    
    # Show some work items
    print(f"\nSample Work Items:")
    for item in sprint.work_items[:3]:
        print(f"  - {item.id}: {item.title[:40]}... ({item.type.value}, {item.status.value})")


def test_burndown_chart():
    """Test burndown chart generation"""
    print_section("2. Burndown Chart")
    
    service = AnalyticsService(data_source="mock")
    chart = service.get_burndown_chart(
        project_id="PROJECT-1",
        sprint_id="SPRINT-1",
        scope_type="story_points"
    )
    
    print(f"Chart Type: {chart.chart_type}")
    print(f"Title: {chart.title}")
    print(f"\nSeries:")
    for series in chart.series:
        print(f"  - {series.name}: {len(series.data)} data points")
    
    print(f"\nMetadata:")
    print(f"  Total Scope: {chart.metadata['total_scope']}")
    print(f"  Completed: {chart.metadata['completed']}")
    print(f"  Remaining: {chart.metadata['remaining']}")
    print(f"  Completion %: {chart.metadata['completion_percentage']}%")
    print(f"  On Track: {chart.metadata['on_track']}")
    
    print(f"\nScope Changes:")
    scope_changes = chart.metadata['scope_changes']
    print(f"  Added: {scope_changes['added']}")
    print(f"  Removed: {scope_changes['removed']}")
    print(f"  Net: {scope_changes['net']}")


def test_velocity_chart():
    """Test velocity chart generation"""
    print_section("3. Velocity Chart")
    
    service = AnalyticsService(data_source="mock")
    chart = service.get_velocity_chart(
        project_id="PROJECT-1",
        sprint_count=6
    )
    
    print(f"Chart Type: {chart.chart_type}")
    print(f"Title: {chart.title}")
    
    print(f"\nVelocity Summary:")
    print(f"  Average Velocity: {chart.metadata['average_velocity']}")
    print(f"  Median Velocity: {chart.metadata['median_velocity']}")
    print(f"  Latest Velocity: {chart.metadata['latest_velocity']}")
    print(f"  Trend: {chart.metadata['trend']}")
    print(f"  Predictability Score: {chart.metadata['predictability_score']}")
    
    print(f"\nPer-Sprint Data:")
    committed_series = chart.series[0]
    completed_series = chart.series[1]
    
    for i in range(min(3, len(committed_series.data))):
        committed = committed_series.data[i]
        completed = completed_series.data[i]
        completion_rate = (completed.value / committed.value * 100) if committed.value > 0 else 0
        print(f"  {committed.label}: {completed.value}/{committed.value} points ({completion_rate:.0f}%)")


def test_sprint_report():
    """Test sprint report generation"""
    print_section("4. Sprint Report")
    
    service = AnalyticsService(data_source="mock")
    report = service.get_sprint_report(
        sprint_id="SPRINT-1",
        project_id="PROJECT-1"
    )
    
    print(f"Sprint: {report.sprint_name} ({report.sprint_id})")
    
    print(f"\nDuration:")
    print(f"  {report.duration['start']} to {report.duration['end']} ({report.duration['days']} days)")
    
    print(f"\nCommitment:")
    print(f"  Planned: {report.commitment['planned_points']} points ({report.commitment['planned_items']} items)")
    print(f"  Completed: {report.commitment['completed_points']} points ({report.commitment['completed_items']} items)")
    print(f"  Completion Rate: {report.commitment['completion_rate'] * 100:.0f}%")
    
    print(f"\nWork Breakdown:")
    for work_type, count in report.work_breakdown.items():
        print(f"  {work_type.capitalize()}: {count}")
    
    print(f"\nTeam Performance:")
    print(f"  Velocity: {report.team_performance['velocity']}")
    print(f"  Capacity Utilized: {report.team_performance['capacity_utilized'] * 100:.0f}%")
    print(f"  Team Size: {report.team_performance['team_size']}")
    
    print(f"\nHighlights:")
    for highlight in report.highlights:
        print(f"  {highlight}")
    
    if report.concerns:
        print(f"\nConcerns:")
        for concern in report.concerns:
            print(f"  {concern}")


def test_project_summary():
    """Test project summary"""
    print_section("5. Project Summary")
    
    service = AnalyticsService(data_source="mock")
    summary = service.get_project_summary(project_id="PROJECT-1")
    
    print(f"Project ID: {summary['project_id']}")
    
    print(f"\nCurrent Sprint:")
    current = summary['current_sprint']
    print(f"  {current['name']} ({current['id']})")
    print(f"  Status: {current['status']}")
    print(f"  Progress: {current['progress']}%")
    
    print(f"\nVelocity:")
    velocity = summary['velocity']
    print(f"  Average: {velocity['average']}")
    print(f"  Latest: {velocity['latest']}")
    print(f"  Trend: {velocity['trend']}")
    
    print(f"\nOverall Statistics:")
    stats = summary['overall_stats']
    print(f"  Total Items: {stats['total_items']}")
    print(f"  Completed: {stats['completed_items']}")
    print(f"  Completion Rate: {stats['completion_rate']}%")
    
    print(f"\nTeam Size: {summary['team_size']}")


def test_json_serialization():
    """Test JSON serialization for API responses"""
    print_section("6. JSON Serialization (API Response)")
    
    service = AnalyticsService(data_source="mock")
    chart = service.get_burndown_chart(
        project_id="PROJECT-1",
        sprint_id="SPRINT-1"
    )
    
    # Convert to dict (as API would do)
    chart_dict = chart.dict()
    
    # Serialize to JSON
    json_str = json.dumps(chart_dict, indent=2, default=str)
    
    print("Sample JSON Response (first 500 chars):")
    print(json_str[:500] + "...")
    
    # Verify it can be parsed back
    parsed = json.loads(json_str)
    print(f"\n✅ Successfully serialized and parsed JSON")
    print(f"   Chart type: {parsed['chart_type']}")
    print(f"   Series count: {len(parsed['series'])}")
    print(f"   Metadata keys: {', '.join(parsed['metadata'].keys())}")


def test_analytics_tools():
    """Test analytics tools for AI agents"""
    print_section("7. AI Agent Tools")
    
    from src.tools.analytics_tools import (
        get_sprint_burndown,
        get_team_velocity,
        get_sprint_report,
        get_project_analytics_summary
    )
    
    print("Available Tools:")
    tools = [
        get_sprint_burndown,
        get_team_velocity,
        get_sprint_report,
        get_project_analytics_summary
    ]
    
    for tool in tools:
        print(f"\n  📊 {tool.name}")
        print(f"     {tool.description[:80]}...")
    
    # Test one tool
    print("\n\nTesting get_project_analytics_summary tool:")
    result = get_project_analytics_summary.invoke({
        "project_id": "PROJECT-1"
    })
    
    # Parse and display
    data = json.loads(result)
    print(f"  Current Sprint: {data['current_sprint']['name']}")
    print(f"  Average Velocity: {data['velocity']['average']}")
    print(f"  Completion Rate: {data['overall_stats']['completion_rate']}%")


def main():
    """Run all tests"""
    print("\n" + "█" * 70)
    print("  ANALYTICS MODULE DEMO")
    print("█" * 70)
    
    try:
        test_mock_data_generation()
        test_burndown_chart()
        test_velocity_chart()
        test_sprint_report()
        test_project_summary()
        test_json_serialization()
        test_analytics_tools()
        
        print_section("✅ All Tests Completed Successfully!")
        print("The analytics module is ready to use!")
        print("\nNext steps:")
        print("  1. Start the API server: python api/main.py")
        print("  2. Test endpoints: curl http://localhost:8000/api/analytics/projects/PROJECT-1/summary")
        print("  3. Ask the AI agent: 'Show me the velocity for PROJECT-1'")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()







