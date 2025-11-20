# Analytics & Charts Implementation Plan

## Overview
Implement server-side analytics and chart generation for project management data, making it accessible to:
- Frontend UI
- AI Agents (as tools)
- External systems via REST API

## Architecture

### Module Structure
```
src/analytics/
├── __init__.py
├── models.py              # Data models for chart data
├── mock_data.py          # Mock data generators
├── service.py            # Core analytics service
├── calculators/          # Chart-specific calculation logic
│   ├── __init__.py
│   ├── burndown.py       # Burndown chart calculator
│   ├── burnup.py         # Burnup chart calculator
│   ├── velocity.py       # Velocity chart calculator
│   ├── cfd.py            # Cumulative Flow Diagram
│   ├── cycle_time.py     # Cycle time / Control chart
│   ├── distribution.py   # Work distribution charts
│   └── trends.py         # Issue trends
└── README.md
```

### API Endpoints Structure
```
/api/analytics/
├── /projects/{project_id}/burndown          # Sprint burndown
├── /projects/{project_id}/burnup            # Sprint burnup
├── /projects/{project_id}/velocity          # Team velocity
├── /projects/{project_id}/cfd               # Cumulative flow diagram
├── /projects/{project_id}/cycle-time        # Cycle time distribution
├── /projects/{project_id}/distribution      # Work distribution
├── /projects/{project_id}/trends            # Issue trends
├── /sprints/{sprint_id}/burndown            # Sprint-specific burndown
├── /sprints/{sprint_id}/report              # Sprint summary report
└── /releases/{release_id}/burndown          # Release burndown
```

## Implementation Phases

### Phase 1: Foundation (Core Infrastructure)
**Duration**: 1-2 days

#### Tasks:
1. **Create analytics module structure**
   - Set up directory structure
   - Create base models for chart data
   - Define common interfaces

2. **Design data models**
   ```python
   # Common chart data structure
   class ChartDataPoint:
       date: datetime
       value: float
       label: Optional[str]
   
   class ChartSeries:
       name: str
       data: List[ChartDataPoint]
       color: Optional[str]
   
   class ChartResponse:
       chart_type: str
       title: str
       series: List[ChartSeries]
       metadata: Dict[str, Any]
   ```

3. **Create mock data generators**
   - Mock sprint data
   - Mock task data with transitions
   - Mock team member data
   - Realistic date ranges and patterns

#### Deliverables:
- `src/analytics/models.py` - Data models
- `src/analytics/mock_data.py` - Mock data generators
- `src/analytics/service.py` - Base analytics service class

---

### Phase 2: Core Charts Implementation (Priority 1)
**Duration**: 3-4 days

#### 2.1 Burndown Chart
**Calculator**: `calculators/burndown.py`

**Input Parameters**:
- `sprint_id` or `project_id`
- `start_date`, `end_date`
- `scope_type`: "story_points" | "tasks" | "hours"

**Output**:
```json
{
  "chart_type": "burndown",
  "title": "Sprint 1 Burndown",
  "series": [
    {
      "name": "Ideal",
      "data": [{"date": "2024-01-01", "value": 100}, ...]
    },
    {
      "name": "Actual",
      "data": [{"date": "2024-01-01", "value": 100}, ...]
    }
  ],
  "metadata": {
    "total_scope": 100,
    "remaining": 20,
    "completed_percentage": 80,
    "on_track": true
  }
}
```

**Mock Data**: Generate realistic declining line with some variance

---

#### 2.2 Velocity Chart
**Calculator**: `calculators/velocity.py`

**Input Parameters**:
- `project_id`
- `sprint_count`: number of sprints to include (default: 6)

**Output**:
```json
{
  "chart_type": "velocity",
  "title": "Team Velocity (Last 6 Sprints)",
  "series": [
    {
      "name": "Committed",
      "data": [{"label": "Sprint 1", "value": 50}, ...]
    },
    {
      "name": "Completed",
      "data": [{"label": "Sprint 1", "value": 45}, ...]
    }
  ],
  "metadata": {
    "average_velocity": 48,
    "trend": "increasing",
    "predictability_score": 0.85
  }
}
```

**Mock Data**: Generate 6-10 sprints with realistic variance (±10-20%)

---

#### 2.3 Sprint Report
**Calculator**: `calculators/sprint_report.py`

**Input Parameters**:
- `sprint_id`

**Output**:
```json
{
  "sprint_name": "Sprint 1",
  "duration": {"start": "2024-01-01", "end": "2024-01-14", "days": 14},
  "commitment": {
    "planned_points": 50,
    "completed_points": 45,
    "completion_rate": 0.90
  },
  "scope_changes": {
    "added": 5,
    "removed": 2,
    "net_change": 3
  },
  "work_breakdown": {
    "stories": 8,
    "bugs": 3,
    "tasks": 15
  },
  "team_performance": {
    "velocity": 45,
    "capacity_utilized": 0.85
  }
}
```

