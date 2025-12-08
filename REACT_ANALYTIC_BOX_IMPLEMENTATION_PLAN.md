# ReAct Analytic Box Implementation Plan

## Overview

Separate ReAct agent and Planner into different UI components (Analytic boxes) with:
- **ReAct Analytic Box**: Token-by-token streaming (no JSON parsing wait)
- **Planner Analytic Box**: Existing JSON-based plan display
- **Color differentiation**: Different colors to distinguish which is running
- **Handover visualization**: When ReAct escalates, show both boxes side-by-side

## Current Architecture

### Existing Components
- `AnalysisBlock` (`web/src/app/pm/chat/components/analysis-block.tsx`): Currently handles both planner and react_agent
- Uses `planMessage` with JSON parsing for planner
- Displays steps, thoughts, and tool calls
- Rendered in `MessageListItem` when `startOfResearch` is true

### Current Flow
1. Backend sends events: `message_chunk`, `tool_calls`, `thoughts`
2. Store processes events and updates messages
3. `AnalysisBlock` reads from store and displays plan/steps
4. For planner: Waits for complete JSON plan before displaying
5. For react_agent: Currently uses same component (needs separation)

## Implementation Plan

### Phase 1: Backend Changes

#### 1.1 Add ReAct Agent Identification in Events
**File**: `src/server/app.py`

**Changes**:
- Ensure `message_chunk` events include `agent: "react_agent"` when from ReAct
- Add `agent_type: "react" | "planner"` field to events for easier frontend routing
- Ensure ReAct content streams token-by-token (already working, just verify)

**Code Location**:
- `_process_message_chunk` function
- `_stream_graph_events` function

**Testing**:
- Verify `agent` field is correctly set in events
- Verify token-by-token streaming works for ReAct

---

### Phase 2: Frontend Store Changes

#### 2.1 Track ReAct vs Planner Research IDs
**File**: `web/src/core/store/store.ts`

**Changes**:
- Add `reactResearchIds: Set<string>` to track ReAct research sessions
- Add `plannerResearchIds: Set<string>` to track Planner research sessions
- When `message_chunk` with `agent: "react_agent"` received:
  - Add message ID to `reactResearchIds`
  - Track ReAct research ID separately
- When `message_chunk` with `agent: "planner"` received:
  - Add message ID to `plannerResearchIds`
  - If escalation from ReAct, link both research IDs

**New State Fields**:
```typescript
reactResearchIds: Set<string>
plannerResearchIds: Set<string>
reactToPlannerEscalation: Map<string, string> // reactResearchId -> plannerResearchId
```

**Testing**:
- Verify ReAct research IDs are tracked separately
- Verify escalation linking works correctly

#### 2.2 Handle ReAct Token-by-Token Streaming
**File**: `web/src/core/store/store.ts`

**Changes**:
- For ReAct `message_chunk` events: Update message content immediately (no JSON parsing)
- For Planner `message_chunk` events: Keep existing JSON parsing logic
- Add `isReactAgent: boolean` flag to Message type (or derive from agent field)

**Code Location**:
- `sendMessage` function
- Event handling in stream loop

**Testing**:
- Verify ReAct content streams token-by-token
- Verify Planner still waits for complete JSON

---

### Phase 3: Create ReAct Analytic Box Component

#### 3.1 Create ReActAnalysisBlock Component
**File**: `web/src/app/pm/chat/components/react-analysis-block.tsx`

