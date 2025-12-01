# Frontend Charts - Comprehensive Learning Guide

## 📊 Overview

The **Frontend Charts** system is a comprehensive analytics dashboard built with **Next.js 15**, **React 19**, and **Recharts** to visualize project management metrics from the backend analytics API.

---

## 🏗️ Architecture

### **Technology Stack**

```yaml
Framework: Next.js 15 (App Router)
UI Library: React 19
Charts: Recharts 3.3.0
State Management: TanStack React Query (v5)
Styling: Tailwind CSS
UI Components: shadcn/ui (Radix UI)
Language: TypeScript
```

### **Directory Structure**

```
web/src/
├── app/pm/
│   ├── charts/
│   │   └── page.tsx                    ← Main charts dashboard page
│   └── chat/components/views/          ← Individual chart components
│       ├── burndown-view.tsx           ← Burndown chart
│       ├── velocity-view.tsx           ← Velocity chart
│       ├── cfd-view.tsx                ← Cumulative Flow Diagram
│       ├── cycle-time-view.tsx         ← Cycle Time chart
│       ├── sprint-report-view.tsx      ← Sprint Report view
│       ├── work-distribution-view.tsx  ← Work Distribution
│       └── issue-trend-view.tsx        ← Issue Trends
├── core/api/hooks/pm/
│   └── use-analytics.ts                ← API hooks for fetching chart data
├── components/ui/                      ← shadcn/ui components
│   ├── card.tsx
│   ├── tabs.tsx
│   ├── select.tsx
│   └── ...
└── lib/
    └── utils.ts                        ← Utility functions
```

---

## 📦 Key Components

### **1. Main Charts Page** (`app/pm/charts/page.tsx`)

**Purpose**: Dashboard page that displays all analytics charts with tabs

**Features**:
- ✅ **Overview Tab**: Shows mini versions of key charts + quick actions
- ✅ **Individual Chart Tabs**: Burndown, Velocity, Sprint Report, CFD, Cycle Time
- ✅ **Project Summary Cards**: Current sprint, average velocity, completion rate, trend
- ✅ **Tab Navigation**: Easy switching between different chart views
- ✅ **Responsive Layout**: Works on mobile, tablet, desktop

**Structure**:
```tsx
<PMLoadingProvider>
  <PMHeader />
  <PMLoadingManager />
  
  <main>
    {/* Project Summary Cards */}
    <SummaryCards data={projectSummary} />
    
    {/* Tabs for Different Charts */}
    <Tabs>
      <TabsList>
        <Tab>Overview</Tab>
        <Tab>Burndown</Tab>
        <Tab>Velocity</Tab>
        <Tab>Sprint Report</Tab>
        <Tab>CFD</Tab>
        <Tab>Cycle Time</Tab>
      </TabsList>
      
      <TabsContent value="overview">
        <MiniCharts />  {/* Small preview versions */}
        <QuickActions /> {/* Navigation buttons */}
      </TabsContent>
      
      <TabsContent value="burndown">
        <BurndownView />
      </TabsContent>
      
      {/* ... other tabs */}
    </Tabs>
  </main>
</PMLoadingProvider>
```

**Query Parameters**:
- `?project={projectId}` - Selects active project
- `?sprint={sprintId}` - Selects specific sprint (for sprint-specific charts)

---

### **2. Chart View Components**

All chart views follow a consistent pattern:

#### **A. Burndown View** (`burndown-view.tsx`)

**Purpose**: Track remaining work vs ideal progress over sprint duration

**Chart Type**: Area Chart (dual series)

**Key Features**:
- Sprint selector dropdown (filtered by status: active > future > completed)
- Real-time status indicator (On Track / Behind Schedule)
- 4 metric cards: Total Scope, Completed, Remaining, Progress %
- Scope changes breakdown (added, removed, net)
- Educational "What is a Burndown Chart?" card

**Data Flow**:
```
useSearchParams() → projectId, sprintId
   ↓
useSprints(projectId) → fetch available sprints
   ↓
useBurndownChart(projectId, sprintId) → fetch chart data
   ↓
Transform data for Recharts
   ↓
Render AreaChart with Ideal + Actual lines
```

