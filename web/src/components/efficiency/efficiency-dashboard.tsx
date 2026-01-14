'use client';

import { useMemo, useState, useEffect } from 'react';
import { startOfMonth, endOfMonth, startOfDay, endOfDay, parseISO, format, eachDayOfInterval, isWeekend, isWithinInterval } from 'date-fns';
import type { DateRange } from 'react-day-picker';
import { Calendar as CalendarIcon, ChevronDown, ChevronUp } from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { cn } from "~/lib/utils";
import { Button } from "~/components/ui/button";
import { Calendar } from "~/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "~/components/ui/popover";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "~/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "~/components/ui/collapsible";

import { type PMUser } from '~/core/api/pm/users';
import { type PMTask } from '~/core/api/pm/tasks';
import { type PMTimeEntry } from '~/core/api/pm/time-entries';
import { EfficiencyGantt } from './efficiency-gantt';
import { useCardGlow, useStatCardGlow } from '~/core/hooks/use-theme-colors';

import { MemberDurationManager, type MemberPeriod, type Holiday } from './member-duration-manager';
import { MemberEfficiencyCard } from './member-efficiency-card';

// Color palette for activity types
const ACTIVITY_COLORS = [
    "#22c55e", // green
    "#3b82f6", // blue
    "#f59e0b", // amber
    "#ef4444", // red
    "#8b5cf6", // violet
    "#ec4899", // pink
    "#14b8a6", // teal
    "#f97316", // orange
];

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

    // Holidays
    holidays?: Holiday[];
    onHolidaysChange?: (holidays: Holiday[]) => void;

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
    holidays = [],
    onHolidaysChange,
    title = "Efficiency Dashboard"
}: EfficiencyDashboardProps) {

    // Get configurable glow classes from theme settings
    const cardGlow = useCardGlow();
    const statCardGlow = useStatCardGlow();

    // View Mode State
    const [viewMode, setViewMode] = useState<'day' | 'week' | 'month'>('day');

    // Member Exclusion State
    const [excludedMemberIds, setExcludedMemberIds] = useState<string[]>([]);

    // Collapsible state for Member Active Periods
    const [isActivePeriodsOpen, setIsActivePeriodsOpen] = useState(true);

    // Load View Mode and Exclusion List from localStorage
    useEffect(() => {
        if (typeof window !== 'undefined') {
            const savedMode = localStorage.getItem('ee-dashboard-view-mode');
            if (savedMode === 'day' || savedMode === 'week' || savedMode === 'month') {
                setViewMode(savedMode);
            }

            const savedExcluded = localStorage.getItem('ee-dashboard-excluded-members');
            if (savedExcluded) {
                try {
                    setExcludedMemberIds(JSON.parse(savedExcluded));
                } catch (e) {
                    console.error("Failed to parse excluded members", e);
                }
            }
        }
    }, []);

    const handleViewModeChange = (v: string) => {
        const mode = v as 'day' | 'week' | 'month';
        setViewMode(mode);
        localStorage.setItem('ee-dashboard-view-mode', mode);
    };

    const handleToggleExclusion = (memberId: string) => {
        setExcludedMemberIds(prev => {
            const next = prev.includes(memberId)
                ? prev.filter(id => id !== memberId)
                : [...prev, memberId];

            localStorage.setItem('ee-dashboard-excluded-members', JSON.stringify(next));
            return next;
        });
    };

    // Filter members based on exclusion list for calculations and display
    const activeMembers = useMemo(() => {
        return members.filter(m => !excludedMemberIds.includes(m.id));
    }, [members, excludedMemberIds]);

    // Calculation Logic for EE (using activeMembers)
    const metrics = useMemo(() => {
        if (!dateRange?.from || !dateRange?.to || activeMembers.length === 0) {
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
        const headcount = activeMembers.length;

        const getBusinessDaysCount = (start: Date, end: Date) => {
            if (start > end) return 0;
            const days = eachDayOfInterval({ start, end });
            // Exclude weekends and holidays
            return days.filter(day => {
                if (isWeekend(day)) return false;
                // Check if this day is within any holiday range
                const isHolidayDay = holidays.some(h => {
                    if (!h.range.from) return false;
                    const holidayStart = new Date(h.range.from);
                    holidayStart.setHours(0, 0, 0, 0);
                    const holidayEnd = h.range.to ? new Date(h.range.to) : new Date(h.range.from);
                    holidayEnd.setHours(23, 59, 59, 999);
                    const checkDay = new Date(day);
                    checkDay.setHours(12, 0, 0, 0);
                    return checkDay >= holidayStart && checkDay <= holidayEnd;
                });
                if (isHolidayDay) return false;
                return true;
            }).length;
        };

        // Helper: Check if a day counts as "Active Capacity" for a member
        const isMemberActiveOnDay = (memberId: string, day: Date, periods: MemberPeriod[]) => {
            // 1. Weekend Check
            if (isWeekend(day)) return false;

            // 2. Holiday Check
            if (isHolidayDay(day)) return false;

            // 3. Vacation Check (Explicit)
            if (isVacationDay(memberId, day)) return false;

            // 4. Default Mode (No periods defined) -> Active
            if (!periods || periods.length === 0) return true;

            // 5. Check specific active periods
            let isActive = false;
            periods.forEach(period => {
                if (period.range.from && isWithinInterval(day, {
                    start: startOfDay(period.range.from),
                    end: endOfDay(period.range.to || period.range.from)
                })) {
                    // Only counts if allocation > 0 (otherwise it's effectively a vacation/gap)
                    if (period.allocation > 0) isActive = true;
                }
            });

            if (isActive) return true;

            return false;
        };

        // Helper: Check if a day is a vacation for a specific member
        const isVacationDay = (memberId: string, day: Date): boolean => {
            const periods = activePeriods[memberId];
            if (!periods) return false;

            for (const period of periods) {
                if (period.vacations) {
                    for (const vacation of period.vacations) {
                        if (vacation.from && isWithinInterval(day, {
                            start: startOfDay(vacation.from),
                            end: endOfDay(vacation.to || vacation.from)
                        })) {
                            return true;
                        }
                    }
                }
            }
            return false;
        };

        // Helper: Check if a day is a holiday
        const isHolidayDay = (day: Date): boolean => {
            const checkDay = new Date(day);
            checkDay.setHours(12, 0, 0, 0);
            return holidays.some(h => {
                if (!h.range.from) return false;
                const holidayStart = new Date(h.range.from);
                holidayStart.setHours(0, 0, 0, 0);
                const holidayEnd = h.range.to ? new Date(h.range.to) : new Date(h.range.from);
                holidayEnd.setHours(23, 59, 59, 999);
                return checkDay >= holidayStart && checkDay <= holidayEnd;
            });
        };

        let totalCapacityHours = 0;

        // Ensure we calculate capacity for EACH member based on their specific duration
        activeMembers.forEach(member => {
            const periods = activePeriods[member.id];

            // If no periods defined -> member is active for entire range (standard behavior)
            if (!periods || periods.length === 0) {
                let memberCapacity = 0;
                const days = eachDayOfInterval({ start: startDate, end: endDate });

                days.forEach(day => {
                    if (!isWeekend(day)) {
                        // Check holidays
                        const isHoliday = holidays.some(h => {
                            if (!h.range.from) return false;
                            const holidayStart = new Date(h.range.from);
                            holidayStart.setHours(0, 0, 0, 0);
                            const holidayEnd = h.range.to ? new Date(h.range.to) : new Date(h.range.from);
                            holidayEnd.setHours(23, 59, 59, 999);
                            const checkDay = new Date(day);
                            checkDay.setHours(12, 0, 0, 0);
                            return checkDay >= holidayStart && checkDay <= holidayEnd;
                        });

                        if (!isHoliday) {
                            memberCapacity += 8;
                        }
                    }
                });
                totalCapacityHours += memberCapacity;
                return;
            }

            // Member has defined periods
            // Iterate through every day of the global range check if it falls into any active period
            // Iterate through every day of the global range check if it falls into any active period
            const days = eachDayOfInterval({ start: startDate, end: endDate });

            days.forEach(day => {
                // 1. Must be weekday
                if (isWeekend(day)) return;

                // 2. Must not be holiday
                const isHoliday = holidays.some(h => {
                    if (!h.range.from) return false;
                    const holidayStart = new Date(h.range.from);
                    holidayStart.setHours(0, 0, 0, 0);
                    const holidayEnd = h.range.to ? new Date(h.range.to) : new Date(h.range.from);
                    holidayEnd.setHours(23, 59, 59, 999);
                    const checkDay = new Date(day);
                    checkDay.setHours(12, 0, 0, 0);
                    return checkDay >= holidayStart && checkDay <= holidayEnd;
                });
                if (isHoliday) return;

                // 3. Must be inside an active period
                // AND not be a personal vacation day
                const activePeriod = periods.find(p => p.range.from && isWithinInterval(day, {
                    start: startOfDay(p.range.from),
                    end: endOfDay(p.range.to || p.range.from)
                }));

                if (activePeriod) {
                    // Check if specific day is a vacation day for this member
                    if (isVacationDay(member.id, day)) {
                        return; // It is a vacation, 0 capacity
                    }

                    // Add capacity based on allocation %
                    const allocation = activePeriod.allocation || 100;
                    totalCapacityHours += 8 * (allocation / 100);
                }
            });
        });

        // Calculate Actual Hours - FILTERED by Active Periods
        let totalAllocatedHours = 0;
        timeEntries.forEach(entry => {
            if (!entry.date) return;
            const entryDate = parseISO(entry.date);
            if (entryDate < startDate || entryDate > endDate) return;

            // CRITICAL FIX: Only count hours if the member was actually "Active" on this day
            // This prevents "1-day active duration" users from having "30-days of work" counted against "1-day capacity".
            const periods = activePeriods[entry.user_id];

            // If unknown user (not in members list), maybe we should count it? 
            // Or strict filter? Let's strict filter to be safe with the math.
            // But if user is missing from members list, they don't contribute to capacity either.
            // So filtering is correct.
            const isKnownMember = activeMembers.some(m => m.id === entry.user_id);
            if (isKnownMember) {
                if (isMemberActiveOnDay(entry.user_id, entryDate, periods || [])) {
                    totalAllocatedHours += entry.hours;
                }
            } else {
                // Fallback for non-members? (Shouldn't happen in this view usually)
                // If we count them here, we inflate numerator without denominator.
                // Better to skip.
            }
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

    }, [members, tasks, timeEntries, dateRange, activePeriods, activeMembers]); // Added timeEntries dependency

    // Aggregate time entries by activity type
    const activityData = useMemo(() => {
        const totalHours = timeEntries.reduce((sum, entry) => sum + entry.hours, 0);
        const activityMap: Record<string, number> = {};
        timeEntries.forEach((entry) => {
            const activityName = entry.activity_type || "Unknown";
            activityMap[activityName] = (activityMap[activityName] || 0) + entry.hours;
        });
        return Object.entries(activityMap)
            .map(([name, hours], index) => ({
                name,
                hours,
                percentage: totalHours > 0 ? ((hours / totalHours) * 100).toFixed(1) : "0",
                color: ACTIVITY_COLORS[index % ACTIVITY_COLORS.length],
            }))
            .sort((a, b) => b.hours - a.hours);
    }, [timeEntries]);

    return (
        <div className="space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className={statCardGlow.className}>
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
                <Card className={statCardGlow.className}>
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
                <Card className={statCardGlow.className}>
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
                <Card className={statCardGlow.className}>
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

            {/* Activity Type Distribution */}
            <Card className={cardGlow.className}>
                <CardHeader>
                    <CardTitle className="text-base">Hours by Activity Type</CardTitle>
                    <CardDescription>Distribution of logged hours across activity types</CardDescription>
                </CardHeader>
                <CardContent>
                    {activityData.length > 0 ? (
                        <div className="flex flex-col lg:flex-row items-center gap-8 h-full">
                            <div className="w-full lg:w-[45%] relative aspect-square max-w-[400px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <PieChart>
                                        <Pie
                                            data={activityData}
                                            cx="50%"
                                            cy="50%"
                                            innerRadius="60%"
                                            outerRadius="100%"
                                            fill="#8884d8"
                                            dataKey="hours"
                                            paddingAngle={2}
                                        >
                                            {activityData.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={entry.color} strokeWidth={0} />
                                            ))}
                                        </Pie>
                                        <Tooltip
                                            contentStyle={{
                                                backgroundColor: "var(--card)",
                                                borderColor: "var(--border)",
                                                borderRadius: "8px",
                                                color: "var(--foreground)",
                                                fontSize: "12px"
                                            }}
                                            itemStyle={{ color: "var(--foreground)" }}
                                            formatter={(value, name, item) => [
                                                `${Number(value).toFixed(1)} hours (${item.payload.percentage ?? 0}%)`,
                                                name
                                            ]}
                                        />
                                    </PieChart>
                                </ResponsiveContainer>
                                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                                    <span className="text-3xl font-bold">{metrics.totalAllocatedHours.toFixed(0)}</span>
                                    <span className="text-xs text-muted-foreground uppercase tracking-wider">Hours</span>
                                </div>
                            </div>
                            <div className="w-full lg:flex-1">
                                <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                                    {activityData.map((activity) => (
                                        <div key={activity.name} className="flex items-center gap-3 group">
                                            <div
                                                className="w-4 h-4 rounded-full flex-shrink-0"
                                                style={{ backgroundColor: activity.color }}
                                            />
                                            <div className="flex-1 min-w-0">
                                                <div className="flex justify-between items-baseline mb-1">
                                                    <span className="font-medium truncate group-hover:text-primary transition-colors">
                                                        {activity.name}
                                                    </span>
                                                    <div className="flex items-baseline gap-2">
                                                        <span className="text-sm font-bold">
                                                            {activity.hours.toFixed(1)}h
                                                        </span>
                                                        <span className="text-xs text-muted-foreground w-12 text-right">
                                                            {activity.percentage}%
                                                        </span>
                                                    </div>
                                                </div>
                                                <div className="w-full bg-secondary/50 rounded-full h-2 overflow-hidden">
                                                    <div
                                                        className="h-full rounded-full transition-all duration-500"
                                                        style={{
                                                            width: `${activity.percentage}%`,
                                                            backgroundColor: activity.color
                                                        }}
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="text-center py-8 text-gray-400">
                            <div className="text-3xl mb-2">📊</div>
                            <p className="text-sm">No activity data for the selected date range</p>
                            <p className="text-xs mt-1">Activity types will appear when time entries are logged</p>
                        </div>
                    )}
                </CardContent>
            </Card>


            {/* Gantt Chart Section with Control Bar */}
            <Card className={cardGlow.className}>
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
                            <Tabs value={viewMode} onValueChange={handleViewModeChange}>
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
                            members={activeMembers}
                            timeEntries={timeEntries}
                            startDate={dateRange.from}
                            endDate={dateRange.to}
                            isLoading={isLoading}
                            viewMode={viewMode}
                            activePeriods={activePeriods}
                            holidays={holidays}
                        />
                    ) : (
                        <div className="text-center py-10 text-gray-400">Please select a date range</div>
                    )}
                </CardContent>
            </Card>
            {/* Member Durations - Collapsible */}
            {onActivePeriodsChange && members.length > 0 && (
                <Collapsible open={isActivePeriodsOpen} onOpenChange={setIsActivePeriodsOpen}>
                    <Card className={cardGlow.className}>
                        <CollapsibleTrigger asChild>
                            <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors rounded-t-xl">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <CardTitle className="text-base">Member Active Periods</CardTitle>
                                        <CardDescription>Specify when members joined or left the project to refine capacity calculations.</CardDescription>
                                    </div>
                                    <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0">
                                        {isActivePeriodsOpen ? (
                                            <ChevronUp className="h-4 w-4" />
                                        ) : (
                                            <ChevronDown className="h-4 w-4" />
                                        )}
                                    </Button>
                                </div>
                            </CardHeader>
                        </CollapsibleTrigger>
                        <CollapsibleContent>
                            <CardContent>
                                <MemberDurationManager
                                    members={members}
                                    activePeriods={activePeriods}
                                    onChange={onActivePeriodsChange}
                                    holidays={holidays}
                                    onHolidaysChange={onHolidaysChange}
                                    excludedMemberIds={excludedMemberIds}
                                    onToggleExclusion={handleToggleExclusion}
                                />
                            </CardContent>
                        </CollapsibleContent>
                    </Card>
                </Collapsible>
            )}

            {/* Individual Member Efficiency Cards */}
            {dateRange?.from && dateRange?.to && activeMembers.length > 0 && (
                <div className="space-y-6 pt-4">
                    <div className="flex items-center justify-between">
                        <h3 className="text-lg font-semibold tracking-tight">Member Details</h3>
                    </div>
                    {activeMembers.map(member => (
                        <MemberEfficiencyCard
                            key={member.id}
                            member={member}
                            // [PM-DEBUG] Passing active periods
                            activePeriods={activePeriods[member.id]}
                            timeEntries={timeEntries}
                            dateRange={{ from: dateRange.from!, to: dateRange.to! }}
                            activityColors={ACTIVITY_COLORS}
                            isLoading={isLoading}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}
