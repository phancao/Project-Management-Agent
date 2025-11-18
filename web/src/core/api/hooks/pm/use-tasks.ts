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

// Cache for tasks by projectId
const tasksCache = new Map<string, { data: Task[]; timestamp: number }>();
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

export function useTasks(projectId?: string) {
  // Initialize from cache if available to avoid loading state
  const getInitialState = () => {
    if (!projectId) {
      return { tasks: [], loading: false, error: null };
    }
    const cached = tasksCache.get(projectId);
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
      return { tasks: cached.data, loading: false, error: null };
    }
    return { tasks: [], loading: true, error: null };
  };
  
  const initialState = getInitialState();
  const [tasks, setTasks] = useState<Task[]>(initialState.tasks);
  const [loading, setLoading] = useState(initialState.loading);
  const [error, setError] = useState<Error | null>(initialState.error);

  const refresh = useCallback((clearTasks: boolean = true, forceRefresh: boolean = false) => {
    // If no project ID, return empty immediately
    if (!projectId) {
      setTasks([]);
      setLoading(false);
      setError(null);
      return;
    }
    
    // Check cache if not forcing refresh
    if (!forceRefresh) {
      const cached = tasksCache.get(projectId);
      if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
        debug.api('Using cached tasks', { projectId, count: cached.data.length });
        setTasks(cached.data);
        setLoading(false);
        setError(null);
        return;
      }
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
        // Update cache
        tasksCache.set(projectId, { data, timestamp: Date.now() });
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
    
    // If no project ID, set loading to false and return empty
    if (!projectId) {
      debug.api('No projectId, setting loading to false');
      setTasks([]);
      setError(null);
      setLoading(false);
      return;
    }
    
    // Check cache first - if we already have cached data from initial state, skip
    const cached = tasksCache.get(projectId);
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
      // Always update from cache if it exists and is valid, even if tasks are already set
      // This ensures we use the latest cached data when switching views
      if (tasks.length !== cached.data.length || JSON.stringify(tasks.map(t => t.id).sort()) !== JSON.stringify(cached.data.map(t => t.id).sort())) {
        debug.api('Using cached tasks in effect', { projectId, count: cached.data.length, currentTasksCount: tasks.length });
        setTasks(cached.data);
        setLoading(false);
        setError(null);
      } else if (loading) {
        // If we have the same tasks but loading is still true, set it to false
        debug.api('Cache matches, setting loading to false', { projectId, count: cached.data.length });
        setLoading(false);
        setError(null);
      }
      return;
    }
    
    // Only fetch if we don't have cached data
    // If tasks are already set from initial state, don't clear them
    if (tasks.length === 0) {
      debug.api('Clearing tasks (projectId changed or cache expired)');
      setTasks([]);
      setError(null);
      setLoading(true);
    }
    
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
          // Update cache
          tasksCache.set(projectId, { data, timestamp: Date.now() });
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
  }, [projectId]); // Removed tasks from deps to avoid infinite loop

  usePMRefresh(() => refresh(true, true)); // Force refresh on PM refresh event

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


