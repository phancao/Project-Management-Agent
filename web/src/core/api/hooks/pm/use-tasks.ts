// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";

import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { usePMRefresh } from "./use-pm-refresh";
import { debug } from "~/app/pm/utils/debug";

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  estimated_hours?: number;
  start_date?: string;
  due_date?: string;
  assigned_to?: string;
  assignee_id?: string;
  project_name?: string;
  sprint_id?: string | null;
  epic_id?: string | null;
}

const fetchTasksFn = async (projectId?: string) => {
  // If no project ID is provided, return empty array (no fallback to /pm/tasks/my)
  if (!projectId) {
    return [];
  }
  
  const url = `pm/projects/${projectId}/tasks`;
  const fullUrl = resolveServiceURL(url);
  debug.api('Fetching tasks', { url: fullUrl, projectId });
  let response: Response;
  try {
    response = await fetch(fullUrl);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    debug.error('Network error fetching tasks', { url: fullUrl, error: errorMessage });
    const userFriendlyError = new Error(`Network error: Unable to connect to the server. Please check your connection and try again.`);
    toast.error("Connection Error", {
      description: "Unable to connect to the server. Please check your connection.",
    });
    throw userFriendlyError;
  }
  
    if (!response.ok) {
    let errorDetail = `HTTP ${response.status}`;
    let userFriendlyMessage = "Failed to load tasks";
    const isClientError = response.status >= 400 && response.status < 500;
    
    try {
      const errorData = await response.json();
      errorDetail = errorData.detail || errorData.message || errorDetail;
      
      // Provide user-friendly messages for specific status codes
      if (response.status === 410) {
        userFriendlyMessage = "Project no longer available";
        const description = errorDetail.includes("410") || errorDetail.includes("Gone")
          ? "This project may have been deleted, archived, or is no longer accessible. Please verify the project exists in your PM provider."
          : errorDetail;
        toast.error(userFriendlyMessage, {
          description,
          duration: 8000,
        });
      } else if (response.status === 404) {
        userFriendlyMessage = "Project not found";
        toast.error(userFriendlyMessage, {
          description: "The requested project could not be found. Please check the project ID.",
          duration: 6000,
        });
      } else if (response.status === 401 || response.status === 403) {
        userFriendlyMessage = "Authentication failed";
        toast.error(userFriendlyMessage, {
          description: "Please check your PM provider credentials and try again.",
          duration: 6000,
        });
      } else if (response.status >= 500) {
        userFriendlyMessage = "Server error";
        toast.error(userFriendlyMessage, {
          description: "The server encountered an error. Please try again later.",
          duration: 6000,
        });
      } else {
        toast.error(userFriendlyMessage, {
          description: errorDetail,
          duration: 5000,
        });
      }
    } catch {
      // If response is not JSON, use status text
      errorDetail = response.statusText || errorDetail;
      
      if (response.status === 410) {
        userFriendlyMessage = "Project no longer available";
        toast.error(userFriendlyMessage, {
          description: "This project may have been deleted or archived.",
          duration: 8000,
        });
      } else {
        toast.error("Failed to load tasks", {
          description: errorDetail,
          duration: 5000,
        });
      }
    }
    
    // Log client errors (4xx) as warnings since they're expected business conditions
    // Log server errors (5xx) as errors since they're unexpected
    if (isClientError) {
      debug.warn('Failed to fetch tasks (client error)', { url: fullUrl, error: errorDetail });
    } else {
      debug.error('Failed to fetch tasks (server error)', { url: fullUrl, error: errorDetail });
    }
    throw new Error(userFriendlyMessage + (errorDetail !== userFriendlyMessage ? `: ${errorDetail}` : ""));
  }
  return response.json();
};

