'use client';

import { useMemo, useState } from 'react';
import { startOfMonth, endOfMonth, startOfDay, endOfDay, parseISO, format, eachDayOfInterval, isWeekend, isWithinInterval } from 'date-fns';
import type { DateRange } from 'react-day-picker';
import { Calendar as CalendarIcon } from "lucide-react";

import { cn } from "~/lib/utils";
import { Button } from "~/components/ui/button";
import { Calendar } from "~/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "~/components/ui/popover";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "~/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "~/components/ui/tabs";

import { type PMUser } from '~/core/api/pm/users';
import { type PMTask } from '~/core/api/pm/tasks';
import { type PMTimeEntry } from '~/core/api/pm/time-entries';
import { EfficiencyGantt } from './efficiency-gantt';

import { MemberDurationManager, type MemberPeriod } from './member-duration-manager';

interface EfficiencyDashboardProps {
    members: PMUser[];
    tasks: PMTask[];
    timeEntries: PMTimeEntry[];
    isLoading: boolean;
    dateRange: DateRange | undefined;
    onDateRangeChange: (range: DateRange | undefined) => void;

    // Member Active Periods (Project Duration)
    activePeriods?: Record<string, MemberPeriod[]>;
    onActivePeriodsChange?: (periods: Record<string, MemberPeriod[]>) => void;

    title?: string;
}

