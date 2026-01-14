// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useEffect, useState, useCallback } from "react";

import { resolvePMServiceURL } from "~/core/api/resolve-pm-service-url";
import { usePMRefresh } from "./use-pm-refresh";

export interface Project {
  id: string;
  name: string;
  description?: string;
  status: string;
}

const fetchProjects = async (): Promise<Project[]> => {
  const pageSize = 100;

  const fetchPage = async (page: number) => {
    let url = resolvePMServiceURL("projects");
    const params = new URLSearchParams();
    params.append("pageSize", pageSize.toString());
    params.append("page", page.toString());

    // Remove default timeouts by using AbortController with long timeout if needed, 
    // but standard fetch should be fine.
    const response = await fetch(`${url}?${params.toString()}`, {
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => response.statusText);
      console.error('[useProjects] Failed to fetch projects:', response.status, errorText);
      throw new Error(`Failed to fetch projects: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  };

  try {
    // 1. Fetch first page
    const firstPageData = await fetchPage(1);

    // Handle both array response (if legacy) and paginated response
    let allItems: Project[] = [];
    let totalItems = 0;

    if (Array.isArray(firstPageData)) {
      // Legacy or non-paginated endpoint
      return firstPageData;
    } else {
      // Paginated endpoint { items: [], total: ... }
      allItems = firstPageData.items || [];
      totalItems = firstPageData.total || 0;
    }

    // 2. Fetch remaining pages if needed
    if (totalItems > allItems.length) {
      const totalPages = Math.ceil(totalItems / pageSize);
      const pagePromises = [];

      for (let p = 2; p <= totalPages; p++) {
        pagePromises.push(fetchPage(p));
      }

      const results = await Promise.all(pagePromises);
      results.forEach(data => {
        if (data.items) {
          allItems = allItems.concat(data.items);
        }
      });
    }

    return allItems;

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

  const refresh = useCallback((isBackground: boolean = false) => {
    if (!isBackground) {
      setLoading(true);
    }
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
    refresh(false);
  }, [refresh]);

  usePMRefresh(() => refresh(true));

  return { projects, loading, error, refresh };
}

