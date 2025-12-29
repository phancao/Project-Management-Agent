# Reporter Node

**Log Prefix:** `[PM-REPORTER]`  
**File:** `backend/graph/nodes.py` → `reporter_node()`

## Purpose
Generates final formatted output from collected data.

## Flow

```
Tool results collected
     ↓
reporter_node
     ↓
Format as markdown
     ↓
Stream to frontend
```

## Debug Logs

| Log Pattern | Meaning |
|-------------|---------|
| `[PM-REPORTER] Generating report` | Report generation started |
| `[PM-REPORTER] Context size:` | Input data size |
| `[PM-REPORTER] Report generated` | Complete |

## Output Format

Reporter produces markdown with:
- Summary section
- Data tables
- Key metrics
- Recommendations (for analysis)

## Common Issues

### Report missing data
- **Symptom:** Empty or incomplete report
- **Check:** Tool results before reporter
- **Fix:** Verify all tools completed successfully

### Duplicate reports
- **Symptom:** Same report appears twice
- **Check:** `final_report` state
- **Fix:** Clear state between queries

## See Also
- [06_streaming.md](06_streaming.md) - How report reaches frontend
