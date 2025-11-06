// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useMemo, useRef, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useProjects } from "~/core/api/hooks/pm/use-projects";
import { findProjectById } from "../utils/project-utils";
import type { Project } from "../types";
import { debug } from "../utils/debug";

/**
 * Custom hook to get the active project and project ID
 * Handles both provider-prefixed and non-prefixed project IDs
 */
export function useProjectData() {
  const searchParams = useSearchParams();
  const { projects, loading: projectsLoading } = useProjects();
  
  const activeProjectId = searchParams.get('project');
  
  // Use a ref to track the previous activeProjectId from URL to detect actual project changes
  const previousActiveProjectIdRef = useRef<string | null>(null);
  
  const activeProject = useMemo<Project | null>(() => {
    if (!activeProjectId || !projects.length) return null;
    return findProjectById(projects, activeProjectId) || null;
  }, [activeProjectId, projects]);
  
  // Use activeProject ID if available, otherwise fallback to activeProjectId from URL
  // This ensures we have a project ID even if the projects list hasn't loaded yet
  // CRITICAL: Always return activeProjectId from URL if available, even if activeProject is null
  // This prevents the projectId from flipping to null during project switching
  const projectIdForData = useMemo(() => {
    const projectChanged = activeProjectId !== previousActiveProjectIdRef.current;
    
    if (projectChanged && activeProjectId) {
      debug.project('Project ID changed in URL', { from: previousActiveProjectIdRef.current, to: activeProjectId });
      previousActiveProjectIdRef.current = activeProjectId;
    }
    
    debug.project('Computing projectIdForData', { activeProjectId, activeProjectId: activeProject?.id, projectsLength: projects.length });
    
    // PRIORITY 1: Use activeProject.id if available (most reliable)
    if (activeProject) {
      debug.project('Using activeProject.id', { projectId: activeProject.id });
      return activeProject.id;
    }
    
    // PRIORITY 2: Use activeProjectId from URL (always available if project is selected)
    // This is critical - even if activeProject is null (projects list not loaded yet),
    // we should still return the activeProjectId from URL to prevent flipping to null
    if (activeProjectId) {
      debug.project('Using activeProjectId from URL', { projectId: activeProjectId });
      return activeProjectId;
    }
    
    // PRIORITY 3: No project ID available
    debug.project('No project ID available, returning null');
    previousActiveProjectIdRef.current = null;
    return null;
  }, [activeProject, activeProjectId, projects.length]);
  
  // Update previous ref when activeProjectId changes
  useEffect(() => {
    if (activeProjectId !== previousActiveProjectIdRef.current) {
      if (activeProjectId) {
        debug.project('activeProjectId changed', { from: previousActiveProjectIdRef.current, to: activeProjectId });
      } else {
        debug.project('activeProjectId cleared', { was: previousActiveProjectIdRef.current });
      }
      previousActiveProjectIdRef.current = activeProjectId;
    }
  }, [activeProjectId]);
  
  // Log when projectIdForData changes
  useEffect(() => {
    debug.project('projectIdForData changed', { projectIdForData });
  }, [projectIdForData]);
  
  return {
    activeProjectId,
    activeProject,
    projectIdForData,
    projectsLoading,
    projects,
  };
}

