// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useMemo, useRef, useEffect } from "react";
import type { Task, Project } from "../types";
import { extractProjectKey } from "../utils/project-utils";
import { debug } from "../utils/debug";

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
      debug.filter('Project ID changed', { from: previousProjectIdRef.current, to: projectId });
      debug.filter('Clearing lastLoadedProjectIdRef', { was: lastLoadedProjectIdRef.current });
      previousProjectIdRef.current = projectId;
      // When project changes, clear the last loaded project ID immediately
      // This ensures new tasks won't be filtered out when they arrive
      lastLoadedProjectIdRef.current = null;
      debug.filter('After clearing, lastLoadedProjectIdRef', { value: lastLoadedProjectIdRef.current });
    }
  }, [projectId]);
  
  // Update ref when tasks are loaded for a project
  useEffect(() => {
    debug.filter('Effect running', { projectId, loading, allTasksLength: allTasks.length, lastLoadedProjectIdRef: lastLoadedProjectIdRef.current });
    
    if (projectId && !loading && allTasks.length > 0) {
      // Only update if we don't have a last loaded project ID, or if it matches current project
      // This prevents overwriting when tasks are still loading for a new project
      if (lastLoadedProjectIdRef.current === null || lastLoadedProjectIdRef.current === projectId) {
        const previousProjectId = lastLoadedProjectIdRef.current;
        if (previousProjectId !== projectId) {
          debug.filter('Tasks loaded for NEW project', { projectId, count: allTasks.length, previousProject: previousProjectId });
        } else {
          debug.filter('Tasks confirmed for project', { projectId, count: allTasks.length });
        }
        lastLoadedProjectIdRef.current = projectId;
        debug.filter('Updated lastLoadedProjectIdRef', { projectId });
      } else {
        debug.filter('Skipping update - lastLoadedProjectIdRef doesn\'t match projectId', { lastLoadedProjectId: lastLoadedProjectIdRef.current, projectId });
      }
    } else if (projectId && loading) {
      debug.filter('Still loading tasks for project', { projectId });
    } else if (projectId && !loading && allTasks.length === 0) {
      debug.filter('No tasks loaded for project (loading finished but no tasks)', { projectId });
    } else if (!projectId) {
      debug.filter('Clearing refs (no projectId)');
      lastLoadedProjectIdRef.current = null;
      previousProjectIdRef.current = null;
    }
  }, [projectId, loading, allTasks.length]);
  
  const filteredTasks = useMemo(() => {
    debug.filter('FILTERING TASKS', {
      allTasksLength: allTasks.length,
      projectId,
      activeProjectId: activeProject?.id,
      lastLoadedProjectIdRef: lastLoadedProjectIdRef.current,
      previousProjectIdRef: previousProjectIdRef.current,
      loading,
    });
    
    if (!projectId) {
      debug.filter('No projectId, returning empty array');
      return [];
    }
    
    if (allTasks.length === 0) {
      debug.filter('No tasks in allTasks, returning empty array');
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
    
    debug.filter('Filter check', {
      hasConfirmedLoadedProject,
      loadedProjectDiffers,
      tasksFromDifferentProject,
    });
    
    if (tasksFromDifferentProject) {
      debug.filter('FILTERING OUT: Tasks are from a different project', {
        lastLoadedProjectId: lastLoadedProjectIdRef.current,
        currentProjectId: projectId,
      });
      return [];
    }
    
    // DEFAULT: Trust backend filtering in all other cases
    // The backend already filters tasks by project, so we should trust it
    // This ensures tasks are shown immediately when switching projects
    // When project changes, lastLoadedProjectIdRef is cleared, so we trust the backend
    debug.filter('TRUSTING BACKEND: Returning all tasks', {
      count: allTasks.length,
      taskIds: allTasks.slice(0, 5).map(t => t.id),
    });
    return allTasks;
  }, [allTasks, projectId, activeProject, loading]);
  
  return {
    tasks: filteredTasks,
    lastLoadedProjectId: lastLoadedProjectIdRef.current,
  };
}

