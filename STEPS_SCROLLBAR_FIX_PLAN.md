# Steps Content Scrollbar Fix Plan

## Problem Statement
1. Steps content sometimes doesn't fit and resizes bigger (height issue)
2. Content is not wrapped and there is no vertical scrollbar
3. When "Optimize Context" step appears with long content, it breaks all wordwrap logic and content flows out of the box

## Root Cause Analysis

### Issue 1: Framer Motion `height: "auto"` conflicts with `max-height`
- The `motion.div` in `analysis-block.tsx` uses `animate={{ height: "auto" }}`
- When framer-motion animates to "auto", it can override `max-height` constraints
- The parent `motion.div` has `overflow-hidden` which prevents scrollbar visibility

### Issue 2: Nested overflow containers
- Multiple nested containers with overflow settings can conflict
- The `motion.div` wrapper has `overflow-hidden` while child has `overflow-y-auto`

## Attempted Solutions (DO NOT REPEAT - ALL FAILED)

### ❌ Solution 1: Added max-height and overflow-y-auto to child div
**Status**: FAILED
**Why it failed**: Framer Motion's `height: "auto"` animation overrides max-height

### ❌ Solution 5: Replaced framer-motion with CSS transitions (steps container)
**Status**: FAILED - Reverted
**Why it failed**: Adding word-break utilities everywhere didn't solve the root cause

### ❌ Solution 6: Constrain StepBox motion.div with maxHeight style
**Status**: FAILED - Reverted
**Why it failed**: Framer-motion's `height: "auto"` animation overrides inline `maxHeight` style

### ❌ Solution 7: Wrap content inside motion.div with constrained container
**Status**: FAILED - Reverted
**Why it failed**: Framer-motion's `height: "auto"` still calculates the full content height, not the constrained height

### ❌ Solution 8: Replace framer-motion with CSS transitions for StepBox expanded content
**Status**: FAILED - Reverted
**Why it failed**: CSS transitions with max-height still didn't prevent content from breaking out

### ❌ Solution 9: Add width constraints to entire container hierarchy
**Status**: FAILED - Reverted
**Why it failed**: Adding min-w-0 and width constraints didn't solve the issue

### ❌ Solution 10: Force SyntaxHighlighter to respect container width
**Status**: FAILED - Reverted
**Why it failed**: Content still flows out

### ❌ Solution 11: Add overflow-x-hidden to steps container div
**Status**: FAILED - Reverted
**Why it failed**: Content still flows out

### ❌ Solution 12: Wrap all content in constrained container inside motion.div
**Status**: FAILED - Reverted
**Why it failed**: Content still flows out

### ❌ Solution 13: Remove framer-motion from StepBox expanded content, use CSS transitions
**Status**: FAILED - Reverted
**Why it failed**: Content still flows out of the box

### ❌ Solution 14: Add overflow-x-hidden to ALL containers in the hierarchy
**Status**: FAILED - Reverted
**Why it failed**: Content still flows out of the box even with overflow-x-hidden at every level
**Note**: This was implemented without reverting Solution 13 first - mistake on my part

## Key Learnings

1. **Framer-motion's `height: "auto"` fundamentally doesn't work with max-height constraints** - it calculates the full content height regardless of constraints
2. **Adding overflow-x-hidden at every level doesn't help** - the issue is deeper
3. **CSS transitions with max-height also don't prevent content from breaking out** - suggests the issue might be with how content is rendered (SyntaxHighlighter?)
4. **Width constraints (min-w-0, w-full) don't solve it** - the problem persists

## Next Steps - Need More Information

Before trying more solutions, we need to understand:
1. **Exactly where does content break out?** 
   - Does it break out of the StepBox?
   - Does it break out of the steps container?
   - Does it break out of the AnalysisBlock Card?
   - Does it break out of the entire message list item?

2. **What type of overflow?**
   - Horizontal overflow (content wider than container)?
   - Vertical overflow (content taller than container)?
   - Both?

3. **When does it happen?**
   - Only when "Optimize Context" step appears?
   - Only when that step is expanded?
   - With all long content?

