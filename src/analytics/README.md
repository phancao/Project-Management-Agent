# Analytics Module

Server-side analytics and chart generation for project management data.

## Overview

The analytics module provides:
- **Mock data generation** for development and testing
- **Chart calculators** for various PM metrics
- **REST API endpoints** for frontend integration
- **AI agent tools** for conversational analytics

## Architecture

```
src/analytics/
├── __init__.py           # Module exports
├── models.py             # Pydantic data models
├── mock_data.py          # Mock data generators
├── service.py            # Main analytics service
└── calculators/          # Chart calculation logic
    ├── burndown.py       # Burndown charts
    ├── velocity.py       # Velocity charts
    └── sprint_report.py  # Sprint reports
```

## Quick Start

### Using the Analytics Service

```python
from src.analytics.service import AnalyticsService

# Initialize with mock data
service = AnalyticsService(data_source="mock")

# Get burndown chart
burndown = service.get_burndown_chart(
    project_id="PROJECT-1",
    sprint_id="SPRINT-1",
    scope_type="story_points"
)

# Get velocity chart
velocity = service.get_velocity_chart(
    project_id="PROJECT-1",
    sprint_count=6
)

# Get sprint report
report = service.get_sprint_report(
    sprint_id="SPRINT-1",
    project_id="PROJECT-1"
)

# Get project summary
summary = service.get_project_summary(
    project_id="PROJECT-1"
)
```

### Using Mock Data Directly

```python
from src.analytics.mock_data import MockDataGenerator

generator = MockDataGenerator(seed=42)

# Generate a single sprint
sprint = generator.generate_sprint_data(sprint_number=1)

# Generate sprint history
sprints = generator.generate_sprint_history(num_sprints=6)

# Generate velocity data
velocity_data = generator.generate_velocity_data(num_sprints=6)

# Generate cycle time data
cycle_times = generator.generate_cycle_time_data(num_items=30)
```

## API Endpoints

### Burndown Chart

**GET** `/api/analytics/projects/{project_id}/burndown`

Query Parameters:
- `sprint_id` (optional): Sprint identifier
- `scope_type` (optional): "story_points" | "tasks" | "hours"

**Example Response:**
```json
{
  "chart_type": "burndown",
  "title": "Sprint 1 Burndown Chart",
  "series": [
    {
      "name": "Ideal",
      "data": [
        {"date": "2024-01-01T00:00:00", "value": 50.0, "label": "2024-01-01"}
      ],
      "color": "#94a3b8",
      "type": "line"
    },
    {
      "name": "Actual",
      "data": [
        {"date": "2024-01-01T00:00:00", "value": 50.0, "label": "2024-01-01"}
      ],
      "color": "#3b82f6",
      "type": "line"
    }
  ],
  "metadata": {
    "total_scope": 50.0,
    "remaining": 10.0,
    "completed": 40.0,
    "completion_percentage": 80.0,
    "on_track": true,
    "scope_changes": {
      "added": 5.0,
      "removed": 2.0,
      "net": 3.0
    }
  }
}
```

### Velocity Chart

**GET** `/api/analytics/projects/{project_id}/velocity`

Query Parameters:
- `sprint_count` (optional): Number of sprints to include (default: 6)

**Example Response:**
```json
{
  "chart_type": "velocity",
  "title": "Team Velocity (Last 6 Sprints)",
  "series": [
    {
      "name": "Committed",
      "data": [
        {"label": "Sprint 1", "value": 45.0}
      ],
      "color": "#94a3b8",
      "type": "bar"
    },
    {
      "name": "Completed",
      "data": [
        {"label": "Sprint 1", "value": 42.0}
      ],
      "color": "#10b981",
      "type": "bar"
    }
  ],
  "metadata": {
    "average_velocity": 43.5,
    "median_velocity": 44.0,
    "latest_velocity": 45.0,
    "trend": "increasing",
    "predictability_score": 0.89,
    "sprint_count": 6
  }
}
```

### Sprint Report

**GET** `/api/analytics/sprints/{sprint_id}/report`

Query Parameters:
- `project_id` (required): Project identifier

