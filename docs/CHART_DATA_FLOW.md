# Chart Data Flow Documentation

This document explains how charts get, handle, and present data in the Project Management Agent.

## Overview

The chart system follows a layered architecture:
1. **Frontend Hook** - Fetches data from API
2. **Backend API Endpoint** - Receives request and routes to service
3. **Analytics Service** - Orchestrates data fetching and calculation
4. **Analytics Adapter** - Fetches raw data from PM providers (JIRA, OpenProject, etc.)
5. **Calculator** - Processes raw data into chart-ready format
6. **Chart View Component** - Renders the visual chart

## Complete Data Flow (Example: Burndown Chart)

### 1. Frontend Hook (`web/src/core/api/hooks/pm/use-analytics.ts`)

```typescript
export function useBurndownChart(projectId: string | null, sprintId?: string, scopeType: string = "story_points") {
  return useQuery({
    queryKey: ["analytics", "burndown", projectId, sprintId, scopeType],
    queryFn: async () => {
      if (!projectId) throw new Error("Project ID is required");
      
      const params = new URLSearchParams();
      if (sprintId) params.append("sprint_id", sprintId);
      params.append("scope_type", scopeType);
      
      const url = resolveServiceURL(`analytics/projects/${projectId}/burndown?${params.toString()}`);
      const response = await fetch(url);
      
      if (!response.ok) {
        // Error handling...
        throw new Error(`Failed to fetch burndown chart: ${errorDetail}`);
      }
      
      return response.json() as Promise<ChartResponse>;
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes cache
  });
}
```

**What it does:**
- Uses React Query (`useQuery`) for data fetching and caching
- Constructs API URL with query parameters
- Handles errors and extracts error details from response
- Returns a `ChartResponse` object

### 2. Backend API Endpoint (`backend/server/app.py`)

```python
@app.get("/api/analytics/projects/{project_id}/burndown")
async def get_burndown_chart(
    project_id: str,
    sprint_id: Optional[str] = None,
    scope_type: str = "story_points"
):
    """Get burndown chart for a project/sprint"""
    try:
        from database.connection import get_db_session
        db_gen = get_db_session()
        db = next(db_gen)
        try:
            # Get analytics service configured for this project
            analytics_service = get_analytics_service(project_id, db)
            
            # Extract actual project ID if in provider_id:project_id format
            actual_project_id = (
                project_id.split(":", 1)[1]
                if ":" in project_id
                else project_id
            )
            
            # Call service to get chart data
            chart = await analytics_service.get_burndown_chart(
                project_id=actual_project_id,
                sprint_id=sprint_id,
                scope_type=scope_type
            )
            
            # Return as JSON (Pydantic model automatically serializes)
            return chart.model_dump()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to get burndown chart: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

**What it does:**
- Receives HTTP GET request with project_id, sprint_id, scope_type
- Gets database session
- Creates analytics service for the project (determines which PM provider to use)
- Extracts actual project ID from composite format (`provider_id:project_id`)
- Calls analytics service method
- Returns JSON response

### 3. Analytics Service (`backend/analytics/service.py`)

```python
class AnalyticsService:
    def __init__(self, adapter: Optional[BaseAnalyticsAdapter] = None):
        self.adapter = adapter
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def get_burndown_chart(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        scope_type: Literal["story_points", "tasks", "hours"] = "story_points"
    ) -> ChartResponse:
        # Check cache first
        cache_key = f"burndown_{project_id}_{sprint_id}_{scope_type}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # If no adapter, return empty chart
        if not self.adapter:
            return ChartResponse(
                chart_type=ChartType.BURNDOWN,
                title="Sprint Burndown",
                series=[],
                metadata={"message": "No data source configured."},
            )
        
        # Fetch raw data from PM provider via adapter
        sprint_data = await self.adapter.get_burndown_data(project_id, sprint_id, scope_type)
        
        if sprint_data is None:
            return ChartResponse(...)  # Empty response
        
        # Convert payload to SprintData model if needed
        if not isinstance(sprint_data, SprintData):
            sprint_data = self._payload_to_sprint_data(sprint_data, project_id)
        
        # Calculate chart data using calculator
        result = BurndownCalculator.calculate(sprint_data, scope_type)
        
        # Cache result
        self._set_cache(cache_key, result)
        
        return result