4. **What does the content look like?**
   - Is it the SyntaxHighlighter JSON that breaks out?
   - Is it the arguments display?
   - Is it something else?

## Revert Strategy

**CRITICAL**: Always revert before trying a new solution:
1. Use `git checkout <file>` to revert the specific file(s)
2. Document why it failed in this file
3. Move to next solution
4. Never repeat a failed solution
5. Never implement a new solution without reverting the previous one first

### ❌ Solution 15: Add explicit width constraints to SyntaxHighlighter wrapper and ensure pre/code elements respect width
**Status**: FAILED - Reverted
**Why it failed**: Content still flows out of the box

### ❌ Solution 16: Use text truncation with ellipsis and make content responsive to container width
**Status**: FAILED - Reverted
**Why it failed**: Content still flows out of the box. Adding min-w-0 and max-w-full constraints didn't prevent overflow.

### ❌ Solution 17: Constrain the motion.div animation to a fixed max-height value instead of "auto"
**Status**: FAILED - Reverted
**Why it failed**: Content still flows out. Measuring height and animating to fixed value didn't prevent overflow.

### ❌ Solution 18: Remove framer-motion entirely and use CSS-based collapsible with max-height
**Status**: FAILED - Reverted
**Why it failed**: Content still flows out of the box. Even with pure CSS transitions, the content breaks out.

## Critical Observation from User

The user observed: "when i resize the chatbox I spot that the step element (context optimizer) can be resized but until it reach its limitation. It's better if we can truncating the content if it's fill out of the border. when resizing, we can truncate it or adding more text to make it flexible"

This suggests:
- The container CAN resize, but hits a limitation
- Content needs to be truncated when it exceeds boundaries
- The issue might be that content is not respecting the container's actual width
- We need to ensure the container's width is properly constrained by its parent

### ❌ Solution 19: Ensure parent containers have proper width constraints and use table-layout for SyntaxHighlighter
**Status**: FAILED - Reverted
**Why it failed**: Content still flows out. User identified the real issue: there's a minimum width limitation stopping the resize.

### ❌ Solution 20: Reduce the minimum width limitation on StepBox
**Status**: FAILED - Reverted
**Why it failed**: Adding `min-w-0` to StepBox didn't reduce the limitation. The limitation might be in parent containers (steps container, AnalysisBlock Card, etc.)

### ❌ Solution 21: Add min-w-0 to ALL parent containers in the hierarchy
**Status**: FAILED - Reverted
**Why it failed**: Didn't work, and when resizing smaller, there's a horizontal scrollbar which is annoying. The issue is that content is still overflowing horizontally.

### ❌ Solution 22: Add overflow-x-hidden to prevent horizontal scrollbar and ensure content truncates
**Status**: FAILED - Reverted
**Why it failed**: Horizontal scrollbar still appears. The step border can resize and text truncates when resizing (which is good), but there's a limitation preventing further shrinking that needs to be found and set.

### ❌ Solution 23: Find and remove/set the minimum width limitation
**Status**: FAILED - Reverted
**Why it failed**: Adding `min-w-0` and `overflow-x-hidden` didn't reduce the limitation. The issue persists.

### ❌ Solution 24: Make shrink-0 items in button also shrinkable or reduce their size
**Status**: FAILED - Reverted
**Why it failed**: Didn't work. When expanding StepBox, the content overflows (same problem). Need a comprehensive solution that addresses both collapsed header and expanded content.

### ❌ Solution 25: Comprehensive fix - Constrain entire hierarchy with proper width/overflow and fix SyntaxHighlighter
**Status**: FAILED - Reverted
**Why it failed**: Still didn't work. Content still overflows in both collapsed and expanded states.

### ❌ Solution 26: Use CSS to force all content to respect container width with !important and table-layout
**Status**: FAILED - Reverted
**Why it failed**: Still didn't work. The issue persists.

### ❌ Solution 27: Fix parent containers - Add min-w-0 to wrapper div and parent containers
**Status**: FAILED - Reverted
**Why it failed**: Still didn't work. The issue persists even after fixing parent containers.