**Example Response:**
```json
{
  "sprint_id": "SPRINT-1",
  "sprint_name": "Sprint 1",
  "duration": {
    "start": "2024-01-01",
    "end": "2024-01-14",
    "days": 14
  },
  "commitment": {
    "planned_points": 50.0,
    "completed_points": 45.0,
    "completion_rate": 0.90,
    "planned_items": 20,
    "completed_items": 18
  },
  "scope_changes": {
    "added": 3,
    "removed": 1,
    "net_change": 2,
    "scope_stability": 0.92
  },
  "work_breakdown": {
    "story": 12,
    "bug": 5,
    "task": 3
  },
  "team_performance": {
    "velocity": 45.0,
    "capacity_hours": 336.0,
    "capacity_used": 310.0,
    "capacity_utilized": 0.92,
    "team_size": 6
  },
  "highlights": [
    "✅ Excellent sprint completion: 90% of committed work delivered",
    "✅ Optimal team capacity utilization: 92%"
  ],
  "concerns": []
}
```

### Project Summary

**GET** `/api/analytics/projects/{project_id}/summary`

**Example Response:**
```json
{
  "project_id": "PROJECT-1",
  "current_sprint": {
    "id": "SPRINT-3",
    "name": "Sprint 3",
    "status": "active",
    "progress": 65.5
  },
  "velocity": {
    "average": 43.5,
    "latest": 45.0,
    "trend": "increasing"
  },
  "overall_stats": {
    "total_items": 150,
    "completed_items": 135,
    "completion_rate": 90.0
  },
  "team_size": 6,
  "generated_at": "2024-01-15T10:30:00"
}
```

## AI Agent Tools

The analytics module provides tools that AI agents can use for conversational analytics.

### Available Tools

#### 1. `get_sprint_burndown`

Get burndown chart data for sprint progress tracking.

**Usage Examples:**
- "Show me the burndown for sprint 1"
- "Is our current sprint on track?"
- "How much work is remaining?"

**Parameters:**
- `project_id`: Project identifier
- `sprint_id` (optional): Sprint identifier
- `scope_type` (optional): "story_points" | "tasks" | "hours"

#### 2. `get_team_velocity`

Get team velocity over recent sprints for capacity planning.

**Usage Examples:**
- "What's our team's velocity?"
- "Show me velocity for the last 10 sprints"
- "Is our velocity improving?"
- "How many story points should we commit to?"

**Parameters:**
- `project_id`: Project identifier
- `sprint_count` (optional): Number of sprints (default: 6)

#### 3. `get_sprint_report`

Get comprehensive sprint summary report.

**Usage Examples:**
- "Give me a summary of sprint 1"
- "How did our last sprint go?"
- "What were the key achievements?"
- "Prepare a sprint review for sprint 3"

**Parameters:**
- `sprint_id`: Sprint identifier
- `project_id`: Project identifier

#### 4. `get_project_analytics_summary`

Get high-level project overview.

**Usage Examples:**
- "How is the project going?"
- "Give me a project status update"
- "What's the current sprint progress?"
- "Show me project health metrics"

**Parameters:**
- `project_id`: Project identifier

## Data Models

### ChartResponse

Standard response format for all charts:

```python
ChartResponse(
    chart_type: ChartType,        # Type of chart
    title: str,                    # Chart title
    series: List[ChartSeries],     # Data series
    metadata: Dict[str, Any],      # Summary statistics
    generated_at: datetime          # Generation timestamp
)
```

### ChartSeries

A data series within a chart:

```python
ChartSeries(
    name: str,                     # Series name (e.g., "Ideal", "Actual")
    data: List[ChartDataPoint],    # Data points
    color: Optional[str],          # Hex color code
    type: Optional[str]            # Chart type (line, bar, area)
)
```

### ChartDataPoint

A single data point:

```python
ChartDataPoint(
    date: Optional[datetime],      # For time-series data
    value: float,                  # Numeric value
    label: Optional[str],          # For categorical data
    metadata: Optional[Dict]       # Additional metadata
)
```

## Chart Types

### Burndown Chart

Shows remaining work over time in a sprint.

**Use Cases:**
- Track sprint progress
- Forecast completion
- Identify if team is on track

