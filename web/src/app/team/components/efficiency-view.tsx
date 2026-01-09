'use client';

import { useState, useMemo } from 'react';
import { startOfMonth, endOfMonth } from 'date-fns';
import type { DateRange } from 'react-day-picker';
import { format } from "date-fns";

import { useTeamDataContext, useTeamUsers, useTeamTasks, useTeamTimeEntries } from "../context/team-data-context";
import { EfficiencyDashboard } from '~/components/efficiency/efficiency-dashboard';
import { useHolidays } from '~/contexts/holidays-context';
import { type MemberPeriod, type Holiday } from '~/components/efficiency/member-duration-manager';

export function EfficiencyView() {
    // 1. Context & Data Hooks
    const { allMemberIds, isLoading: isContextLoading } = useTeamDataContext();
    const { teamMembers, isLoading: isUsersLoading } = useTeamUsers(allMemberIds);
    const { holidays, addHoliday, removeHoliday, getMemberVacations, addMemberVacation, removeMemberVacation } = useHolidays();

    // 2. State for Date Range (Default: Current Month)
    const [date, setDate] = useState<DateRange | undefined>({
        from: startOfMonth(new Date()),
        to: new Date(),
    });

    // 3. State for Member Active Periods (stored in localStorage per team)
    const [activePeriods, setActivePeriods] = useState<Record<string, MemberPeriod[]>>({});

    const { teamTasks, isLoading: isTasksLoading } = useTeamTasks(allMemberIds, {
        startDate: date?.from ? format(date.from, 'yyyy-MM-dd') : undefined,
        endDate: date?.to ? format(date.to, 'yyyy-MM-dd') : undefined,
    });

    // 4. Fetch Time Entries (Worklogs) - for ALL projects
    const { teamTimeEntries, isLoading: isTimeLoading } = useTeamTimeEntries(allMemberIds, {
        startDate: date?.from ? format(date.from, 'yyyy-MM-dd') : undefined,
        endDate: date?.to ? format(date.to, 'yyyy-MM-dd') : undefined,
    });

    const isLoading = isContextLoading || isUsersLoading || isTasksLoading || isTimeLoading;

    // Handle holidays changes (sync to global context)
    const handleHolidaysChange = (newHolidays: Holiday[]) => {
        // Clear existing and add new
        while (holidays.length > 0) {
            removeHoliday(0);
        }
        newHolidays.forEach(h => addHoliday(h));
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
            onActivePeriodsChange={setActivePeriods}
            holidays={holidays}
            onHolidaysChange={handleHolidaysChange}
            title="Team Efficiency (EE)"
        />
    );
}
