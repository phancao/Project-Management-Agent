# Frontend Architecture Overview

## Technology Stack

- **Framework**: Next.js 15.5.6 (App Router)
- **Language**: TypeScript
- **UI Library**: React 19.2.0
- **Styling**: Tailwind CSS 4.1.16
- **State Management**: 
  - Zustand (global state)
  - React Query (@tanstack/react-query) for server state
  - React Context (PMLoadingContext)
- **UI Components**: Radix UI primitives + custom components
- **Drag & Drop**: @dnd-kit/core, @dnd-kit/sortable
- **Build Tool**: Next.js with Turbo mode

## Project Structure

```
web/src/
├── app/                          # Next.js App Router pages
│   ├── api/                      # Next.js API routes (proxies to backend)
│   │   ├── pm/                   # PM-related API proxies
│   │   └── utils/                # API utilities (get-backend-url.ts)
│   ├── chat/                     # General chat interface
│   ├── pm/                       # Project Management module
│   │   ├── chat/                 # PM chat interface
│   │   ├── components/           # PM-specific components
│   │   ├── context/              # PM loading context
│   │   ├── hooks/                # PM-specific hooks
│   │   ├── overview/             # Overview page
│   │   └── utils/                # PM utilities
│   ├── projects/                 # Projects page
│   └── settings/                 # Settings page
├── components/                    # Shared UI components
│   ├── deer-flow/                # Custom components
│   ├── editor/                   # Rich text editor
│   ├── magicui/                  # UI animations
│   └── ui/                       # Base UI components (Radix)
├── core/                         # Core business logic
│   ├── api/                      # API clients and hooks
│   │   ├── hooks/                # React hooks for data fetching
│   │   │   └── pm/              # PM-specific hooks
│   │   └── resolve-service-url.ts
│   ├── config/                   # Configuration
│   ├── mcp/                      # MCP (Model Context Protocol) integration
│   ├── messages/                 # Message handling
│   ├── sse/                      # Server-Sent Events
│   └── store/                    # Zustand stores
└── lib/                          # Utility libraries
```

## Key Architecture Patterns

### 1. Data Flow Architecture

```
User Action
    ↓
React Component (UI)
    ↓
Custom Hook (useTasks, useProjects, etc.)
    ↓
Next.js API Route (/api/pm/projects/route.ts)
    ↓
Backend Service (http://api:8000)
    ↓
PM Service (http://pm-service:8001)
    ↓
PM Provider (OpenProject, JIRA, etc.)
```

### 2. Project ID Format

**Composite ID Format**: `provider_id:project_id`

- Example: `d7e300c6-d6c0-4c08-bc8d-e41967458d86:478`
- Provider ID: UUID of the PM provider connection
- Project ID: Native project ID from the PM system

**Key Functions**:
- `extractProviderId(projectId)`: Extracts provider UUID from composite ID
- `extractProjectKey(projectId)`: Extracts native project ID
- `getProviderTypeFromProjectId()`: Maps provider ID to provider type (jira, openproject_v13, etc.)

### 3. API Communication

#### Client-Side (Browser)
- Uses `resolveServiceURL()` → `NEXT_PUBLIC_API_URL` (default: `http://localhost:8000/api/`)
- Direct fetch to backend (CORS configured)

#### Server-Side (Next.js API Routes)
- Uses `getBackendUrl()` → `http://api:8000` (Docker service name)
- Next.js API routes act as proxies to backend
- Located in `web/src/app/api/pm/`

**Why Two Approaches?**
- Browser: Uses `localhost:8000` (accessible from host machine)
- Server: Uses `api:8000` (Docker internal networking)

### 4. State Management

#### Three-Tier State Architecture

1. **Server State** (React Query)
   - Cached API responses
   - Automatic refetching
   - Optimistic updates

2. **Global State** (Zustand)
   - User preferences
   - Settings
   - UI state

3. **Context State** (React Context)
   - `PMLoadingContext`: Tracks loading states for PM data
   - `PMLoadingProvider`: Provides loading state management

#### Data Fetching Hooks

Located in `web/src/core/api/hooks/pm/`:

- `use-projects.ts`: Fetches project list
- `use-tasks.ts`: Fetches tasks for a project (with caching)
- `use-sprints.ts`: Fetches sprints
- `use-epics.ts`: Fetches epics
- `use-statuses.ts`: Fetches statuses
- `use-priorities.ts`: Fetches priorities
- `use-users.ts`: Fetches users
- `use-providers.ts`: Fetches PM provider connections
- `use-pm-refresh.ts`: Handles PM refresh events

