// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useEffect, useState } from "react";

export interface Project {
  id: string;
  name: string;
  description?: string;
  status: string;
}

const fetchProjects = async (): Promise<Project[]> => {
  const response = await fetch("http://localhost:8000/api/pm/projects");
  if (!response.ok) {
    throw new Error("Failed to fetch projects");
  }
  return response.json();
};

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
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

  return { projects, loading, error };
}

