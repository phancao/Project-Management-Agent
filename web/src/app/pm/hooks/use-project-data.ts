// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useMemo } from "react";
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
  
  const activeProject = useMemo<Project | null>(() => {
    if (!activeProjectId || !projects.length) return null;
    return findProjectById(projects, activeProjectId) || null;
  }, [activeProjectId, projects]);
  
  // Use activeProject ID if available, otherwise fallback to activeProjectId from URL
  // This ensures we have a project ID even if the projects list hasn't loaded yet
  const projectIdForData = useMemo(() => {
    if (activeProject) {
      return activeProject.id;
    }
    if (activeProjectId) {
      return activeProjectId;
    }
    return null;
  }, [activeProject, activeProjectId]);
  
  return {
    activeProjectId,
    activeProject,
    projectIdForData,
    projectsLoading,
    projects,
  };
}

