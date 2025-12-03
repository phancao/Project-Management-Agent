# PM Agent Detection Indicators

## How to Know if PM Agent is Being Used

### Backend Logs Indicators

When PM Agent is used, you'll see these log messages:

1. **PM Query Detection**:
   ```
   [PLANNER] 🔵 PM QUERY DETECTED - Indicators: project_id: ..., keywords: ...
   [PLANNER] Using 'planner' template (has built-in PM query handling)
   ```

2. **PM Plan Detection**:
   ```
   [PLANNER] Step types: pm_query, pm_query, pm_query
   [PLANNER] ✅ PM PLAN DETECTED - Contains pm_query steps
   ```

3. **Agent Execution**:
   ```
   🎯 INVOKING AGENT: agent_name='pm_agent', step='...'
   ```

### Frontend Indicators

1. **Agent Badge in Step Boxes**:
   - Each tool call step shows an agent badge
   - **Blue badge with "PM Agent"** = PM Agent is executing
   - **Purple badge with "Researcher"** = Researcher is executing
   - **Green badge with "Coder"** = Coder is executing

2. **Step Box Display**:
   - Steps show: `#1 PM Agent` or `1/11 PM Agent`
   - Tool names are PM-specific: `list_tasks`, `sprint_report`, `velocity_chart`, etc.

3. **Analysis Block**:
   - Shows "AI Analysis" or plan title
   - Lists all tool calls with agent badges
   - PM Agent steps will show blue "PM Agent" badges

### PM Query Detection Keywords

The system detects PM queries by checking for these keywords in the user message:

#### Project Analysis
- "project analysis", "comprehensive project", "project status"
- "project performance", "project health", "project overview"
- "how is the project"

#### Sprint Analysis
- "sprint analysis", "analyze sprint", "analyse sprint"
- "sprint performance", "sprint metrics", "sprint velocity"
- "sprint report", "sprint [number]"

#### Resource Analysis
- "resource analysis", "resource allocation", "resource assignation"
- "workload analysis", "team workload", "resource utilization"

#### Epic Analysis
- "epic analysis", "epic progress", "epic status", "analyze epic"

#### Task Analysis
- "task analysis", "task completion", "task progress"
- "task metrics", "task statistics", "task distribution"

#### Team Metrics
- "team performance", "team velocity", "team metrics"
- "how is the team"

#### Analytics Charts
- "velocity chart", "burndown chart", "burndown analysis"
- "cfd chart", "cycle time", "work distribution"
- "issue trend", "issue trend analysis"

#### Data Queries
- "list tasks", "list sprints", "list projects", "list epics"
- "show tasks", "show sprints", "show projects", "show epics"
- "my tasks", "my projects"

### What Happens When PM Query is Detected

1. **Planner** detects PM keywords → Creates plan with `step_type: "pm_query"`
2. **Validation** checks plan → Ensures required tools are included
3. **Research Team** routes to **PM Agent** (not Researcher or Coder)
4. **PM Agent** executes steps → Calls PM tools (list_tasks, sprint_report, etc.)
5. **Reporter** generates report → Uses PM data from tool results

### Troubleshooting

#### If PM Agent is NOT being used:

1. **Check logs for PM QUERY DETECTED**:
   ```bash
   docker logs pm-backend-api | grep "PM QUERY DETECTED"
   ```

2. **Check step types in plan**:
   ```bash
   docker logs pm-backend-api | grep "Step types"
   ```
   - Should show: `pm_query, pm_query, pm_query`
   - If shows: `research, research` → Wrong! Should be `pm_query`

3. **Check agent name in execution**:
   ```bash
   docker logs pm-backend-api | grep "INVOKING AGENT"
   ```
   - Should show: `agent_name='pm_agent'`
   - If shows: `agent_name='researcher'` → Wrong routing!

4. **Check frontend agent badges**:
   - Look for blue "PM Agent" badges in step boxes
   - If you see purple "Researcher" badges → Wrong agent!

#### Common Issues:

1. **Missing Keywords**: Query doesn't match PM keywords → Add to `pm_keywords` list
2. **Wrong Step Type**: Planner creates `step_type: "research"` → Check planner prompt
3. **Routing Issue**: Steps are `pm_query` but routes to researcher → Check `_execute_agent_step`

### Example: Resource Assignation Query

**Query**: "analyse the resource assignation in this project"

**Expected Flow**:
1. ✅ PM QUERY DETECTED - Keywords: "resource assignation", "project"
2. ✅ Plan created with `step_type: "pm_query"`
3. ✅ Analysis type detected: `RESOURCE`
4. ✅ Required tools: `list_users`, `list_tasks`, `work_distribution_chart`
5. ✅ PM Agent executes steps
6. ✅ Frontend shows blue "PM Agent" badges

**Indicators to Check**:
- Backend logs: `[PLANNER] 🔵 PM QUERY DETECTED`
- Backend logs: `[PLANNER] ✅ PM PLAN DETECTED`
- Backend logs: `agent_name='pm_agent'`
- Frontend: Blue "PM Agent" badges in step boxes
- Frontend: PM tool names (list_tasks, work_distribution_chart, etc.)