---

### Phase 3: Advanced Flow Charts (Priority 2)
**Duration**: 3-4 days

#### 3.1 Cumulative Flow Diagram (CFD)
**Calculator**: `calculators/cfd.py`

**Input Parameters**:
- `project_id` or `sprint_id`
- `date_range`: start and end dates

**Output**:
```json
{
  "chart_type": "cfd",
  "title": "Cumulative Flow Diagram",
  "series": [
    {"name": "Done", "data": [...]},
    {"name": "In Progress", "data": [...]},
    {"name": "To Do", "data": [...]}
  ],
  "metadata": {
    "avg_cycle_time_days": 3.5,
    "avg_wip": 12,
    "bottlenecks": ["In Progress"]
  }
}
```

**Mock Data**: Stacked area chart with increasing completion and controlled WIP

---

#### 3.2 Cycle Time / Control Chart
**Calculator**: `calculators/cycle_time.py`

**Input Parameters**:
- `project_id`
- `period_days`: analysis period (default: 30)
- `percentile`: 50th, 75th, 85th, 95th

**Output**:
```json
{
  "chart_type": "cycle_time",
  "title": "Cycle Time Distribution",
  "series": [
    {
      "name": "Tasks",
      "data": [
        {"label": "TASK-1", "value": 2.5, "date": "2024-01-15"},
        ...
      ]
    }
  ],
  "metadata": {
    "percentiles": {
      "p50": 2.5,
      "p75": 4.0,
      "p85": 5.5,
      "p95": 8.0
    },
    "mean": 3.2,
    "std_dev": 1.8,
    "outliers": ["TASK-123"]
  }
}
```

**Mock Data**: Normal distribution with some outliers

---

### Phase 4: Distribution & Trends (Priority 3)
**Duration**: 2-3 days

#### 4.1 Work Distribution Charts
**Calculator**: `calculators/distribution.py`

**Types**:
- By Assignee
- By Priority
- By Type (Story, Bug, Task)
- By Component/Module

**Output**:
```json
{
  "chart_type": "distribution",
  "distribution_by": "assignee",
  "title": "Work Distribution by Team Member",
  "series": [
    {
      "name": "Current Sprint",
      "data": [
        {"label": "Alice", "value": 25},
        {"label": "Bob", "value": 30},
        ...
      ]
    }
  ],
  "metadata": {
    "total_items": 100,
    "balance_score": 0.85
  }
}
```

---

#### 4.2 Issue Trend Chart
**Calculator**: `calculators/trends.py`

**Input Parameters**:
- `project_id`
- `period_days`: default 90
- `issue_type`: "all" | "bugs" | "stories"

**Output**:
```json
{
  "chart_type": "trend",
  "title": "Issue Trend (Last 90 Days)",
  "series": [
    {"name": "Created", "data": [...]},
    {"name": "Resolved", "data": [...]},
    {"name": "Net Change", "data": [...]}
  ],
  "metadata": {
    "total_created": 150,
    "total_resolved": 140,
    "open_backlog": 50,
    "resolution_rate": 0.93
  }
}
```

---

### Phase 5: Strategic Charts
**Duration**: 2-3 days

#### 5.1 Burnup Chart
**Calculator**: `calculators/burnup.py`

**Output**: Similar to burndown but shows cumulative work completed + total scope line

#### 5.2 Epic/Feature Progress
**Calculator**: `calculators/epic_progress.py`

**Output**: Progress bars for large initiatives

#### 5.3 Release Burndown
**Calculator**: `calculators/release_burndown.py`

**Output**: Multi-sprint burndown toward release goal

---

## API Integration

### Adding to FastAPI (api/main.py)

```python
from src.analytics.service import AnalyticsService
from src.analytics.models import ChartResponse

analytics_service = AnalyticsService()

@app.get("/api/analytics/projects/{project_id}/burndown")
async def get_burndown(
    project_id: str,
    sprint_id: Optional[str] = None,
    scope_type: str = "story_points"
):
    chart_data = await analytics_service.get_burndown_chart(
        project_id=project_id,
        sprint_id=sprint_id,
        scope_type=scope_type
    )
    return chart_data

# ... similar endpoints for other charts
```

---

## AI Agent Integration

### Adding Analytics Tools (src/tools/analytics_tools.py)

