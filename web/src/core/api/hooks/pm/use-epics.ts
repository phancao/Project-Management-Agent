// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useEffect, useState, useCallback } from "react";

import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { usePMRefresh } from "./use-pm-refresh";

export interface Epic {
  id: string;
  name: string;
  description?: string;
  project_id?: string;
  status?: string;
  priority?: string;
  start_date?: string;
  end_date?: string;
  owner_id?: string;
  color?: string; // Optional color for UI display
}

const fetchEpics = async (projectId: string): Promise<Epic[]> => {
  const url = resolveServiceURL(`pm/projects/${projectId}/epics`);
  const response = await fetch(url.toString());
  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage = `Failed to fetch epics: ${response.status} ${response.statusText}`;
    try {
      const errorData = JSON.parse(errorText);
      errorMessage = errorData.detail || errorMessage;
    } catch {
      // If response is not JSON, use the text or default message
      if (errorText) {
        errorMessage = errorText;
      }
    }
    throw new Error(errorMessage);
  }
  const data = await response.json();
  // Map the response to include color if not present
  return data.map((epic: any) => ({
    ...epic,
    color: epic.color || `bg-${["yellow", "orange", "blue", "green", "purple", "pink", "indigo"][epic.id?.charCodeAt(0) % 7 || 0]}-400`,
  }));
};

export function useEpics(projectId: string | null | undefined) {
  const [epics, setEpics] = useState<Epic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(() => {
    if (!projectId) {
      setEpics([]);
      setLoading(false);
      setError(null);
      return;
    }
    
    setLoading(true);
    setError(null);
    // Clear epics immediately when project changes to avoid showing stale data
    setEpics([]);
    
    fetchEpics(projectId)
      .then((data) => {
        setEpics(data);
        setLoading(false);
        setError(null);
      })
      .catch((err) => {
        setError(err as Error);
        setEpics([]); // Clear epics on error to avoid showing stale data
        setLoading(false);
      });
  }, [projectId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  usePMRefresh(refresh);

  const createEpic = useCallback(async (epicData: Omit<Epic, "id">): Promise<Epic> => {
    if (!projectId) {
      throw new Error("Project ID is required to create an epic");
    }
    
    const url = resolveServiceURL(`pm/projects/${projectId}/epics`);
    const response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(epicData),
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = `Failed to create epic: ${response.status} ${response.statusText}`;
      try {
        const errorData = JSON.parse(errorText);
        errorMessage = errorData.detail || errorMessage;
      } catch {
        if (errorText) {
          errorMessage = errorText;
        }
      }
      throw new Error(errorMessage);
    }
    
    const createdEpic = await response.json();
    await refresh(); // Refresh the list
    return {
      ...createdEpic,
      color: createdEpic.color || `bg-${["yellow", "orange", "blue", "green", "purple", "pink", "indigo"][createdEpic.id?.charCodeAt(0) % 7 || 0]}-400`,
    };
  }, [projectId, refresh]);

  const updateEpic = useCallback(async (epicId: string, updates: Partial<Epic>): Promise<Epic> => {
    if (!projectId) {
      throw new Error("Project ID is required to update an epic");
    }
    
    const url = resolveServiceURL(`pm/projects/${projectId}/epics/${epicId}`);
    const response = await fetch(url.toString(), {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(updates),
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = `Failed to update epic: ${response.status} ${response.statusText}`;
      try {
        const errorData = JSON.parse(errorText);
        errorMessage = errorData.detail || errorMessage;
      } catch {
        if (errorText) {
          errorMessage = errorText;
        }
      }
      throw new Error(errorMessage);
    }
    
    const updatedEpic = await response.json();
    await refresh(); // Refresh the list
    return {
      ...updatedEpic,
      color: updatedEpic.color || `bg-${["yellow", "orange", "blue", "green", "purple", "pink", "indigo"][updatedEpic.id?.charCodeAt(0) % 7 || 0]}-400`,
    };
  }, [projectId, refresh]);

  const deleteEpic = useCallback(async (epicId: string): Promise<void> => {
    if (!projectId) {
      throw new Error("Project ID is required to delete an epic");
    }
    
    const url = resolveServiceURL(`pm/projects/${projectId}/epics/${epicId}`);
    const response = await fetch(url.toString(), {
      method: "DELETE",
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = `Failed to delete epic: ${response.status} ${response.statusText}`;
      try {
        const errorData = JSON.parse(errorText);
        errorMessage = errorData.detail || errorMessage;
      } catch {
        if (errorText) {
          errorMessage = errorText;
        }
      }
      throw new Error(errorMessage);
    }
    
    await refresh(); // Refresh the list
  }, [projectId, refresh]);

  return { epics, loading, error, refresh, createEpic, updateEpic, deleteEpic };
}