**Changes**:
- Clone from `AnalysisBlock` component
- Remove JSON parsing logic (ReAct doesn't use JSON)
- Stream content token-by-token from message content
- Different color scheme (e.g., blue/cyan for ReAct vs green for Planner)
- Display thoughts and tool calls as they arrive (no waiting for complete plan)

**Key Features**:
- Real-time token-by-token content display
- Thoughts displayed immediately (from `thoughts` events)
- Tool calls displayed as they arrive
- Different visual styling (color, icon, etc.)

**Props**:
```typescript
interface ReActAnalysisBlockProps {
  researchId: string;
  className?: string;
}
```

**Visual Design**:
- Header: "⚡ ReAct Analysis" (with lightning icon)
- Color scheme: Blue/cyan gradient (vs Planner's green)
- Border: Blue border (vs Planner's green border)
- Background: Light blue tint (vs Planner's light green)

**Testing**:
- Verify component renders correctly
- Verify token-by-token streaming works
- Verify thoughts and tool calls display correctly

#### 3.2 Create PlannerAnalysisBlock Component (Refactor Existing)
**File**: `web/src/app/pm/chat/components/planner-analysis-block.tsx`

**Changes**:
- Refactor existing `AnalysisBlock` to be Planner-specific
- Keep JSON parsing logic
- Rename to `PlannerAnalysisBlock`
- Update color scheme to green (if not already)

**Visual Design**:
- Header: "📋 Planner Analysis" (with planner icon)
- Color scheme: Green gradient
- Border: Green border
- Background: Light green tint

**Testing**:
- Verify refactored component works as before
- Verify JSON parsing still works

---

### Phase 4: Update Message Rendering

#### 4.1 Update MessageListItem to Route to Correct Component
**File**: `web/src/app/pm/chat/components/message-list-view.tsx`

**Changes**:
- Check `message.agent` to determine which component to render
- If `agent === "react_agent"`: Render `ReActAnalysisBlock`
- If `agent === "planner"`: Render `PlannerAnalysisBlock`
- If escalation (ReAct → Planner): Render both side-by-side

**Code Logic**:
```typescript
if (startOfResearch && message?.id) {
  const state = useStore.getState();
  const isReactAgent = message.agent === "react_agent";
  const isPlanner = message.agent === "planner";
  const escalationLink = state.reactToPlannerEscalation.get(message.id);
  
  if (isReactAgent && escalationLink) {
    // Show both: ReAct (left) and Planner (right) side-by-side
    content = (
      <div className="w-full px-4 grid grid-cols-2 gap-4">
        <ReActAnalysisBlock researchId={message.id} />
        <PlannerAnalysisBlock researchId={escalationLink} />
      </div>
    );
  } else if (isReactAgent) {
    content = (
      <div className="w-full px-4">
        <ReActAnalysisBlock researchId={message.id} />
      </div>
    );
  } else if (isPlanner) {
    content = (
      <div className="w-full px-4">
        <PlannerAnalysisBlock researchId={message.id} />
      </div>
    );
  }
}
```

**Testing**:
- Verify correct component renders for each agent type
- Verify side-by-side display works for escalation

---

### Phase 5: Styling and Visual Differentiation

#### 5.1 Create Color Theme System
**File**: `web/src/app/pm/chat/components/analysis-themes.ts`

**Changes**:
- Define color themes for ReAct and Planner
- Export theme objects with colors, gradients, borders

**Theme Definition**:
```typescript
export const reactTheme = {
  primary: "blue",
  gradient: "from-blue-500 to-cyan-500",
  border: "border-blue-500",
  background: "bg-blue-50 dark:bg-blue-950",
  text: "text-blue-700 dark:text-blue-300",
  icon: "⚡",
  name: "ReAct Analysis"
};

export const plannerTheme = {
  primary: "green",
  gradient: "from-green-500 to-emerald-500",
  border: "border-green-500",
  background: "bg-green-50 dark:bg-green-950",
  text: "text-green-700 dark:text-green-300",
  icon: "📋",
  name: "Planner Analysis"
};
```

**Testing**:
- Verify themes are applied correctly
- Verify dark mode support

#### 5.2 Apply Themes to Components
**Files**:
- `react-analysis-block.tsx`
- `planner-analysis-block.tsx`

**Changes**:
- Import and apply theme colors
- Update all color references to use theme
- Ensure consistent styling

**Testing**:
- Verify visual differentiation is clear
- Verify accessibility (contrast ratios)

---

### Phase 6: Handover Visualization

#### 6.1 Create Handover Indicator
**File**: `web/src/app/pm/chat/components/handover-indicator.tsx`

**Changes**:
- Component to show connection between ReAct and Planner boxes
- Visual arrow or connector line
- Text: "Escalated to Planner" or "Handing over to Planner"

**Design**:
- Arrow icon pointing from ReAct box to Planner box
- Subtle animation (pulse or fade)
- Tooltip explaining escalation

**Testing**:
- Verify handover indicator displays correctly
- Verify animation works smoothly

#### 6.2 Update Side-by-Side Layout
**File**: `web/src/app/pm/chat/components/message-list-view.tsx`

**Changes**:
- Improve side-by-side layout for escalation
- Add handover indicator between boxes
- Ensure responsive design (stack on mobile)

**Layout**:
```
[ReAct Box] → [Handover Indicator] → [Planner Box]
```

**Testing**:
- Verify layout works on desktop
- Verify responsive stacking on mobile
- Verify handover indicator is visible

---

## Testing Plan

### Unit Tests

#### Test 1: ReAct Token-by-Token Streaming
**File**: `web/src/core/store/store.test.ts` (create if needed)

**Test**:
- Simulate ReAct `message_chunk` events
- Verify content updates incrementally
- Verify no JSON parsing occurs

#### Test 2: Planner JSON Parsing
**File**: `web/src/core/store/store.test.ts`

**Test**:
- Simulate Planner `message_chunk` events
- Verify JSON parsing still works
- Verify plan structure is correct

#### Test 3: Escalation Linking
**File**: `web/src/core/store/store.test.ts`

**Test**:
- Simulate ReAct escalation
- Verify `reactToPlannerEscalation` map is updated
- Verify both research IDs are tracked

### Integration Tests

#### Test 4: ReAct Analysis Block Rendering
**File**: `web/src/app/pm/chat/components/react-analysis-block.test.tsx`

**Test**:
- Render component with mock ReAct data
- Verify token-by-token content display
- Verify thoughts and tool calls render

#### Test 5: Planner Analysis Block Rendering
**File**: `web/src/app/pm/chat/components/planner-analysis-block.test.tsx`

**Test**:
- Render component with mock Planner data
- Verify JSON plan parsing
- Verify steps display correctly

#### Test 6: Side-by-Side Escalation Display
**File**: `web/src/app/pm/chat/components/message-list-view.test.tsx`

**Test**:
- Render escalation scenario
- Verify both boxes display
- Verify handover indicator shows

### E2E Tests

#### Test 7: Simple ReAct Query
**Scenario**:
1. User asks: "List users in project X"
2. ReAct handles query
3. Verify ReAct Analytic Box appears
4. Verify content streams token-by-token
5. Verify blue/cyan color scheme

**Expected**:
- ReAct box appears immediately
- Content streams without waiting
- No JSON parsing delay

#### Test 8: ReAct Escalation
**Scenario**:
1. User asks complex query
2. ReAct starts, then escalates
3. Verify both boxes appear side-by-side
4. Verify handover indicator shows
5. Verify Planner box shows plan

**Expected**:
- ReAct box appears first (blue)
- Planner box appears after escalation (green)
- Both visible side-by-side
- Handover indicator between them

#### Test 9: Direct Planner Query
**Scenario**:
1. User asks complex query (or ReAct already escalated)
2. Coordinator routes directly to Planner
3. Verify only Planner box appears
4. Verify JSON plan parsing works

**Expected**:
- Only Planner box appears (green)
- Plan displays after JSON parsing
- No ReAct box

### Visual Regression Tests

#### Test 10: Color Differentiation
**Screenshot Tests**:
- ReAct box (blue/cyan)
- Planner box (green)
- Side-by-side escalation
- Dark mode variants

**Tools**: Playwright or similar

---

## Implementation Checklist

### Backend
- [ ] Verify `agent` field in events
- [ ] Add `agent_type` field (optional, for easier routing)
- [ ] Test ReAct token-by-token streaming

### Frontend Store
- [ ] Add `reactResearchIds` state
- [ ] Add `plannerResearchIds` state
- [ ] Add `reactToPlannerEscalation` map
- [ ] Update event handling for ReAct
- [ ] Test ReAct streaming
- [ ] Test escalation linking

### Components
- [ ] Create `ReActAnalysisBlock` component
- [ ] Refactor `AnalysisBlock` to `PlannerAnalysisBlock`
- [ ] Create `handover-indicator` component
- [ ] Create `analysis-themes.ts` file
- [ ] Apply themes to components

### Routing
- [ ] Update `MessageListItem` routing logic
- [ ] Implement side-by-side escalation display
- [ ] Test component routing

### Styling
- [ ] Apply ReAct theme (blue/cyan)
- [ ] Apply Planner theme (green)
- [ ] Ensure dark mode support
- [ ] Test accessibility

### Testing
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Write E2E tests
- [ ] Visual regression tests

---

## Timeline Estimate

- **Phase 1 (Backend)**: 2 hours
- **Phase 2 (Store)**: 4 hours
- **Phase 3 (Components)**: 8 hours
- **Phase 4 (Routing)**: 4 hours
- **Phase 5 (Styling)**: 4 hours
- **Phase 6 (Handover)**: 4 hours
- **Testing**: 8 hours

**Total**: ~34 hours (~4-5 days)

---

## Risk Mitigation

### Risk 1: Breaking Existing Planner Flow
**Mitigation**: 
- Refactor carefully, keep existing logic
- Extensive testing of Planner flow
- Feature flag to toggle new components

### Risk 2: Performance with Token-by-Token Streaming
**Mitigation**:
- Use React.memo for components
- Debounce updates if needed
- Monitor performance metrics

### Risk 3: Visual Clarity
**Mitigation**:
- User testing for color differentiation
- Accessibility audit (contrast ratios)
- Clear labels and icons

---

## Success Criteria

1. ✅ ReAct Analytic Box streams token-by-token (no JSON wait)
2. ✅ Planner Analytic Box works as before (JSON parsing)
3. ✅ Clear visual differentiation (colors, icons)
4. ✅ Side-by-side display on escalation
5. ✅ Handover indicator visible
6. ✅ All tests pass
7. ✅ No regression in existing functionality

