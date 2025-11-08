// Analytics API hooks for fetching chart data
import { useQuery } from "@tanstack/react-query";
import { resolveServiceURL } from "~/lib/utils";

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
  return useQuery({
    queryKey: ["analytics", "burndown", projectId, sprintId, scopeType],
    queryFn: async () => {
      if (!projectId) throw new Error("Project ID is required");
      
      const params = new URLSearchParams();
      if (sprintId) params.append("sprint_id", sprintId);
      params.append("scope_type", scopeType);
      
      const url = resolveServiceURL(`analytics/projects/${projectId}/burndown?${params.toString()}`);
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch burndown chart: ${response.statusText}`);
      }
      
      return response.json() as Promise<ChartResponse>;
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch velocity chart data
 */
export function useVelocityChart(projectId: string | null, sprintCount: number = 6) {
  return useQuery({
    queryKey: ["analytics", "velocity", projectId, sprintCount],
    queryFn: async () => {
      if (!projectId) throw new Error("Project ID is required");
      
      const url = resolveServiceURL(`analytics/projects/${projectId}/velocity?sprint_count=${sprintCount}`);
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch velocity chart: ${response.statusText}`);
      }
      
      return response.json() as Promise<ChartResponse>;
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch sprint report
 */
export function useSprintReport(sprintId: string | null, projectId: string | null) {
  return useQuery({
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
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch project analytics summary
 */
export function useProjectSummary(projectId: string | null) {
  return useQuery({
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
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch CFD (Cumulative Flow Diagram) chart data
 */
export function useCFDChart(projectId: string | null, sprintId?: string, daysBack: number = 30) {
  return useQuery({
    queryKey: ["analytics", "cfd", projectId, sprintId, daysBack],
    queryFn: async () => {
      if (!projectId) throw new Error("Project ID is required");
      
      const params = new URLSearchParams();
      if (sprintId) params.append("sprint_id", sprintId);
      params.append("days_back", daysBack.toString());
      
      const url = resolveServiceURL(`analytics/projects/${projectId}/cfd?${params.toString()}`);
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch CFD chart: ${response.statusText}`);
      }
      
      return response.json() as Promise<ChartResponse>;
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

