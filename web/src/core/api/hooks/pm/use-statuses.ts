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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(() => {
    if (!projectId) {
      setStatuses([]);
      setLoading(false);
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
        setLoading(false);
        // Don't set statuses to empty on error, keep previous values
      });
  }, [projectId, entityType]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { statuses, loading, error, refresh };
}

