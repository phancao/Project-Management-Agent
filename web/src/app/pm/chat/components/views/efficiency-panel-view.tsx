"use client";

import { useEffect, useState, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { format, startOfMonth } from "date-fns";
import type { DateRange } from "react-day-picker";
import { Settings2, Database, FolderOpen, Loader2 } from "lucide-react";

import { EfficiencyDashboard } from "~/components/efficiency/efficiency-dashboard";
import { type MemberPeriod, type Holiday } from "~/components/efficiency/member-duration-manager";
import { useHolidays } from "~/contexts/holidays-context";
import {
    useProjectMembers,
    useProjectTasks,
    useProjectTimeEntries
} from "~/core/api/hooks/pm/use-project-efficiency";
import { useProviders } from "~/core/api/hooks/pm/use-providers";
import { useProjectsByProvider } from "~/core/api/hooks/pm/use-projects";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Badge } from "~/components/ui/badge";

/**
 * Project Efficiency (EE) Panel View
 * 
 * This is a Project-Centric widget that queries data by projectId and providerId.
 * It follows the Widget Autonomy Standard:
 * - providerId is MANDATORY (can be configured inline)
 * - Data is fetched from the remote provider, not from local DB
 */
interface EfficiencyPanelViewProps {
    projectId?: string;     // Project to query data from (can be configured inline)
    providerId?: string;    // Provider ID (can be configured inline)
    instanceId?: string;
}