```python
from langchain.tools import tool

@tool
def get_sprint_burndown(sprint_id: str) -> dict:
    """
    Get burndown chart data for a sprint.
    Useful for understanding sprint progress and forecasting completion.
    
    Args:
        sprint_id: The sprint identifier
    
    Returns:
        Burndown chart data with ideal and actual lines
    """
    from src.analytics.service import AnalyticsService
    service = AnalyticsService()
    return service.get_burndown_chart(sprint_id=sprint_id)

@tool
def get_team_velocity(project_id: str, sprint_count: int = 6) -> dict:
    """
    Get team velocity over recent sprints.
    Useful for sprint planning and capacity estimation.
    
    Args:
        project_id: The project identifier
        sprint_count: Number of recent sprints to analyze
    
    Returns:
        Velocity chart with committed vs completed story points
    """
    from src.analytics.service import AnalyticsService
    service = AnalyticsService()
    return service.get_velocity_chart(project_id=project_id, sprint_count=sprint_count)

# ... more analytics tools
```

### Register with Agent

```python
# In src/config/tools.py or agent configuration
from src.tools.analytics_tools import (
    get_sprint_burndown,
    get_team_velocity,
    get_cfd,
    get_cycle_time
)

ANALYTICS_TOOLS = [
    get_sprint_burndown,
    get_team_velocity,
    get_cfd,
    get_cycle_time,
]
```

---

## Testing Strategy

### Unit Tests
- Test each calculator independently
- Verify mock data generation
- Validate data model serialization

### Integration Tests
- Test API endpoints
- Test AI agent tool invocation
- Verify data flow from mock → service → API

### Test Files
```
tests/analytics/
├── test_burndown.py
├── test_velocity.py
├── test_cfd.py
├── test_cycle_time.py
├── test_distribution.py
├── test_api_endpoints.py
└── test_agent_tools.py
```

---

## Future Integration with Real Data

### Phase 6: Real Data Integration (Future)

When ready to connect to real JIRA/OpenProject data:

1. **Create data adapters**:
```python
# src/analytics/adapters/jira_adapter.py
class JiraAnalyticsAdapter:
    def get_sprint_data(self, sprint_id: str) -> SprintData:
        # Fetch from JIRA
        pass
    
    def get_issue_transitions(self, issue_ids: List[str]) -> List[Transition]:
        # Fetch transition history
        pass
```

2. **Update service to use adapters**:
```python
class AnalyticsService:
    def __init__(self, data_source: str = "mock"):
        if data_source == "mock":
            self.adapter = MockDataAdapter()
        elif data_source == "jira":
            self.adapter = JiraAnalyticsAdapter()
        elif data_source == "openproject":
            self.adapter = OpenProjectAnalyticsAdapter()
```

3. **Configuration**:
```yaml
# conf.yaml
analytics:
  data_source: "mock"  # or "jira", "openproject"
  cache_ttl: 300  # seconds
  default_sprint_count: 6
```

---

## Key Design Principles

1. **Separation of Concerns**
   - Calculators: Pure calculation logic
   - Service: Orchestration and caching
   - API: HTTP interface
   - Tools: AI agent integration

2. **Data Source Agnostic**
   - Mock data for development
   - Easy to swap for real providers
   - Adapter pattern for extensibility

3. **Consistent Data Models**
   - Standardized chart data format
   - Easy to consume by frontend
   - Language-agnostic JSON responses

4. **Performance**
   - Cache computed charts
   - Async operations where possible
   - Efficient mock data generation

5. **Extensibility**
   - Easy to add new chart types
   - Plugin-style calculator registration
   - Provider-agnostic design

---

## Success Criteria

### Phase 1-3 Complete:
- ✅ 7 core chart types working with mock data
- ✅ All API endpoints functional
- ✅ AI agent can query analytics
- ✅ Full test coverage (>80%)
- ✅ Documentation complete

### Ready for Real Data:
- ✅ Adapter pattern implemented
- ✅ Configuration system in place
- ✅ Performance acceptable (<500ms per chart)
- ✅ Caching working correctly

---

## Timeline Summary

| Phase | Duration | Deliverables |
|-------|----------|-------------|
| Phase 1: Foundation | 1-2 days | Module structure, models, mock data |
| Phase 2: Core Charts | 3-4 days | Burndown, Velocity, Sprint Report |
| Phase 3: Flow Charts | 3-4 days | CFD, Cycle Time |
| Phase 4: Distribution | 2-3 days | Work distribution, Trends |
| Phase 5: Strategic | 2-3 days | Burnup, Epic Progress, Release Burndown |
| **Total** | **11-16 days** | **Complete analytics system with mock data** |

---

## Next Steps

1. Review and approve this plan
2. Start with Phase 1: Create module structure
3. Implement mock data generators
4. Build out Phase 2 core charts
5. Iterate with feedback

---

## Questions to Resolve

1. **Chart customization**: Should we support custom date ranges, filters, groupings?
2. **Real-time updates**: Should charts support WebSocket for live updates?
3. **Export formats**: Should we support CSV/Excel export of chart data?
4. **Caching strategy**: Redis vs in-memory vs database?
5. **Permissions**: Should analytics respect project-level permissions?
















