// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useMemo, useRef, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { useProjects } from "~/core/api/hooks/pm/use-projects";
import { useProviders } from "~/core/api/hooks/pm/use-providers";
import { findProjectById } from "../utils/project-utils";
import type { Project } from "../types";
import { debug } from "../utils/debug";

/**
 * Custom hook to get the active project and project ID
 * Handles both provider-prefixed and non-prefixed project IDs
 * ALSO validates that the provider is active before allowing data fetching
 */
export function useProjectData() {
  const searchParams = useSearchParams();
  const { projects, loading: projectsLoading } = useProjects();
  const { mappings, loading: providersLoading } = useProviders();

  const activeProjectId = searchParams.get('project');
  const [providerDisabled, setProviderDisabled] = useState(false);
  const disabledToastShownRef = useRef(false);

  // Use a ref to track the previous activeProjectId from URL to detect actual project changes
  const previousActiveProjectIdRef = useRef<string | null>(null);

  const activeProject = useMemo<Project | null>(() => {
    if (!activeProjectId || !projects.length) return null;
    return findProjectById(projects, activeProjectId) || null;
  }, [activeProjectId, projects]);

  // Check if the provider for the current project is active
  const isProviderActive = useMemo(() => {
    if (!activeProjectId) return true; // No project selected, nothing to validate
    if (providersLoading) return true; // Still loading, assume active

    // Extract provider ID from project ID (format: "providerId:projectKey")
    const parts = activeProjectId.split(':');
    if (parts.length < 2) return true; // Invalid format, let backend handle

    const providerId = parts[0];
    const isActive = mappings.isActiveMap.get(providerId);

    // If we have info about this provider, return its status
    // Otherwise, assume active (let backend validate)
    return isActive !== false;
  }, [activeProjectId, mappings.isActiveMap, providersLoading]);

  // Show toast when provider is disabled (only once per project)
  useEffect(() => {
    if (!isProviderActive && activeProjectId && !disabledToastShownRef.current) {
      disabledToastShownRef.current = true;
      setProviderDisabled(true);

      toast.error("Provider Disabled", {
        id: "provider-disabled", // Deduplicate
        description: "The provider for this project is disabled. Please enable it or select a different project.",
        duration: 15000,
        action: {
          label: "Select Project",
          onClick: () => {
            const url = new URL(window.location.href);
            url.searchParams.delete("project");
            window.history.replaceState({}, "", url.toString());
            window.location.reload();
          },
        },
      });
    } else if (isProviderActive) {
      disabledToastShownRef.current = false;
      setProviderDisabled(false);
    }
  }, [isProviderActive, activeProjectId]);

  // Reset toast flag when project changes
  useEffect(() => {
    if (activeProjectId !== previousActiveProjectIdRef.current) {
      disabledToastShownRef.current = false;
      previousActiveProjectIdRef.current = activeProjectId;
    }
  }, [activeProjectId]);

  // Compute projectIdForData - returns null if provider is disabled OR providers still loading
  const projectIdForData = useMemo(() => {
    // Wait for providers to load before making any data requests
    // This prevents hooks from firing before we can validate the provider
    if (providersLoading) {
      debug.project('Providers still loading, returning null for projectIdForData');
      return null;
    }

    // If provider is disabled, return null to prevent data fetching
    if (!isProviderActive) {
      debug.project('Provider disabled, returning null for projectIdForData');
      return null;
    }

    debug.project('Computing projectIdForData', { activeProjectId, activeProjectIdFromProject: activeProject?.id, projectsLength: projects.length });

    // PRIORITY 1: Use activeProject.id if available (most reliable)
    if (activeProject) {
      debug.project('Using activeProject.id', { projectId: activeProject.id });
      return activeProject.id;
    }

    // PRIORITY 2: Use activeProjectId from URL (always available if project is selected)
    if (activeProjectId) {
      debug.project('Using activeProjectId from URL', { projectId: activeProjectId });
      return activeProjectId;
    }

    // PRIORITY 3: No project ID available
    debug.project('No project ID available, returning null');
    return null;
  }, [activeProject, activeProjectId, projects.length, isProviderActive, providersLoading]);

  // Log when projectIdForData changes
  useEffect(() => {
    debug.project('projectIdForData changed', { projectIdForData });
  }, [projectIdForData]);

  return {
    activeProjectId,
    activeProject,
    projectIdForData,
    projectsLoading,
    providersLoading,
    providerDisabled, // New: indicates provider is disabled
    projects,
  };
}

