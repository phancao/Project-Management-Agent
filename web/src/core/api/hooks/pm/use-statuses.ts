// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useEffect, useState, useCallback } from "react";

import { resolveServiceURL } from "~/core/api/resolve-service-url";

export interface Status {
  id: string;
  name: string;
  color?: string;
  is_closed?: boolean;
  is_default?: boolean;
}

const fetchStatusesFn = async (projectId?: string, entityType: string = "task") => {
  if (!projectId) {
    return [];
  }
  
  const url = resolveServiceURL(`pm/projects/${projectId}/statuses?entity_type=${entityType}`);
  
  const response = await fetch(url);
  
  if (!response.ok) {
    const errorText = await response.text();
    let errorDetail = `HTTP ${response.status}`;
    try {
      const errorData = JSON.parse(errorText);
      errorDetail = errorData.detail || errorData.message || errorDetail;
    } catch {
      errorDetail = response.statusText || errorDetail;
    }
    throw new Error(`Failed to fetch statuses: ${errorDetail}`);
  }
  
  const data = await response.json();
  return data.statuses || [];
};

export function useStatuses(projectId?: string, entityType: string = "task") {
  const [statuses, setStatuses] = useState<Status[]>([]);
  const [loading, setLoading] = useState(true); // Start as true to show loading state initially
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(() => {
    if (!projectId) {
      setStatuses([]);
      setLoading(false);
      setError(null);
      return;
    }
    
    setLoading(true);
    setError(null);
    fetchStatusesFn(projectId, entityType)
      .then((data) => {
        setStatuses(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err as Error);
        setStatuses([]); // Clear statuses on error to avoid showing stale data
        setLoading(false);
      });
  }, [projectId, entityType]);

  useEffect(() => {
    // Clear statuses immediately when projectId changes to avoid showing stale data
    setStatuses([]);
    setError(null);
    
    // If no project ID, set loading to false and return empty
    if (!projectId) {
      setLoading(false);
      return;
    }
    
    setLoading(true);
    
    // Use a flag to track if this effect is still relevant (projectId hasn't changed)
    let isCurrent = true;
    
    // Fetch new data
    fetchStatusesFn(projectId, entityType)
      .then((data) => {
        // Only update state if this effect is still relevant (projectId hasn't changed)
        if (isCurrent) {
          setStatuses(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        // Only update state if this effect is still relevant (projectId hasn't changed)
        if (isCurrent) {
          setError(err as Error);
          setStatuses([]);
          setLoading(false);
        }
      });
    
    // Cleanup: mark this effect as stale if projectId changes
    return () => {
      isCurrent = false;
    };
  }, [projectId, entityType]);

  return { statuses, loading, error, refresh };
}

