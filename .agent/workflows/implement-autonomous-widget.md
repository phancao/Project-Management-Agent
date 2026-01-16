---
description: How to implement a new Autonomous Widget (Provider-First)
---

# Implement Autonomous Widget

Follow this workflow when creating or refactoring a widget to ensure it complies with the **Widget Autonomy Standard**.

## 1. Define Props
The widget MUST accept `providerId` as a **MANDATORY** prop.
```typescript
interface MyWidgetProps {
    providerId: string; // MANDATORY - widget will not fetch without this
    config?: Record<string, any>;
    // ... other props
}
```

## 2. Guard Against Missing Provider
Before fetching ANY data, check if `providerId` is set. Show a configuration prompt if missing.

```typescript
// STRICT Widget Autonomy: Require explicit providerId
const hasValidConfig = Boolean(providerId);

if (!hasValidConfig) {
    return <ProviderRequiredCard />;
}
```

> **IMPORTANT**: Do NOT allow legacy member IDs from localStorage to trigger data fetching without an explicit provider.

## 3. Use Provider-Aware Hooks
Pass `providerId` explicitly to all data hooks.

**Bad**:
```typescript
const { tasks } = useTeamTasks(memberIds);
```

**Good**:
```typescript
const { tasks } = useTeamTasks(memberIds, { providerId: props.providerId });
```

## 4. Data Fetching Layer
Ensure hooks pass `providerId` to the API layer.
```typescript
export function useTeamTasks(ids, options) {
   return useQuery({
       queryFn: () => listTasks({ ..., providerId: options.providerId })
   })
}
```

**API Function Signatures**: Verify argument order! Example:
```typescript
// listUsers(projectId?, providerId?) - pass undefined for unused args
listUsers(undefined, providerId);  // CORRECT
listUsers(providerId);              // WRONG - passes to projectId position
```

## 5. Error Handling
- If the provider is unreachable, show an error for that specific widget.
- DO NOT fall back to local DB or global defaults.
- DO NOT silently fetch from another provider.

## 6. Config-Triggered Reload
When config changes (e.g., user selects a new provider), the widget must refetch data.

**Pattern**: Use `key` prop on the component to force full remount on config change:

```tsx
// In custom-dashboard-view.tsx or parent wrapper
<Component key={JSON.stringify(instance.config)} config={instance.config} />
```

This ensures:
- Component state resets completely
- useEffect hooks re-run
- Data refetches with new config

## 7. Clear Legacy Data
If refactoring an existing widget, legacy data in localStorage may cause issues:

```javascript
// Browser console commands to clear legacy data
localStorage.removeItem('pm-dashboard-store-v2');  // Dashboard widget configs
localStorage.removeItem('gravity_teams_v1');        // Team member IDs
location.reload();
```

## 8. Verification
// turbo
```bash
# Verify strictly without Local DB
docker stop project-management-agent-openproject_db_v13-1
```
- Reload the page.
- Widget should show "Provider Required" if no providerId is configured.
- Widget should load data from remote provider when providerId IS configured.

---

## Reference Implementation
See `TeamWorklogs` refactoring (Jan 2026):
- [worklogs-view.tsx](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/web/src/app/pm/chat/components/views/worklogs-view.tsx)
- [team-data-context.tsx](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/web/src/app/team/context/team-data-context.tsx)
- [custom-dashboard-view.tsx](file:///Volumes/Data%201/Gravity_ProjectManagementAgent/Project-Management-Agent/web/src/app/pm/chat/components/views/custom-dashboard-view.tsx) (config-triggered reload)