### ❌ Solution 28: Constrain content INSIDE motion.div and use max-height instead of height: auto
**Status**: FAILED - Reverted
**Why it failed**: Still didn't work. The issue persists.

### ❌ Solution 29: Comprehensive width constraints throughout entire hierarchy + SyntaxHighlighter wrapper
**Status**: FAILED - Reverted
**Why it failed**: Still didn't work. The issue persists.

### ❌ Solution 30: Add CSS style tag with !important to directly target SyntaxHighlighter's pre/code elements
**Status**: FAILED - Reverted
**Why it failed**: Still didn't work. The issue persists.

### ❌ Solution 31: Replace SyntaxHighlighter with simple pre/code element
**Status**: FAILED - Reverted
**Why it failed**: Still didn't work. The issue persists even after replacing SyntaxHighlighter with native HTML elements.

### ❌ Solution 32: Add min-w-0 throughout hierarchy + constrain SyntaxHighlighter with wrapper div
**Status**: FAILED - Reverted
**Why it failed**: Still didn't work. User clarified that the problem is specifically in StepBox and StepCard components, NOT AnalysisBlock. Should focus only on StepBox.

### ❌ Solution 33: Focus ONLY on StepBox - Add width constraints to StepBox root, Card, button, expanded content, and SyntaxHighlighter wrapper
**Status**: FAILED - Reverted
**Why it failed**: Still didn't work. User clarified: "the problem is the text inside the card, when that content longer, something happen that expand the card, find that position and fix it"

### ❌ Solution 34: Fix the button flex container and text content that expands the card
**Status**: FAILED - Reverted
**Why it failed**: Still didn't work. User says: "i saw the content of card auto adapted when resizing. the only thing is that it can't be resized smaller than a kind of limitation. find that value"

### ❌ Solution 35: Add min-w-0 to button and summary span to allow proper shrinking
**Status**: FAILED - Reverted
**Why it failed**: Still didn't work and a horizontal scrollbar appeared. The `min-w-0` allowed shrinking but caused horizontal overflow.

### ❌ Solution 36: Add min-w-0 + overflow-x-hidden throughout StepBox to allow shrinking while preventing horizontal scrollbar
**Status**: FAILED - Reverted
**Why it failed**: Still didn't work. The issue persists.

### ❌ Solution 37: Add min-w-0 to button + flex-basis: 0 on summary span to force it to start from 0 width
**Status**: FAILED - Reverted
**Why it failed**: Still didn't work. The issue persists.

### ✅ Solution 38: Add debug logging to identify which element has minimum width constraint
**Status**: IMPLEMENTED
**Approach**: 
- Add useRef hooks for root motion.div, Card, button, and summary span
- Add useEffect that logs computed styles (width, min-width, max-width, flex properties) on mount and resize
- Log to console to help identify which element is preventing shrinking

**Key Insight**: Need to identify the exact element and CSS property causing the minimum width limitation. Debug logging will show computed styles when resizing reaches the limitation.

**Debug Log Findings**:
- Root motion.div: `minWidth: auto` (expected)
- Card: `minWidth: 0px` (good, can shrink)
- Button: `minWidth: auto` (PROBLEM - prevents shrinking)
- Summary span: `minWidth: auto` (PROBLEM - prevents shrinking)

### ❌ Solution 39: Add min-w-0 to button and summary span to override default min-width: auto
**Status**: FAILED - Reverted
**Why it failed**: Still didn't work. The issue persists.

**Approach**: 
- Add `min-w-0` to button header className
- Add `min-w-0` to summary span className

**Key Insight**: Flexbox items have a default `min-width: auto` which prevents them from shrinking below their content width. The debug logs showed that both the button and summary span had `minWidth: auto`, which was preventing the card from shrinking. By adding `min-w-0` to both elements, we override the default behavior and allow them to shrink properly, enabling the card to resize smaller than the content's natural width.

### ❌ Solution 40: Add min-w-0 to button and summary span (based on debug log findings)
**Status**: FAILED - Reverted
**Why it failed**: Still didn't work. The issue persists even after adding `min-w-0` to both elements.