```

**What it does:**
- Checks cache first (5-minute TTL)
- Uses adapter to fetch raw data from PM provider
- Converts raw data to standardized `SprintData` model
- Calls calculator to process data into chart format
- Caches result for performance
- Returns `ChartResponse` with series and metadata

### 4. Analytics Adapter (`backend/analytics/adapters/pm_adapter.py`)

```python
class PMProviderAnalyticsAdapter(BaseAnalyticsAdapter):
    def __init__(self, provider: BasePMProvider):
        self.provider = provider
    
    async def get_burndown_data(
        self,
        project_id: str,
        sprint_id: Optional[str] = None,
        scope_type: str = "story_points"
    ) -> Dict[str, Any]:
        """Fetch burndown data from PM provider"""
        project_key = self._extract_project_key(project_id)
        
        # Get sprint info
        if not sprint_id:
            sprints = await self.provider.list_sprints(project_id=project_key, state="active")
            sprint = sprints[0] if sprints else None
            sprint_id = sprint.id if sprint else None
        else:
            sprint = await self.provider.get_sprint(sprint_id)
        
        # Get all tasks in the sprint
        all_tasks = await self.provider.list_tasks(project_id=project_key)
        sprint_tasks = [t for t in all_tasks if t.sprint_id == sprint_id]
        
        # Transform tasks for calculator
        tasks_data = []
        for task in sprint_tasks:
            story_points = 0
            if task.raw_data and "storyPoints" in task.raw_data:
                story_points = task.raw_data["storyPoints"] or 0
            elif task.estimated_hours:
                story_points = task.estimated_hours / 8  # Convert hours to points
            
            status_lower = (task.status or "").lower()
            is_completed = any(keyword in status_lower for keyword in ["done", "closed", "completed"])
            
            tasks_data.append({
                "id": task.id,
                "title": task.title,
                "story_points": story_points,
                "status": task.status,
                "completed": is_completed,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            })
        
        return {
            "sprint": {
                "id": sprint.id,
                "name": sprint.name,
                "start_date": sprint.start_date.isoformat(),
                "end_date": sprint.end_date.isoformat(),
                "status": sprint.status,
            },
            "tasks": tasks_data,
        }
```

**What it does:**
- Extracts project key from composite ID
- Calls PM provider methods (`list_sprints`, `list_tasks`, `get_sprint`)
- Filters tasks by sprint
- Transforms provider-specific data format to standardized format
- Extracts story points (from raw_data or converts from hours)
- Determines completion status
- Returns dictionary with sprint info and tasks

### 5. Calculator (`backend/analytics/calculators/burndown.py`)

```python
class BurndownCalculator:
    @staticmethod
    def calculate(
        sprint_data: SprintData,
        scope_type: Literal["story_points", "tasks", "hours"] = "story_points"
    ) -> ChartResponse:
        # Calculate total scope
        if scope_type == "story_points":
            total_scope = sum(item.story_points or 0 for item in sprint_data.work_items)
        elif scope_type == "hours":
            total_scope = sum(item.estimated_hours or 0 for item in sprint_data.work_items)
        else:
            total_scope = len(sprint_data.work_items)
        
        # Account for scope changes
        added_scope = sum(...)
        removed_scope = sum(...)
        final_scope = total_scope + added_scope - removed_scope
        
        # Generate ideal line (linear burndown)
        ideal_series = BurndownCalculator._calculate_ideal_line(
            sprint_data.start_date,
            sprint_data.end_date,
            final_scope
        )
        
        # Generate actual line (based on completed work)
        actual_series = BurndownCalculator._calculate_actual_line(
            sprint_data,
            scope_type,
            final_scope
        )
        
        # Calculate metadata
        completed = final_scope - actual_series.data[-1].value
        remaining = actual_series.data[-1].value
        completion_percentage = (completed / final_scope * 100) if final_scope > 0 else 0
        on_track = current_actual <= ideal_value
        
        return ChartResponse(
            chart_type=ChartType.BURNDOWN,
            title=f"{sprint_data.name} Burndown Chart",
            series=[ideal_series, actual_series],
            metadata={
                "total_scope": round(final_scope, 2),
                "remaining": round(remaining, 2),
                "completed": round(completed, 2),
                "completion_percentage": round(completion_percentage, 2),
                "on_track": on_track,
                ...
            }
        )
