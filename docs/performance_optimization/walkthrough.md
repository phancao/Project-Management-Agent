# Performance & Loading Improvements Walkthrough

## 1. Backend Performance Optimization
**Goal**: Reduce project loading time.

*   **Change**: Refactored `PMHandler` methods (`list_projects`, `list_tasks`, `list_sprints`, `list_users`, `list_epics`) to use `asyncio.gather`.
*   **Result**: Provider API calls are now executed in parallel.
*   **Verification**: 
    *   Created `tests/verify_parallel_projects.py` (mocking 1s latency per provider).
    *   **Result**: Execution time dropped from ~2s (sequential) to ~1s (parallel).
    *   Logs confirm simultaneous start times for provider requests.

## 2. Global Loading Overlay
**Goal**: Prevent user interaction during initial load and provide clear feedback.

*   **Implementation**:
    *   Created `LoadingContext` (`loading-context.tsx`) and `LoadingProvider`.
    *   Created `LoadingScreen` (`loading-screen.tsx`) with a backdrop and spinner.
    *   Integrated `LoadingProvider` into `web/src/app/layout.tsx`.
    *   Connected `PMLoadingManager` (`web/src/app/pm/components/pm-loading-manager.tsx`) to trigger the overlay during the initial `listProviders` and `listProjects` phase.
*   **User Experience**: Users now see a blocking "Loading..." screen when entering the PM module, ensuring they don't interact with a partially loaded UI.

## 3. Background Refresh (Non-Blocking)
**Goal**: Refresh data without freezing the UI.

*   **Change**: Refactored `useProjects` hook.
*   **Logic**: 
    *   Added `isBackground` flag to `refresh` function.
    *   `usePMRefresh` (triggered by SSE) now calls `refresh(true)`, skipping the `setLoading(true)` step.
*   **Result**: The UI remains interactive and visible while new data is fetched in the background.

## 4. Debugging & Observability
*   **Enhanced Logging**: Added `[PM-DEBUG]` tagged logs with `run_id` to `pm_handler.py` for easy tracing of parallel execution specific requests.
*   **Artifacts**: 
    *   [Merged Debug Logs](merged_debug_logs.md)
    *   [Sequence Analysis](sequence_analysis.md)
