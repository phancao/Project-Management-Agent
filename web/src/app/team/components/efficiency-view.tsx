'use client';

import { useState, useMemo, useEffect } from 'react';
import { startOfMonth, endOfMonth } from 'date-fns';
import type { DateRange } from 'react-day-picker';
import { format } from "date-fns";

import { useTeamDataContext, useTeamUsers, useTeamTasks, useTeamTimeEntries } from "../context/team-data-context";
import { EfficiencyDashboard } from '~/components/efficiency/efficiency-dashboard';
import { useHolidays } from '~/contexts/holidays-context';
import { type MemberPeriod, type Holiday } from '~/components/efficiency/member-duration-manager';

const EE_TEAM_PERIODS_KEY = 'ee-durations-team-global';

export function EfficiencyView() {
    // 1. Context & Data Hooks
    const { allMemberIds, isLoading: isContextLoading } = useTeamDataContext();
    const { teamMembers, isLoading: isUsersLoading } = useTeamUsers(allMemberIds);
    const { holidays, addHoliday, removeHoliday } = useHolidays();

    // 2. State for Date Range (Default: Current Month)
    const [date, setDate] = useState<DateRange | undefined>({
        from: startOfMonth(new Date()),
        to: new Date(),
    });

    // 3. State for Member Active Periods (persisted globally for team)
    const [activePeriods, setActivePeriods] = useState<Record<string, MemberPeriod[]>>({});

    // Load active periods from localStorage
    useEffect(() => {
        try {
            const saved = localStorage.getItem(EE_TEAM_PERIODS_KEY);
            if (saved) {
                const parsed = JSON.parse(saved);
                const hydrated: Record<string, MemberPeriod[]> = {};

                Object.keys(parsed).forEach(key => {
                    hydrated[key] = parsed[key].map((item: any) => ({
                        range: {
                            from: item.range?.from ? new Date(item.range.from) : undefined,
                            to: item.range?.to ? new Date(item.range.to) : undefined
                        },
                        allocation: item.allocation || 100,
                        vacations: item.vacations?.map((v: any) => ({
                            from: v.from ? new Date(v.from) : undefined,
                            to: v.to ? new Date(v.to) : undefined
                        })) || []
                    }));
                });
                setActivePeriods(hydrated);
            }
        } catch (e) {
            console.error("Failed to load Team EE active periods", e);
        }
    }, []);

    // Handle active periods change with persistence
    const handleActivePeriodsChange = (periods: Record<string, MemberPeriod[]>) => {
        setActivePeriods(periods);
        localStorage.setItem(EE_TEAM_PERIODS_KEY, JSON.stringify(periods));
    };

    const { teamTasks, isLoading: isTasksLoading } = useTeamTasks(allMemberIds, {
        startDate: date?.from ? format(date.from, 'yyyy-MM-dd') : undefined,
        endDate: date?.to ? format(date.to, 'yyyy-MM-dd') : undefined,
    });

    // 4. Fetch Time Entries (Worklogs) - for ALL projects (multi-project aggregation)
    const { teamTimeEntries, isLoading: isTimeLoading } = useTeamTimeEntries(allMemberIds, {
        startDate: date?.from ? format(date.from, 'yyyy-MM-dd') : undefined,
        endDate: date?.to ? format(date.to, 'yyyy-MM-dd') : undefined,
    });

    const isLoading = isContextLoading || isUsersLoading || isTasksLoading || isTimeLoading;

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

    return (
        <EfficiencyDashboard
            members={teamMembers}
            tasks={teamTasks}
            timeEntries={teamTimeEntries}
            isLoading={isLoading}
            dateRange={date}
            onDateRangeChange={setDate}
            activePeriods={activePeriods}
            onActivePeriodsChange={handleActivePeriodsChange}
            holidays={holidays}
            onHolidaysChange={handleHolidaysChange}
            title="Team Efficiency (EE)"
        />
    );
}