```

**What it does:**
- Calculates total scope (story points, hours, or task count)
- Accounts for scope changes (added/removed items)
- Generates ideal burndown line (linear from start to end)
- Generates actual burndown line (based on completed work per day)
- Calculates metadata (completion %, on track status, etc.)
- Returns `ChartResponse` with two series (ideal and actual) plus metadata

### 6. Chart View Component (`web/src/app/pm/chat/components/views/burndown-view.tsx`)

```typescript
export function BurndownView() {
  const searchParams = useSearchParams();
  const projectId = searchParams?.get("project");
  const sprintParam = searchParams?.get("sprint");
  
  // Fetch sprints for selection
  const { sprints, loading: sprintsLoading } = useSprints(projectId ?? "");
  
  // Fetch chart data
  const { data: chartData, isLoading: loading, error } = useBurndownChart(projectId, selectedSprintId);
  
  // Transform chart data for Recharts
  const burndownData = chartData?.series[0]?.data.map((point, index) => {
    const actualPoint = chartData.series[1]?.data[index];
    return {
      day: point.label || new Date(point.date!).toLocaleDateString(),
      ideal: point.value,
      actual: actualPoint?.value || 0,
    };
  }) || [];
  
  // Extract metadata
  const metadata = chartData?.metadata || {};
  const totalScope = metadata.total_scope || 0;
  const remaining = metadata.remaining || 0;
  const completed = metadata.completed || 0;
  const onTrack = metadata.on_track || false;
  
  // Render chart
  return (
    <div className="space-y-6">
      {/* Header with sprint selector */}
      <Select value={selectedSprintId} onValueChange={handleSprintChange}>
        {/* Sprint selection dropdown */}
      </Select>
      
      {/* Metrics Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card>Total Scope: {totalScope}</Card>
        <Card>Completed: {completed}</Card>
        <Card>Remaining: {remaining}</Card>
        <Card>Progress: {completionPercentage}%</Card>
      </div>
      
      {/* Chart */}
      <Card>
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={burndownData}>
            <Area dataKey="ideal" name="Ideal Burndown" />
            <Area dataKey="actual" name="Actual Burndown" />
            <XAxis dataKey="day" />
            <YAxis />
            <Tooltip />
            <Legend />
          </AreaChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
}
```

**What it does:**
- Uses React hooks to fetch chart data
- Transforms backend data format to Recharts format
- Extracts metadata for display in cards
- Renders UI components (sprint selector, metrics cards, chart)
- Handles loading and error states

## Data Models

### ChartResponse (Backend)
```python
class ChartResponse(BaseModel):
    chart_type: ChartType
    title: str
    series: List[ChartSeries]
    metadata: Dict[str, Any]
    generated_at: datetime

class ChartSeries(BaseModel):
    name: str
    data: List[ChartDataPoint]
    color: Optional[str] = None
    type: Optional[str] = None

class ChartDataPoint(BaseModel):
    date: Optional[datetime] = None
    value: float
    label: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
```

### ChartResponse (Frontend TypeScript)
```typescript
export interface ChartResponse {
  chart_type: string;
  title: string;
  series: ChartSeries[];
  metadata: Record<string, any>;
  generated_at: string;
}

export interface ChartSeries {
  name: string;
  data: ChartDataPoint[];
  color?: string;
  type?: string;
}

export interface ChartDataPoint {
  date?: string;
  value: number;
  label?: string;
  metadata?: Record<string, any>;
}
```

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Frontend: BurndownView Component                              │
│    - User selects sprint                                         │
│    - Calls useBurndownChart(projectId, sprintId)                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Frontend Hook: useBurndownChart                               │
│    - Constructs API URL: /api/analytics/projects/{id}/burndown  │
│    - Fetches with React Query                                    │
│    - Returns ChartResponse                                       │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼ HTTP GET
┌─────────────────────────────────────────────────────────────────┐
│ 3. Backend API: /api/analytics/projects/{project_id}/burndown    │
│    - Extracts project_id from URL                                │
│    - Gets database session                                       │
│    - Creates AnalyticsService with adapter                        │
│    - Calls analytics_service.get_burndown_chart()                │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. AnalyticsService.get_burndown_chart()                         │
│    - Checks cache (5 min TTL)                                    │
│    - Calls adapter.get_burndown_data()                           │
│    - Converts to SprintData model                                │
│    - Calls BurndownCalculator.calculate()                        │
│    - Caches and returns ChartResponse                            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. PMProviderAnalyticsAdapter.get_burndown_data()               │
│    - Extracts project key                                       │
│    - Calls provider.list_sprints()                              │
│    - Calls provider.list_tasks()                                │
│    - Filters tasks by sprint                                     │
│    - Transforms to standardized format                           │
│    - Returns dict with sprint info and tasks                     │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. PM Provider (JIRA/OpenProject/Mock)                          │
│    - Makes API calls to external service                         │
│    - Returns PMTask, PMSprint objects                            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. BurndownCalculator.calculate()                                │
│    - Calculates total scope                                     │
│    - Generates ideal line (linear burndown)                      │
│    - Generates actual line (from completed work)                 │
│    - Calculates metadata (completion %, on track, etc.)          │
│    - Returns ChartResponse with series and metadata              │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. Backend returns JSON ChartResponse                            │
│    - Series: [ideal_series, actual_series]                      │
│    - Metadata: {total_scope, remaining, completed, ...}          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. Frontend: BurndownView receives data                         │
│    - Transforms to Recharts format                              │
│    - Displays metrics cards                                     │
│    - Renders AreaChart with ideal and actual lines               │
└─────────────────────────────────────────────────────────────────┘
```

## Key Features

### Caching
- **Backend**: 5-minute cache in AnalyticsService
- **Frontend**: React Query cache (5-minute staleTime)

### Error Handling
- **Frontend**: Extracts error details from response body
- **Backend**: Logs errors with full traceback, returns appropriate HTTP status codes

### Data Transformation
- **Adapter**: Converts provider-specific format → standardized format
- **Calculator**: Processes standardized data → chart-ready format
- **Frontend**: Transforms chart format → Recharts format

### Provider Abstraction
- Adapter pattern allows different PM providers (JIRA, OpenProject, Mock)
- All providers implement same interface
- Calculators work with standardized data models

## Other Charts

All charts follow the same pattern:
- **Velocity Chart**: Uses `VelocityCalculator`, fetches multiple sprints
- **CFD Chart**: Uses `calculate_cfd()`, fetches tasks with status history
- **Cycle Time Chart**: Uses `calculate_cycle_time()`, fetches completed tasks
- **Work Distribution**: Uses `calculate_work_distribution()`, groups by dimension
- **Issue Trend**: Uses `calculate_issue_trend()`, tracks created/resolved over time

Each chart has its own:
- Calculator function/class
- Adapter method to fetch data
- Service method to orchestrate
- API endpoint
- Frontend hook
- View component

