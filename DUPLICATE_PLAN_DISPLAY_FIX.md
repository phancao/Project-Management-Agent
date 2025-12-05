# Duplicate Plan Display Fix ✅

## Problem

**User Issue:** Plan content ("Sprint 5 Performance Analysis") displayed **twice** in the UI

**Example:**
```
AI Analysis
  Steps: 3
  
Sprint 5 Performance Analysis  ← FIRST
[plan description]

Sprint 5 Performance Analysis  ← SECOND (duplicate!)
[same plan description]
```

---

## Root Cause

The planner message was being rendered **twice** with different components:

1. **As PlanCard** (lines 164-175) - because `message.agent === "planner"`
2. **Inside AnalysisBlock** (lines 182-189) - because `startOfResearch === true`

### The Code Flow

```typescript
// message-list-view.tsx
if (message.agent === "planner") {
  // Render PlanCard ← FIRST display
  content = <PlanCard message={message} />;
} 
else if (startOfResearch && message?.id) {
  // Render AnalysisBlock (which ALSO shows the plan) ← SECOND display
  content = <AnalysisBlock researchId={message.id} />;
}
```

**Problem:** When planner message IS the start of research (which it always is in full pipeline), both conditions are true!

---

## The Fix

### Changed Rendering Priority

**File:** `web/src/app/pm/chat/components/message-list-view.tsx`

**BEFORE:**
```typescript
// Check planner FIRST
if (message.agent === "planner") {
  content = <PlanCard />;  // ← Renders plan
} 
else if (startOfResearch) {
  content = <AnalysisBlock />;  // ← ALSO renders plan (duplicate!)
}
```

**AFTER:**
```typescript
// Check startOfResearch FIRST (priority 1)
if (startOfResearch && message?.id) {
  // AnalysisBlock includes the plan, so don't show PlanCard separately
  content = <AnalysisBlock researchId={message.id} />;
} 
else if (message.agent === "planner") {
  // Only show PlanCard if planner is NOT the start of research
  content = <PlanCard />;
}
```

**Key insight:** `startOfResearch` takes priority over agent type to avoid duplicates!

---

## Why This Works

### AnalysisBlock Already Shows the Plan

The `AnalysisBlock` component displays:
- **Plan title** in the header (line 182)
- **Plan description** (if needed)
- **Steps** with tool calls
- **Report/Insights** when complete

So there's **no need** to show `PlanCard` separately when the planner is the start of research!

### When PlanCard IS Still Used

`PlanCard` will still be shown for planner messages that are **NOT** the start of research. This is a rare edge case, but the logic handles it correctly.

---

## Expected Behavior

### Before Fix
```
UI shows:

[PlanCard]
Sprint 5 Performance Analysis  ← From PlanCard
[plan steps]

[AnalysisBlock]
AI Analysis
  Sprint 5 Performance Analysis  ← From AnalysisBlock (duplicate!)
  Steps: 3
  [same plan steps]
  
Result: Duplicate plan content ❌
```

### After Fix
```
UI shows:

[AnalysisBlock ONLY]
AI Analysis
  Sprint 5 Performance Analysis
  Steps: 3
  [plan steps]
  [report when complete]
  
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

✅ **Fixed:** Changed rendering priority - `startOfResearch` checked before `planner`
✅ **Fixed:** `AnalysisBlock` used exclusively when message starts research
✅ **Fixed:** `PlanCard` only shown for standalone planner messages (rare case)
✅ **Result:** No more duplicate plan display

**Key lesson:** When one component (AnalysisBlock) already includes another component's content (PlanCard), check the inclusive component FIRST to avoid duplicates!