**Code Pattern**:
```tsx
export function BurndownView() {
  const searchParams = useSearchParams();
  const projectId = searchParams?.get("project");
  const sprintId = searchParams?.get("sprint");
  
  // Fetch data
  const { sprints } = useSprints(projectId);
  const { data: chartData, isLoading, error } = useBurndownChart(projectId, sprintId);
  
  // Transform data for Recharts
  const burndownData = chartData?.series[0]?.data.map((point, index) => ({
    day: point.label,
    ideal: point.value,
    actual: chartData.series[1]?.data[index]?.value || 0,
  }));
  
  // Render
  return (
    <div>
      <MetricCards />
      <ResponsiveContainer>
        <AreaChart data={burndownData}>
          <Area dataKey="ideal" stroke="#8884d8" fill="url(#colorIdeal)" />
          <Area dataKey="actual" stroke="#82ca9d" fill="url(#colorActual)" />
        </AreaChart>
      </ResponsiveContainer>
      <ScopeChanges />
      <EducationalCard />
    </div>
  );
}
```

**Recharts Configuration**:
- **Chart Type**: `AreaChart`
- **Series**: 2 areas (Ideal, Actual)
- **Gradients**: Linear gradients for fill colors
- **Axes**: X (days), Y (story points/hours)
- **Tooltip**: Custom styling with background
- **Legend**: Automatic legend generation

---

#### **B. Velocity View** (`velocity-view.tsx`)

**Purpose**: Show team performance over multiple sprints

**Chart Type**: Bar Chart (grouped bars)

**Key Features**:
- Trend indicator badge (↗ Increasing, → Stable, ↘ Decreasing)
- 4 metric cards: Average, Median, Latest, Predictability
- Insights section with recommendations
- Educational "What is a Velocity Chart?" card

**Data Flow**:
```
useVelocityChart(projectId, sprintCount=6)
   ↓
Backend returns committed vs completed per sprint
   ↓
Transform to Recharts format
   ↓
Render BarChart with 2 bars per sprint
```

**Code Pattern**:
```tsx
export function VelocityView() {
  const { data: chartData } = useVelocityChart(projectId, 6);
  
  // Transform
  const velocityData = chartData?.series[0]?.data.map((point, index) => ({
    sprint: point.label,
    committed: point.value,
    completed: chartData.series[1]?.data[index]?.value || 0,
  }));
  
  // Render
  return (
    <BarChart data={velocityData}>
      <Bar dataKey="committed" fill="#94a3b8" />
      <Bar dataKey="completed" fill="#10b981" />
    </BarChart>
  );
}
```