**Caching Strategy**:
- Tasks: 5-minute cache (`CACHE_DURATION = 5 * 60 * 1000`)
- Projects: No explicit cache (React Query handles it)
- Other data: React Query default caching

### 5. PM Views Architecture

#### Main Layout (`/pm/chat/page.tsx`)

```
┌─────────────────────────────────────────────────┐
│ PMHeader (Fixed Top)                            │
│ - Project Selector                              │
│ - Navigation Tabs (Overview, Project Management)│
│ - Provider Management Button                    │
└─────────────────────────────────────────────────┘
┌──────────────┬─────────────────────────────────┐
│              │                                   │
│ MessagesBlock│ PMViewsPanel                     │
│ (40% width)  │ (60% width)                      │
│              │                                   │
│ - AI Chat    │ - Backlog View                   │
│ - Messages   │ - Board View                     │
│              │ - Charts View                     │
│              │ - Timeline View                  │
│              │ - Team View                       │
└──────────────┴─────────────────────────────────┘
```

#### PM Views Panel (`pm-views-panel.tsx`)

Five main views:
1. **Backlog View** (`backlog-view.tsx`): Sprint-based task organization
2. **Board View** (`sprint-board-view.tsx`): Kanban board with drag & drop
3. **Charts View** (`charts-panel-view.tsx`): Analytics and visualizations
4. **Timeline View** (`timeline-view.tsx`): Gantt-style timeline
5. **Team View** (`team-assignments-view.tsx`): Team workload distribution

### 6. Drag & Drop System

**Library**: `@dnd-kit/core`, `@dnd-kit/sortable`

**Key Components**:
- `DndContext`: Main drag context
- `SortableContext`: Sortable items container
- `useSortable`: Hook for sortable items
- `DragOverlay`: Drag preview overlay

**Drag Types**:
- `task`: Task cards
- `sprint`: Sprint sections (in backlog view)
- `epic`: Epic sections

**Board View Drag Flow**:
1. User drags task card
2. `onDragStart`: Records drag state
3. `onDragOver`: Updates visual feedback
4. `onDragEnd`: Calls API to update task status/sprint
5. Optimistic update + refresh on success

### 7. Loading State Management

**PMLoadingContext** (`pm-loading-context.tsx`):

Tracks loading states for:
- Providers
- Filter Data (projects, sprints, statuses, priorities, epics)
- Tasks

**States**:
- `isFilterDataReady`: All filter data loaded
- `canLoadTasks`: Can safely load tasks (providers + filter data ready)

**Refresh Mechanism**:
- `pm_refresh` custom event: Dispatched when PM data should refresh
- `usePMRefresh()` hook: Listens for refresh events
- All data hooks subscribe to refresh events

### 8. Error Handling

**Three-Level Error Handling**:

1. **Network Errors**: Toast notifications via `sonner`
2. **API Errors**: User-friendly error messages
3. **Component Errors**: Error boundaries (if implemented)

**Error Types Handled**:
- 404: Project not found
- 410: Project no longer available
- 401/403: Authentication failed
- 500+: Server error
- Network errors: Connection issues

### 9. Project Selection Flow

```
1. User opens /pm/chat
2. PMHeader loads projects via useProjects()
3. If no project in URL, auto-selects first project
4. Router.push(`/pm/chat?project=${projectId}`)
5. All views read projectId from URL via useSearchParams()
6. useProjectData() hook extracts projectId from URL
7. Data hooks (useTasks, useSprints, etc.) fetch data for projectId
```

**Key Hook**: `useProjectData()`
- Extracts `projectId` from URL search params
- Finds matching project from projects list
- Returns `projectIdForData` (prioritizes activeProject.id, falls back to URL param)

### 10. Provider Management

**Provider Types Supported**:
- `openproject`: OpenProject v16
- `openproject_v13`: OpenProject v13 (current)
- `jira`: JIRA
- `clickup`: ClickUp
- `mock`: Demo/mock data

**Provider Utilities** (`provider-utils.ts`):
- `extractProviderId()`: Gets provider UUID from project ID
- `getProviderTypeFromProjectId()`: Maps provider ID → type
- `getProviderBadgeConfig()`: Gets badge styling for provider type

