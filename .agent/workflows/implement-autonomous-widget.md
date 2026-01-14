---
description: How to implement a new Autonomous Widget (Provider-First)
---

# Implement Autonomous Widget

Follow this workflow when creating or refactoring a widget to ensure it complies with the **Widget Autonomy Standard**.

## 1. Define Props
The widget MUST accept `providerId` (and optionally `config` object) as props.
```typescript
interface MyWidgetProps {
    providerId: string; // MANDATORY
    config?: Record<string, any>;
    // ... other props
}
```

## 2. Use Provider-Aware Hooks
Do NOT use generic hooks without passing the `providerId`.
Update or creating hooks to accept `providerId`.

**Bad**:
```typescript
const { tasks } = useTeamTasks(memberIds);
```

**Good**:
```typescript
const { tasks } = useTeamTasks(memberIds, { providerId: props.providerId });
```

## 3. Data Fetching
Ensure the hook implementation passes `providerId` to the API layer.
```typescript
// definition in hook
export function useTeamTasks(ids, options) {
   return useQuery({
       queryFn: () => listTasks({ ..., providerId: options.providerId })
   })
}
```

## 4. Error Handling
The widget must handle the "Provider Unavailable" state gracefully strictly based on the passed `providerId`.
- If the provider is unreachable, show an error for that specific widget.
- DO NOT fall back to local DB or global defaults.

## 5. Verification
// turbo
```bash
# Verify strictly without Local DB
docker stop project-management-agent-openproject_db_v13-1
```
- Reload the page.
- The widget should load data from the remote provider defined by `providerId`.
