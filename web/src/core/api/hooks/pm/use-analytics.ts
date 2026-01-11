// Analytics API hooks for fetching chart data
import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { usePMRefresh } from "./use-pm-refresh";

// Types based on backend analytics models
export interface ChartDataPoint {
  date?: string;
  value: number;
  label?: string;
  metadata?: Record<string, any>;
}

export interface ChartSeries {
  name: string;
  data: ChartDataPoint[];
  color?: string;
  type?: string;
}

export interface ChartResponse {
  chart_type: string;
  title: string;
  series: ChartSeries[];
  metadata: Record<string, any>;
  generated_at: string;
}

export interface SprintReport {
  sprint_id: string;
  sprint_name: string;
  duration: {
    start: string;
    end: string;
    days: number;
  };
  commitment: {
    planned_points: number;
    completed_points: number;
    completion_rate: number;
    planned_items: number;
    completed_items: number;
  };
  scope_changes: {
    added: number;
    removed: number;
    net_change: number;
    scope_stability: number;
  };
  work_breakdown: Record<string, number>;
  team_performance: {
    velocity: number;
    capacity_hours: number;
    capacity_used: number;
    capacity_utilized: number;
    team_size: number;
  };
  highlights: string[];
  concerns: string[];
}

export interface ProjectSummary {
  project_id: string;
  current_sprint?: {
    id: string;
    name: string;
    status: string;
    progress: number;
  };
  velocity: {
    average: number;
    latest: number;
    trend: string;
  };
  overall_stats: {
    total_items: number;
    completed_items: number;
    completion_rate: number;
  };
  team_size: number;
  generated_at: string;
}

/**
 * Hook to fetch burndown chart data
 */
export function useBurndownChart(projectId: string | null, sprintId?: string, scopeType: string = "story_points") {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["analytics", "burndown", projectId, sprintId, scopeType],
    queryFn: async () => {
      if (!projectId) throw new Error("Project ID is required");

      const params = new URLSearchParams();
      if (sprintId) params.append("sprint_id", sprintId);
      params.append("scope_type", scopeType);

      const url = resolveServiceURL(`analytics/projects/${projectId}/burndown?${params.toString()}`);
      const response = await fetch(url);

      if (!response.ok) {
        let errorDetail = response.statusText;
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || errorData.message || errorDetail;
        } catch {
          // If response is not JSON, use status text
        }
        throw new Error(`Failed to fetch burndown chart: ${errorDetail}`);
      }

      return response.json() as Promise<ChartResponse>;
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes - data is fresh for 5 minutes
    gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes (formerly cacheTime)
  });

  // Listen for PM refresh events and invalidate query
  usePMRefresh(() => {
    queryClient.invalidateQueries({ queryKey: ["analytics", "burndown", projectId, sprintId, scopeType] });
  });

  return query;
}

/**
 * Hook to fetch velocity chart data
 */
export function useVelocityChart(projectId: string | null, sprintCount: number = 6) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["analytics", "velocity", projectId, sprintCount],
    queryFn: async () => {
      if (!projectId) throw new Error("Project ID is required");

      const url = resolveServiceURL(`analytics/projects/${projectId}/velocity?sprint_count=${sprintCount}`);
      const response = await fetch(url);

      if (!response.ok) {
        let errorDetail = response.statusText;
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || errorData.message || errorDetail;
        } catch {
          // If response is not JSON, use status text
        }
        throw new Error(`Failed to fetch velocity chart: ${errorDetail}`);
      }

      return response.json() as Promise<ChartResponse>;
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes - data is fresh for 5 minutes
    gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes
  });

  // Listen for PM refresh events and invalidate query
  usePMRefresh(() => {
    queryClient.invalidateQueries({ queryKey: ["analytics", "velocity", projectId, sprintCount] });
  });

  return query;
}

/**
 * Hook to fetch sprint report
 */
export function useSprintReport(sprintId: string | null, projectId: string | null) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["analytics", "sprint-report", sprintId, projectId],
    queryFn: async () => {
      if (!sprintId || !projectId) throw new Error("Sprint ID and Project ID are required");

      const url = resolveServiceURL(`analytics/sprints/${sprintId}/report?project_id=${projectId}`);
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Failed to fetch sprint report: ${response.statusText}`);
      }

      return response.json() as Promise<SprintReport>;
    },
    enabled: !!sprintId && !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes - data is fresh for 5 minutes
    gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes
  });

  // Listen for PM refresh events and invalidate query
  usePMRefresh(() => {
    queryClient.invalidateQueries({ queryKey: ["analytics", "sprint-report", sprintId, projectId] });
  });

  return query;
}

/**
 * Hook to fetch project analytics summary
 */
export function useProjectSummary(projectId: string | null) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["analytics", "summary", projectId],
    queryFn: async () => {
      if (!projectId) throw new Error("Project ID is required");

      const url = resolveServiceURL(`analytics/projects/${projectId}/summary`);
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Failed to fetch project summary: ${response.statusText}`);
      }

      return response.json() as Promise<ProjectSummary>;
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes - data is fresh for 5 minutes
    gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes
  });

  // Listen for PM refresh events and invalidate query
  usePMRefresh(() => {
    queryClient.invalidateQueries({ queryKey: ["analytics", "summary", projectId] });
  });

  return query;
}

/**
 * Hook to fetch CFD (Cumulative Flow Diagram) chart data
 */
