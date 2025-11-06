// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";

import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { usePMRefresh } from "./use-pm-refresh";

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
  sprint_id?: string;
  epic_id?: string;
}

const fetchTasksFn = async (projectId?: string) => {
  // If no project ID is provided, return empty array (no fallback to /pm/tasks/my)
  if (!projectId) {
    return [];
  }
  
  const url = `pm/projects/${projectId}/tasks`;
  const fullUrl = resolveServiceURL(url);
  console.log(`[useTasks] Fetching tasks from: ${fullUrl}`);
  let response: Response;
  try {
    response = await fetch(fullUrl);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(`[useTasks] Network error fetching tasks from ${fullUrl}:`, errorMessage);
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
      console.warn(`Failed to fetch tasks from ${fullUrl}: ${errorDetail}`);
    } else {
      console.error(`Failed to fetch tasks from ${fullUrl}: ${errorDetail}`);
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
    // Clear tasks immediately when projectId changes
    setTasks([]);
    setError(null);
    
    // If no project ID, set loading to false and return empty
    if (!projectId) {
      setLoading(false);
      return;
    }
    
    setLoading(true);
    
    // Fetch new data
    fetchTasksFn(projectId)
      .then((data) => {
        setTasks(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err as Error);
        setTasks([]);
        setLoading(false);
      });
  }, [projectId]);

  usePMRefresh(refresh);

  return { tasks, loading, error, refresh };
}

export function useMyTasks() {
  return useTasks();
}

const fetchAllTasksFn = async () => {
  const fullUrl = resolveServiceURL("pm/tasks/all");
  console.log(`[useAllTasks] Fetching all tasks from: ${fullUrl}`);
  let response: Response;
  try {
    response = await fetch(fullUrl);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(`[useAllTasks] Network error fetching all tasks from ${fullUrl}:`, errorMessage);
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
      console.warn(`Failed to fetch all tasks from ${fullUrl}: ${errorDetail}`);
    } else {
      console.error(`Failed to fetch all tasks from ${fullUrl}: ${errorDetail}`);
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