**Calculation:**
- Ideal line: Linear burndown from total scope to zero
- Actual line: Remaining work based on completed items
- Accounts for scope changes during sprint

### Velocity Chart

Shows team completion rate over multiple sprints.

**Use Cases:**
- Sprint planning and capacity estimation
- Track performance trends
- Assess team predictability

**Calculation:**
- Committed: Planned story points per sprint
- Completed: Actually delivered story points
- Trend: Linear regression to detect improvement/decline

### Sprint Report

Comprehensive sprint summary with metrics and insights.

**Use Cases:**
- Sprint reviews and retrospectives
- Performance analysis
- Stakeholder reporting

**Includes:**
- Commitment vs delivery
- Scope changes
- Work breakdown by type
- Capacity utilization
- Highlights and concerns

## Mock Data Generation

The mock data generator creates realistic test data for development.

### Features

- **Reproducible**: Use seed for consistent data
- **Realistic variance**: Natural fluctuations in velocity, cycle time
- **Work item transitions**: Simulates task state changes
- **Team dynamics**: Multiple team members with work distribution
- **Scope changes**: Items added/removed during sprints

### Customization

```python
generator = MockDataGenerator(seed=42)

# Custom sprint duration
sprint = generator.generate_sprint_data(
    sprint_number=1,
    start_date=date.today() - timedelta(days=7),
    duration_days=7  # One-week sprint
)

# Generate more sprints
sprints = generator.generate_sprint_history(
    num_sprints=10,
    sprint_duration_days=14
)

# More cycle time samples
cycle_times = generator.generate_cycle_time_data(
    num_items=100,
    days_back=90
)
```

## Extending with Real Data

To integrate with real JIRA/OpenProject data:

### 1. Create Data Adapter

```python
# src/analytics/adapters/jira_adapter.py
class JiraAnalyticsAdapter:
    def get_sprint_data(self, sprint_id: str) -> SprintData:
        # Fetch from JIRA API
        pass
    
    def get_sprint_history(self, project_id: str) -> List[SprintData]:
        # Fetch sprint history
        pass
```

### 2. Update Service

```python
class AnalyticsService:
    def __init__(self, data_source: str = "mock"):
        if data_source == "jira":
            self.adapter = JiraAnalyticsAdapter()
        elif data_source == "openproject":
            self.adapter = OpenProjectAnalyticsAdapter()
        else:
            self.adapter = MockDataAdapter()
```

### 3. Configuration

```yaml
# conf.yaml
analytics:
  data_source: "jira"  # or "mock", "openproject"
  cache_ttl: 300
```

## Performance Considerations

### Caching

The service includes built-in caching (5-minute TTL by default):

```python
service = AnalyticsService()

# First call: calculates and caches
chart1 = service.get_burndown_chart("PROJECT-1", "SPRINT-1")

# Second call: returns cached result
chart2 = service.get_burndown_chart("PROJECT-1", "SPRINT-1")

# Clear cache when needed
service.clear_cache()
```

### Optimization Tips

1. **Use appropriate sprint counts**: Default 6 sprints for velocity is optimal
2. **Cache at API level**: Consider Redis for multi-instance deployments
3. **Batch requests**: Fetch related charts together
4. **Async operations**: Service supports async/await patterns

## Testing

Run tests:

```bash
pytest tests/test_analytics.py -v
```

Test coverage includes:
- Mock data generation
- Chart calculations
- Service layer
- API endpoints
- AI agent tools

## Future Enhancements

Planned features (see `docs/ANALYTICS_IMPLEMENTATION_PLAN.md`):

### Priority 2 Charts:
- Cumulative Flow Diagram (CFD)
- Cycle Time / Control Chart
- Work Distribution Charts
- Issue Trend Analysis

### Priority 3 Charts:
- Burnup Chart
- Epic Progress Tracking
- Release Burndown
- Time Tracking Charts

## Support

For issues or questions:
- Check implementation plan: `docs/ANALYTICS_IMPLEMENTATION_PLAN.md`
- Review tests: `tests/test_analytics.py`
- See API docs: `docs/API.md`

## License

MIT License - See LICENSE file for details







