# Cursor-Style "Thought" Display Implementation

## What Cursor Shows

In Cursor, the UI displays agent actions as separate steps:
- **Thought** 💭 - Reasoning before an action
- **Read** 📖 - File reading action
- **Grepped** 🔍 - Search action  
- **Search** 🌐 - Web search action
- **Tool calls** 🔧 - Other tool executions

## Current Implementation

### Backend (✅ Done)
- **Thought Extraction**: Added in `react_agent_node` to extract thoughts from AIMessage content before tool calls
- **Thought Storage**: Thoughts are stored in `react_thoughts` in state
- **Pattern Matching**: Extracts thoughts from patterns like "Thought:", "I need to", etc.

### Frontend (⚠️ TODO)
We need to:
1. **Add "Thought" step type** to `StepBox` component
2. **Display thoughts** before tool calls (Cursor-style)
3. **Add Thought icon** (💭 or Brain icon)

## Implementation Plan

### 1. Update Message Types
```typescript
// web/src/core/messages/types.ts
export interface Message {
  // ... existing fields
  reactThoughts?: Array<{
    thought: string;
    before_tool: boolean;
    step_index: number;
  }>;
}
```

### 2. Update StepBox Component
```typescript
// web/src/app/pm/chat/components/step-box.tsx
const TOOL_ICONS: Record<string, React.ReactNode> = {
  // ... existing icons
  thought: <Brain size={12} />,  // Add Thought icon
};

function getToolDisplayName(toolName: string): string {
  const nameMap: Record<string, string> = {
    // ... existing names
    thought: "Thought",  // Add Thought display name
  };
  // ...
}
```

### 3. Display Thoughts in Analysis Block
```typescript
// web/src/app/pm/chat/components/analysis-block.tsx
// When rendering steps, interleave thoughts with tool calls:
{message.reactThoughts?.map((thought, idx) => (
  <ThoughtBox key={`thought-${idx}`} thought={thought.thought} />
))}
{toolCalls.map((toolCall, index) => (
  <StepBox key={toolCall.id} toolCall={toolCall} ... />
))}
```

### 4. Create ThoughtBox Component
```typescript
// web/src/app/pm/chat/components/thought-box.tsx
export function ThoughtBox({ thought }: { thought: string }) {
  return (
    <Card className="border-purple-200 bg-purple-50/50">
      <div className="flex items-start gap-2 px-3 py-2">
        <Brain size={14} className="text-purple-600 mt-0.5" />
        <div className="flex-1">
          <div className="text-xs font-medium text-purple-900 mb-1">Thought</div>
          <div className="text-sm text-purple-800">{thought}</div>
        </div>
      </div>
    </Card>
  );
}
```

## Current Status

✅ **Backend**: Thought extraction implemented
⚠️ **Frontend**: Needs implementation to display thoughts

## Next Steps

1. Test thought extraction in backend logs
2. Implement ThoughtBox component
3. Integrate thoughts into AnalysisBlock
4. Style to match Cursor's UI


