// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";

import { resolveServiceURL } from "~/core/api/resolve-service-url";

export interface User {
  id: string;
  name: string;
  email?: string;
  username?: string;
  avatar_url?: string;
}

const fetchUsersFn = async (projectId?: string) => {
  if (!projectId) {
    return [];
  }

  const url = resolveServiceURL(`pm/projects/${projectId}/users`);

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
    throw new Error(`Failed to fetch users: ${errorDetail}`);
  }

  return await response.json();
};

export function useUsers(projectId?: string) {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(() => {
    if (!projectId) {
      setUsers([]);
      setLoading(false);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    fetchUsersFn(projectId)
      .then((data) => {
        setUsers(data);
        setLoading(false);
      })
      .catch((err) => {
        // Log as warning instead of error - this is often expected (e.g., missing username for JIRA)
        const errorMessage = err instanceof Error ? err.message : String(err);

        // Check if it's a permission/authentication issue (403, 401, Forbidden, Unauthorized)
        const isPermissionError =
          errorMessage.includes("403") ||
          errorMessage.includes("Forbidden") ||
          errorMessage.includes("401") ||
          errorMessage.includes("Unauthorized") ||
          errorMessage.includes("JIRA requires email") ||
          errorMessage.includes("username");

        if (isPermissionError) {
          // This is a configuration/permission issue - show a warning toast
          console.warn(`[useUsers] Cannot fetch users for project ${projectId}: ${errorMessage}. Users list will be empty.`);
          toast.warning("Cannot load users", {
            description: "Your API key doesn't have permission to access the users endpoint, or the provider requires additional configuration.",
          });
        } else {
          // This is an unexpected error - show an error toast
          console.error(`[useUsers] Failed to fetch users for project ${projectId}:`, err);
          toast.error("Failed to load users", {
            description: errorMessage,
          });
        }
        setError(err as Error);
        setUsers([]);
        setLoading(false);
      });
  }, [projectId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { users, loading, error, refresh, count: users.length };
}

