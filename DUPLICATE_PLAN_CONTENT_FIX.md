# Duplicate Plan Content Fix ✅

## Problem

**User Issue:** Plan content ("Sprint 5 Performance Analysis" description) displayed **twice** in the UI

**Example:**
```
AI Analysis
  Steps: 2
  
Sprint 5 Performance Analysis  ← FIRST
[full plan description]

Sprint 5 Performance Analysis  ← SECOND (duplicate!)
[same plan description]
```

---

## Root Cause

The planner message was being rendered **twice**:

1. **As a regular message** - showing its full content (plan description)
2. **Inside AnalysisBlock** - which also displays the plan content

The issue: Even though AnalysisBlock only uses the plan **title**, the planner message itself was being rendered as a regular message, showing its full JSON content (which includes the plan description).

---

## The Fix

### File: `web/src/app/pm/chat/components/message-list-view.tsx`

**Added early return** to skip rendering planner messages that are part of research blocks:

```typescript
// Check if this planner message is part of a research block
const researchPlanIds = useStore((state) => state.researchPlanIds);
const isPlannerInResearch = message.agent === "planner" && 
  researchPlanIds && 
  Array.from(researchPlanIds.values()).includes(message.id);

// Skip rendering planner messages that are part of research blocks
// They will be shown in AnalysisBlock instead
if (isPlannerInResearch) {
  return null;  // ← Don't render it!
}
```

**Why this works:**
- If planner message ID is in `researchPlanIds.values()`, it means it's part of a research block
- AnalysisBlock will display the plan (title + content via planMessage)
- So we skip rendering the planner message separately

---

## Expected Behavior

### Before Fix
```
UI shows:

[Planner Message]  ← Rendered as regular message
Sprint 5 Performance Analysis
[full plan description]

[AnalysisBlock]  ← Also shows plan
AI Analysis
  Sprint 5 Performance Analysis
  [plan description again]
  
Result: Duplicate plan content ❌
```

### After Fix
```
UI shows:

[AnalysisBlock ONLY]  ← Planner message skipped
AI Analysis
  Sprint 5 Performance Analysis
  Steps: 2
  [plan description shown once]
  
Result: Single, clean display ✅
```

---

## Test It! 🚀

**Refresh your browser** and try: "analyse sprint 5"

**You should see:**
- ✅ **ONE** "AI Analysis" block
- ✅ **ONE** plan title/description
- ✅ Steps listed once
- ✅ Clean, non-duplicate display

---

## Summary

✅ **Fixed:** Added early return to skip planner messages in research blocks
✅ **Fixed:** Planner messages now only shown in AnalysisBlock
✅ **Result:** No more duplicate plan content

**Key insight:** Planner messages that are part of research blocks should NOT be rendered separately - they're already included in AnalysisBlock!


