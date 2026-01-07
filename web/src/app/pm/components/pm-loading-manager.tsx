// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { listProviders } from "~/core/api/pm/providers";
import { usePMLoading } from "../context/pm-loading-context";
import { useLoading } from "~/core/contexts/loading-context";
import { useProjects } from "~/core/api/hooks/pm/use-projects";
import { useStatuses } from "~/core/api/hooks/pm/use-statuses";
import { usePriorities } from "~/core/api/hooks/pm/use-priorities";
import { useEpics } from "~/core/api/hooks/pm/use-epics";
import { useSprints } from "~/core/api/hooks/pm/use-sprints";
import { debug } from "../utils/debug";

/**
 * PMLoadingManager orchestrates the loading order:
 * 1. Load providers first
 * 2. Load filter data (projects, sprints, statuses, priorities, epics) after providers
 * 3. Tasks are loaded separately by the views that need them, after filter data is ready
 */
export function PMLoadingManager() {
  const searchParams = useSearchParams();
  const activeProjectId = searchParams.get('project');
  const globalLoading = useLoading();

  const {
    state,
    setProvidersState,
    setProjectsState,
    setSprintsState,
    setStatusesState,
    setPrioritiesState,
    setEpicsState,
  } = usePMLoading();

  // Step 1: Load providers
  useEffect(() => {
    // Only load if we're in loading state and don't have data yet
    if (state.providers.loading && !state.providers.data && !state.providers.error) {
      debug.state('Step 1: Loading providers...');
      globalLoading.setLoading(true, "Loading providers...");

      // Add timeout to prevent infinite loading
      const timeoutId = setTimeout(() => {
        debug.error('Provider loading timeout - resetting loading state');
        const timeoutError = new Error('Request timeout: Failed to load providers within 30 seconds. Please check if the backend server is running.');
        setProvidersState({
          loading: false,
          error: timeoutError,
          data: null,
        });
        globalLoading.setLoading(false);
        toast.error("Provider loading timeout", {
          description: timeoutError.message,
          duration: 10000,
        });
      }, 30000); // 30 second timeout

      // Include disabled providers so isActiveMap can gate requests to disabled providers
      listProviders(true)
        .then((providers) => {
          clearTimeout(timeoutId);
          debug.state('Providers loaded', { count: providers.length });
          // Filter out providers without id and ensure id is always a string
          const validProviders = providers.filter((p): p is typeof p & { id: string } => !!p.id);
          setProvidersState({
            loading: false,
            error: null,
            data: validProviders,
          });
          // Don't turn off global loading here, wait for projects
        })
        .catch((error) => {
          clearTimeout(timeoutId);
          debug.error('Failed to load providers', error);
          const errorMessage = error instanceof Error ? error.message : String(error);
          const errorObj = error instanceof Error ? error : new Error(String(error));

          setProvidersState({
            loading: false,
            error: errorObj,
            data: null,
          });
          globalLoading.setLoading(false);

          // Show error toast to user
          toast.error("Failed to load providers", {
            description: errorMessage,
            duration: 10000, // Show for 10 seconds
          });
        });

      return () => {
        clearTimeout(timeoutId);
      };
    }
  }, [state.providers.loading, state.providers.data, state.providers.error, setProvidersState, globalLoading]);

  // Step 2: Load filter data after providers are loaded
  // Use the existing hooks but sync their state with our loading context
  const { projects, loading: projectsLoading, error: projectsError } = useProjects();
  const { statuses, loading: statusesLoading, error: statusesError } = useStatuses(
    activeProjectId ?? undefined,
    "task"
  );
  const { priorities, loading: prioritiesLoading, error: prioritiesError } = usePriorities(
    activeProjectId ?? undefined
  );
  const { epics, loading: epicsLoading, error: epicsError } = useEpics(
    activeProjectId ?? undefined
  );
  const { sprints, loading: sprintsLoading, error: sprintsError } = useSprints(
    activeProjectId ?? "",
    undefined
  );

  // Sync projects state
  useEffect(() => {
    if (!state.providers.loading && state.providers.data) {
      if (projectsLoading) {
        // If still loading projects, update message but keep loading true
        // Only if global loading was already true (initial load)
        if (globalLoading.isLoading) {
          globalLoading.setLoading(true, "Loading projects...");
        }
      } else {
        // Projects loaded, if we were global loading, stop it
        if (globalLoading.isLoading) {
          globalLoading.setLoading(false);
        }
      }

      setProjectsState({
        loading: projectsLoading,
        error: projectsError,
        data: projects,
      });
    } else if (state.providers.loading) {
    } else if (!state.providers.data) {
    }
  }, [projects, projectsLoading, projectsError, state.providers.loading, state.providers.data, state.providers.error, setProjectsState, globalLoading]);

  // Sync sprints state (only load if project is selected)
  useEffect(() => {
    if (!state.providers.loading && state.providers.data && activeProjectId) {
      setSprintsState({
        loading: sprintsLoading,
        error: sprintsError,
        data: sprints,
      });
    } else if (!activeProjectId) {
      setSprintsState({
        loading: false,
        error: null,
        data: [],
      });
    }
  }, [sprints, sprintsLoading, sprintsError, activeProjectId, state.providers.loading, state.providers.data, setSprintsState]);

  // Sync statuses state (only load if project is selected)
  useEffect(() => {
    if (!state.providers.loading && state.providers.data && activeProjectId) {
      setStatusesState({
        loading: statusesLoading,
        error: statusesError,
        data: statuses,
      });
    } else if (!activeProjectId) {
      setStatusesState({
        loading: false,
        error: null,
        data: [],
      });
    }
  }, [statuses, statusesLoading, statusesError, activeProjectId, state.providers.loading, state.providers.data, setStatusesState]);

  // Sync priorities state (only load if project is selected)
  useEffect(() => {
    if (!state.providers.loading && state.providers.data && activeProjectId) {
      setPrioritiesState({
        loading: prioritiesLoading,
        error: prioritiesError,
        data: priorities,
      });
    } else if (!activeProjectId) {
      setPrioritiesState({
        loading: false,
        error: null,
        data: [],
      });
    }
  }, [priorities, prioritiesLoading, prioritiesError, activeProjectId, state.providers.loading, state.providers.data, setPrioritiesState]);

  // Sync epics state (only load if project is selected)
  useEffect(() => {
    if (!state.providers.loading && state.providers.data && activeProjectId) {
      setEpicsState({
        loading: epicsLoading,
        error: epicsError,
        data: epics,
      });
    } else if (!activeProjectId) {
      setEpicsState({
        loading: false,
        error: null,
        data: [],
      });
    }
  }, [epics, epicsLoading, epicsError, activeProjectId, state.providers.loading, state.providers.data, setEpicsState]);

  // This component doesn't render anything, it just manages loading state
  return null;
}

