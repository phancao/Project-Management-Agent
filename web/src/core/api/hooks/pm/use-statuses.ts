// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useEffect, useState, useCallback } from "react";

import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { usePMRefresh } from "./use-pm-refresh";

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

// Cache for statuses by projectId and entityType
const statusesCache = new Map<string, { data: Status[]; timestamp: number }>();
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

const getCacheKey = (projectId: string, entityType: string) => {
  return `${projectId}:${entityType}`;
};

export function useStatuses(projectId?: string, entityType: string = "task") {
  // Initialize from cache if available to avoid loading state
  const getInitialState = () => {
    if (!projectId) {
      return { statuses: [], loading: false, error: null };
    }
    const cacheKey = getCacheKey(projectId, entityType);
    const cached = statusesCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
      return { statuses: cached.data, loading: false, error: null };
    }
    return { statuses: [], loading: true, error: null };
  };
  
  const initialState = getInitialState();
  const [statuses, setStatuses] = useState<Status[]>(initialState.statuses);
  const [loading, setLoading] = useState(initialState.loading);
  const [error, setError] = useState<Error | null>(initialState.error);
  
  // Update state if projectId or entityType changes and we have cached data
  useEffect(() => {
    if (projectId) {
      const cacheKey = getCacheKey(projectId, entityType);
      const cached = statusesCache.get(cacheKey);
      if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
        if (statuses.length === 0 || loading) {
          setStatuses(cached.data);
          setLoading(false);
          setError(null);
        }
      }
    }
  }, [projectId, entityType, statuses.length, loading]);

  const refresh = useCallback((forceRefresh: boolean = false) => {
    if (!projectId) {
      setStatuses([]);
      setLoading(false);
      setError(null);
      return;
    }
    
    const cacheKey = getCacheKey(projectId, entityType);
    
    // Check cache if not forcing refresh
    if (!forceRefresh) {
      const cached = statusesCache.get(cacheKey);
      if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
        setStatuses(cached.data);
        setLoading(false);
        setError(null);
        return;
      }
    }
    
    setLoading(true);
    setError(null);
    fetchStatusesFn(projectId, entityType)
      .then((data) => {
        // Update cache
        statusesCache.set(cacheKey, { data, timestamp: Date.now() });
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
    // If no project ID, set loading to false and return empty
    if (!projectId) {
      setStatuses([]);
      setError(null);
      setLoading(false);
      return;
    }
    
    const cacheKey = getCacheKey(projectId, entityType);
    
    // Check cache first - if we already have cached data from initial state, skip
    const cached = statusesCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
      // Only update if state doesn't match cache (e.g., projectId changed)
      if (statuses.length !== cached.data.length || statuses.length === 0) {
        setStatuses(cached.data);
        setLoading(false);
        setError(null);
      } else if (loading) {
        // If we have the same statuses but loading is still true, set it to false
        setLoading(false);
        setError(null);
      }
      return;
    }
    
    // Only fetch if we don't have cached data
    // If statuses are already set from initial state, don't clear them
    if (statuses.length === 0) {
      setLoading(true);
    }
    
    // Use a flag to track if this effect is still relevant (projectId hasn't changed)
    let isCurrent = true;
    
    // Fetch new data
    fetchStatusesFn(projectId, entityType)
      .then((data) => {
        // Only update state if this effect is still relevant (projectId hasn't changed)
        if (isCurrent) {
          // Update cache
          statusesCache.set(cacheKey, { data, timestamp: Date.now() });
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
  }, [projectId, entityType]); // Removed statuses and loading from deps to avoid infinite loop

  // Listen for PM refresh events
  usePMRefresh(() => refresh(true)); // Force refresh on PM refresh event

  return { statuses, loading, error, refresh };
}

