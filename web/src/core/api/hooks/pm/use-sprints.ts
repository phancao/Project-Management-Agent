// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useEffect, useState, useCallback } from "react";

import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { usePMRefresh } from "./use-pm-refresh";

export interface Sprint {
  id: string;
  name: string;
  start_date?: string;
  end_date?: string;
  status: string;
}

const fetchSprints = async (projectId: string, state?: string): Promise<Sprint[]> => {
  const url = new URL(resolveServiceURL(`pm/projects/${projectId}/sprints`));
  if (state) {
    url.searchParams.set('state', state);
  }
  const response = await fetch(url.toString());
  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage = `Failed to fetch sprints: ${response.status} ${response.statusText}`;
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
  return response.json();
};

export function useSprints(projectId: string, state?: string) {
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(() => {
    if (!projectId) {
      setSprints([]);
      setLoading(false);
      setError(null);
      return;
    }
    
    setLoading(true);
    setError(null);
    // Clear sprints immediately when project changes to avoid showing stale data
    // from previous projects
    setSprints([]);
    
    fetchSprints(projectId, state)
      .then((data) => {
        setSprints(data);
        setLoading(false);
        setError(null);
      })
      .catch((err) => {
        setError(err as Error);
        setSprints([]); // Clear sprints on error to avoid showing stale data
        setLoading(false);
      });
  }, [projectId, state]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  usePMRefresh(refresh);

  return { sprints, loading, error, refresh };
}

