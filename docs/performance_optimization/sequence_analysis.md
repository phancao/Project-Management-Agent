# Sequence Analysis: Project Loading Optimization

## Overview
This analysis details the optimized sequence of events for loading projects and related entities, highlighting the transition from sequential to parallel execution and the integration of the user-facing loading overlay.

## Sequence Diagram (Optimized)

```mermaid
sequenceDiagram
    participant User
    participant Frontend (LoadingProvider)
    participant PMLoadingManager
    participant Backend (PMHandler)
    participant Provider 1
    participant Provider 2

    User->>Frontend (LoadingProvider): Opens PM Page
    Frontend (LoadingProvider)->>User: Show Global Loading Overlay

    PMLoadingManager->>Backend (PMHandler): REST API: /projects (list_projects)
    
    rect rgb(200, 255, 200)
    Note right of Backend (PMHandler): Parallel Execution
    Backend (PMHandler)->>Provider 1: fetch_projects()
    Backend (PMHandler)->>Provider 2: fetch_projects()
    Provider 1-->>Backend (PMHandler): Return Data (Latency: T1)
    Provider 2-->>Backend (PMHandler): Return Data (Latency: T2)
    end
    
    Backend (PMHandler)-->>PMLoadingManager: Return Merged ProjectsList
    
    PMLoadingManager->>Frontend (LoadingProvider): setLoading(false)
    Frontend (LoadingProvider)->>User: Hide Overlay, Show Dashboard

    Note over Frontend (LoadingProvider): Background Refresh
    loop Periodic / SSE Trigger
        Frontend (LoadingProvider)->>Backend (PMHandler): list_projects (Background)
        Backend (PMHandler)-->>Frontend (LoadingProvider): Updated Data
        Note right of Frontend (LoadingProvider): UI does NOT freeze (Loading Overlay remains Hidden)
    end
```

## Key Improvements

1.  **Parallel Backend Fetching**:
    *   **Before**: `Total Time = Sum(Provider_Latencies)`
    *   **After**: `Total Time = Max(Provider_Latencies)`
    *   **Impact**: Significant reduction in loading time, especially with slow providers.

2.  **Blocking Loading Overlay**:
    *   **Implementation**: `LoadingProvider` + `LoadingScreen`
    *   **Behavior**: Blocks user interaction during the critical initial load phase, preventing "empty state" confusion and interaction with incomplete data.

3.  **Background Refresh**:
    *   **Before**: Refresh triggered global `loading=true`, causing UI freeze/flash.
    *   **After**: Refresh keeps `loading=false` locally, updating data silently when available.