**Recharts Configuration**:
- **Chart Type**: `BarChart`
- **Bars**: 2 grouped bars (Committed, Completed)
- **Colors**: Gray (#94a3b8) for committed, Green (#10b981) for completed
- **Radius**: Rounded corners `[4, 4, 0, 0]`
- **Label**: Y-axis label "Story Points"

---

#### **C. Sprint Report View** (`sprint-report-view.tsx`)

**Purpose**: Comprehensive sprint summary with all key metrics

**Layout Type**: Card-based layout (not a chart)

**Sections**:
1. **Sprint Header**: Name, dates, status
2. **Commitment Metrics**: Planned vs completed, completion rate
3. **Work Breakdown**: By type (stories, bugs, tasks)
4. **Team Performance**: Velocity, capacity utilization
5. **Scope Changes**: Added, removed, stability score
6. **Highlights**: Auto-generated positive achievements
7. **Concerns**: Auto-generated warnings and issues

**Data Structure**:
```typescript
interface SprintReport {
  sprint_id: string;
  sprint_name: string;
  duration: { start, end, days };
  commitment: { planned_points, completed_points, completion_rate };
  scope_changes: { added, removed, net_change, scope_stability };
  work_breakdown: { story: 10, bug: 3, task: 5 };
  team_performance: { velocity, capacity_utilized };
  highlights: string[];  // ["✅ Great completion", ...]
  concerns: string[];    // ["⚠️ Low capacity", ...]
}
```

---

#### **D. CFD View** (`cfd-view.tsx`)

**Purpose**: Visualize work flow through different states over time

**Chart Type**: Stacked Area Chart

**Key Features**:
- Shows accumulation of work in each state (To Do, In Progress, Done)
- Identifies bottlenecks (wide bands = slow flow)
- Date range selector (last 30/60/90 days)

**Recharts Configuration**:
- **Chart Type**: `AreaChart`
- **Stacking**: Multiple stacked areas
- **Colors**: Different color per state
- **Legend**: Shows all states

---

#### **E. Cycle Time View** (`cycle-time-view.tsx`)

**Purpose**: Track how long items take from start to finish

**Chart Type**: Scatter Plot / Control Chart

**Key Features**:
- Shows individual items as points
- Percentile lines (50th, 75th, 85th, 95th)
- Identifies outliers
- Helps predict delivery times

---

#### **F. Work Distribution View** (`work-distribution-view.tsx`)

**Purpose**: Show workload balance across team/priority/type

**Chart Type**: Pie Chart or Bar Chart

**Dimensions**:
- By Assignee (workload per person)
- By Priority (critical, high, medium, low)
- By Type (story, bug, task)
- By Status (to do, in progress, done)

---

### **3. API Hooks** (`core/api/hooks/pm/use-analytics.ts`)

**Purpose**: Centralized data fetching with React Query

**Pattern**: Each chart has a dedicated hook

#### **Available Hooks**:

```typescript
// Burndown Chart
useBurndownChart(projectId, sprintId?, scopeType="story_points")

// Velocity Chart
useVelocityChart(projectId, sprintCount=6)

// Sprint Report
useSprintReport(sprintId, projectId)

// Project Summary
useProjectSummary(projectId)

// Cumulative Flow Diagram
useCFDChart(projectId, sprintId?, daysBack=30)

// Cycle Time
useCycleTimeChart(projectId, sprintId?, daysBack=60)

// Work Distribution
useWorkDistributionChart(projectId, dimension="assignee", sprintId?)

// Issue Trends
useIssueTrendChart(projectId, daysBack=30, sprintId?)
```

#### **Hook Structure**:

```typescript
export function useBurndownChart(projectId, sprintId, scopeType) {
  const queryClient = useQueryClient();
  
  const query = useQuery({
    queryKey: ["analytics", "burndown", projectId, sprintId, scopeType],
    queryFn: async () => {
      const url = resolveServiceURL(`analytics/projects/${projectId}/burndown?...`);
      const response = await fetch(url);
      if (!response.ok) throw new Error(...);
      return response.json();
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,  // Cache for 5 minutes
    gcTime: 10 * 60 * 1000,     // Keep in cache for 10 minutes
  });
  
  // Auto-refresh on PM data changes
  usePMRefresh(() => {
    queryClient.invalidateQueries({ queryKey: [...] });
  });
  
  return query;
}
```

#### **Features**:
- ✅ **Automatic Caching**: 5-minute stale time, 10-minute garbage collection
- ✅ **Error Handling**: Detailed error messages with fallbacks
- ✅ **Auto-Refresh**: Invalidates on PM data changes via `usePMRefresh`
- ✅ **TypeScript**: Full type safety with interfaces
- ✅ **Loading States**: `isLoading`, `error`, `data`
- ✅ **Conditional Fetching**: Only fetches when `projectId` is provided

---

## 🎨 Recharts Components Used

### **Chart Types**

```typescript
// Area Chart (Burndown, CFD)
<AreaChart data={data}>
  <Area dataKey="ideal" stroke="#8884d8" fill="url(#gradient)" />
</AreaChart>

// Bar Chart (Velocity)
<BarChart data={data}>
  <Bar dataKey="committed" fill="#94a3b8" />
</BarChart>

// Line Chart (Trends)
<LineChart data={data}>
  <Line dataKey="created" stroke="#3b82f6" />
</LineChart>

// Pie Chart (Distribution)
<PieChart>
  <Pie data={data} dataKey="value" nameKey="name" />
</PieChart>
```

### **Common Components**

```typescript
<ResponsiveContainer width="100%" height={400}>
  <AreaChart data={data}>
    {/* Gradients */}
    <defs>
      <linearGradient id="colorIdeal" x1="0" y1="0" x2="0" y2="1">
        <stop offset="5%" stopColor="#8884d8" stopOpacity={0.3}/>
        <stop offset="95%" stopColor="#8884d8" stopOpacity={0}/>
      </linearGradient>
    </defs>
    
    {/* Grid */}
    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
    
    {/* Axes */}
    <XAxis dataKey="day" stroke="#666" />
    <YAxis stroke="#666" />
    
    {/* Tooltip */}
    <Tooltip 
      contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)' }}
      formatter={(value) => `${value.toFixed(1)}h`}
    />
    
    {/* Legend */}
    <Legend />
    
    {/* Data Series */}
    <Area dataKey="ideal" stroke="#8884d8" fill="url(#colorIdeal)" />
  </AreaChart>
</ResponsiveContainer>
```

---

## 🔄 Data Flow

### **End-to-End Flow**

```
1. User selects project in UI
   ↓
2. URL updates with ?project={id}
   ↓
3. Charts page reads URL params
   ↓
4. Hook fetches data from backend
   GET /api/analytics/projects/{id}/burndown
   ↓
5. Backend analytics service
   - Fetches from PM providers (or mock data)
   - Runs calculator (e.g., BurndownCalculator)
   - Returns ChartResponse JSON
   ↓
6. Frontend hook receives data
   - React Query caches result (5 min)
   - Component re-renders
   ↓
7. Data transformation
   - Backend format → Recharts format
   - Extract metadata (totals, percentages, etc.)
   ↓
8. Render chart
   - Recharts renders SVG
   - Shows loading/error states
   - Displays metrics cards
```

### **API Response Format**

All charts return a standardized format:

```json
{
  "chart_type": "burndown",
  "title": "Sprint 1 Burndown Chart",
  "series": [
    {
      "name": "Ideal",
      "data": [
        { "date": "2024-01-01", "value": 50.0, "label": "Day 1" }
      ],
      "color": "#94a3b8",
      "type": "line"
    },
    {
      "name": "Actual",
      "data": [
        { "date": "2024-01-01", "value": 50.0, "label": "Day 1" }
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
    "on_track": true
  },
  "generated_at": "2024-01-15T10:30:00"
}
```

---

## 🎯 Design Patterns

### **1. Consistent UI Pattern**

Every chart view follows this structure:

```tsx
export function ChartView() {
  // 1. URL params
  const searchParams = useSearchParams();
  const projectId = searchParams?.get("project");
  
  // 2. Fetch data
  const { data, isLoading, error } = useChartData(projectId);
  
  // 3. Loading state
  if (isLoading) return <LoadingSpinner />;
  
  // 4. Error state with educational card
  if (error) return (
    <>
      <ErrorCard error={error} />
      <EducationalCard />
    </>
  );
  
  // 5. Transform data
  const chartData = transformForRecharts(data);
  const metadata = data.metadata;
  
  // 6. Render
  return (
    <div className="space-y-6">
      {/* Header with title and actions */}
      <Header title={data.title} actions={<Filters />} />
      
      {/* Metric cards */}
      <MetricsGrid metadata={metadata} />
      
      {/* Main chart */}
      <Card>
        <ResponsiveContainer>
          <ChartComponent data={chartData} />
        </ResponsiveContainer>
      </Card>
      
      {/* Additional insights */}
      <InsightsCard metadata={metadata} />
      
      {/* Educational card */}
      <EducationalCard />
    </div>
  );
}
```

### **2. Error Handling Pattern**

```tsx
if (error) {
  return (
    <div className="space-y-6">
      <Card className="p-6 text-center">
        <div className="rounded-full bg-red-100 p-3">
          <span className="text-2xl">📊</span>
        </div>
        <h3>Unable to Load Chart</h3>
        <p>
          {error.message.includes("503") 
            ? "Chart not available for this project type."
            : "Error loading chart. Please try again."}
        </p>
      </Card>
      <EducationalCard />  {/* Always show educational value! */}
    </div>
  );
}
```

### **3. Data Transformation Pattern**

Backend format (server) → Frontend format (Recharts):

```typescript
// Backend series format
chartData.series = [
  { name: "Ideal", data: [{ date: "2024-01-01", value: 50 }] },
  { name: "Actual", data: [{ date: "2024-01-01", value: 48 }] }
]

// Transform to Recharts format
const rechartsData = chartData.series[0].data.map((point, index) => ({
  day: point.label || formatDate(point.date),
  ideal: point.value,
  actual: chartData.series[1]?.data[index]?.value || 0,
}));

// Recharts expects: [{ day: "Day 1", ideal: 50, actual: 48 }]
```

### **4. Metrics Card Pattern**

```tsx
<div className="grid grid-cols-1 md:grid-cols-4 gap-4">
  <Card className="p-4">
    <div className="text-sm text-gray-500">Total Scope</div>
    <div className="text-2xl font-bold text-gray-900">
      {metadata.total_scope.toFixed(1)} pts
    </div>
  </Card>
  {/* ... 3 more cards */}
</div>
```

---

## 🚀 Key Features

### **1. Real-Time Updates**

```typescript
// Auto-refresh when PM data changes
usePMRefresh(() => {
  queryClient.invalidateQueries({ queryKey: ["analytics", ...] });
});
```

### **2. Smart Caching**

```typescript
staleTime: 5 * 60 * 1000,  // Data fresh for 5 minutes
gcTime: 10 * 60 * 1000,    // Cache for 10 minutes
```

### **3. Responsive Design**

```tsx
// Mobile-first grid
<div className="grid grid-cols-1 md:grid-cols-4 gap-4">
  {/* Cards */}
</div>

// Responsive container
<ResponsiveContainer width="100%" height={400}>
  <AreaChart>...</AreaChart>
</ResponsiveContainer>
```

### **4. Dark Mode Support**

```tsx
<div className="bg-gray-50 dark:bg-gray-900">
  <h1 className="text-gray-900 dark:text-white">Title</h1>
  <p className="text-gray-600 dark:text-gray-400">Subtitle</p>
</div>
```

### **5. Educational Cards**

Every chart includes an explanation:

```tsx
const BurndownDescription = () => (
  <Card className="p-6 bg-blue-50 dark:bg-blue-900/20">
    <h3>📊 What is a Burndown Chart?</h3>
    <p>A burndown chart tracks...</p>
    <ul>
      <li>Monitor if team is on track</li>
      <li>Identify ahead/behind schedule</li>
    </ul>
  </Card>
);
```

---

## 🛠️ Common Tasks

### **Add a New Chart**

1. **Create view component**:
```tsx
// web/src/app/pm/chat/components/views/my-chart-view.tsx
export function MyChartView() {
  const { data } = useMyChart(projectId);
  return <BarChart data={data} />;
}
```

2. **Add API hook**:
```typescript
// web/src/core/api/hooks/pm/use-analytics.ts
export function useMyChart(projectId: string) {
  return useQuery({
    queryKey: ["analytics", "myChart", projectId],
    queryFn: async () => {
      const url = resolveServiceURL(`analytics/projects/${projectId}/my-chart`);
      return fetch(url).then(r => r.json());
    },
    enabled: !!projectId,
  });
}
```

3. **Add to charts page**:
```tsx
// web/src/app/pm/charts/page.tsx
import { MyChartView } from "../chat/components/views/my-chart-view";

<TabsList>
  <TabsTrigger value="my-chart">My Chart</TabsTrigger>
</TabsList>

<TabsContent value="my-chart">
  <MyChartView />
</TabsContent>
```

### **Customize Chart Colors**

```tsx
// For consistency, use these colors:
const CHART_COLORS = {
  ideal: "#8884d8",    // Blue
  actual: "#82ca9d",   // Green
  committed: "#94a3b8", // Gray
  completed: "#10b981", // Green
  warning: "#f59e0b",   // Amber
  danger: "#ef4444",    // Red
};
```

### **Add Custom Tooltip**

```tsx
<Tooltip 
  contentStyle={{ 
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    border: '1px solid #ccc',
    borderRadius: '8px'
  }}
  formatter={(value: number) => [
    `${value.toFixed(1)} pts`,
    'Story Points'
  ]}
/>
```

---

## 📱 Responsive Breakpoints

```css
/* Tailwind breakpoints used */
sm: 640px   /* Small devices */
md: 768px   /* Tablets */
lg: 1024px  /* Laptops */
xl: 1280px  /* Desktops */
2xl: 1536px /* Large screens */
```

**Usage in components**:
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  {/* 1 col mobile, 2 cols tablet, 4 cols desktop */}
</div>
```

---

## 🎨 UI Component Library

Built with **shadcn/ui** (Radix UI + Tailwind):

```tsx
import { Card } from "~/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "~/components/ui/tabs";
import { Select, SelectTrigger, SelectContent, SelectItem } from "~/components/ui/select";
import { Button } from "~/components/ui/button";
```

All components are:
- ✅ Fully accessible (ARIA)
- ✅ Keyboard navigable
- ✅ Dark mode compatible
- ✅ Customizable with Tailwind

---

## 🔍 Debugging Tips

### **Check API Response**
```typescript
const { data } = useBurndownChart(projectId, sprintId);
console.log("Chart data:", data);
console.log("Metadata:", data?.metadata);
```

### **Inspect React Query Cache**
```tsx
import { useQueryClient } from "@tanstack/react-query";

const queryClient = useQueryClient();
console.log(queryClient.getQueryData(["analytics", "burndown", projectId]));
```

### **Enable Debug Mode**
```bash
# In .env
NEXT_PUBLIC_DEBUG=true
```

---

## 📊 Chart Status

| Chart | Status | Component | Hook | Backend |
|-------|--------|-----------|------|---------|
| Burndown | ✅ Complete | `burndown-view.tsx` | `useBurndownChart` | ✅ |
| Velocity | ✅ Complete | `velocity-view.tsx` | `useVelocityChart` | ✅ |
| Sprint Report | ✅ Complete | `sprint-report-view.tsx` | `useSprintReport` | ✅ |
| CFD | ✅ Complete | `cfd-view.tsx` | `useCFDChart` | ✅ |
| Cycle Time | ✅ Complete | `cycle-time-view.tsx` | `useCycleTimeChart` | ✅ |
| Work Distribution | ✅ Complete | `work-distribution-view.tsx` | `useWorkDistributionChart` | ✅ |
| Issue Trends | ✅ Complete | `issue-trend-view.tsx` | `useIssueTrendChart` | ✅ |

---

## 🚀 Next Steps

### **Potential Enhancements**:

1. **Export Functionality**: Download charts as PNG/PDF
2. **Date Range Picker**: More flexible date filtering
3. **Comparison Mode**: Compare multiple sprints side-by-side
4. **Real-Time Updates**: WebSocket for live chart updates
5. **Custom Dashboards**: User-configurable layouts
6. **Chart Annotations**: Add notes/comments to specific data points
7. **Mobile App**: React Native version

---

## 📚 Quick Reference

### **Import Recharts Components**
```typescript
import { 
  AreaChart, Area,
  BarChart, Bar,
  LineChart, Line,
  PieChart, Pie,
  CartesianGrid, XAxis, YAxis,
  Tooltip, Legend,
  ResponsiveContainer
} from "recharts";
```

### **Fetch Chart Data**
```typescript
import { useBurndownChart } from "~/core/api/hooks/pm/use-analytics";

const { data, isLoading, error } = useBurndownChart(projectId, sprintId);
```

### **Render Chart**
```tsx
<ResponsiveContainer width="100%" height={400}>
  <AreaChart data={chartData}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="day" />
    <YAxis />
    <Tooltip />
    <Legend />
    <Area dataKey="ideal" stroke="#8884d8" fill="url(#gradient)" />
  </AreaChart>
</ResponsiveContainer>
```

---

**Status**: ✅ Frontend Charts fully documented and understood!  
**Generated**: 2025-11-24  
**Technology**: Next.js 15 + React 19 + Recharts 3.3

