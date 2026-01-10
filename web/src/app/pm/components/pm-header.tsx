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
import { cn } from "~/lib/utils";
import { RefreshCw, ChevronDown, Check, Menu } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "~/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandInput as CommandInputBase, CommandItem, CommandList } from "~/components/ui/command";
import { Sheet, SheetContent, SheetTrigger, SheetHeader, SheetTitle } from "~/components/ui/sheet";
import { useProjects } from "~/core/api/hooks/pm/use-projects";
import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { useProviders } from "~/core/api/hooks/pm/use-providers";
import { useAuth } from "~/core/contexts/auth-context";
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
  const { } = useAuth(); // Keep for future use, but logout moved to settings
  const [regeneratingMockData, setRegeneratingMockData] = useState(false);
  const [projectComboboxOpen, setProjectComboboxOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Detect mobile
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const selectedProjectId = propSelectedProjectId || new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '').get('project');

  // Helper to get provider type from project ID
  const getProviderType = (projectId: string | undefined): string | null => {
    return getProviderTypeFromProjectId(projectId, mappings.typeMap);
  };

  // Helper to get provider badge component
  const getProviderBadge = (providerType: string | null) => {
    // getProviderBadgeConfig handles null by returning "??" badge
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

  const isChat = pathname?.includes('/chat') ?? false;
  const isMeeting = pathname?.includes('/meeting') ?? false;
  const isTeam = pathname?.includes('/team') ?? false;

  // Auto-select first project if no project is selected (only on Project Management page)
  useEffect(() => {
    // Don't auto-redirect if we're on meeting or team page
    if (!isMeeting && !isTeam && !selectedProjectId && projects.length > 0 && selectedProject) {
      router.push(`/pm/chat?project=${selectedProject}`);
    }
  }, [projects.length, selectedProject, selectedProjectId, router, isMeeting, isTeam]);

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

  const NavButtons = ({ vertical = false }: { vertical?: boolean }) => (
    <div className={`flex ${vertical ? 'flex-col gap-2 w-full' : 'items-center gap-3 border-r border-border/40 pr-6'}`}>
      <Link href={`/pm/chat${selectedProject ? `?project=${selectedProject}` : ''}`} className={vertical ? 'w-full' : ''}>
        <Button
          variant={isChat ? "default" : "ghost"}
          size="sm"
          className={cn(
            "rounded-xl font-medium transition-all duration-300",
            isChat ? "bg-brand text-white shadow-lg shadow-brand/25 hover:bg-brand/90" : "hover:bg-brand/5 hover:text-brand",
            vertical ? "w-full justify-start text-base py-6" : "px-5"
          )}
        >
          Project Management
        </Button>
      </Link>

      <Link href="/team" className={vertical ? 'w-full' : ''}>
        <Button
          variant={pathname?.includes('/team') ? "default" : "ghost"}
          size="sm"
          className={cn(
            "rounded-xl font-medium transition-all duration-300 hover:bg-brand/5 hover:text-brand",
            pathname?.includes('/team') ? "bg-brand text-white shadow-lg shadow-brand/25 hover:bg-brand/90" : "hover:bg-brand/5 hover:text-brand",
            vertical ? "w-full justify-start text-base py-6" : "px-5"
          )}
        >
          <span className="mr-2">👥</span>
          <span>Team Management</span>
        </Button>
      </Link>

      <Link href="/meeting" className={vertical ? 'w-full' : ''}>
        <Button
          variant={isMeeting ? "default" : "ghost"}
          size="sm"
          className={cn(
            "rounded-xl font-medium transition-all duration-300 hover:bg-brand/5 hover:text-brand",
            isMeeting ? "bg-brand text-white shadow-lg shadow-brand/25 hover:bg-brand/90" : "hover:bg-brand/5 hover:text-brand",
            vertical ? "w-full justify-start text-base py-6" : "px-5"
          )}
        >
          <span className="mr-2">🎙️</span>
          <span>Meeting</span>
        </Button>
      </Link>
    </div>
  );

  const RightActions = ({ vertical = false }: { vertical?: boolean }) => (
    <div className={`flex ${vertical ? 'flex-col gap-3 w-full mt-4 pt-6 border-t border-border/40' : 'items-center gap-3'}`}>
      <Tooltip title="Provider Management">
        <Button
          variant="ghost"
          size="sm"
          className={cn(
            "rounded-xl transition-all duration-300 hover:bg-brand/5 hover:text-brand",
            vertical ? "w-full justify-start text-base py-6" : "px-4"
          )}
          onClick={() => {
            const event = new CustomEvent("pm_show_providers");
            window.dispatchEvent(event);
          }}
        >
          <span className="mr-2 text-base">🔌</span>
          Provider
        </Button>
      </Tooltip>
      <div className={cn("flex items-center", vertical ? "justify-between px-2" : "")}>
        {vertical && <span className="text-sm font-medium text-muted-foreground">Appearance</span>}
        <ThemeToggle />
      </div>
      <Suspense>
        <SettingsDialog />
      </Suspense>
    </div>
  );

  return (
    <>
      <ProviderManagementDialog />
      <header className="fixed top-0 left-0 flex h-16 w-full items-center justify-between px-4 sm:px-6 bg-card/90 backdrop-blur-md shadow-sm border-b border-gray-200 dark:border-gray-700 z-50">
        <div className="flex items-center gap-4 flex-1 overflow-hidden">
          {/* Mobile Menu Trigger */}
          {isMobile && (
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="shrink-0">
                  <Menu className="w-5 h-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-80">
                <SheetHeader className="mb-6">
                  <SheetTitle className="flex items-center gap-2">
                    <span className="text-xl">🌌</span> Galaxy AI Project Manager
                  </SheetTitle>
                </SheetHeader>
                <NavButtons vertical />
                <RightActions vertical />
              </SheetContent>
            </Sheet>
          )}

          {/* Logo / Title (Hidden on small mobile if no room, but usually stays) */}
          {!isMobile && (
            <div className="flex items-center gap-3 shrink-0 mr-4">
              <span className="text-2xl filter drop-shadow-sm">🌌</span>
              <span className="font-semibold text-lg tracking-tight text-foreground/90 hidden sm:inline-block">Galaxy AI Project Manager</span>
            </div>
          )}

          {/* Navigation Tabs - Hidden on mobile */}
          {!isMobile && <NavButtons />}

          {/* Project Selector - Responsive width */}
          {!isMeeting && !isTeam && (
            <div className="flex items-center gap-3 flex-1 max-w-[440px] ml-4">
              <Popover open={projectComboboxOpen} onOpenChange={setProjectComboboxOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={projectComboboxOpen}
                    className="w-full justify-between overflow-hidden rounded-xl border-border/60 hover:border-brand/40 bg-background/50 backdrop-blur-sm transition-all shadow-sm"
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
                              <span className="text-muted-foreground italic">No project selected</span>
                            );
                          }
                          if (isMockProject) {
                            return (
                              <>
                                <span className="inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 shrink-0">
                                  DEMO
                                </span>
                                <span className="truncate font-medium">{project.name}</span>
                              </>
                            );
                          }
                          return (
                            <>
                              {getProviderBadge(providerType)}
                              <span className="truncate font-medium">{project.name}</span>
                            </>
                          );
                        })()}
                      </div>
                    ) : (
                      <span className="text-muted-foreground truncate italic">Select Project...</span>
                    )}
                    <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-40 group-hover:opacity-100 transition-opacity" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[320px] sm:w-[440px] p-0 rounded-2xl shadow-2xl border-border/40" align="start">
                  <Command
                    filter={(value, search) => {
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
                                <span>Mock Project</span>
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
              {!isMobile && isMockProjectSelected && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRegenerateMockData}
                  disabled={regeneratingMockData}
                  className="whitespace-nowrap"
                >
                  <RefreshCw className={`mr-2 h-4 w-4 ${regeneratingMockData ? "animate-spin" : ""}`} />
                  Regenerate
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Right side: Provider | DarkMode | Setting - Hidden on mobile */}
        {!isMobile && <RightActions />}
      </header>
    </>
  );
}