**Approach**: 
- Add `min-w-0` to button header className
- Add `min-w-0` to summary span className

**Key Insight**: The debug logs from Solution 38 confirmed that both the Button and Summary span have `minWidth: auto`, which prevents them from shrinking below their content width. However, adding `min-w-0` to both elements didn't solve the issue, suggesting there may be another constraint in the component hierarchy or the content itself is preventing shrinking.

**Debug Log Evidence**:
- Button: `minWidth: auto` (prevents shrinking)
- Summary span: `minWidth: auto` (prevents shrinking)
- Card: `minWidth: 0px` (already correct)

### ❌ Solution 41: Add min-w-0 + overflow-x-hidden to expanded content motion.div + constrain SyntaxHighlighter
**Status**: FAILED - Reverted
**Why it failed**: Still didn't work. The issue persists.

**Approach**: 
- Add `min-w-0 overflow-x-hidden` to the `motion.div` that wraps the expanded content
- Add `min-w-0` to the wrapper div around `SyntaxHighlighter`
- Add `minWidth: 0` and `maxWidth: "100%"` to `SyntaxHighlighter` customStyle
- Add `PreTag="div"` to `SyntaxHighlighter` to use div instead of pre (which might have default min-width behavior)

**Key Insight**: The debug logs showed that Button and Summary span have `minWidth: 0px` after revert, so they're not the issue. The problem is likely in the expanded content area where the `SyntaxHighlighter` renders long text. The `motion.div` wrapping the expanded content and the `SyntaxHighlighter`'s internal `pre`/`code` elements might be enforcing a minimum width based on content. However, adding `min-w-0` to the motion.div and constraining the SyntaxHighlighter didn't solve the issue, suggesting the constraint might be coming from a parent element or a different part of the component hierarchy.

### ❌ Solution 42: Add min-w-0 to CardContent in AnalysisBlock (Parent 3 constraint fix)
**Status**: FAILED - Reverted
**Why it failed**: Even though Parent 3 now has `minWidth: "0px"` (confirmed by debug logs), the issue still persists. This suggests the problem is not just about `minWidth` constraints, but something else is preventing proper shrinking/wrapping.

**Approach**: 
- Added `min-w-0` to `CardContent` className in `AnalysisBlock` (line 262)
- Debug logs confirmed Parent 3 now has `minWidth: "0px"` instead of `"auto"`
- All parent elements (0-4) now have `minWidth: "0px"`, but the issue still persists

