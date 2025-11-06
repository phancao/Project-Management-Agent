// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { listProviders } from "~/core/api/pm/providers";
import { usePMLoading } from "../context/pm-loading-context";
import { useProjects } from "~/core/api/hooks/pm/use-projects";
import { useStatuses } from "~/core/api/hooks/pm/use-statuses";
import { usePriorities } from "~/core/api/hooks/pm/use-priorities";
import { useEpics } from "~/core/api/hooks/pm/use-epics";
import { useSprints } from "~/core/api/hooks/pm/use-sprints";

/**
 * PMLoadingManager orchestrates the loading order:
 * 1. Load providers first
 * 2. Load filter data (projects, sprints, statuses, priorities, epics) after providers
 * 3. Tasks are loaded separately by the views that need them, after filter data is ready
 */
export function PMLoadingManager() {
  const searchParams = useSearchParams();
  const activeProjectId = searchParams.get('project');
  
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
    if (state.providers.loading && !state.providers.data) {
      console.log('[PMLoadingManager] Step 1: Loading providers...');
      listProviders()
        .then((providers) => {
          console.log('[PMLoadingManager] Providers loaded:', providers.length);
          setProvidersState({
            loading: false,
            error: null,
            data: providers,
          });
        })
        .catch((error) => {
          console.error('[PMLoadingManager] Failed to load providers:', error);
          setProvidersState({
            loading: false,
            error: error instanceof Error ? error : new Error(String(error)),
            data: null,
          });
        });
    }
  }, [state.providers.loading, state.providers.data, setProvidersState]);

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
    activeProjectId || "",
    undefined
  );

  // Sync projects state
  useEffect(() => {
    if (!state.providers.loading && state.providers.data) {
      setProjectsState({
        loading: projectsLoading,
        error: projectsError,
        data: projects,
      });
    }
  }, [projects, projectsLoading, projectsError, state.providers.loading, state.providers.data, setProjectsState]);

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