**Provider Mappings** (`use-providers.ts`):
- `typeMap`: provider_id → provider_type
- `urlMap`: provider_id → base_url

### 11. Task Caching Strategy

**Location**: `use-tasks.ts`

**Cache Implementation**:
```typescript
const tasksCache = new Map<string, { data: Task[]; timestamp: number }>();
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes
```

**Cache Key**: `projectId`

**Cache Behavior**:
- Cache checked before fetch
- Cache used for initial state (avoids loading flash)
- Cache invalidated on refresh event
- Cache updated after successful fetch

**Why Cache?**
- Prevents loading flash when switching views
- Reduces API calls
- Improves perceived performance

### 12. API Route Proxies

**Purpose**: Next.js API routes proxy requests to backend

**Why Needed?**
- Server-side requests need Docker service name (`api:8000`)
- Browser requests use `localhost:8000`
- API routes handle server-side → backend communication

**Example**: `web/src/app/api/pm/projects/route.ts`
```typescript
const BACKEND_URL = getBackendUrl(); // http://api:8000
const url = `${BACKEND_URL}/api/pm/projects`;
const response = await fetch(url);
```

**All PM API Routes**:
- `/api/pm/projects` → Backend `/api/pm/projects`
- `/api/pm/projects/[project_id]/tasks` → Backend `/api/pm/projects/{id}/tasks`
- `/api/pm/projects/[project_id]/sprints` → Backend `/api/pm/projects/{id}/sprints`
- ... (14 total routes)

### 13. Debug Utilities

**Location**: `web/src/app/pm/utils/debug.ts`

**Debug Categories**:
- `debug.api()`: API calls
- `debug.project()`: Project selection
- `debug.error()`: Errors
- `debug.warn()`: Warnings
- `debug.timeStart()` / `debug.timeEnd()`: Performance timing

**Usage**: Controlled by environment or feature flags

### 14. Key Files Reference

**Core Hooks**:
- `web/src/core/api/hooks/pm/use-tasks.ts`: Task fetching with cache
- `web/src/core/api/hooks/pm/use-projects.ts`: Project fetching
- `web/src/app/pm/hooks/use-project-data.ts`: Project ID resolution

**Components**:
- `web/src/app/pm/components/pm-header.tsx`: Top navigation + project selector
- `web/src/app/pm/chat/components/pm-views-panel.tsx`: View switcher
- `web/src/app/pm/chat/components/views/backlog-view.tsx`: Backlog view
- `web/src/app/pm/chat/components/views/sprint-board-view.tsx`: Kanban board

**Utilities**:
- `web/src/app/pm/utils/provider-utils.ts`: Provider ID extraction
- `web/src/app/pm/utils/project-utils.ts`: Project ID utilities
- `web/src/core/api/resolve-service-url.ts`: URL resolution (client-side)
- `web/src/app/api/utils/get-backend-url.ts`: Backend URL (server-side)

**Types**:
- `web/src/app/pm/types/index.ts`: PM type definitions

## Common Patterns

### 1. Project ID Handling
Always use composite format: `provider_id:project_id`
- Extract provider ID: `extractProviderId(projectId)`
- Extract project key: `extractProjectKey(projectId)`

### 2. Data Fetching
Use custom hooks from `core/api/hooks/pm/`
- They handle caching, error handling, and refresh events
- Subscribe to `pm_refresh` events automatically

### 3. Loading States
Use `PMLoadingContext` for coordinated loading states
- Check `canLoadTasks` before fetching tasks
- Use `isFilterDataReady` to know when filter data is loaded

### 4. Error Handling
- Network errors: Show toast with user-friendly message
- API errors: Parse error response, show appropriate message
- Log errors with `debug.error()` for debugging

### 5. URL State Management
- Project selection stored in URL: `?project=provider_id:project_id`
- Use `useSearchParams()` to read
- Use `router.push()` to update

## Future Considerations

1. **Pagination**: Currently loads all tasks (up to 5000 limit). Consider implementing client-side pagination for large projects.

2. **Optimistic Updates**: Some views (board) use optimistic updates. Consider expanding to other views.

3. **Real-time Updates**: Currently uses polling/refresh events. Consider WebSocket/SSE for real-time updates.

4. **Offline Support**: No offline support currently. Consider service workers for offline caching.

5. **Performance**: Large task lists (300+ tasks) may need virtualization. Consider `react-window` or `react-virtual`.