export function EfficiencyPanelView({
    projectId: propProjectId,
    providerId: propProviderId,
    instanceId
}: EfficiencyPanelViewProps) {
    const searchParams = useSearchParams();

    // Storage keys for configuration persistence
    const storageKeyConfig = instanceId
        ? `ee-config-instance-${instanceId}`
        : `ee-config-global`;

    // Local selection state (persisted to localStorage)
    const [selectedProviderId, setSelectedProviderId] = useState<string | undefined>(() => {
        if (propProviderId) return propProviderId;
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem(storageKeyConfig);
            if (saved) {
                try {
                    const config = JSON.parse(saved);
                    return config.providerId;
                } catch { /* ignore */ }
            }
        }
        return undefined;
    });

    const [selectedProjectId, setSelectedProjectId] = useState<string | undefined>(() => {
        if (propProjectId) return propProjectId;
        // Check URL params
        const urlProjectId = searchParams.get("project");
        if (urlProjectId) return urlProjectId;
        // Check localStorage
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem(storageKeyConfig);
            if (saved) {
                try {
                    const config = JSON.parse(saved);
                    return config.projectId;
                } catch { /* ignore */ }
            }
        }
        return undefined;
    });

    // Save config to localStorage when selections change
    useEffect(() => {
        if (selectedProviderId || selectedProjectId) {
            localStorage.setItem(storageKeyConfig, JSON.stringify({
                providerId: selectedProviderId,
                projectId: selectedProjectId
            }));
        }
    }, [selectedProviderId, selectedProjectId, storageKeyConfig]);

    // Fetch providers
    const { providers, loading: loadingProviders } = useProviders();

    // Fetch projects for selected provider
    const { projects, loading: loadingProjects } = useProjectsByProvider(selectedProviderId);

    // Handle provider change - reset project selection
    const handleProviderChange = (providerId: string) => {
        setSelectedProviderId(providerId);
        setSelectedProjectId(undefined); // Reset project when provider changes
    };

    // Use effective IDs (from props or local selection)
    const effectiveProviderId = propProviderId || selectedProviderId;
    const effectiveProjectId = propProjectId || selectedProjectId;

    // Keys for localStorage - scoped to instance if available, else project, else global
    const storageKeyDate = instanceId
        ? `ee-daterange-instance-${instanceId}`
        : (effectiveProjectId ? `ee-daterange-project-${effectiveProjectId}` : `ee-daterange-global`);
    const storageKeyDurations = instanceId
        ? `ee-durations-instance-${instanceId}`
        : (effectiveProjectId ? `ee-durations-project-${effectiveProjectId}` : `ee-durations-global`);

    const [dateRange, setDateRange] = useState<DateRange | undefined>(() => {
        // Initialize from localStorage if available
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem(storageKeyDate);
            if (saved) {
                try {
                    const parsed = JSON.parse(saved);
                    return {
                        from: parsed.from ? new Date(parsed.from) : undefined,
                        to: parsed.to ? new Date(parsed.to) : undefined
                    };
                } catch { /* ignore */ }
            }
        }
        // Default: start of month to today
        return { from: startOfMonth(new Date()), to: new Date() };
    });

    // Save dateRange to localStorage when it changes
    const handleDateRangeChange = (range: DateRange | undefined) => {
        setDateRange(range);
        if (range) {
            localStorage.setItem(storageKeyDate, JSON.stringify(range));
        }
    };

    // Member Active Periods (Persistence) - Using MemberPeriod for allocation support
    const [activePeriods, setActivePeriods] = useState<Record<string, MemberPeriod[]>>({});

    // Holidays from global context (managed at /settings/holidays)
    const { holidays, addHoliday, removeHoliday } = useHolidays();

    // Handle holidays changes (sync to global context)
    const handleHolidaysChange = (newHolidays: Holiday[]) => {
        // Sync with context - compare and update
        const getKey = (h: Holiday) => (h.range.from?.toISOString() || '') + h.name;
        const currentSet = new Set(holidays.map(getKey));
        const newSet = new Set(newHolidays.map(getKey));

        // Remove holidays not in new list
        holidays.forEach((h, i) => {
            const key = getKey(h);
            if (!newSet.has(key)) {
                removeHoliday(i);
            }
        });

        // Add holidays not in current list
        newHolidays.forEach(h => {
            const key = getKey(h);
            if (!currentSet.has(key)) {
                addHoliday(h);
            }
        });
    };

    // Load from localStorage on mount - with backward compatibility
    useEffect(() => {
        try {
            const saved = localStorage.getItem(storageKeyDurations);
            if (saved) {
                const parsed = JSON.parse(saved);
                const hydrated: Record<string, MemberPeriod[]> = {};
                Object.keys(parsed).forEach(key => {
                    hydrated[key] = parsed[key].map((item: any) => {
                        // Check if it's new MemberPeriod format or old DateRange format
                        if (item.range) {
                            return {
                                range: {
                                    from: item.range.from ? new Date(item.range.from) : undefined,
                                    to: item.range.to ? new Date(item.range.to) : undefined
                                },
                                allocation: item.allocation ?? 100,
                                vacations: item.vacations?.map((v: any) => ({
                                    from: v.from ? new Date(v.from) : undefined,
                                    to: v.to ? new Date(v.to) : undefined
                                }))
                            };
                        } else {
                            return {
                                range: {
                                    from: item.from ? new Date(item.from) : undefined,
                                    to: item.to ? new Date(item.to) : undefined
                                },
                                allocation: 100
                            };
                        }
                    });
                });
                setActivePeriods(hydrated);
            }
        } catch (e) {
            console.error("Failed to load active periods", e);
        }
    }, [storageKeyDurations]);

    const handleActivePeriodsChange = (periods: Record<string, MemberPeriod[]>) => {
        setActivePeriods(periods);
        localStorage.setItem(storageKeyDurations, JSON.stringify(periods));
    };

    // ==================================================
    // PROJECT-CENTRIC DATA FETCHING (Widget Autonomy Standard)
    // ==================================================

    const dateOptions = useMemo(() => ({
        startDate: dateRange?.from ? format(dateRange.from, 'yyyy-MM-dd') : undefined,
        endDate: dateRange?.to ? format(dateRange.to, 'yyyy-MM-dd') : undefined,
    }), [dateRange]);

    // Fetch project members (users assigned to this project)
    const {
        data: members = [],
        isLoading: isLoadingMembers
    } = useProjectMembers(effectiveProjectId, effectiveProviderId);

    // Fetch project tasks
    const {
        data: tasks = [],
        isLoading: isLoadingTasks
    } = useProjectTasks(effectiveProjectId, effectiveProviderId, dateOptions);

    // Fetch project time entries (worklogs)
    const {
        data: timeEntries = [],
        isLoading: isLoadingTimeEntries
    } = useProjectTimeEntries(effectiveProjectId, effectiveProviderId, dateOptions);

    const isLoading = isLoadingMembers || isLoadingTasks || isLoadingTimeEntries;

    // ==================================================
    // CONFIGURATION UI (when no provider/project selected)
    // ==================================================

    if (!effectiveProviderId || !effectiveProjectId) {
        return (
            <div className="h-full flex items-center justify-center p-6">
                <Card className="w-full max-w-md">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Settings2 className="w-5 h-5" />
                            Configure Project Efficiency
                        </CardTitle>
                        <CardDescription>
                            Select a provider and project to view efficiency metrics.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {/* Provider Selection */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium flex items-center gap-2">
                                <Database className="w-4 h-4 text-muted-foreground" />
                                Provider
                            </label>
                            <Select
                                value={selectedProviderId || ""}
                                onValueChange={handleProviderChange}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder={loadingProviders ? "Loading providers..." : "Select a provider"} />
                                </SelectTrigger>
                                <SelectContent>
                                    {providers.filter(p => p.is_active).map(provider => (
                                        <SelectItem key={provider.id} value={provider.id}>
                                            <div className="flex items-center gap-2">
                                                <Badge variant="outline" className="text-xs">
                                                    {provider.provider_type}
                                                </Badge>
                                                {provider.provider_type} ({new URL(provider.base_url).hostname})
                                            </div>
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Project Selection (only shown after provider is selected) */}
                        {selectedProviderId && (
                            <div className="space-y-2">
                                <label className="text-sm font-medium flex items-center gap-2">
                                    <FolderOpen className="w-4 h-4 text-muted-foreground" />
                                    Project
                                </label>
                                <Select
                                    value={selectedProjectId || ""}
                                    onValueChange={setSelectedProjectId}
                                    disabled={loadingProjects}
                                >
                                    <SelectTrigger>
                                        {loadingProjects ? (
                                            <div className="flex items-center gap-2">
                                                <Loader2 className="w-4 h-4 animate-spin" />
                                                Loading projects...
                                            </div>
                                        ) : (
                                            <SelectValue placeholder="Select a project" />
                                        )}
                                    </SelectTrigger>
                                    <SelectContent>
                                        {projects.map(project => (
                                            <SelectItem key={project.id} value={project.id}>
                                                {project.name}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                {projects.length === 0 && !loadingProjects && (
                                    <p className="text-xs text-muted-foreground">
                                        No projects found for this provider.
                                    </p>
                                )}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        );
    }

    // ==================================================
    // MAIN DASHBOARD VIEW
    // ==================================================

    // Find the selected project name for display
    const selectedProject = projects.find(p => p.id === effectiveProjectId);
    const selectedProvider = providers.find(p => p.id === effectiveProviderId);

    return (
        <div className="h-full space-y-4">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-4">
                    <h2 className="text-lg font-semibold tracking-tight">Project Efficiency (EE)</h2>
                    {/* Compact project indicator with change option */}
                    <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="text-xs">
                            {selectedProvider?.provider_type || 'Provider'}
                        </Badge>
                        <span className="text-sm text-muted-foreground">
                            {selectedProject?.name || effectiveProjectId}
                        </span>
                        <button
                            className="text-xs text-muted-foreground hover:text-foreground underline"
                            onClick={() => {
                                setSelectedProviderId(undefined);
                                setSelectedProjectId(undefined);
                            }}
                        >
                            Change
                        </button>
                    </div>
                </div>
            </div>
            <EfficiencyDashboard
                members={members}
                tasks={tasks}
                timeEntries={timeEntries}
                isLoading={isLoading}
                dateRange={dateRange}
                onDateRangeChange={handleDateRangeChange}
                activePeriods={activePeriods}
                onActivePeriodsChange={handleActivePeriodsChange}
                holidays={holidays}
                onHolidaysChange={handleHolidaysChange}
                title="Project Efficiency"
            />
        </div>
    );
}
