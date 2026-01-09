---
description: How to debug and fix issues following the strict PTAFVC protocol
---

# Debugging and Fix Issue Protocol

## Artifact Output Location

**ALL debug artifacts MUST be saved to the PROJECT directory, NOT the brain directory:**
```
/Volumes/Data 1/Gravity_ProjectManagementAgent/Project-Management-Agent/merged_debug_logs.md
```

## Artifact Files

| File | Purpose |
|------|---------|
| `merged_debug_logs.md` | **ONLY** raw debug logs - no analysis, no plans |
| `implementation_plan.md` | Analysis, root cause, fix solutions |
| `task.md` | Task checklist and progress tracking |

---

## PTAFVC Protocol (MUST FOLLOW)

### 1. **P**lan
Create solution plan in `implementation_plan.md`

### 2. **T**race - MANDATORY: Collect ALL Logs

**Step A**: Run Docker log collection - output to PROJECT directory
// turbo
```bash
python3 scripts/collect_debug_logs.py --since 5m --output merged_debug_logs.md
```

**Step B**: MANDATORY - Capture browser console logs from CURRENT tab

**CRITICAL**: You MUST use the `browser_subagent` to attach to the EXISTING tab. Do NOT navigate to the URL again, as this reloads the page.

```
Use browser_subagent with task:
"List browser pages. IDENTIFY the currently active 'Project Manager' tab.
Attach to that EXISTING page ID.
CRITICAL: Do NOT navigate to the URL again (which reloads/opens new tab). Just capture logs from the current state.
Capture console logs. Report logs containing: PM-DEBUG, MERGE, tool_calls, tool_call_result, SSE, STORE, RENDER, errors.
Also check DOM for tool entries and their status.
Return the FULL console log output as text."
```

**Step C**: IMMEDIATELY append browser logs to `merged_debug_logs.md`

After receiving browser logs from Step B, you MUST run this command to append them:
// turbo
```bash
cat >> merged_debug_logs.md << 'EOF'

---

## Browser Console Logs

```
[BROWSER] <paste each log line here with [BROWSER] prefix>
```
EOF
```

**CRITICAL**: You must PHYSICALLY WRITE the browser logs to the file using write_to_file or a shell command. Do NOT just "analyze" them in your head.

**Step C.1**: SORT logs by timestamp to interleave backend and browser chronologically

After appending browser logs, create a properly sorted timeline using Python:
// turbo
```bash
python3 -c "
import re
from pathlib import Path

content = Path('merged_debug_logs.md').read_text()
# Extract lines with timestamps (HH:MM:SS.mmm pattern)
lines = content.split('\n')
timestamped = []
other = []
for line in lines:
    match = re.search(r'(\d{2}:\d{2}:\d{2}\.\d{3})', line)
    if match:
        timestamped.append((match.group(1), line))
    else:
        other.append(line)
# Sort by timestamp
timestamped.sort(key=lambda x: x[0])
# Rebuild file
header = '''# Merged Debug Logs (Sorted by Timestamp)

---

## Full Timeline (Backend + Browser Merged)

\`\`\`
'''
footer = '''
\`\`\`
'''
sorted_content = header + '\n'.join([line for _, line in timestamped]) + footer
Path('merged_debug_logs.md').write_text(sorted_content)
print(f'Sorted {len(timestamped)} log entries by timestamp')
"
```

**Step D**: VERIFY - Check merged_debug_logs.md contains `[BROWSER]` entries
// turbo
```bash
grep -c "\[BROWSER\]" merged_debug_logs.md
```
⚠️ **DO NOT PROCEED TO ANALYZE IF COUNT IS 0** - browser logs are missing!

### 3. **A**nalyze
- Study `merged_debug_logs.md` (MUST contain BOTH `[BACKEND]` AND `[BROWSER]` logs)
- Document findings in `implementation_plan.md`

### 4. **F**ix
Implement the fix

### 5. **V**erify
// turbo
```bash
docker restart pm-backend-api pm-mcp-server && sleep 5
```
Then user tests. After test, collect logs again (repeat Step 2 above).

### 6. **C**leanup
After user confirms fix works, delete added debug code.

---

## Critical Rules

1. **NO FALLBACK OR MOCKUP DATA**
2. **NO DEDUPLICATION** - trace the actual issue
3. **ALWAYS use the script** for Docker log collection
4. **ALWAYS collect browser console logs** - use existing tab, don't open new tab
5. **ALWAYS verify browser logs exist in merged file before analyzing** - grep for [BROWSER]
6. **ALWAYS merge and arrange logs by timestamp**
7. **ALWAYS WRITE browser logs to the file** - do not just analyze them mentally
8. If fix doesn't work: mark as "NOT WORKING", revert, create new plan

---

## Script Options

// turbo
```bash
# Basic: Docker logs only (last 5 min)
python3 scripts/collect_debug_logs.py --since 5m --output merged_debug_logs.md
```

// turbo
```bash
# With time range
python3 scripts/collect_debug_logs.py --since 10m --output merged_debug_logs.md
```

---

## Example: Correct Log Merge

After Step A, `merged_debug_logs.md` contains:
```
02:48:24.031 [BACKEND] [PM-AGENT] 🔧 TOOL CALL: list_sprints(...)
02:48:24.517 [BACKEND] [PM-TOOLS] list_sprints completed in 0.49s
```

After Step C (appending browser logs), it should contain:
```
02:48:24.031 [BACKEND] [PM-AGENT] 🔧 TOOL CALL: list_sprints(...)
02:48:24.517 [BACKEND] [PM-TOOLS] list_sprints completed in 0.49s

---

## Browser Console Logs

[BROWSER] 02:48:24.100 [PM-DEBUG][RENDER] SHOW: id=tool-call-xxx, agent=pm_agent
[BROWSER] 02:48:24.200 [PM-DEBUG][SSE] YIELD: type=message_chunk
```