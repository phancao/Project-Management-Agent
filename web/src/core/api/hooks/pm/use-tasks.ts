// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useEffect, useState } from "react";

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  estimated_hours?: number;
  assigned_to?: string;
  project_name?: string;
}

const fetchTasks = async (projectId?: string, assigneeId?: string): Promise<Task[]> => {
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

  useEffect(() => {
    fetchTasks(projectId)
      .then((data) => {
        setTasks(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err as Error);
        setLoading(false);
      });
  }, [projectId]);

  return { tasks, loading, error };
}

export function useMyTasks() {
  return useTasks();
}

export function useAllTasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchAllTasks = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/pm/tasks/all");
        if (!response.ok) {
          throw new Error("Failed to fetch all tasks");
        }
        const data = await response.json();
        setTasks(data);
        setLoading(false);
      } catch (err) {
        setError(err as Error);
        setLoading(false);
      }
    };

    fetchAllTasks();
  }, []);

  return { tasks, loading, error };
}