export function useTasks(projectId?: string) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true); // Start as true to show loading state initially
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback((clearTasks: boolean = true) => {
    // If no project ID, return empty immediately
    if (!projectId) {
      setTasks([]);
      setLoading(false);
      setError(null);
      return;
    }
    
    // Optionally clear tasks to avoid showing stale data
    // Don't clear if we're just refreshing after an update (to prevent flash)
    if (clearTasks) {
      setTasks([]);
    }
    setLoading(true);
    setError(null);
    
    fetchTasksFn(projectId)
      .then((data) => {
        setTasks(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err as Error);
        setTasks([]); // Clear tasks on error
        setLoading(false);
      });
  }, [projectId]);

  useEffect(() => {
    debug.api('Effect triggered', { projectId });
    // Clear tasks immediately when projectId changes to avoid showing stale data
    debug.api('Clearing tasks (projectId changed)');
    setTasks([]);
    setError(null);
    
    // If no project ID, set loading to false and return empty
    if (!projectId) {
      debug.api('No projectId, setting loading to false');
      setLoading(false);
      return;
    }
    
    debug.api('Setting loading to true for projectId', { projectId });
    setLoading(true);
    
    // Use a flag to track if this effect is still relevant (projectId hasn't changed)
    let isCurrent = true;
    debug.timeStart(`fetch-tasks-${projectId}`);
    
    // Fetch new data
    fetchTasksFn(projectId)
      .then((data) => {
        debug.timeEnd(`fetch-tasks-${projectId}`, `Tasks fetched successfully. Count: ${data.length}`);
        debug.api('Tasks fetched successfully', { 
          count: data.length, 
          projectId, 
          isCurrent,
          taskIds: data.length > 0 ? data.slice(0, 5).map(t => t.id) : []
        });
        // Only update state if this effect is still relevant (projectId hasn't changed)
        if (isCurrent) {
          debug.api('Updating state with tasks', { count: data.length });
          setTasks(data);
          setLoading(false);
          debug.api('State updated');
        } else {
          debug.api('Effect is stale (projectId changed), ignoring response');
        }
      })
      .catch((err) => {
        debug.error('Error fetching tasks', { projectId, error: err });
        // Only update state if this effect is still relevant (projectId hasn't changed)
        if (isCurrent) {
          setError(err as Error);
          setTasks([]);
          setLoading(false);
        } else {
          debug.api('Effect is stale (projectId changed), ignoring error');
        }
      });
    
    // Cleanup: mark this effect as stale if projectId changes
    return () => {
      debug.api('Cleanup: marking effect as stale', { projectId });
      isCurrent = false;
    };
  }, [projectId]);

  usePMRefresh(refresh);

  return { tasks, loading, error, refresh };
}

export function useMyTasks() {
  return useTasks();
}

const fetchAllTasksFn = async () => {
  const fullUrl = resolveServiceURL("pm/tasks/all");
  debug.api('Fetching all tasks', { url: fullUrl });
  let response: Response;
  try {
    response = await fetch(fullUrl);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    debug.error('Network error fetching all tasks', { url: fullUrl, error: errorMessage });
    const userFriendlyError = new Error(`Network error: Unable to connect to the server. Please check your connection and try again.`);
    toast.error("Connection Error", {
      description: "Unable to connect to the server. Please check your connection.",
    });
    throw userFriendlyError;
  }
  
  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}`;
    let userFriendlyMessage = "Failed to load tasks";
    const isClientError = response.status >= 400 && response.status < 500;
    
    try {
      const errorData = await response.json();
      errorDetail = errorData.detail || errorData.message || errorDetail;
      
      if (response.status === 401 || response.status === 403) {
        userFriendlyMessage = "Authentication failed";
        toast.error(userFriendlyMessage, {
          description: "Please check your PM provider credentials and try again.",
          duration: 6000,
        });
      } else if (response.status >= 500) {
        userFriendlyMessage = "Server error";
        toast.error(userFriendlyMessage, {
          description: "The server encountered an error. Please try again later.",
          duration: 6000,
        });
      } else {
        toast.error(userFriendlyMessage, {
          description: errorDetail,
          duration: 5000,
        });
      }
    } catch {
      errorDetail = response.statusText || errorDetail;
      toast.error("Failed to load tasks", {
        description: errorDetail,
        duration: 5000,
      });
    }
    
    // Log client errors (4xx) as warnings since they're expected business conditions
    // Log server errors (5xx) as errors since they're unexpected
    if (isClientError) {
      debug.warn('Failed to fetch all tasks (client error)', { url: fullUrl, error: errorDetail });
    } else {
      debug.error('Failed to fetch all tasks (server error)', { url: fullUrl, error: errorDetail });
    }
    throw new Error(userFriendlyMessage + (errorDetail !== userFriendlyMessage ? `: ${errorDetail}` : ""));
  }
  return response.json();
};

export function useAllTasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    fetchAllTasksFn()
      .then((data) => {
        setTasks(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err as Error);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  usePMRefresh(refresh);

  return { tasks, loading, error, refresh };
}

