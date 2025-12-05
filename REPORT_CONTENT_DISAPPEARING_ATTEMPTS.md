# Report Content Disappearing - Attempted Solutions

## Problem
Report block content streams successfully, then disappears right after it's fully filled.

## Attempted Solution #1 (FAILED - Reverted)

### Changes Made:
1. **Backend (`src/server/streaming.py`)**:
   - Modified `make_event()` to preserve content field for final events (even if empty)
   - Added logging for final events with empty content
   - Only remove empty content for non-final events

2. **Frontend (`web/src/core/messages/merge-message.ts`)**:
   - Added defensive check in `mergeTextMessage()` to preserve existing content when final event has no new content
   - Ensured contentChunks are preserved

3. **Frontend (`web/src/core/store/store.ts`)**:
   - Added defensive check in `updateMessage()` to preserve existing content if new message has empty content
   - Added defensive check in `updateMessages()` to preserve existing content
   - Added `alreadyUpdatedMessages` tracking to skip duplicate updates in cleanup loop

### Why It Failed:
The defensive checks didn't prevent the content from disappearing. The root cause is likely different - possibly:
- Content is being cleared at a different point in the flow
- The issue is with how React re-renders the component
- Content is being overwritten by a different mechanism
- The problem is in the ResearchReportBlock component itself

### Next Steps:
- Investigate the ResearchReportBlock component rendering logic
- Check if there's a React state update that's clearing content
- Look for any code that resets message content after streaming completes
- Check browser console for any errors during the disappearance
- Add more detailed logging to track exactly when content disappears

## Attempted Solution #2 (TESTING)

### Hypothesis:
The cleanup loop at lines 297-317 in `store.ts` is overwriting messages with stale versions. When we iterate over `state.messages.entries()`, we get message objects that might be stale (from before the final update), and then we call `updateMessage(msg)` which overwrites the good content with stale content.

### Root Cause:
1. When `finish_reason` is received, `updateMessage(message)` is called immediately with the merged message (line 265)
2. The cleanup loop then reads messages from `state.messages` (line 297)
3. If the message in the store is a stale reference (from before the final merge), it might have empty or incomplete content
4. The cleanup loop then calls `updateMessage(msg)` with this stale message, overwriting the good content

### Fix:
- Track messages that were already updated when `finish_reason` was received
- Skip those messages in the cleanup loop to prevent overwriting with stale versions
- This ensures that messages updated with the final merged content are not overwritten

### Result: FAILED - Content still disappeared

## Attempted Solution #3 (IN PROGRESS)

### Hypothesis:
The issue might be in how React re-renders or how the message object reference changes. The `displayContent` useMemo depends on `message?.content` and `message?.contentChunks`. If the message object is replaced entirely (new reference), React will recalculate, and if the new message has empty content, displayContent becomes empty.

### Investigation:
- Added comprehensive debug logging:
  1. **ResearchReportBlock**: Tracks content changes on every render
  2. **mergeMessage**: Logs content before/after merge for reporter messages
  3. **updateMessage**: Logs and prevents content loss for reporter messages
  4. **updateMessages**: Logs and prevents content loss in batch updates
  5. **Cleanup loop**: Logs when processing finished reporter messages
- All logs include messageId, content lengths, and stack traces for errors
- Next: Test and check browser console to see exactly when/where content disappears

