// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useMemo, useRef, useEffect } from "react";
import type { Task, Project } from "../types";
import { extractProjectKey } from "../utils/project-utils";

interface UseTaskFilteringOptions {
  allTasks: Task[];
  projectId: string | null;
  activeProject: Project | null;
  loading: boolean;
}

/**
 * Custom hook for filtering tasks by project
 * Handles quick project switching by trusting backend filtering
 */
export function useTaskFiltering({
  allTasks,
  projectId,
  activeProject,
  loading,
}: UseTaskFilteringOptions) {
  // Track the last project ID that tasks were loaded for
  const lastLoadedProjectIdRef = useRef<string | null>(null);
  
  // Update ref when tasks are loaded for a new project
  useEffect(() => {
    if (projectId && !loading && allTasks.length > 0) {
      const previousProjectId = lastLoadedProjectIdRef.current;
      if (previousProjectId !== projectId) {
        console.log("[useTaskFiltering] Tasks loaded for NEW project:", projectId, "count:", allTasks.length, "previous project:", previousProjectId);
      }
      lastLoadedProjectIdRef.current = projectId;
    } else if (projectId && loading) {
      // Loading started - don't clear the ref yet, keep it until new tasks arrive
      if (lastLoadedProjectIdRef.current !== projectId) {
        console.log("[useTaskFiltering] Starting to load tasks for NEW project:", projectId, "previous project:", lastLoadedProjectIdRef.current);
      }
    } else if (!projectId) {
      lastLoadedProjectIdRef.current = null;
    }
  }, [projectId, loading, allTasks.length]);
  
  const filteredTasks = useMemo(() => {
    console.log("[useTaskFiltering] Filtering tasks. allTasks:", allTasks.length, "projectId:", projectId, "activeProject:", activeProject?.id, "lastLoadedProjectId:", lastLoadedProjectIdRef.current, "loading:", loading);
    
    if (!projectId) {
      console.log("[useTaskFiltering] No projectId, returning empty array");
      return [];
    }
    
    if (allTasks.length === 0) {
      return [];
    }
    
    // CRITICAL: Only filter out tasks if we're CERTAIN they're from a different project
    // This prevents filtering out valid tasks during quick project switching
    const tasksFromDifferentProject = lastLoadedProjectIdRef.current !== null && 
                                      lastLoadedProjectIdRef.current !== projectId &&
                                      !loading; // Only check if not currently loading (to avoid race conditions)
    
    if (tasksFromDifferentProject) {
      console.log("[useTaskFiltering] CERTAIN: Tasks are from a different project, returning empty array. lastLoadedProjectId:", lastLoadedProjectIdRef.current, "projectId:", projectId);
      return [];
    }
    
    // DEFAULT: Trust backend filtering in all other cases
    // The backend already filters tasks by project, so we should trust it
    // This ensures tasks are shown immediately when switching projects
    console.log("[useTaskFiltering] Trusting backend filtering. Returning all", allTasks.length, "tasks.");
    return allTasks;
  }, [allTasks, projectId, activeProject, loading]);
  
  return {
    tasks: filteredTasks,
    lastLoadedProjectId: lastLoadedProjectIdRef.current,
  };
}

