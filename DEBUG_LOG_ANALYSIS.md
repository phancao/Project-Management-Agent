# Debug Log Analysis Guide

## Where to Check Logs

The debug logs are in the **browser console** (not server logs). Open your browser's Developer Tools (F12) and go to the Console tab.

## What to Look For

### 1. ResearchReportBlock Logs
Look for logs like:
```
[ResearchReportBlock] messageId=xxx, contentLen=1234, chunksLen=5, chunksTotalLen=1234, isStreaming=false, finishReason=stop
```

**Key indicators:**
- `contentLen=0` when it should have content = content disappeared
- `chunksTotalLen > 0` but `contentLen=0` = content is in chunks but not in main content
- `❌ Content disappeared!` = content was lost after streaming completed

### 2. mergeMessage Logs
Look for logs like:
```
[Store] mergeMessage: messageId=xxx, contentBefore=1000, contentAfter=1200, eventType=message_chunk, hasFinishReason=false
```

**Key indicators:**
- `contentAfter=0` when `contentBefore > 0` = content lost during merge
- `❌ Content lost during merge!` = mergeMessage is clearing content

### 3. updateMessage Logs
Look for logs like:
```
[Store.updateMessage] ❌ REPORTER CONTENT LOSS! messageId=xxx, existingContentLen=5000, newContentLen=0, isStreaming=false, finishReason=stop
Stack trace for content loss
```

**Key indicators:**
- This error means `updateMessage` is trying to overwrite good content with empty content
- Check the stack trace to see what code path called `updateMessage`

### 4. updateMessages (Batch) Logs
Look for logs like:
```
[Store.updateMessages] ❌ REPORTER CONTENT LOSS in batch update! messageId=xxx, existingContentLen=5000, newContentLen=0
Stack trace for batch content loss
```

**Key indicators:**
- This means batch updates are clearing content
- Usually happens in the cleanup loop or scheduled updates

### 5. Cleanup Loop Logs
Look for logs like:
```
[Store] Cleanup loop found reporter message: messageId=xxx, contentLen=5000, finishReason=stop
[Store] Cleanup loop updating reporter message: messageId=xxx, contentLen=5000
```

**Key indicators:**
- `contentLen=0` in cleanup loop = message already has empty content when cleanup runs
- This suggests content was lost BEFORE the cleanup loop

## Analysis Steps

1. **Reproduce the issue** - Trigger a report generation
2. **Open browser console** - F12 → Console tab
3. **Filter logs** - Use browser console filter to show only logs containing:
   - `ResearchReportBlock`
   - `Store`
   - `❌`
   - `reporter`
4. **Look for the sequence:**
   - Content is present (contentLen > 0)
   - Content disappears (contentLen becomes 0)
   - Which log appears right before contentLen becomes 0?

## What to Report

When you see the content disappear, please share:

1. **The last log showing content present:**
   ```
   [ResearchReportBlock] messageId=xxx, contentLen=5000, ...
   ```

2. **The first log showing content gone:**
   ```
   [ResearchReportBlock] messageId=xxx, contentLen=0, ...
   ```

3. **Any error logs between them:**
   ```
   [Store.updateMessage] ❌ REPORTER CONTENT LOSS! ...
   ```

4. **The sequence of Store logs:**
   - All `mergeMessage` logs
   - All `updateMessage` logs  
   - All `updateMessages` logs
   - All cleanup loop logs

This will help identify exactly where and when the content is being lost.