export function useCFDChart(projectId: string | null, sprintId?: string, daysBack: number = 30) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["analytics", "cfd", projectId, sprintId, daysBack],
    queryFn: async () => {
      if (!projectId) throw new Error("Project ID is required");

      const params = new URLSearchParams();
      if (sprintId) params.append("sprint_id", sprintId);
      params.append("days_back", daysBack.toString());

      const url = resolveServiceURL(`analytics/projects/${projectId}/cfd?${params.toString()}`);
      const response = await fetch(url);

      if (!response.ok) {
        let errorDetail = response.statusText;
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || errorData.message || errorDetail;
        } catch {
          // If response is not JSON, use status text
        }
        throw new Error(`Failed to fetch CFD chart: ${errorDetail}`);
      }

      return response.json() as Promise<ChartResponse>;
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes - data is fresh for 5 minutes
    gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes
  });

  // Listen for PM refresh events and invalidate query
  usePMRefresh(() => {
    queryClient.invalidateQueries({ queryKey: ["analytics", "cfd", projectId, sprintId, daysBack] });
  });

  return query;
}

/**
 * Hook to fetch Cycle Time / Control Chart data
 */
export function useCycleTimeChart(projectId: string | null, sprintId?: string, daysBack: number = 60) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["analytics", "cycleTime", projectId, sprintId, daysBack],
    queryFn: async () => {
      if (!projectId) throw new Error("Project ID is required");

      const params = new URLSearchParams();
      if (sprintId) params.append("sprint_id", sprintId);
      params.append("days_back", daysBack.toString());

      const url = resolveServiceURL(`analytics/projects/${projectId}/cycle-time?${params.toString()}`);
      const response = await fetch(url);

      if (!response.ok) {
        let errorDetail = response.statusText;
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || errorData.message || errorDetail;
        } catch {
          // If response is not JSON, use status text
        }
        throw new Error(`Failed to fetch cycle time chart: ${errorDetail}`);
      }

      return response.json() as Promise<ChartResponse>;
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes - data is fresh for 5 minutes
    gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes
  });

  // Listen for PM refresh events and invalidate query
  usePMRefresh(() => {
    queryClient.invalidateQueries({ queryKey: ["analytics", "cycleTime", projectId, sprintId, daysBack] });
  });

  return query;
}

/**
 * Hook to fetch Work Distribution chart data
 */
export function useWorkDistributionChart(
  projectId: string | null,
  dimension: "assignee" | "priority" | "type" | "status" = "assignee",
  sprintId?: string
) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["analytics", "workDistribution", projectId, dimension, sprintId],
    queryFn: async () => {
      if (!projectId) throw new Error("Project ID is required");

      const params = new URLSearchParams();
      params.append("dimension", dimension);
      if (sprintId) params.append("sprint_id", sprintId);

      const url = resolveServiceURL(`analytics/projects/${projectId}/work-distribution?${params.toString()}`);
      const response = await fetch(url);

      if (!response.ok) {
        let errorDetail = response.statusText;
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || errorData.message || errorDetail;
        } catch {
          // If response is not JSON, use status text
        }
        throw new Error(`Failed to fetch work distribution chart: ${errorDetail}`);
      }

      return response.json() as Promise<ChartResponse>;
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes - data is fresh for 5 minutes
    gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes
  });

  // Listen for PM refresh events and invalidate query
  usePMRefresh(() => {
    queryClient.invalidateQueries({ queryKey: ["analytics", "workDistribution", projectId, dimension, sprintId] });
  });

  return query;
}

/**
 * Hook to prefetch Work Distribution chart data for instant tab switching.
 * Returns a callback that can prefetch distribution data for any dimension.
 */
export function usePrefetchWorkDistribution() {
  const queryClient = useQueryClient();

  const prefetch = useCallback(
    (projectId: string, dimension: "assignee" | "priority" | "type" | "status", sprintId?: string) => {
      queryClient.prefetchQuery({
        queryKey: ["analytics", "workDistribution", projectId, dimension, sprintId],
        queryFn: async () => {
          const params = new URLSearchParams();
          params.append("dimension", dimension);
          if (sprintId) params.append("sprint_id", sprintId);

          const url = resolveServiceURL(`analytics/projects/${projectId}/work-distribution?${params.toString()}`);
          const response = await fetch(url);

          if (!response.ok) {
            let errorDetail = response.statusText;
            try {
              const errorData = await response.json();
              errorDetail = errorData.detail || errorData.message || errorDetail;
            } catch {
              // If response is not JSON, use status text
            }
            throw new Error(`Failed to fetch work distribution chart: ${errorDetail}`);
          }

          return response.json() as Promise<ChartResponse>;
        },
        staleTime: 5 * 60 * 1000, // 5 minutes
      });
    },
    [queryClient]
  );

  return prefetch;
}

/**
 * Hook to fetch Issue Trend Analysis chart data
 */
export function useIssueTrendChart(projectId: string | null, daysBack: number = 30, sprintId?: string) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["analytics", "issueTrend", projectId, daysBack, sprintId],
    queryFn: async () => {
      if (!projectId) throw new Error("Project ID is required");

      const params = new URLSearchParams();
      params.append("days_back", daysBack.toString());
      if (sprintId) params.append("sprint_id", sprintId);

      const url = resolveServiceURL(`analytics/projects/${projectId}/issue-trend?${params.toString()}`);
      const response = await fetch(url);

      if (!response.ok) {
        let errorDetail = response.statusText;
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || errorData.message || errorDetail;
        } catch {
          // If response is not JSON, use status text
        }
        throw new Error(`Failed to fetch issue trend chart: ${errorDetail}`);
      }

      return response.json() as Promise<ChartResponse>;
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes - data is fresh for 5 minutes
    gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes
  });

  // Listen for PM refresh events and invalidate query
  usePMRefresh(() => {
    queryClient.invalidateQueries({ queryKey: ["analytics", "issueTrend", projectId, daysBack, sprintId] });
  });

  return query;
}

