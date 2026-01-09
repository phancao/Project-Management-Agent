'use client';

import { useState } from 'react';
import { startOfMonth, endOfMonth } from 'date-fns';
import type { DateRange } from 'react-day-picker';
import { format } from "date-fns";

import { useTeamDataContext, useTeamUsers, useTeamTasks, useTeamTimeEntries } from "../context/team-data-context";
import { EfficiencyDashboard } from '~/components/efficiency/efficiency-dashboard';

export function EfficiencyView() {
    // 1. Context & Data Hooks
    const { allMemberIds, isLoading: isContextLoading } = useTeamDataContext();
    const { teamMembers, isLoading: isUsersLoading } = useTeamUsers(allMemberIds);
    // 2. State for Date Range (Default: Current Month)
    const [date, setDate] = useState<DateRange | undefined>({
        from: startOfMonth(new Date()),
        to: new Date(),
    });

    const { teamTasks, isLoading: isTasksLoading } = useTeamTasks(allMemberIds, {
        startDate: date?.from ? format(date.from, 'yyyy-MM-dd') : undefined,
        endDate: date?.to ? format(date.to, 'yyyy-MM-dd') : undefined,
    });

    // 3. Fetch Time Entries (Worklogs)
    const { teamTimeEntries, isLoading: isTimeLoading } = useTeamTimeEntries(allMemberIds, {
        startDate: date?.from ? format(date.from, 'yyyy-MM-dd') : undefined,
        endDate: date?.to ? format(date.to, 'yyyy-MM-dd') : undefined,
    });

    const isLoading = isContextLoading || isUsersLoading || isTasksLoading || isTimeLoading;

    return (
        <EfficiencyDashboard
            members={teamMembers}
            tasks={teamTasks}
            timeEntries={teamTimeEntries}
            isLoading={isLoading}
            dateRange={date}
            onDateRangeChange={setDate}
        />
    );
}
