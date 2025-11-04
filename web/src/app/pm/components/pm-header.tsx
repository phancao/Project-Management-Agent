// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useMemo, useEffect, useState } from "react";
import { Suspense } from "react";

import { Button } from "~/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { useProjects } from "~/core/api/hooks/pm/use-projects";
import { listProviders } from "~/core/api/pm/providers";

import { ThemeToggle } from "../../../components/deer-flow/theme-toggle";
import { Tooltip } from "../../../components/deer-flow/tooltip";
import { SettingsDialog } from "../../settings/dialogs/settings-dialog";

const ProviderManagementDialog = dynamic(() => import("../chat/components/provider-management-dialog").then(mod => ({ default: mod.ProviderManagementDialog })), {
  ssr: false,
});

interface PMHeaderProps {
  selectedProjectId?: string | null;
  onProjectChange?: (projectId: string) => void;
}

export function PMHeader({ selectedProjectId: propSelectedProjectId, onProjectChange }: PMHeaderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { projects, loading: projectsLoading } = useProjects();
  const [providers, setProviders] = useState<Array<{ id: string; provider_type: string }>>([]);
  
  const selectedProjectId = propSelectedProjectId || new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '').get('project');

  // Fetch providers to map project IDs to provider types
  useEffect(() => {
    listProviders().then((providers) => {
      const mapped = providers.map(p => ({
        id: p.id || '',
        provider_type: p.provider_type || ''
      })).filter(p => p.id && p.provider_type);
      setProviders(mapped);
    }).catch(console.error);
  }, []);

  // Create mapping from provider_id to provider_type
  const providerTypeMap = useMemo(() => {
    const map = new Map<string, string>();
    providers.forEach(p => {
      if (p.id && p.provider_type) {
        map.set(p.id, p.provider_type);
      }
    });
    return map;
  }, [providers]);

  // Helper to get provider type from project ID
  const getProviderType = (projectId: string | undefined): string | null => {
    if (!projectId) return null;
    const parts = projectId.split(":");
    if (parts.length >= 2) {
      const providerId: string | undefined = parts[0];
      if (!providerId) return null;
      return providerTypeMap.get(providerId) || null;
    }
    return null;
  };

  // Helper to get provider color/badge
  const getProviderBadge = (providerType: string | null) => {
    if (!providerType) return null;
    const config = {
      jira: { label: "JIRA", color: "bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200" },
      openproject: { label: "OP", color: "bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200" },
      clickup: { label: "CU", color: "bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200" },
    };
    const badge = config[providerType as keyof typeof config] || { 
      label: providerType.toUpperCase().slice(0, 2), 
      color: "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200" 
    };
    return (
      <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${badge.color}`}>
        {badge.label}
      </span>
    );
  };

  // Determine selected project: use prop or URL param, or first project
  const selectedProject = useMemo(() => {
    if (selectedProjectId && projects.some(p => p.id === selectedProjectId)) {
      return selectedProjectId;
    }
    if (projects.length > 0 && projects[0]?.id) {
      return projects[0].id;
    }
    return "";
  }, [selectedProjectId, projects]);

  const isOverview = pathname?.includes('/overview') ?? false;
  const isChat = pathname?.includes('/chat') ?? false;

  // Auto-select first project if no project is selected (only on Project Management page)
  useEffect(() => {
    if (!isOverview && !selectedProjectId && projects.length > 0 && selectedProject) {
      router.push(`/pm/chat?project=${selectedProject}`);
    }
  }, [projects.length, selectedProject, selectedProjectId, router, isOverview]);

  const handleProjectChange = (projectId: string) => {
    if (onProjectChange) {
      onProjectChange(projectId);
    } else {
      router.push(`/pm/chat?project=${projectId}`);
    }
  };

  return (
    <>
      <ProviderManagementDialog />
      <header className="fixed top-0 left-0 flex h-16 w-full items-center justify-between px-6 bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 z-50">
        <div className="flex items-center gap-4 flex-1">
          {/* Navigation Tabs */}
          <div className="flex items-center gap-2 border-r border-gray-200 dark:border-gray-700 pr-4">
            <Link href="/pm/overview">
              <Button
                variant={isOverview ? "default" : "ghost"}
                size="sm"
                className={isOverview ? "bg-blue-600 hover:bg-blue-700 text-white" : ""}
              >
                Overview
              </Button>
            </Link>
            <Link href={`/pm/chat${selectedProject ? `?project=${selectedProject}` : ''}`}>
              <Button
                variant={isChat ? "default" : "ghost"}
                size="sm"
                className={isChat ? "bg-blue-600 hover:bg-blue-700 text-white" : ""}
              >
                Project Management
              </Button>
            </Link>
          </div>

          {/* Project Selector - Only show on Project Management page */}
          {!isOverview && (
            <div className="flex items-center gap-2 min-w-[200px]">
              <Select value={selectedProject || undefined} onValueChange={handleProjectChange} disabled={projectsLoading || projects.length === 0}>
                <SelectTrigger className="w-full">
                  {selectedProject ? (
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      {(() => {
                        const project = projects.find(p => p.id === selectedProject);
                        const providerType = getProviderType(selectedProject);
                        return project ? (
                          <>
                            {getProviderBadge(providerType)}
                            <span className="truncate">{project.name}</span>
                          </>
                        ) : (
                          <span className="text-gray-500">No project selected</span>
                        );
                      })()}
                    </div>
                  ) : (
                    <SelectValue placeholder="Loading projects..." />
                  )}
                </SelectTrigger>
                <SelectContent>
                  {projects.map(project => {
                    const providerType = getProviderType(project.id);
                    return (
                      <SelectItem key={project.id} value={project.id}>
                        <div className="flex items-center gap-2">
                          {getProviderBadge(providerType)}
                          <span>{project.name}</span>
                        </div>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>

        {/* Right side: Provider | DarkMode | Setting */}
        <div className="flex items-center gap-2">
          <Tooltip title="Provider Management">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                const event = new CustomEvent("pm_show_providers");
                window.dispatchEvent(event);
              }}
            >
              <span className="mr-2">🔌</span>
              Provider
            </Button>
          </Tooltip>
          <ThemeToggle />
          <Suspense>
            <SettingsDialog />
          </Suspense>
        </div>
      </header>
    </>
  );
}
