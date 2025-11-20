// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useEffect, useState, useCallback } from "react";

import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { usePMRefresh } from "./use-pm-refresh";

export interface Project {
  id: string;
  name: string;
  description?: string;
  status: string;
}

const fetchProjects = async (): Promise<Project[]> => {
  const url = resolveServiceURL("pm/projects");
  console.log('[useProjects] Fetching projects from:', url);
  
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
      },
      // Remove timeout for now to see if request completes
      // The backend responds in ~0.75s, so 10s timeout should be fine
    });
    
    if (!response.ok) {
      const errorText = await response.text().catch(() => response.statusText);
      console.error('[useProjects] Failed to fetch projects:', response.status, errorText);
      throw new Error(`Failed to fetch projects: ${response.status} ${response.statusText}`);
    }
    const data = await response.json();
    console.log('[useProjects] Projects loaded:', data.length, data);
    return data;
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      console.error('[useProjects] Request was aborted');
      throw new Error('Request was aborted');
    }
    console.error('[useProjects] Network error fetching projects:', error);
    throw error;
  }
};

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    fetchProjects()
      .then((data) => {
        setProjects(data);
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

  return { projects, loading, error, refresh };
}

