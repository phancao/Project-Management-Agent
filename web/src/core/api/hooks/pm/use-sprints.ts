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

// Cache for sprints by projectId and state
const sprintsCache = new Map<string, { data: Sprint[]; timestamp: number }>();
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

const getCacheKey = (projectId: string, state?: string) => {
  return state ? `${projectId}:${state}` : projectId;
};

export function useSprints(projectId: string, state?: string) {
  // Initialize from cache if available to avoid loading state
  const getInitialState = () => {
    if (!projectId) {
      return { sprints: [], loading: false, error: null };
    }
    const cacheKey = getCacheKey(projectId, state);
    const cached = sprintsCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
      return { sprints: cached.data, loading: false, error: null };
    }
    return { sprints: [], loading: true, error: null };
  };

  const initialState = getInitialState();
  const [sprints, setSprints] = useState<Sprint[]>(initialState.sprints);
  const [loading, setLoading] = useState(initialState.loading);
  const [error, setError] = useState<Error | null>(initialState.error);

  const refresh = useCallback((forceRefresh: boolean = false) => {
    if (!projectId) {
      setSprints([]);
      setLoading(false);
      setError(null);
      return;
    }

    const cacheKey = getCacheKey(projectId, state);

    // Check cache if not forcing refresh
    if (!forceRefresh) {
      const cached = sprintsCache.get(cacheKey);
      if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
        setSprints(cached.data);
        setLoading(false);
        setError(null);
        return;
      }
    }

    setLoading(true);
    setError(null);
    // Clear sprints immediately when project changes to avoid showing stale data
    // from previous projects
    setSprints([]);

    fetchSprints(projectId, state)
      .then((data) => {
        // Update cache
        sprintsCache.set(cacheKey, { data, timestamp: Date.now() });
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
    if (!projectId) {
      setSprints([]);
      setLoading(false);
      setError(null);
      return;
    }

    const cacheKey = getCacheKey(projectId, state);

    // Check cache first - if we already have cached data from initial state, skip
    const cached = sprintsCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
      // Only update if state doesn't match cache (e.g., projectId changed)
      if (sprints.length !== cached.data.length || sprints.length === 0) {
        setSprints(cached.data);
        setLoading(false);
        setError(null);
      }
      return;
    }

    // Only fetch if we don't have cached data
    // If sprints are already set from initial state, don't clear them
    if (sprints.length === 0) {
      setLoading(true);
    }

    // Fetch if not cached
    refresh(false);
  }, [projectId, state, refresh]); // Removed sprints from deps to avoid infinite loop

  usePMRefresh(() => refresh(true)); // Force refresh on PM refresh event

  return { sprints, loading, error, refresh, count: sprints.length };
}

