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
  const previousProjectIdRef = useRef<string | null>(null);
  
  // Update refs when projectId changes
  useEffect(() => {
    if (projectId !== previousProjectIdRef.current) {
      const timestamp = performance.now();
      console.log(`[useTaskFiltering] 🔄 [${timestamp.toFixed(2)}ms] Project ID changed:`, previousProjectIdRef.current, "->", projectId);
      console.log(`[useTaskFiltering] 🔄 [${timestamp.toFixed(2)}ms] Clearing lastLoadedProjectIdRef (was:`, lastLoadedProjectIdRef.current, ")");
      previousProjectIdRef.current = projectId;
      // When project changes, clear the last loaded project ID immediately
      // This ensures new tasks won't be filtered out when they arrive
      lastLoadedProjectIdRef.current = null;
      console.log(`[useTaskFiltering] 🔄 [${timestamp.toFixed(2)}ms] After clearing, lastLoadedProjectIdRef:`, lastLoadedProjectIdRef.current);
    }
  }, [projectId]);
  
  // Update ref when tasks are loaded for a project
  useEffect(() => {
    const timestamp = performance.now();
    console.log(`[useTaskFiltering] 📊 [${timestamp.toFixed(2)}ms] Effect running. projectId:`, projectId, "loading:", loading, "allTasks.length:", allTasks.length, "lastLoadedProjectIdRef:", lastLoadedProjectIdRef.current);
    
    if (projectId && !loading && allTasks.length > 0) {
      // Only update if we don't have a last loaded project ID, or if it matches current project
      // This prevents overwriting when tasks are still loading for a new project
      if (lastLoadedProjectIdRef.current === null || lastLoadedProjectIdRef.current === projectId) {
        const previousProjectId = lastLoadedProjectIdRef.current;
        if (previousProjectId !== projectId) {
          console.log(`[useTaskFiltering] ✅ [${timestamp.toFixed(2)}ms] Tasks loaded for NEW project:`, projectId, "count:", allTasks.length, "previous project:", previousProjectId);
        } else {
          console.log(`[useTaskFiltering] ✅ [${timestamp.toFixed(2)}ms] Tasks confirmed for project:`, projectId, "count:", allTasks.length);
        }
        lastLoadedProjectIdRef.current = projectId;
        console.log(`[useTaskFiltering] ✅ [${timestamp.toFixed(2)}ms] Updated lastLoadedProjectIdRef to:`, projectId);
      } else {
        console.log(`[useTaskFiltering] ⚠️ [${timestamp.toFixed(2)}ms] Skipping update - lastLoadedProjectIdRef (`, lastLoadedProjectIdRef.current, ") doesn't match projectId (", projectId, ")");
      }
    } else if (projectId && loading) {
      console.log(`[useTaskFiltering] ⏳ [${timestamp.toFixed(2)}ms] Still loading tasks for project:`, projectId);
    } else if (projectId && !loading && allTasks.length === 0) {
      console.log(`[useTaskFiltering] ⚠️ [${timestamp.toFixed(2)}ms] No tasks loaded for project:`, projectId, "(loading finished but no tasks)");
    } else if (!projectId) {
      console.log(`[useTaskFiltering] 🧹 [${timestamp.toFixed(2)}ms] Clearing refs (no projectId)`);
      lastLoadedProjectIdRef.current = null;
      previousProjectIdRef.current = null;
    }
  }, [projectId, loading, allTasks.length]);
  
  const filteredTasks = useMemo(() => {
    const timestamp = performance.now();
    const startTime = timestamp;
    console.log(`[useTaskFiltering] 🔍 [${timestamp.toFixed(2)}ms] FILTERING TASKS`);
    console.log(`[useTaskFiltering]   [${timestamp.toFixed(2)}ms] - allTasks.length:`, allTasks.length);
    console.log(`[useTaskFiltering]   [${timestamp.toFixed(2)}ms] - projectId:`, projectId);
    console.log(`[useTaskFiltering]   [${timestamp.toFixed(2)}ms] - activeProject?.id:`, activeProject?.id);
    console.log(`[useTaskFiltering]   [${timestamp.toFixed(2)}ms] - lastLoadedProjectIdRef:`, lastLoadedProjectIdRef.current);
    console.log(`[useTaskFiltering]   [${timestamp.toFixed(2)}ms] - previousProjectIdRef:`, previousProjectIdRef.current);
    console.log(`[useTaskFiltering]   [${timestamp.toFixed(2)}ms] - loading:`, loading);
    
    if (!projectId) {
      console.log(`[useTaskFiltering] ❌ [${timestamp.toFixed(2)}ms] No projectId, returning empty array`);
      return [];
    }
    
    if (allTasks.length === 0) {
      console.log(`[useTaskFiltering] ❌ [${timestamp.toFixed(2)}ms] No tasks in allTasks, returning empty array`);
      return [];
    }
    
    // CRITICAL: Only filter out tasks if we're CERTAIN they're from a different project
    // We're certain if ALL of these are true:
    // 1. We have a last loaded project ID (tasks were loaded for a specific project)
    // 2. It's different from the current project ID
    // 3. We're not currently loading (tasks have finished loading)
    // 4. The last loaded project ID is not null (we've confirmed tasks were loaded for that project)
    // 
    // We DON'T filter if:
    // - Project just changed (lastLoadedProjectIdRef is null, meaning we cleared it)
    // - We're currently loading (new tasks might be arriving)
    // - lastLoadedProjectIdRef is null (project changed, cleared the ref)
    const hasConfirmedLoadedProject = lastLoadedProjectIdRef.current !== null;
    const loadedProjectDiffers = lastLoadedProjectIdRef.current !== projectId;
    const tasksFromDifferentProject = hasConfirmedLoadedProject && 
                                      loadedProjectDiffers &&
                                      !loading;
    
    const checkTime = performance.now();
    console.log(`[useTaskFiltering]   [${checkTime.toFixed(2)}ms] - hasConfirmedLoadedProject:`, hasConfirmedLoadedProject);
    console.log(`[useTaskFiltering]   [${checkTime.toFixed(2)}ms] - loadedProjectDiffers:`, loadedProjectDiffers);
    console.log(`[useTaskFiltering]   [${checkTime.toFixed(2)}ms] - tasksFromDifferentProject:`, tasksFromDifferentProject);
    
    if (tasksFromDifferentProject) {
      const filterTime = performance.now();
      console.log(`[useTaskFiltering] 🚫 [${filterTime.toFixed(2)}ms] FILTERING OUT: Tasks are from a different project`);
      console.log(`[useTaskFiltering]   [${filterTime.toFixed(2)}ms] - lastLoadedProjectId:`, lastLoadedProjectIdRef.current);
      console.log(`[useTaskFiltering]   [${filterTime.toFixed(2)}ms] - current projectId:`, projectId);
      console.log(`[useTaskFiltering]   [${filterTime.toFixed(2)}ms] - Returning empty array`);
      return [];
    }
    
    // DEFAULT: Trust backend filtering in all other cases
    // The backend already filters tasks by project, so we should trust it
    // This ensures tasks are shown immediately when switching projects
    // When project changes, lastLoadedProjectIdRef is cleared, so we trust the backend
    const endTime = performance.now();
    const duration = endTime - startTime;
    console.log(`[useTaskFiltering] ✅ [${endTime.toFixed(2)}ms] TRUSTING BACKEND: Returning all`, allTasks.length, "tasks (took", duration.toFixed(2), "ms)");
    console.log(`[useTaskFiltering]   [${endTime.toFixed(2)}ms] - Task IDs:`, allTasks.slice(0, 5).map(t => t.id).join(", "), allTasks.length > 5 ? "..." : "");
    return allTasks;
  }, [allTasks, projectId, activeProject, loading]);
  
  return {
    tasks: filteredTasks,
    lastLoadedProjectId: lastLoadedProjectIdRef.current,
  };
}

