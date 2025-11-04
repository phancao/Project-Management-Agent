// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useEffect, useState, useCallback } from "react";
import { usePMRefresh } from "./use-pm-refresh";

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  estimated_hours?: number;
  start_date?: string;
  due_date?: string;
  assigned_to?: string;
  project_name?: string;
  sprint_id?: string;
  epic_id?: string;
}

const fetchTasksFn = async (projectId?: string) => {
  let url = "http://localhost:8000/api/pm/tasks/my";
  if (projectId) {
    url = `http://localhost:8000/api/pm/projects/${projectId}/tasks`;
  }
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("Failed to fetch tasks");
  }
  return response.json();
};

export function useTasks(projectId?: string) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    fetchTasksFn(projectId)
      .then((data) => {
        setTasks(data);
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

  return { tasks, loading, error, refresh };
}

export function useMyTasks() {
  return useTasks();
}

const fetchAllTasksFn = async () => {
  const response = await fetch("http://localhost:8000/api/pm/tasks/all");
  if (!response.ok) {
    throw new Error("Failed to fetch all tasks");
  }
  return response.json();
};

export function useAllTasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    fetchAllTasksFn()
      .then((data) => {
        setTasks(data);
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

  return { tasks, loading, error, refresh };
}

