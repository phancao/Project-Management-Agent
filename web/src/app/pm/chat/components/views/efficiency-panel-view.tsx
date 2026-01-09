"use client";

import { useEffect, useState, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { format, startOfMonth, endOfMonth } from "date-fns";
import type { DateRange } from "react-day-picker";

import { EfficiencyDashboard } from "~/components/efficiency/efficiency-dashboard";
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

    const [dateRange, setDateRange] = useState<DateRange | undefined>({
        from: startOfMonth(new Date()),
        to: new Date(),
    });

    // Member Active Periods (Persistence)
    const [activePeriods, setActivePeriods] = useState<Record<string, DateRange[]>>({});

    // Load from localStorage on mount
    useEffect(() => {
        if (!projectId) return;
        try {
            const saved = localStorage.getItem(`ee-durations-project-${projectId}`);
            if (saved) {
                const parsed = JSON.parse(saved);
                const hydrated: Record<string, DateRange[]> = {};
                Object.keys(parsed).forEach(key => {
                    hydrated[key] = parsed[key].map((range: any) => ({
                        from: range.from ? new Date(range.from) : undefined,
                        to: range.to ? new Date(range.to) : undefined
                    }));
                });
                setActivePeriods(hydrated);
            }
        } catch (e) {
            console.error("Failed to load active periods", e);
        }
    }, [projectId]);

    const handleActivePeriodsChange = (periods: Record<string, DateRange[]>) => {
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
                onDateRangeChange={setDateRange}
                activePeriods={activePeriods}
                onActivePeriodsChange={handleActivePeriodsChange}
                title="Project Efficiency"
            />
        </div>
    );
}