export function EfficiencyDashboard({
    members,
    tasks,
    timeEntries,
    isLoading,
    dateRange,
    onDateRangeChange,
    activePeriods = {},
    onActivePeriodsChange,
    title = "Efficiency Dashboard"
}: EfficiencyDashboardProps) {

    // View Mode State
    const [viewMode, setViewMode] = useState<'day' | 'week' | 'month'>('day');

    // Calculation Logic for EE
    const metrics = useMemo(() => {
        if (!dateRange?.from || !dateRange?.to || members.length === 0) {
            return {
                headcount: 0,
                billableBMM: 0,
                eePercent: 0,
                totalCapacityHours: 0,
                totalAllocatedHours: 0
            };
        }

        const startDate = startOfDay(dateRange.from);
        const endDate = endOfDay(dateRange.to);
        const headcount = members.length;

        const getBusinessDaysCount = (start: Date, end: Date) => {
            if (start > end) return 0;
            const days = eachDayOfInterval({ start, end });
            return days.filter(day => !isWeekend(day)).length;
        };

        const getMemberCapacityHours = (memberId: string) => {
            const periods = activePeriods[memberId];

            // Default: Full Duration (100% Capacity) if no periods defined
            if (!periods || periods.length === 0) {
                return getBusinessDaysCount(startDate, endDate) * 8;
            }

            // Custom Duration with Allocation
            const days = eachDayOfInterval({ start: startDate, end: endDate });

            let memberTotalCapacity = 0;

            days.forEach(day => {
                if (isWeekend(day)) return;

                // Find all active periods for this day
                // Sum allocations (e.g. 50% + 50% = 100%)
                let dailyAllocation = 0;
                let isActive = false;

                periods.forEach(period => {
                    if (period.range.from && isWithinInterval(day, {
                        start: startOfDay(period.range.from),
                        end: endOfDay(period.range.to || period.range.from)
                    })) {
                        isActive = true;
                        dailyAllocation += period.allocation;
                    }
                });

                if (isActive) {
                    // Cap at 100%? Or allow overtime planning? 
                    // Standard capacity should probably be actual allocation.
                    // If someone is 50% allocated, their target is 4h.
                    memberTotalCapacity += 8 * (dailyAllocation / 100);
                }
            });

            return memberTotalCapacity;
        };

        // Calculate Total Capacity (Sum of individual capacities)
        let totalCapacityHours = 0;
        members.forEach(member => {
            totalCapacityHours += getMemberCapacityHours(member.id);
        });

        // Calculate Actual Hours
        let totalAllocatedHours = 0;
        timeEntries.forEach(entry => {
            if (!entry.date) return;
            const entryDate = parseISO(entry.date);
            if (entryDate < startDate || entryDate > endDate) return;
            totalAllocatedHours += entry.hours;
        });

        const eePercent = totalCapacityHours > 0 ? (totalAllocatedHours / totalCapacityHours) * 100 : 0;
        // Billable BMM (Actual FTE): Total Hours / (Standard Month ~ 160h? Or Standard Period?)
        // Let's keep it as Total Hours / (Standard Period Business Days * 8) to show FTE equivalent
        const standardBusinessDays = getBusinessDaysCount(startDate, endDate) || 1;
        const billableBMM = totalAllocatedHours / (standardBusinessDays * 8);

        return {
            headcount,
            billableBMM,
            eePercent,
            totalCapacityHours,
            totalAllocatedHours
        };

    }, [members, tasks, timeEntries, dateRange, activePeriods]); // Added timeEntries dependency

    return (
        <div className="space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-gray-500">EE (Efficiency)</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className={cn(
                            "text-2xl font-bold",
                            metrics.eePercent >= 90 ? "text-emerald-600" :
                                metrics.eePercent >= 80 ? "text-amber-600" : "text-red-600"
                        )}>
                            {metrics.eePercent.toFixed(1)}%
                        </div>
                        <p className="text-xs text-gray-400 mt-1">Target: &gt;90%</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-gray-500">Billable FTE</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                            {metrics.billableBMM.toFixed(1)}
                        </div>
                        <p className="text-xs text-gray-400 mt-1">Actual Man-Months (Equiv.)</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-gray-500">Total Headcount</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                            {metrics.headcount}
                        </div>
                        <p className="text-xs text-gray-400 mt-1">Active Members</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-gray-500">Un-billable / Bench</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                            {(metrics.headcount - metrics.billableBMM).toFixed(1)}
                        </div>
                        <p className="text-xs text-gray-400 mt-1">Capacity Gap</p>
                    </CardContent>
                </Card>
            </div>

            {/* Gantt Chart Section with Control Bar */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle className="text-base">Worklog Progress ({viewMode === 'day' ? 'Daily' : viewMode === 'week' ? 'Weekly' : 'Monthly'})</CardTitle>
                            <CardDescription>
                                Logged hours per member.
                                {viewMode === 'day' && <span className="text-emerald-600 font-medium ml-1">Green = 8h target met.</span>}
                                {viewMode === 'week' && <span className="text-emerald-600 font-medium ml-1">Green = 40h target met.</span>}
                                {viewMode === 'month' && <span className="text-emerald-600 font-medium ml-1">Green = Monthly Capacity met.</span>}
                            </CardDescription>
                        </div>
                        <div className="flex items-center gap-2">
                            <Popover>
                                <PopoverTrigger asChild>
                                    <Button
                                        id="date"
                                        variant={"outline"}
                                        className={cn(
                                            "w-[260px] justify-start text-left font-normal h-8 text-sm",
                                            !dateRange && "text-muted-foreground"
                                        )}
                                    >
                                        <CalendarIcon className="mr-2 h-4 w-4" />
                                        {dateRange?.from ? (
                                            dateRange.to ? (
                                                <>
                                                    {format(dateRange.from, "LLL dd, y")} -{" "}
                                                    {format(dateRange.to, "LLL dd, y")}
                                                </>
                                            ) : (
                                                format(dateRange.from, "LLL dd, y")
                                            )
                                        ) : (
                                            <span>Pick a date range</span>
                                        )}
                                    </Button>
                                </PopoverTrigger>
                                <PopoverContent className="w-auto p-0" align="end">
                                    <Calendar
                                        initialFocus
                                        mode="range"
                                        defaultMonth={dateRange?.from}
                                        selected={dateRange}
                                        onSelect={onDateRangeChange}
                                        numberOfMonths={2}
                                        disabled={{ after: new Date() }}
                                    />
                                </PopoverContent>
                            </Popover>
                            <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as 'day' | 'week' | 'month')}>
                                <TabsList className="h-8">
                                    <TabsTrigger value="day" className="text-xs px-3">Day</TabsTrigger>
                                    <TabsTrigger value="week" className="text-xs px-3">Week</TabsTrigger>
                                    <TabsTrigger value="month" className="text-xs px-3">Month</TabsTrigger>
                                </TabsList>
                            </Tabs>
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    {dateRange?.from && dateRange?.to ? (
                        <EfficiencyGantt
                            members={members}
                            timeEntries={timeEntries}
                            startDate={dateRange.from}
                            endDate={dateRange.to}
                            isLoading={isLoading}
                            viewMode={viewMode}
                            activePeriods={activePeriods}
                        />
                    ) : (
                        <div className="text-center py-10 text-gray-400">Please select a date range</div>
                    )}
                </CardContent>
            </Card>
            {/* Member Durations */}
            {onActivePeriodsChange && members.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Member Active Periods</CardTitle>
                        <CardDescription>Specify when members joined or left the project to refine capacity calculations.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <MemberDurationManager
                            members={members}
                            activePeriods={activePeriods}
                            onChange={onActivePeriodsChange}
                        />
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
