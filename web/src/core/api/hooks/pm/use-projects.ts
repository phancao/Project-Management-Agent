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
  const response = await fetch(resolveServiceURL("pm/projects"));
  if (!response.ok) {
    throw new Error("Failed to fetch projects");
  }
  return response.json();
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

