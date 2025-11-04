// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useEffect, useState, useCallback } from "react";
import { usePMRefresh } from "./use-pm-refresh";

export interface Sprint {
  id: string;
  name: string;
  start_date?: string;
  end_date?: string;
  status: string;
}

const fetchSprints = async (projectId: string): Promise<Sprint[]> => {
  const response = await fetch(`http://localhost:8000/api/pm/projects/${projectId}/sprints`);
  if (!response.ok) {
    throw new Error("Failed to fetch sprints");
  }
  return response.json();
};

export function useSprints(projectId: string) {
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(() => {
    if (!projectId) {
      setLoading(false);
      return;
    }
    
    setLoading(true);
    fetchSprints(projectId)
      .then((data) => {
        setSprints(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err as Error);
        setLoading(false);
      });
  }, [projectId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  usePMRefresh(refresh);

  return { sprints, loading, error, refresh };
}

