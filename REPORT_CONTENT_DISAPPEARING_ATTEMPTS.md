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

## Attempted Solution #3 (FAILED - Reverted)

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
- Debug logs show content is present when finish_reason arrives, but disappears later

### Attempted Fix:
- Tracked messages updated with `finish_reason` using `messagesUpdatedWithFinishReason` Set
- Modified `scheduleUpdate()` to skip messages already updated with finish_reason
- Modified cleanup loop to skip messages already updated with finish_reason
- Goal: Prevent stale pending updates from overwriting finalized reporter content

### Why It Failed:
The fix didn't prevent content from disappearing. The root cause is likely different - possibly:
- Content is being cleared by a different mechanism (not pending updates)
- The issue is in how the message object is cloned/referenced
- React component is re-rendering with a stale message reference
- Content is being cleared by a subsequent event after finish_reason

### Next Steps:
- Check if there's a subsequent event (like tool_call_result) that's clearing content
- Investigate if `deepClone` in mergeMessage is causing issues
- Check if ResearchReportBlock is receiving a different message object reference
- Look for any code that resets or clears message content after streaming

## Attempted Solution #4 (FAILED - Reverted)

### Hypothesis:
Subsequent events (like `message_chunk`, `tool_calls`) are being processed for messages that already have `finish_reason`, and these events are overwriting the finalized content.

### Fix:
- Skip processing events for messages that already have `finish_reason` (except `tool_call_result` which is safe)
- This prevents subsequent events from overwriting finalized content

### Why It Failed:
The fix didn't prevent content from disappearing. This suggests the issue is not with subsequent events overwriting content.

### Next Steps:
- Check if the issue is in how `deepClone` preserves content/contentChunks
- Verify if `updateMessage` is properly preserving both `content` and `contentChunks`
- Check if ResearchReportBlock's `displayContent` computation is the issue
- Investigate if there's a React re-render issue where the message reference changes

## Attempted Solution #5 (FAILED - Reverted)

### Hypothesis:
For finalized reporter messages, we need to make them completely content-immutable - never allow content to be reduced or cleared, even if a new update has less content.

### Fix:
- Enhanced defensive checks in both `updateMessage` and `updateMessages`
- For reporter messages with `finishReason` and existing content, NEVER allow content to be reduced or cleared
- If new message has less content or empty content, always preserve existing content and contentChunks

### Why It Failed:
Even making finalized messages content-immutable didn't prevent the content from disappearing. This suggests the issue might be:
- Happening BEFORE updateMessage/updateMessages are called
- In how `mergeMessage` returns a deepClone (maybe the clone loses content?)
- In how the message is retrieved/displayed in the component
- A race condition where multiple updates happen simultaneously

### Next Steps:
- Check if `deepClone` in mergeMessage is properly preserving content
- Investigate if there's an issue with how messages are retrieved from the store
- Check if the issue is in the component's useMemo dependencies
- Look for any code that directly mutates the message object in the store

## Attempted Solution #6 (FAILED - Reverted)

### Hypothesis:
Content might be lost during the merge operation itself. If we preserve content before merging and restore it after merging for finalized reporter messages, we can prevent content loss at the source.

### Fix:
- Modified `mergeMessage` to preserve `content` and `contentChunks` for finalized reporter messages before merging
- After merging, restore preserved content if it was lost or reduced
- This prevents content loss during merge operations

### Why It Failed:
The fix didn't prevent content from disappearing. This suggests the issue is not in the merge operation itself.

### Next Steps:
- Need to investigate where content is actually being cleared
- Check browser console logs more carefully to see the exact sequence of events
- Consider if the issue is in how React renders the component or how useMessage hook retrieves the message
- Look for any direct state mutations or side effects that might clear content

## Attempted Solution #7 (FAILED - Reverted)

### Hypothesis:
Updates might be reducing content length (not just clearing it completely). For finalized reporter messages, we should always preserve the maximum content length to prevent any reduction.

### Fix:
- Modified both `updateMessage` and `updateMessages` to compare content lengths for finalized reporter messages
- If existing content is longer than new content, preserve the existing content
- This prevents any update from reducing content length, not just clearing it completely

### Why It Failed:
The fix didn't prevent content from disappearing. This suggests the issue is not with content length reduction during updates.

### Next Steps:
- All defensive approaches have failed - need to investigate the root cause more fundamentally
- Check if the issue is in how ResearchReportBlock retrieves/renders the message
- Verify if the messageId is changing or if the component is unmounting/remounting
- Check if there's a React state update that's causing the component to re-render with empty content
- Consider adding more detailed logging to track the exact moment content disappears

## Attempted Solution #8 (IN PROGRESS - Comprehensive Debug Logging)

### Approach:
Instead of trying to fix the issue blindly, add comprehensive debug logging throughout the entire workflow to trace exactly where content disappears. This systematic approach will help identify the root cause.

### Debug Logging Added:
1. **When reporter content starts streaming** (`[DEBUG-REPORTER-STREAM]`):
   - Logs when a message_chunk event is received for reporter
   - Shows chunk length and current content length
   - Shows first 50 chars of the chunk

2. **In mergeTextMessage** (`[DEBUG-MERGE-TEXT]`):
   - Logs before/after content and chunks length
   - Shows last 50 chars before and after merge
   - Shows the new chunk being added

3. **After mergeMessage** (`[DEBUG-REPORTER-MERGE]`):
   - Logs content length before→after merge
   - Logs chunks length before→after merge
   - Shows last 50 chars before and after
   - Warns if content is reduced or lost

4. **When finish_reason arrives** (`[DEBUG-REPORTER-FINISH]`):
   - Logs final content length and chunks length
   - Shows last 50 chars of final content

5. **When adding to pendingUpdates** (`[DEBUG-REPORTER-PENDING]`):
   - Logs when message is added to pending updates

6. **In scheduleUpdate** (`[DEBUG-REPORTER-SCHEDULE]`):
   - Logs when scheduled update processes reporter messages
   - Shows content and chunks length for each message

7. **In updateMessage** (`[DEBUG-REPORTER-UPDATE]`):
   - Logs existing→new content length
   - Logs existing→new chunks length
   - Shows last 50 chars of existing and new content
   - Includes stack trace

8. **In updateMessages (batch)** (`[DEBUG-REPORTER-BATCH]`):
   - Logs for each reporter message in batch
   - Shows content and chunks length changes
   - Shows last 50 chars before and after

9. **In cleanup loop** (`[DEBUG-REPORTER-CLEANUP]`):
   - Logs when cleanup processes reporter messages
   - Shows content and chunks length
   - Shows last 50 chars before cleanup
   - Includes stack trace

10. **In helper updateMessage** (`[DEBUG-REPORTER-HELPER]`):
    - Logs when helper function processes reporter messages
    - Shows content and chunks length
    - Shows last 50 chars
    - Includes stack trace

### Goal:
By tracking content through every step of the workflow, we can identify exactly where and when content disappears. The logs will show:
- The last point where content exists
- The first point where content is missing
- The function/operation that causes the loss
- Stack traces to see the call chain

### Next Steps:
- Run the application and collect debug logs
- Analyze the logs to find the exact point where content disappears
- Identify the function causing the issue
- Implement targeted fix based on findings

