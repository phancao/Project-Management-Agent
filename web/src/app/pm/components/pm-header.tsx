// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useMemo, useEffect, useState } from "react";
import { Suspense } from "react";

import { toast } from "sonner";

import { Button } from "~/components/ui/button";
import { RefreshCw, ChevronDown, Check } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "~/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "~/components/ui/command";
import { useProjects } from "~/core/api/hooks/pm/use-projects";
import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { useProviders } from "~/core/api/hooks/pm/use-providers";
import {
  getProviderTypeFromProjectId,
  getProviderBadgeConfig,
  extractProviderId,
} from "../utils/provider-utils";

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
  const { projects, loading: projectsLoading, refresh: refreshProjects } = useProjects();
  const { mappings } = useProviders();
  const [regeneratingMockData, setRegeneratingMockData] = useState(false);
  const [projectComboboxOpen, setProjectComboboxOpen] = useState(false);

  const selectedProjectId = propSelectedProjectId || new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '').get('project');

  // Helper to get provider type from project ID
  const getProviderType = (projectId: string | undefined): string | null => {
    return getProviderTypeFromProjectId(projectId, mappings.typeMap);
  };

  // Helper to get provider badge component
  const getProviderBadge = (providerType: string | null) => {
    if (!providerType) return null;
    const config = getProviderBadgeConfig(providerType);
    return (
      <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${config.color}`}>
        {config.label}
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

  const mockProjects = useMemo(
    () => projects.filter(project => project.id?.startsWith("mock:")),
    [projects]
  );

  // Group real projects by provider (using provider_id as key, base_url for display)
  const projectsByProvider = useMemo(() => {
    const grouped = new Map<string, { baseUrl: string; projects: typeof projects }>();

    projects.forEach(project => {
      if (project.id?.startsWith("mock:")) return; // Skip mock projects

      const providerId = extractProviderId(project.id);
      if (!providerId || providerId === "mock") return;

      // Get base URL from mappings, or use a fallback if not found
      // This allows projects to show even if provider mapping isn't loaded yet
      const baseUrl = mappings.urlMap.get(providerId) || `Provider ${providerId.substring(0, 8)}...`;

      if (!grouped.has(providerId)) {
        grouped.set(providerId, { baseUrl, projects: [] });
      }
      grouped.get(providerId)!.projects.push(project);
    });

    return grouped;
  }, [projects, mappings.urlMap]);

  // Helper to extract domain from URL
  const getDomainFromUrl = (url: string | undefined): string => {
    if (!url) return '';
    try {
      // Remove protocol if present
      let cleanUrl = url.replace(/^https?:\/\//, '');
      // Remove trailing slash
      cleanUrl = cleanUrl.replace(/\/$/, '');
      // Extract domain (everything before the first /)
      const domain = cleanUrl.split('/')[0];
      return domain || url;
    } catch {
      return url;
    }
  };

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

  const isMockProjectSelected = selectedProject?.startsWith("mock:") ?? false;

  const handleRegenerateMockData = async () => {
    if (regeneratingMockData) {
      return;
    }
    setRegeneratingMockData(true);
    try {
      const response = await fetch(resolveServiceURL("pm/mock/regenerate"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Request failed with status ${response.status}`);
      }

      const result = await response.json();
      const generatedAt = result?.metadata?.generated_at;
      toast.success("Mock data regenerated", {
        description: generatedAt ? `Generated at ${new Date(generatedAt).toLocaleString()}` : undefined,
      });
      refreshProjects();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error("Failed to regenerate mock data", {
        description: message,
      });
    } finally {
      setRegeneratingMockData(false);
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
            <Link href="/meeting">
              <Button
                variant="ghost"
                size="sm"
                className="hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <span className="sm:mr-2">🎙️</span>
                <span className="sm:inline hidden">Meeting</span>
              </Button>
            </Link>
          </div>

          {/* Project Selector - Only show on Project Management page */}
          {!isOverview && (
            <div className="flex items-center gap-2 min-w-[200px]">
              <Popover open={projectComboboxOpen} onOpenChange={setProjectComboboxOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={projectComboboxOpen}
                    className="w-full justify-between"
                    disabled={projectsLoading || projects.length === 0}
                  >
                    {selectedProject ? (
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        {(() => {
                          const project = projects.find(p => p.id === selectedProject);
                          const providerType = getProviderType(selectedProject);
                          const isMockProject = selectedProject.startsWith("mock:");
                          if (!project) {
                            return (
                              <span className="text-gray-500">No project selected</span>
                            );
                          }
                          if (isMockProject) {
                            return (
                              <>
                                <span className="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium bg-amber-100 dark:bg-amber-900 text-amber-800 dark:text-amber-200">
                                  DEMO
                                </span>
                                <span className="truncate">Mock Project (Demo Data)</span>
                              </>
                            );
                          }
                          return (
                            <>
                              {getProviderBadge(providerType)}
                              <span className="truncate">{project.name}</span>
                            </>
                          );
                        })()}
                      </div>
                    ) : (
                      <span className="text-gray-500">Loading projects...</span>
                    )}
                    <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[400px] p-0" align="start">
                  <Command
                    filter={(value, search) => {
                      // Use exact substring matching (case-insensitive)
                      const searchLower = search.toLowerCase();
                      const valueLower = value.toLowerCase();
                      return valueLower.includes(searchLower) ? 1 : 0;
                    }}
                  >
                    <CommandInput placeholder="Search projects..." />
                    <CommandList>
                      <CommandEmpty>No projects found.</CommandEmpty>
                      {mockProjects.length > 0 && (
                        <CommandGroup heading="Demo Projects">
                          {mockProjects.map(project => (
                            <CommandItem
                              key={project.id}
                              value="Mock Project Demo Data"
                              onSelect={() => {
                                handleProjectChange(project.id);
                                setProjectComboboxOpen(false);
                              }}
                            >
                              <div className="flex items-center gap-2 flex-1">
                                <span className="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium bg-amber-100 dark:bg-amber-900 text-amber-800 dark:text-amber-200">
                                  DEMO
                                </span>
                                <span>Mock Project (Demo Data)</span>
                              </div>
                              <Check
                                className={`ml-2 h-4 w-4 ${selectedProject === project.id ? "opacity-100" : "opacity-0"
                                  }`}
                              />
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      )}
                      {Array.from(projectsByProvider.entries()).map(([providerId, { baseUrl, projects: providerProjects }]) => (
                        <CommandGroup key={providerId} heading={getDomainFromUrl(baseUrl)}>
                          {providerProjects.map(project => {
                            const projectProviderType = getProviderType(project.id);
                            return (
                              <CommandItem
                                key={project.id}
                                value={project.name}
                                onSelect={() => {
                                  handleProjectChange(project.id);
                                  setProjectComboboxOpen(false);
                                }}
                              >
                                <div className="flex items-center gap-2 flex-1">
                                  {getProviderBadge(projectProviderType)}
                                  <span>{project.name}</span>
                                </div>
                                <Check
                                  className={`ml-2 h-4 w-4 ${selectedProject === project.id ? "opacity-100" : "opacity-0"
                                    }`}
                                />
                              </CommandItem>
                            );
                          })}
                        </CommandGroup>
                      ))}
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
              {isMockProjectSelected ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRegenerateMockData}
                  disabled={regeneratingMockData}
                  className="whitespace-nowrap"
                >
                  <RefreshCw className={`mr-2 h-4 w-4 ${regeneratingMockData ? "animate-spin" : ""}`} />
                  {regeneratingMockData ? "Regenerating..." : "Regenerate mock data"}
                </Button>
              ) : null}
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
