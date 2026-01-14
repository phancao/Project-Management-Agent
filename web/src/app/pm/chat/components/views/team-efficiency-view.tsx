"use client";

import { useEffect, useState, useMemo } from "react";
import { format, startOfMonth } from "date-fns";
import type { DateRange } from "react-day-picker";

import { EfficiencyDashboard } from "~/components/efficiency/efficiency-dashboard";
import { type MemberPeriod, type Holiday } from "~/components/efficiency/member-duration-manager";
import { useHolidays } from "~/contexts/holidays-context";
import { useTeamUsers, useTeamTasks, useTeamTimeEntries } from "~/app/team/context/team-data-context";

/**
 * Team Efficiency View
 * 
 * This is a Team-Centric view that queries data by member IDs.
 * It aggregates data across multiple providers and projects based on configured team members.
 * 
 * Use this for: Analyzing efficiency of a cross-project team
 * 
 * For project-specific efficiency, use EfficiencyPanelView instead.
 */
interface TeamEfficiencyViewProps {
    configuredMemberIds?: string[];  // Member IDs to include
    instanceId?: string;
}

export function TeamEfficiencyView({
    configuredMemberIds,
    instanceId
}: TeamEfficiencyViewProps) {
    // Keys for localStorage - scoped to instance, else global
    const storageKeyDate = instanceId
        ? `ee-daterange-team-instance-${instanceId}`
        : `ee-daterange-team-global`;
    const storageKeyDurations = instanceId
        ? `ee-durations-team-instance-${instanceId}`
        : `ee-durations-team-global`;

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
    // TEAM-CENTRIC DATA FETCHING
    // Queries by member IDs, aggregates across providers/projects
    // ==================================================

    const effectiveMemberIds = configuredMemberIds || [];

    // Use provider-grouped hooks from team-data-context
    const { teamMembers: users, isLoading: isLoadingUsers } = useTeamUsers(effectiveMemberIds);

    const { teamTasks: tasks, isLoading: isLoadingTasks } = useTeamTasks(effectiveMemberIds, {
        startDate: dateRange?.from ? format(dateRange.from, 'yyyy-MM-dd') : undefined,
        endDate: dateRange?.to ? format(dateRange.to, 'yyyy-MM-dd') : undefined,
    });

    const { teamTimeEntries: timeEntries, isLoading: isLoadingTimeEntries } = useTeamTimeEntries(effectiveMemberIds, {
        startDate: dateRange?.from ? format(dateRange.from, 'yyyy-MM-dd') : undefined,
        endDate: dateRange?.to ? format(dateRange.to, 'yyyy-MM-dd') : undefined,
    });

    const isLoading = isLoadingUsers || isLoadingTasks || isLoadingTimeEntries;

    // Show prompt if no members configured
    if (effectiveMemberIds.length === 0) {
        return (
            <div className="h-full flex items-center justify-center">
                <div className="text-center text-muted-foreground">
                    <p className="font-medium">Configure Team Members</p>
                    <p className="text-sm">Select team members to view efficiency metrics.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="h-full space-y-4">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold tracking-tight">Team Efficiency (EE)</h2>
            </div>
            <EfficiencyDashboard
                members={users}
                tasks={tasks}
                timeEntries={timeEntries}
                isLoading={isLoading}
                dateRange={dateRange}
                onDateRangeChange={handleDateRangeChange}
                activePeriods={activePeriods}
                onActivePeriodsChange={handleActivePeriodsChange}
                holidays={holidays}
                onHolidaysChange={handleHolidaysChange}
                title="Team Efficiency"
            />
        </div>
    );
}
