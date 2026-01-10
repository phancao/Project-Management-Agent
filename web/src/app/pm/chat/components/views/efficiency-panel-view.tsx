"use client";

import { useEffect, useState, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { format, startOfMonth, endOfMonth } from "date-fns";
import type { DateRange } from "react-day-picker";

import { EfficiencyDashboard } from "~/components/efficiency/efficiency-dashboard";
import { type MemberPeriod, type Holiday } from "~/components/efficiency/member-duration-manager";
import { useHolidays } from "~/contexts/holidays-context";
import { listTasks, type PMTask } from "~/core/api/pm/tasks";
import { listTimeEntries, type PMTimeEntry } from "~/core/api/pm/time-entries";
import { listUsers, type PMUser } from "~/core/api/pm/users";

export function EfficiencyPanelView() {
    const searchParams = useSearchParams();
    const projectId = searchParams.get("project");

    const [isLoading, setIsLoading] = useState(false);
    const [tasks, setTasks] = useState<PMTask[]>([]);
    const [users, setUsers] = useState<PMUser[]>([]);
    const [timeEntries, setTimeEntries] = useState<PMTimeEntry[]>([]);

    const [dateRange, setDateRange] = useState<DateRange | undefined>(() => {
        // Initialize from localStorage if available
        if (typeof window !== 'undefined' && projectId) {
            const saved = localStorage.getItem(`ee-daterange-project-${projectId}`);
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
        if (projectId && range) {
            localStorage.setItem(`ee-daterange-project-${projectId}`, JSON.stringify(range));
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
        if (!projectId) return;
        try {
            const saved = localStorage.getItem(`ee-durations-project-${projectId}`);
            if (saved) {
                const parsed = JSON.parse(saved);
                const hydrated: Record<string, MemberPeriod[]> = {};
                Object.keys(parsed).forEach(key => {
                    hydrated[key] = parsed[key].map((item: any) => {
                        // Check if it's new MemberPeriod format or old DateRange format
                        if (item.range) {
                            // New format: { range: DateRange, allocation: number, vacations?: DateRange[] }
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
                            // Old format: DateRange directly
                            return {
                                range: {
                                    from: item.from ? new Date(item.from) : undefined,
                                    to: item.to ? new Date(item.to) : undefined
                                },
                                allocation: 100 // Default allocation for old data
                            };
                        }
                    });
                });
                setActivePeriods(hydrated);
            }
        } catch (e) {
            console.error("Failed to load active periods", e);
        }
    }, [projectId]);

    const handleActivePeriodsChange = (periods: Record<string, MemberPeriod[]>) => {
        setActivePeriods(periods);
        if (projectId) {
            localStorage.setItem(`ee-durations-project-${projectId}`, JSON.stringify(periods));
        }
    };

    // 1. Fetch Base Data (Users & Tasks) when project changes
    useEffect(() => {
        if (!projectId) return;

        const loadBaseData = async () => {
            setIsLoading(true);
            try {
                // Fetch Users and Project Tasks
                const [fetchedUsers, fetchedTasks] = await Promise.all([
                    listUsers(),
                    listTasks({ project_id: projectId }),
                ]);
                setUsers(fetchedUsers);
                setTasks(fetchedTasks);
            } catch (error) {
                console.error("Failed to load project data for efficiency view", error);
            } finally {
                setIsLoading(false);
            }
        };

        void loadBaseData();
    }, [projectId]);

    // 2. Fetch Time Entries when Date Range Matches
    useEffect(() => {
        if (!projectId || !dateRange?.from || !dateRange?.to) return;

        const loadTimeEntries = async () => {
            setIsLoading(true);
            try {
                const entries = await listTimeEntries({
                    startDate: format(dateRange.from!, 'yyyy-MM-dd'),
                    endDate: format(dateRange.to!, 'yyyy-MM-dd')
                });

                // Client-side filter: Only entries linked to Project Tasks
                const projectTaskIds = new Set(tasks.map(t => t.id));
                const projectEntries = entries.filter(e => e.task_id && projectTaskIds.has(e.task_id));

                setTimeEntries(projectEntries);

            } catch (error) {
                console.error("Failed to load time entries", error);
            } finally {
                setIsLoading(false);
            }
        };

        // Only fetch/filter time entries if we have tasks loaded (to filter against)
        if (tasks.length > 0) {
            void loadTimeEntries();
        }
    }, [projectId, dateRange, tasks]);

    // 3. Filter Members to Project Team (Active Assignees)
    const projectMembers = useMemo(() => {
        return users.filter(u => tasks.some(t => t.assignee_id === u.id));
    }, [users, tasks]);

    if (!projectId) {
        return (
            <div className="flex h-full items-center justify-center p-8 text-muted-foreground">
                <p>Please select a project to view efficiency metrics.</p>
            </div>
        );
    }

    return (
        <div className="h-full space-y-4">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold tracking-tight">Efficiency Metrics</h2>
            </div>
            <EfficiencyDashboard
                members={projectMembers}
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
