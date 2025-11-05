// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useEffect, useState, useCallback } from "react";

import { resolveServiceURL } from "~/core/api/resolve-service-url";

export interface Priority {
  id: string;
  name: string;
  color?: string;
  is_default?: boolean;
  position?: number;
}

const fetchPrioritiesFn = async (projectId?: string) => {
  if (!projectId) {
    return [];
  }
  
  const url = resolveServiceURL(`pm/projects/${projectId}/priorities`);
  
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
    throw new Error(`Failed to fetch priorities: ${errorDetail}`);
  }
  
  const data = await response.json();
  return data.priorities || [];
};

export function usePriorities(projectId?: string) {
  const [priorities, setPriorities] = useState<Priority[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(() => {
    if (!projectId) {
      setPriorities([]);
      setLoading(false);
      return;
    }
    
    setLoading(true);
    setError(null);
    fetchPrioritiesFn(projectId)
      .then((data) => {
        setPriorities(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err as Error);
        setLoading(false);
        // Don't set priorities to empty on error, keep previous values
      });
  }, [projectId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { priorities, loading, error, refresh };
}

