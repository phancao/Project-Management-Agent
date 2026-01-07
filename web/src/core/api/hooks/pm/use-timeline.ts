import { useCallback, useEffect, useState } from "react";

import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { usePMRefresh } from "./use-pm-refresh";

export interface TimelineSprint {
  id: string;
  name: string;
  start_date: string | null;
  end_date: string | null;
  status?: string | null;
  goal?: string | null;
  duration_days?: number | null;
  is_scheduled: boolean;
  missing_reason?: string | null;
}

export interface TimelineTask {
  id: string;
  title: string;
  description?: string | null;
  status?: string | null;
  priority?: string | null;
  estimated_hours?: number | null;
  start_date: string | null;
  due_date: string | null;
  project_name?: string | null;
  epic_id?: string | null;
  sprint_id?: string | null;
  sprint_name?: string | null;
  sprint_start_date?: string | null;
  sprint_end_date?: string | null;
  assignee_id?: string | null;
  assignee_name?: string | null;  // From PM Service
  assigned_to?: string | null;    // Legacy/alias
  duration_days?: number | null;
  is_scheduled: boolean;
  missing_reason?: string | null;
}

export interface ProjectTimelineResponse {
  project_id: string;
  project_key?: string;
  project_name?: string;
  sprints: TimelineSprint[];
  tasks: TimelineTask[];
  unscheduled: {
    sprints: TimelineSprint[];
    tasks: TimelineTask[];
  };
}

const fetchTimeline = async (projectId: string): Promise<ProjectTimelineResponse> => {
  const url = resolveServiceURL(`pm/projects/${projectId}/timeline`);
  const response = await fetch(url);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Failed to load project timeline (status ${response.status})`);
  }
  return response.json();
};

export function useTimeline(projectId?: string | null) {
  const [timeline, setTimeline] = useState<ProjectTimelineResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(!!projectId);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(() => {
    if (!projectId) {
      setTimeline(null);
      setLoading(false);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    fetchTimeline(projectId)
      .then((data) => {
        setTimeline(data);
      })
      .catch((err: Error) => {
        setTimeline(null);
        setError(err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [projectId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  usePMRefresh(refresh);

  return { timeline, loading, error, refresh };
}