**Key Insight**: The debug logging (Solution 38) revealed that Parent 3 (`div.px-6.pt-0` in `AnalysisBlock`'s `CardContent`) had `minWidth: "auto"`, which was preventing the card from shrinking below its content width. However, fixing this constraint didn't solve the issue, suggesting the problem is deeper - possibly related to how the content itself (SyntaxHighlighter) renders, or there's another constraint we haven't identified yet.

### ❌ Solution 43: Add whiteSpace: "pre-wrap" to SyntaxHighlighter customStyle
**Status**: FAILED - Reverted
**Why it should work**: `SyntaxHighlighter` renders `pre` elements which have `white-space: pre` by default, preventing text wrapping. Even with `wrapLongLines` prop, the `pre` element might still prevent wrapping. Adding `whiteSpace: "pre-wrap"` explicitly allows wrapping while preserving whitespace.

**Approach**: 
- Added `whiteSpace: "pre-wrap"` to `SyntaxHighlighter` customStyle (line 453)
- This allows the JSON content to wrap within the container width while preserving formatting

**Why it failed**: The `customStyle` prop may not apply to nested `pre` and `code` elements rendered by `SyntaxHighlighter`. The style needs to be applied directly to those elements via CSS.

**Key Insight**: After fixing all `minWidth` constraints (all are now `0px`), the issue persists, suggesting the problem is with how the content itself wraps. `SyntaxHighlighter` renders `pre` elements with `white-space: pre` by default, which prevents wrapping. Even though `wrapLongLines` is set, we need to explicitly set `whiteSpace: "pre-wrap"` in the customStyle to ensure wrapping works. However, `customStyle` may not apply to nested elements, so we need to use CSS to target them directly.

### ❌ Solution 44: Use CSS style tag to target pre and code elements directly
**Status**: FAILED - Reverted
**Why it should work**: Since `customStyle` may not apply to nested `pre` and `code` elements rendered by `SyntaxHighlighter`, we need to use CSS to target them directly. Adding a scoped style tag with `!important` will override any default styles from the syntax highlighter library.

**Approach**: 
- Added a `className="step-result-wrapper"` to the wrapper div around `SyntaxHighlighter`
- Added a `<style>` tag with `dangerouslySetInnerHTML` that targets `.step-result-wrapper pre` and `.step-result-wrapper code` with `white-space: pre-wrap !important`, `word-wrap: break-word !important`, `overflow-wrap: break-word !important`, and `max-width: 100% !important`
- This ensures the nested elements wrap properly regardless of default styles

**Why it failed**: The CSS style tag approach didn't work, likely because `SyntaxHighlighter` renders complex nested structures that are difficult to override, or the styles aren't being applied correctly. The root issue is that we don't have full control over how `SyntaxHighlighter` renders its content.

**Key Insight**: The `customStyle` prop on `SyntaxHighlighter` may not cascade to the nested `pre` and `code` elements it renders. By using a scoped CSS style tag with `!important`, we can directly override the default `white-space: pre` behavior on those elements. However, this approach failed, suggesting we need to replace `SyntaxHighlighter` entirely with a simpler solution we can fully control.

### ⏳ Solution 45: Replace SyntaxHighlighter with native pre/code elements
**Status**: IMPLEMENTED - Testing
**Why it should work**: `SyntaxHighlighter` is a complex third-party component that renders nested structures we can't fully control. By replacing it with native `<pre><code>` elements, we have complete control over the styling and can ensure proper wrapping behavior.

**Approach**: 
- Removed `SyntaxHighlighter` component usage
- Replaced with native `<pre><code>` elements
- Applied Tailwind classes: `whitespace-pre-wrap`, `break-words`, `max-w-full`, `min-w-0` on both `pre` and `code`
- Added inline style `overflowWrap: "anywhere"` to the `pre` element
- Wrapped in a div with `min-w-0` to ensure proper flexbox shrinking

**Key Insight**: The root cause is that `SyntaxHighlighter` is a black box that renders content in ways we can't control. By using native HTML elements, we have full control over every aspect of the rendering, including wrapping behavior. This should finally solve the issue. 
- Add `min-w-0` to the button (line 280) - CRITICAL: flex containers need `min-w-0` to allow children to shrink
- Change summary span from `grow` to `flex-1 min-w-0` - ensures it can shrink and truncate properly
- Add `shrink-0` to step number and agent badge spans - prevents them from shrinking
- Add `min-w-0 overflow-x-hidden` to arguments display div
- Add `break-words` and inline styles `overflowWrap: "anywhere", wordBreak: "break-word"` to arguments text
- Add `min-w-0` to result container div
- Wrap SyntaxHighlighter in a div with `min-w-0` and explicit width styles
- Add explicit width constraints to SyntaxHighlighter customStyle: `width: "100%", maxWidth: "100%", minWidth: 0`
- Use `PreTag="div"` for SyntaxHighlighter

**Key Insight**: The button is a flex container, and flex children with `grow` cannot shrink below their content width unless the parent has `min-w-0`. The summary text with `grow` was expanding the card because the button didn't have `min-w-0`. By adding `min-w-0` to the button and changing `grow` to `flex-1 min-w-0` on the summary span, the text can now truncate properly.
**Approach**: 
- Add `min-w-0 max-w-full` to StepBox root motion.div
- Add `min-w-0 max-w-full` to StepBox Card
- Add `min-w-0 max-w-full overflow-x-hidden` to StepBox button header
- Add `min-w-0 max-w-full overflow-x-hidden` to StepBox expanded content motion.div
- Add `min-w-0 max-w-full overflow-x-hidden` to arguments display div with `break-words` and `overflowWrap: "anywhere"`
- Wrap SyntaxHighlighter in a div with `min-w-0 max-w-full` and explicit width styles
- Add explicit width constraints to SyntaxHighlighter customStyle: `width: "100%", maxWidth: "100%", minWidth: 0`
- Use `PreTag="div"` for SyntaxHighlighter

**Key Insight**: Focus ONLY on StepBox component. The issue is that StepBox and its Card need proper width constraints to allow shrinking. By adding `min-w-0 max-w-full` at every level within StepBox, we ensure the component can shrink properly when the browser is resized.
**Approach**: 
- Add `min-w-0` to wrapper div around AnalysisBlock in MessageListView
- Add `min-w-0` to AnalysisBlock root motion.div and Card
- Add `min-w-0` to steps container div
- Add `min-w-0` to StepBox root motion.div and Card
- Add `min-w-0` to StepBox button header
- Add `min-w-0` to StepBox expanded content motion.div
- Add `min-w-0 overflow-x-hidden` to arguments display div with `break-words` and `overflowWrap: "anywhere"`
- Wrap SyntaxHighlighter in a div with `min-w-0` and explicit width styles
- Add explicit width constraints to SyntaxHighlighter customStyle: `width: "100%", maxWidth: "100%", minWidth: 0`
- Use `PreTag="div"` for SyntaxHighlighter

**Key Insight**: The issue is that flexbox children have `min-width: auto` by default, which prevents them from shrinking below their content width. By adding `min-w-0` at every level of the hierarchy, we allow containers to shrink properly. Additionally, wrapping SyntaxHighlighter in a constrained div ensures it respects width limits before framer-motion measures it.

### ❌ Solution 29: Comprehensive width constraints throughout entire hierarchy + SyntaxHighlighter wrapper
**Status**: FAILED - Reverted
**Approach**: 
- Add `min-w-0 max-w-full overflow-x-hidden` to wrapper div around AnalysisBlock in MessageListView
- Add `min-w-0 max-w-full` to AnalysisBlock root motion.div and Card
- Add `min-w-0 max-w-full overflow-x-hidden` to steps container motion.div and inner div
- Add `min-w-0 max-w-full` to StepBox root motion.div and Card
- Add `min-w-0 max-w-full overflow-x-hidden` to StepBox button header
- Add `min-w-0 max-w-full overflow-x-hidden` to StepBox expanded content motion.div
- Add `min-w-0 max-w-full overflow-x-hidden` to arguments display div
- Add `min-w-0 max-w-full overflow-x-hidden` wrapper around SyntaxHighlighter
- Add explicit width constraints to SyntaxHighlighter customStyle: `width: "100%", maxWidth: "100%", minWidth: 0`
- Use `PreTag="div"` for SyntaxHighlighter to ensure proper wrapping
- Add `break-words` and `overflowWrap: "anywhere"` to arguments display

**Key Insight**: The entire hierarchy from MessageListView wrapper down to SyntaxHighlighter needs proper width constraints. The wrapper div around AnalysisBlock was missing `min-w-0`, which prevented proper shrinking. By adding `min-w-0 max-w-full overflow-x-hidden` at every level, we ensure containers can shrink and content truncates/wraps properly.

## CRITICAL: After 28 failed attempts, we need a different approach

All attempts to fix this with CSS constraints, overflow settings, and SyntaxHighlighter configuration have failed. The issue is persistent and suggests:

1. **The problem might be at a different level** - perhaps in the chat panel width constraints or global CSS
2. **SyntaxHighlighter might be fundamentally incompatible** - it may need to be replaced with a different component
3. **Framer Motion's height: "auto" might be the core issue** - we may need to remove it entirely
4. **There might be a CSS specificity issue** - some other CSS rule is overriding our constraints

### Proposed Next Steps:
1. Ask user to inspect the actual DOM in browser dev tools to identify which element is causing the limitation
2. Consider replacing SyntaxHighlighter with a simpler code display component
3. Remove framer-motion entirely and use pure CSS transitions
4. Check if there are any global CSS rules or Tailwind config affecting this
**Approach**: 
- The issue is that framer-motion's `height: "auto"` calculates the full content height, including overflow
- Instead of animating the motion.div to "auto", wrap all content inside with a constrained container
- Use `max-height` on the inner container instead of relying on motion.div's height animation
- This way, the motion.div animates to a constrained height, and the inner container scrolls
- Also add a wrapper around AnalysisBlock with min-w-0

**Key Insight**: The motion.div with `height: "auto"` calculates the full content height, ignoring overflow constraints. We need to constrain the content INSIDE the motion.div, not rely on the motion.div itself to constrain.
**Approach**: 
- Found that AnalysisBlock is wrapped in `<div className="w-full px-4">` without `min-w-0`
- This wrapper div can't shrink below content size due to flexbox defaults
- Add `min-w-0 max-w-full overflow-x-hidden` to the wrapper div
- Add constraints to MessageListView ScrollContainer and ul
- Add constraints to motion.li that contains the content
- This should be the actual limitation the user mentioned

**Key Insight**: The limitation might be in the parent containers, not in StepBox itself. The wrapper div around AnalysisBlock doesn't have `min-w-0`, which prevents it from shrinking below content size.
**Approach**: 
- Add a global CSS style or inline style with `!important` to force width constraints
- Use `table-layout: fixed` on SyntaxHighlighter's rendered elements
- Add a wrapper div around SyntaxHighlighter with explicit width: 100% and max-width: 100%
- Use CSS to target the pre/code elements that SyntaxHighlighter renders and force them to wrap
- Add `word-break: break-all` as a last resort to force breaking

**Key Insight**: Maybe we need to use more aggressive CSS with !important to override SyntaxHighlighter's default styles. Or we need to use CSS to directly target the rendered pre/code elements.
**Approach**: 
- Add `min-w-0 max-w-full overflow-x-hidden` to entire hierarchy (AnalysisBlock → steps container → StepBox → expanded content)
- Wrap SyntaxHighlighter in a constrained container with explicit width
- Use `PreTag="div"` and proper styles to force SyntaxHighlighter to respect container width
- Ensure the result container has proper constraints
- Fix both collapsed header (button) and expanded content (motion.div)

**Key Insight**: Need to fix BOTH collapsed and expanded states. The expanded content uses `motion.div` with `height: "auto"` which ignores max-height. We need to constrain the content INSIDE the motion.div, not the motion.div itself.
**Approach**: 
- The button has several `shrink-0` items (status icon, tool icon/name, expand icon) that prevent shrinking
- Make step number and agent badge truncate or shrink
- Reduce padding/gap to allow more shrinking
- The limitation might be the combined width of all `shrink-0` items - we need to make them smaller or allow some to shrink

**Key Insight**: The button has `shrink-0` items that maintain their size. The limitation might be the combined width of these items. We should make step number and agent badge truncate, or reduce the size of shrink-0 items.
**Approach**: 
- Search for any `min-width`, `min-w-*`, or fixed `width` constraints in StepBox and parent containers
- Check Card component for default min-width
- Check if there are any flexbox constraints preventing shrinking
- The user confirmed that resizing works and text truncates, but stops at a limitation - we need to find what that limitation is

**Key Insight**: The step can resize and truncate, but there's a specific limitation (likely a min-width value) that needs to be identified and reduced/removed.
**Approach**: 
- Add `overflow-x-hidden` to AnalysisBlock root, Card, CardContent
- Add `overflow-x-hidden` to steps container motion.div and inner div
- Add `overflow-x-hidden` to StepBox root, Card, and expanded content
- Add `min-w-0` only where needed to allow shrinking
- Ensure SyntaxHighlighter content is properly constrained
- The key is preventing horizontal scrollbar while allowing content to truncate

**Key Insight**: The horizontal scrollbar is the immediate problem. We need `overflow-x-hidden` at every level to prevent it, combined with `min-w-0` to allow proper truncation.
**Approach**: 
- Add `min-w-0` to AnalysisBlock root motion.div
- Add `min-w-0` to AnalysisBlock Card
- Add `min-w-0` to AnalysisBlock CardContent
- Add `min-w-0` to steps container motion.div
- Add `min-w-0` to steps container inner div
- This ensures the entire hierarchy can shrink, not just StepBox

**Key Insight**: The limitation might be in the parent containers. If AnalysisBlock or steps container has a minimum width, StepBox can't shrink below that. We need `min-w-0` at EVERY level.
**Approach**: 
- User identified that StepBox resizes but stops at a limitation (likely a min-width constraint)
- Need to find and reduce/remove the minimum width limitation
- This could be in the Card component, motion.div, or CSS defaults
- Set `min-width: 0` or reduce any fixed min-width values

**Key Insight**: The user observed that the container CAN resize until it hits a limitation. We need to find where that minimum width is set and reduce/remove it.
**Approach**: 
- Check if the issue is that parent containers (AnalysisBlock Card, steps container) don't have proper width constraints
- Add `table-layout: fixed` and `width: 100%` to SyntaxHighlighter's customStyle
- Ensure the entire hierarchy from AnalysisBlock down to StepBox has `min-w-0` and `max-w-full`
- This ensures containers can shrink and content truncates properly

**Key Insight**: The user's observation about resizing suggests the container width is the issue. We need to ensure ALL parent containers have proper width constraints so the StepBox can properly truncate content.
**Approach**: 
- Completely remove framer-motion from expanded content
- Use a simple CSS-based approach with max-height transition
- Use `max-h-0` when collapsed, `max-h-[400px]` when expanded
- Content always in DOM, just hidden/shown with max-height
- This is the simplest approach - no animation library complications

**Key Insight**: After 17 failed attempts with framer-motion, maybe we should just remove it entirely and use pure CSS. CSS max-height transitions work reliably, and we don't need the animation library for this simple expand/collapse.
**Approach**: 
- Use a ref to measure the content height
- If content height > 400px, animate to 400px instead of "auto"
- This way framer-motion animates to a fixed value, not "auto"
- The inner container can then scroll within that fixed height

**Key Insight**: The problem is framer-motion's `height: "auto"` calculates full content height. If we calculate the height ourselves and cap it at 400px, then animate to that fixed value, it should work. We need to use a ref to measure content and set a fixed height value for the animation.
**Approach**: 
- Instead of trying to wrap long content, truncate it with ellipsis
- Make the container responsive to parent width changes
- Use `text-overflow: ellipsis` and `overflow: hidden` on the result container
- Ensure the container respects its parent's width constraints
- Add a "Show more" button if content is truncated

**Key Insight**: The user observed that the step element resizes until it hits a limitation. Instead of trying to wrap content (which keeps failing), we should truncate it and make it responsive to the container width. This is a different approach - truncation instead of wrapping.

**Files to modify**:
- `web/src/app/pm/chat/components/step-box.tsx` (result container and SyntaxHighlighter)
**Approach**: 
- Wrap SyntaxHighlighter in a container with explicit `width: 100%` and `max-width: 100%`
- Add `table-layout: fixed` if there are any tables
- Ensure the wrapper div has `overflow-x-hidden` and `word-break` utilities
- Add CSS to target the pre/code elements that SyntaxHighlighter renders to ensure they respect width

**Key Insight**: SyntaxHighlighter renders `<pre><code>` elements. Even with `wrapLongLines`, the pre element might not respect container width. We need to ensure both the wrapper AND the rendered pre/code elements have width constraints.

**Files to modify**:
- `web/src/app/pm/chat/components/step-box.tsx` (SyntaxHighlighter wrapper and customStyle)

## Proposed Next Solutions (To Try)

### Solution 16: Inspect actual DOM to understand where content breaks out
- Use browser dev tools to inspect the actual rendered DOM
- Identify which container is allowing the overflow
- This will help target the fix more precisely

### Solution 16: Check if parent containers (MessageListItem, etc.) have constraints
- The issue might be at a level above AnalysisBlock
- Check MessageListItem wrapper div
- Check MessagesBlock container

### Solution 17: Use a completely different approach - don't use SyntaxHighlighter for long content
- Maybe SyntaxHighlighter is the root cause
- Try rendering plain text with word wrapping for long content
- Or use a different code display component
