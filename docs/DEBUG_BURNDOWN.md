# Debugging Burndown Chart Issues

## How to View Backend Logs

### Option 1: Check the Terminal Running the Backend Server

If you started the backend server with:
```bash
python server.py
# or
uv run server.py
```

The logs will appear directly in that terminal.

### Option 2: Use the Log File

If you started the backend with:
```bash
bash scripts/dev/start_backend_with_logs.sh
```

Then view logs with:
```bash
bash scripts/dev/tail_backend_logs.sh
# or
tail -f logs/backend.log
```

### Option 3: Enable DEBUG Logging

To see detailed debug logs, restart the backend with DEBUG level:

```bash
python server.py --log-level debug
# or
uv run server.py --log-level debug
```

## What to Look For

When loading the burndown chart for Sprint 4, you should see logs like:

### 1. Task Discovery
```
[PMProviderAnalyticsAdapter] ===== BURNDOWN DEBUG START =====
[PMProviderAnalyticsAdapter] Project: ..., Sprint ID: ... 
[PMProviderAnalyticsAdapter] Found X total tasks in project
[PMProviderAnalyticsAdapter] Found Y tasks matching sprint ...
```

### 2. Task Completion Status
```
[PMProviderAnalyticsAdapter] Task 85982: title=..., status=..., is_burndowned=True/False, story_points=..., completed_at=...
[PMProviderAnalyticsAdapter]   Task 85982 raw: percentageComplete=100, status.isClosed=True, status.name=...
```

### 3. Status Mapping
```
[AnalyticsService] Task 85982 marked as completed=True, setting status to DONE
```

### 4. Burndown Calculation
```
[BurndownCalculator] Checking item 85982: status=TaskStatus.DONE, completed_at=..., story_points=...
[BurndownCalculator] Item 85982 counted as completed: X story_points on YYYY-MM-DD
```

## Common Issues

### Issue: No tasks found for sprint
- Check: `[PMProviderAnalyticsAdapter] Found 0 tasks matching sprint`
- Cause: Sprint ID mismatch or tasks not assigned to sprint
- Solution: Verify sprint_id in tasks matches the sprint ID being queried

### Issue: Tasks found but is_burndowned=False
- Check: `[PMProviderAnalyticsAdapter] Task ... is_burndowned=False`
- Cause: Task status resolver not detecting completion
- Solution: Check `percentageComplete` and `status.isClosed` in raw data

### Issue: Tasks not mapped to DONE
- Check: No `[AnalyticsService] Task ... marked as completed` logs
- Cause: `completed` flag not being set or checked correctly
- Solution: Verify `is_burndowned()` returns True for completed tasks

### Issue: Tasks DONE but not counted
- Check: `[BurndownCalculator] Checking item` but no "counted as completed" logs
- Cause: Completion date logic or date comparison issue
- Solution: Check if `completed_at` is set and date comparison is working

## Quick Test

1. Load the burndown chart for Sprint 4
2. Check backend logs for the entries above
3. Share the relevant log sections to diagnose the issue

