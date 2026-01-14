# Merged Debug Logs (Team EE Performance Investigation)

---

## Investigation Summary

**Issue**: Team EE page is extremely slow
**Date**: 2026-01-14T23:27

---

## Backend Logs

No backend logs found in the last 5 minutes (0 entries from pm-backend-api and pm-mcp-server).
This indicates the issue is **frontend-only**.

---

## Browser Console Logs (Captured via Browser Subagent)

```
[BROWSER] Console is being spammed with repetitive [PM-DEBUG][TIME_ENTRIES] logs
[BROWSER] allTimeEntries: 0
[BROWSER] FILTER: {allCount: 0, memberIds: Array(1), ...}
[BROWSER] The logs repeat continuously indicating a RE-RENDER LOOP
[BROWSER] React warnings about missing descriptions for DialogContent (unrelated)
[BROWSER] Memory usage: ~82.6 MB (stable)
```

---

## DOM Analysis

- **DOM Complexity Jump**: For just 1 member selected, total DOM elements jumped from 321 to 946
- **No Active Spinners**: Page appears loaded but unresponsive
- **Available Users List**: 638 users rendered without virtualization
- **MemberEfficiencyCard**: Renders dense calendar grid with many nested divs per cell

---

## Root Cause Analysis

### Primary Issue: Debug Logs Inside useMemo Causing Re-render Detection

File: `web/src/app/team/context/team-data-context.tsx`

**Problem Code (lines 296-314, 324-346)**:
```typescript
// Inside useQueries queryFn - logs on every query
queryFn: async () => {
    console.log('[PM-DEBUG][TIME_ENTRIES] QUERY:', { ... });  // LINE 297-302
    const result = await listTimeEntries({ ... });
    console.log('[PM-DEBUG][TIME_ENTRIES] RESULT:', { ... }); // LINE 309-313
    return result;
}

// Inside useMemo - logs on every recalculation
const allTimeEntries = useMemo(() => {
    ...
    console.log('[PM-DEBUG][TIME_ENTRIES] allTimeEntries:', entries.length); // LINE 331
    return entries;
}, [timeQueries]);

const teamTimeEntries = useMemo(() => {
    const filtered = allTimeEntries.filter(...);
    console.log('[PM-DEBUG][TIME_ENTRIES] FILTER:', { ... }); // LINE 337-344
    return filtered;
}, [allTimeEntries, memberIds]);
```

### Secondary Issue: Potential Array Reference Instability

The `memberIds` array passed as a dependency may be recreated on each render by parent components, causing the useMemo to recalculate repeatedly.

### Impact

1. Every component re-render triggers console.log spam
2. Console.log with complex objects (arrays) has performance overhead
3. Creates perception of "infinite loop" in React DevTools
4. Browser main thread blocked by excessive logging

---

## Recommended Fix

1. **Remove or conditionally disable debug logs** in production
2. **Memoize memberIds** at the calling component level
3. Consider using `useRef` for debug counters instead of inline console.log
