// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useMemo, useRef, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useProjects } from "~/core/api/hooks/pm/use-projects";
import { findProjectById } from "../utils/project-utils";
import type { Project } from "../types";

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
    const timestamp = performance.now();
    const projectChanged = activeProjectId !== previousActiveProjectIdRef.current;
    
    if (projectChanged && activeProjectId) {
      console.log(`[useProjectData] 🔄 [${timestamp.toFixed(2)}ms] Project ID changed in URL:`, previousActiveProjectIdRef.current, "->", activeProjectId);
      previousActiveProjectIdRef.current = activeProjectId;
    }
    
    console.log(`[useProjectData] 🔍 [${timestamp.toFixed(2)}ms] Computing projectIdForData. activeProjectId:`, activeProjectId, "activeProject:", activeProject?.id, "projects.length:", projects.length);
    
    // PRIORITY 1: Use activeProject.id if available (most reliable)
    if (activeProject) {
      console.log(`[useProjectData] ✅ [${timestamp.toFixed(2)}ms] Using activeProject.id:`, activeProject.id);
      return activeProject.id;
    }
    
    // PRIORITY 2: Use activeProjectId from URL (always available if project is selected)
    // This is critical - even if activeProject is null (projects list not loaded yet),
    // we should still return the activeProjectId from URL to prevent flipping to null
    if (activeProjectId) {
      console.log(`[useProjectData] ✅ [${timestamp.toFixed(2)}ms] Using activeProjectId from URL:`, activeProjectId);
      return activeProjectId;
    }
    
    // PRIORITY 3: No project ID available
    console.log(`[useProjectData] ⚠️ [${timestamp.toFixed(2)}ms] No project ID available, returning null`);
    previousActiveProjectIdRef.current = null;
    return null;
  }, [activeProject, activeProjectId, projects.length]);
  
  // Update previous ref when activeProjectId changes
  useEffect(() => {
    if (activeProjectId !== previousActiveProjectIdRef.current) {
      const timestamp = performance.now();
      if (activeProjectId) {
        console.log(`[useProjectData] 🔄 [${timestamp.toFixed(2)}ms] activeProjectId changed:`, previousActiveProjectIdRef.current, "->", activeProjectId);
      } else {
        console.log(`[useProjectData] 🧹 [${timestamp.toFixed(2)}ms] activeProjectId cleared (was:`, previousActiveProjectIdRef.current, ")");
      }
      previousActiveProjectIdRef.current = activeProjectId;
    }
  }, [activeProjectId]);
  
  // Log when projectIdForData changes
  useEffect(() => {
    const timestamp = performance.now();
    console.log(`[useProjectData] 📊 [${timestamp.toFixed(2)}ms] projectIdForData changed to:`, projectIdForData);
  }, [projectIdForData]);
  
  return {
    activeProjectId,
    activeProject,
    projectIdForData,
    projectsLoading,
    projects,
  };
}

