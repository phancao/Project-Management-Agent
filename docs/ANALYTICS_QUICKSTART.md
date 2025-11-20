# Analytics Module - Quick Start

## ✅ Implementation Complete!

The analytics module has been successfully implemented with **mock data** for development and testing. All core PM charts are now available via API and AI agents!

## 🎯 What's Implemented

### 1. **Core Charts** (Phase 1)
- ✅ **Burndown Chart** - Track sprint progress
- ✅ **Velocity Chart** - Team performance over sprints
- ✅ **Sprint Report** - Comprehensive sprint summary

### 2. **Infrastructure**
- ✅ Mock data generator (realistic test data)
- ✅ Pydantic data models for type safety
- ✅ REST API endpoints  
- ✅ AI agent tools integration
- ✅ Caching layer (5-minute TTL)
- ✅ Comprehensive tests

## 🚀 Quick Test

Run the demo:
```bash
python3 test_analytics_demo.py
```

Example output:
```
Sprint ID: SPRINT-1
Status: active
Planned Points: 79.0
Completed Points: 49.0
Completion %: 55.06%
On Track: False
```

## 📡 API Endpoints

All endpoints available at `http://localhost:8000/api/analytics/...`

### 1. Burndown Chart
```bash
GET /api/analytics/projects/PROJECT-1/burndown?sprint_id=SPRINT-1
```

### 2. Velocity Chart
```bash
GET /api/analytics/projects/PROJECT-1/velocity?sprint_count=6
```

### 3. Sprint Report
```bash
GET /api/analytics/sprints/SPRINT-1/report?project_id=PROJECT-1
```

### 4. Project Summary
```bash
GET /api/analytics/projects/PROJECT-1/summary
```

## 🤖 AI Agent Integration

The AI agent now has 4 new analytics tools:

1. **get_sprint_burndown** - "Show me the burndown chart"
2. **get_team_velocity** - "What's our team velocity?"
3. **get_sprint_report** - "Give me a sprint summary"  
4. **get_project_analytics_summary** - "How is the project going?"

### Example Prompts

- "Show me the burndown for sprint 1"
- "What's our team's average velocity?"
- "Is our current sprint on track?"
- "How did our last sprint go?"
- "Give me a project status update"

## 📊 Available Charts

| Chart | Purpose | Key Metrics |
|-------|---------|-------------|
| **Burndown** | Sprint progress | Remaining work, completion %, on track status |
| **Velocity** | Team performance | Average velocity, trend, predictability |
| **Sprint Report** | Comprehensive summary | Commitment, capacity, highlights, concerns |

## 🧪 Testing

Run tests:
```bash
pytest tests/test_analytics.py -v
```

Test coverage:
- Mock data generation ✅
- Chart calculations ✅
- Service layer ✅
- API integration ✅
- Agent tools ✅

## 📁 Module Structure

```
backend/analytics/
├── __init__.py           # Module exports
├── models.py             # Pydantic data models
├── mock_data.py          # Mock data generators
├── service.py            # Analytics service
├── calculators/          # Chart calculations
│   ├── burndown.py
│   ├── velocity.py
│   └── sprint_report.py
└── README.md             # Full documentation
```

## 🔌 Integration Points

### 1. **Frontend**
Call REST API endpoints to fetch chart data for visualization.

```javascript
// Example: Fetch burndown chart
const response = await fetch('/api/analytics/projects/PROJECT-1/burndown');
const chartData = await response.json();
```

### 2. **AI Agents**
Tools are auto-registered with researcher and coder agents.

```python
# Agents can now call analytics tools automatically
agent.invoke("Show me the velocity for PROJECT-1")
```

### 3. **Other Systems**
Standard JSON API responses make integration easy.

## 🎨 Chart Response Format

All charts return a standard format:

```json
{
  "chart_type": "burndown",
  "title": "Sprint 1 Burndown Chart",
  "series": [
    {
      "name": "Ideal",
      "data": [{"date": "2024-01-01", "value": 50}],
      "color": "#94a3b8",
      "type": "line"
    }
  ],
  "metadata": {
    "total_scope": 50.0,
    "remaining": 10.0,
    "on_track": true
  },
  "generated_at": "2024-01-15T10:30:00"
}
```

## 🚦 Next Steps

### Phase 2: Add More Charts
- Cumulative Flow Diagram (CFD)
- Cycle Time / Control Chart
- Work Distribution Charts  
- Issue Trend Analysis

See `docs/ANALYTICS_IMPLEMENTATION_PLAN.md` for full roadmap.

### Phase 3: Real Data Integration
When ready to connect to JIRA/OpenProject:

1. Create data adapters (e.g., `JiraAnalyticsAdapter`)
2. Update service to use adapters
3. Configure data source in `conf.yaml`

```python
# Switch to real data
service = AnalyticsService(data_source="jira")
```

## 📖 Documentation

- **Full docs**: `backend/analytics/README.md`
- **Implementation plan**: `docs/ANALYTICS_IMPLEMENTATION_PLAN.md`
- **Tests**: `tests/test_analytics.py`
- **Demo**: `test_analytics_demo.py`

## 🎉 What You Can Do Now

1. **Frontend developers**: Start building chart visualizations using the API
2. **PM users**: Ask the AI agent about project analytics
3. **Developers**: Extend with additional chart types  
4. **DevOps**: Deploy API endpoints

## 💡 Usage Examples

### Python API
```python
from backend.analytics.service import AnalyticsService

service = AnalyticsService(data_source="mock")

# Get burndown
burndown = service.get_burndown_chart("PROJECT-1", "SPRINT-1")

# Get velocity
velocity = service.get_velocity_chart("PROJECT-1", sprint_count=6)

# Get summary
summary = service.get_project_summary("PROJECT-1")
```

### REST API
```bash
# Test with curl
curl http://localhost:8000/api/analytics/projects/PROJECT-1/summary

# Or httpie
http GET localhost:8000/api/analytics/projects/PROJECT-1/velocity
```

### AI Agent
```
User: "Show me the velocity for PROJECT-1"

Agent: [Uses get_team_velocity tool]
       Average velocity: 43.5 story points
       Trend: increasing
       Latest sprint: 45.0 points
```

## ⚙️ Configuration

Current settings (in `backend/analytics/service.py`):
- **Data source**: "mock" (change to "jira" or "openproject" later)
- **Cache TTL**: 300 seconds (5 minutes)
- **Default sprint count**: 6 sprints for velocity

## 🔍 Troubleshooting

### Issue: No data returned
**Solution**: Make sure you're using mock data source for testing

### Issue: Chart calculation errors
**Solution**: Check that sprint dates are valid and work items have required fields

### Issue: API endpoints return 500
**Solution**: Check server logs for detailed error messages

## 📞 Support

For questions or issues:
1. Check the README: `backend/analytics/README.md`
2. Review the tests: `tests/test_analytics.py`
3. See implementation plan: `docs/ANALYTICS_IMPLEMENTATION_PLAN.md`

---

**Status**: ✅ Ready for use with mock data  
**Next Milestone**: Phase 2 - Additional chart types  
**Data Source**: Mock (ready for JIRA/OpenProject integration)







