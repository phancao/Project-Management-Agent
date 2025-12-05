# Duplicate Research Block Fix ✅

## Problem

**User Issue:** "Why there is duplicated analysing block and it loading infinitely"

**Root Cause:** `react_agent` was NOT included in the list of agents that create research blocks!

---

## What Was Happening

### The Broken Flow

```
1. User: "analyse sprint 5"
   ↓
2. [REACT-AGENT] Starts execution
   ❌ NO research block created (react_agent not in list!)
   ↓
3. [REACT-AGENT] Error: 331K tokens (too large!)
   ⬆️ Escalates to planner
   ↓
4. [PLANNER] Creates plan
   ↓
5. [PM_AGENT] Executes first step
   ✅ Creates FIRST research block (pm_agent IS in list)
   ↓
6. [REPORTER] Generates report
   ✅ Uses the same research block
   ↓
7. [REACT-AGENT] Messages still streaming from step 2
   ✅ Creates SECOND research block (late!)
   ↓
RESULT: TWO research blocks! ❌
        One from pm_agent, one from react_agent
```

---

## The Code Bug

### File: `web/src/core/store/store.ts` (line 360-378)

**BEFORE (BROKEN):**
```typescript
function appendMessage(message: Message) {
  // Track research activities for all research-related agents
  if (
    message.agent === "coder" ||
    message.agent === "reporter" ||
    message.agent === "researcher" ||
    message.agent === "pm_agent"  // ← react_agent MISSING!
  ) {
    const ongoingResearchId = getOngoingResearchId();
    
    if (!ongoingResearchId) {
      const id = message.id;
      appendResearch(id);  // ← Creates research block
      openResearch(id);
    }
    appendResearchActivity(message);
  }
  useStore.getState().appendMessage(message);
}
```

**AFTER (FIXED):**
```typescript
function appendMessage(message: Message) {
  // Track research activities for all research-related agents
  if (
    message.agent === "coder" ||
    message.agent === "reporter" ||
    message.agent === "researcher" ||
    message.agent === "pm_agent" ||
    message.agent === "react_agent"  // ✅ NEW: Include ReAct agent
  ) {
    const ongoingResearchId = getOngoingResearchId();
    
    if (!ongoingResearchId) {
      const id = message.id;
      appendResearch(id);  // ← Creates research block
      openResearch(id);
    }
    appendResearchActivity(message);
  }
  useStore.getState().appendMessage(message);
}
```

---

## Why This Caused Duplicates

### Scenario 1: ReAct Success (No Escalation)
```
[REACT-AGENT] ✅ Success
    ↓
[REPORTER] Generates report
    ↓
✅ ONE research block (from react_agent)
```
**Result:** Works fine!

### Scenario 2: ReAct Escalates (The Bug!)
```
[REACT-AGENT] Starts (no research block yet)
    ↓
[REACT-AGENT] Escalates
    ↓
[PM_AGENT] Starts → Creates research block #1
    ↓
[REPORTER] Uses research block #1
    ↓
[REACT-AGENT] Late messages → Creates research block #2
    ↓
❌ TWO research blocks!
```
**Result:** Duplicate blocks, infinite loading!

---

## Why Infinite Loading?

The second research block (from react_agent) never gets a reporter message, so:
- `ongoingResearchId` stays set
- Frontend shows "Analyzing..." forever
- No report ever comes for the second block

---

## The Fix

Added `react_agent` to the list of agents that create research blocks.

**Now:**
1. **ReAct starts** → Creates research block immediately
2. **If ReAct escalates** → Uses the SAME research block
3. **PM_Agent runs** → Appends to existing research block
4. **Reporter completes** → Closes the research block

**Result:** ✅ ONE research block, no duplicates!

---

## Expected Behavior Now

### Scenario 1: Fast Path (ReAct Success)
```
[REACT-AGENT] Starts → Creates research block
[REACT-AGENT] ✅ Success
[REPORTER] Generates report → Closes research block
```
**UI:** One "AI Analysis" block, completes in 5-7s

### Scenario 2: Escalation (ReAct → Full Pipeline)
```
[REACT-AGENT] Starts → Creates research block
[REACT-AGENT] Escalates (data too large)
[PLANNER] Creates plan → Uses SAME research block
[PM_AGENT] Executes → Appends to SAME research block
[REPORTER] Generates report → Closes SAME research block
```
**UI:** One "AI Analysis" block, completes in 20-30s

---

## Test It! 🚀

**Try: "analyse sprint 5"**

**Before fix:**
```
UI: 
┌─────────────────────┐
│ AI Analysis (1)     │  ← From pm_agent
│ ✅ Complete         │
└─────────────────────┘

┌─────────────────────┐
│ AI Analysis (2)     │  ← From react_agent (late!)
│ 🔄 Analyzing...     │  ← Stuck forever!
└─────────────────────┘
```

**After fix:**
```
UI:
┌─────────────────────┐
│ AI Analysis         │  ← ONE block
│ ✅ Complete         │
└─────────────────────┘
```

---

## Files Changed

1. ✅ `web/src/core/store/store.ts`
   - Added `react_agent` to research block creation logic (line 367)

---

## Summary

✅ **Fixed:** Added `react_agent` to the list of agents that create research blocks
✅ **Result:** No more duplicate research blocks
✅ **Result:** No more infinite loading
✅ **UX:** Clean, single analysis block for all queries

**Key lesson:** When adding new agent types, remember to update ALL the places where agent types are checked (message rendering, research tracking, etc.)!


