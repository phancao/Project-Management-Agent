import { useMemo } from 'react';
import { format, eachDayOfInterval, eachWeekOfInterval, eachMonthOfInterval, startOfWeek, endOfWeek, startOfMonth, endOfMonth, isSameDay, isToday, isWeekend, isSameMonth, isSameWeek, differenceInBusinessDays, isWithinInterval, startOfDay, endOfDay } from 'date-fns';
import { cn } from '~/lib/utils';
import { type PMUser } from '~/core/api/pm/users';
import { type PMTimeEntry } from '~/core/api/pm/time-entries';
import { type PMTask } from '~/core/api/pm/tasks';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "~/components/ui/tooltip";
import { type MemberPeriod, type Holiday } from './member-duration-manager';
import { DailyWorklogChart } from './daily-worklog-chart';

interface EfficiencyGanttProps {
    members: PMUser[];
    timeEntries: PMTimeEntry[];
    tasks?: PMTask[];  // Tasks for looking up task names
    startDate: Date;
    endDate: Date;
    isLoading: boolean;
    viewMode: 'day' | 'week' | 'month';
    activePeriods?: Record<string, MemberPeriod[]>;
    holidays?: Holiday[];
}

export function EfficiencyGantt({ members, timeEntries, tasks = [], startDate, endDate, isLoading, viewMode, activePeriods = {}, holidays = [] }: EfficiencyGanttProps) {

    // 1. Generate Periods (Columns)
    const periods = useMemo(() => {
        const interval = { start: startDate, end: endDate };
        switch (viewMode) {
            case 'week':
                return eachWeekOfInterval(interval, { weekStartsOn: 1 });
            case 'month':
                return eachMonthOfInterval(interval);
            case 'day':
            default:
                return eachDayOfInterval(interval);
        }
    }, [startDate, endDate, viewMode]);

    // 2. Helper: Get Period Key for a Date
    const getPeriodKey = (date: Date) => {
        switch (viewMode) {
            case 'week':
                return format(startOfWeek(date, { weekStartsOn: 1 }), 'yyyy-MM-dd');
            case 'month':
                return format(startOfMonth(date), 'yyyy-MM-dd');
            case 'day':
            default:
                return format(date, 'yyyy-MM-dd');
        }
    };

    // 3. Helper: Check if a day is a holiday
    const isHoliday = (day: Date): boolean => {
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

    // 4. Helper: Check if a day is a vacation for a member
    const isVacation = (memberId: string, day: Date): boolean => {
        const memberPeriods = activePeriods[memberId];
        if (!memberPeriods) return false;

        for (const period of memberPeriods) {
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

    // 5. Helper: Get allocation percentage for a member on a specific day
    const getMemberAllocation = (memberId: string, day: Date): number => {
        // Check for holiday first
        if (isHoliday(day)) return 0;

        // Check for vacation
        if (isVacation(memberId, day)) return 0;

        const memberPeriods = activePeriods[memberId];
        if (!memberPeriods || memberPeriods.length === 0) {
            return 100; // Default 100% if no periods defined
        }

        // Find if this day falls within any active period
        for (const period of memberPeriods) {
            if (period.range.from && isWithinInterval(day, {
                start: startOfDay(period.range.from),
                end: endOfDay(period.range.to || period.range.from)
            })) {
                return period.allocation;
            }
        }

        return 0; // If day is outside all active periods, member is not active
    };

    // 4. Helper: Get Target Hours for a Period (Business Days * 8 * allocation)
    const getTargetHours = (memberId: string, periodStart: Date) => {
        let periodEnd;
        switch (viewMode) {
            case 'week':
                periodEnd = endOfWeek(periodStart, { weekStartsOn: 1 });
                break;
            case 'month':
                periodEnd = endOfMonth(periodStart);
                break;
            case 'day':
            default: {
                const allocation = getMemberAllocation(memberId, periodStart);
                return (8 * allocation) / 100; // e.g., 50% = 4h target
            }
        }

        // For week/month: calculate weighted capacity based on allocation per day
        const days = eachDayOfInterval({ start: periodStart, end: periodEnd });
        let totalCapacity = 0;
        for (const day of days) {
            if (!isWeekend(day)) {
                const allocation = getMemberAllocation(memberId, day);
                totalCapacity += (8 * allocation) / 100;
            }
        }

        return totalCapacity;
    };

    // Build task lookup map for quick name resolution
    const taskMap = useMemo(() => {
        const map = new Map<string, PMTask>();
        tasks.forEach(t => map.set(t.id, t));
        return map;
    }, [tasks]);

    // 4. Aggregate hours per member per period (with task breakdown)
    const worklogMap = useMemo(() => {
        const hoursMap = new Map<string, number>();
        const taskBreakdownMap = new Map<string, { taskId: string, taskName: string, projectName: string, hours: number }[]>();

        timeEntries.forEach(entry => {
            if (!entry.date) return;
            const keyDate = new Date(entry.date);
            const periodKey = getPeriodKey(keyDate);
            const key = `${entry.user_id}_${periodKey}`;

            // Aggregate total hours
            const existing = hoursMap.get(key) || 0;
            hoursMap.set(key, existing + entry.hours);

            // Aggregate task breakdown
            const taskBreakdown = taskBreakdownMap.get(key) || [];
            const taskId = entry.task_id || 'no-task';
            // Use _links.workPackage.title directly from time entry (always available)
            // Fall back to task lookup, then to ID-based name
            const taskNameFromLinks = entry._links?.workPackage?.title;
            const projectNameFromLinks = entry._links?.project?.title;
            const task = taskMap.get(taskId);
            const taskName = taskNameFromLinks || task?.name || task?.title || (taskId === 'no-task' ? 'General Work' : `Task ${taskId.split(':').pop()}`);
            const projectName = projectNameFromLinks || 'Unknown Project';

            const existingTask = taskBreakdown.find(t => t.taskId === taskId);
            if (existingTask) {
                existingTask.hours += entry.hours;
            } else {
                taskBreakdown.push({ taskId, taskName, projectName, hours: entry.hours });
            }
            taskBreakdownMap.set(key, taskBreakdown);
        });

        return { hoursMap, taskBreakdownMap };
    }, [timeEntries, viewMode, taskMap]);

    // 5. Status Color Helper (Dynamic Target)
    const getStatusColor = (hours: number, target: number) => {
        if (hours === 0) return 'bg-transparent';
        const ratio = hours / target;

        if (ratio > 1.05) return 'bg-red-500 text-red-100'; // > 105%
        if (ratio >= 0.9) return 'bg-emerald-500 text-emerald-100'; // > 90%
        return 'bg-amber-400 text-amber-900'; // Under
    };

    if (isLoading) {
        return (
            <div className="w-full h-64 flex items-center justify-center text-gray-400 animate-pulse">
                Loading worklogs...
            </div>
        );
    }

    return (
        <div className="border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm bg-white dark:bg-gray-950">
            <div className="overflow-x-auto">
                <div className="min-w-max">
                    {/* Month Header Row (Day View Only) */}
                    {viewMode === 'day' && (
                        <div className="flex border-b border-gray-200 dark:border-gray-800 bg-gray-100/50 dark:bg-gray-900/70">
                            {/* Empty cell for member column */}
                            <div className="sticky left-0 w-48 shrink-0 p-2 bg-gray-100 dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800 z-10" />
                            {/* Month groups */}
                            {(() => {
                                const monthGroups: { month: string; count: number }[] = [];
                                let currentMonth = '';
                                periods.forEach(period => {
                                    const monthKey = format(period, 'MMM yyyy');
                                    if (monthKey !== currentMonth) {
                                        monthGroups.push({ month: monthKey, count: 1 });
                                        currentMonth = monthKey;
                                    } else if (monthGroups.length > 0) {
                                        monthGroups[monthGroups.length - 1]!.count++;
                                    }
                                });
                                return monthGroups.map((group, idx) => (
                                    <div
                                        key={`${group.month}-${idx}`}
                                        className="shrink-0 p-1 text-center text-xs font-semibold text-gray-600 dark:text-gray-400 border-r border-gray-200 dark:border-gray-700 last:border-0"
                                        style={{ width: `${group.count * 48}px` }}
                                    >
                                        {group.month}
                                    </div>
                                ));
                            })()}
                        </div>
                    )}

                    {/* Date Header */}
                    <div className="flex border-b border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50">
                        {/* Member Name Column Header */}
                        <div className="sticky left-0 w-48 shrink-0 p-3 text-xs font-semibold text-gray-500 uppercase tracking-wider bg-gray-50 dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800 z-10">
                            Team Member
                        </div>
                        {/* Periods Header */}
                        {periods.map(period => {
                            const isWknd = viewMode === 'day' && isWeekend(period);
                            const isCurrent = (viewMode === 'day' && isToday(period)) ||
                                (viewMode === 'week' && isSameWeek(period, new Date(), { weekStartsOn: 1 })) ||
                                (viewMode === 'month' && isSameMonth(period, new Date()));
                            return (
                                <div
                                    key={period.toISOString()}
                                    className={cn(
                                        "shrink-0 p-2 text-center text-xs border-r border-gray-100 dark:border-gray-800 last:border-0",
                                        viewMode === 'day' ? "w-12" : viewMode === 'week' ? "w-24" : "w-32",
                                        isWknd ? "bg-slate-200/80 dark:bg-slate-800/60" : "",
                                        isCurrent && !isWknd ? "bg-indigo-50/50 dark:bg-indigo-900/20" : ""
                                    )}
                                >
                                    <div className={cn("font-medium", "text-gray-700 dark:text-gray-300")}>
                                        {viewMode === 'day' && format(period, 'd')}
                                        {viewMode === 'week' && `W${format(period, 'w')}`}
                                        {viewMode === 'month' && format(period, 'MMM')}
                                    </div>
                                    <div className={cn(
                                        "text-[10px] uppercase",
                                        isWknd ? "text-slate-500 dark:text-slate-400" : "text-gray-400"
                                    )}>
                                        {viewMode === 'day' && format(period, 'EEEEE')}
                                        {viewMode === 'week' && format(period, 'MMM d')}
                                        {viewMode === 'month' && format(period, 'yyyy')}
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* Rows */}
                    <div className="divide-y divide-gray-100 dark:divide-gray-800">
                        {members.map(member => (
                            <div key={member.id} className="flex hover:bg-gray-50/50 dark:hover:bg-gray-900/30 transition-colors group">
                                {/* Member Name */}
                                <div className="sticky left-0 w-48 shrink-0 p-3 flex items-center gap-2 bg-white dark:bg-sidebar group-hover:bg-gray-50 dark:group-hover:bg-sidebar border-r border-border z-20">
                                    <div className="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-medium">
                                        {member.name.charAt(0)}
                                    </div>
                                    <span className="text-sm font-medium text-foreground truncate" title={member.name}>
                                        {member.name}
                                    </span>
                                </div>

                                {/* Period Cells */}
                                <TooltipProvider delayDuration={0}>
                                    {periods.map(period => {
                                        const dateKey = `${member.id}_${getPeriodKey(period)}`;
                                        const hours = worklogMap.hoursMap.get(dateKey) || 0;
                                        const taskBreakdown = worklogMap.taskBreakdownMap.get(dateKey) || [];
                                        const target = getTargetHours(member.id, period);
                                        const isWknd = viewMode === 'day' && isWeekend(period);
                                        const isHolidayDay = viewMode === 'day' && isHoliday(period);
                                        const isVacationDay = viewMode === 'day' && isVacation(member.id, period);
                                        const isNonWorkingDay = isWknd || isHolidayDay || isVacationDay;
                                        const percentage = target > 0 ? Math.min((hours / target) * 100, 100) : 0;

                                        // SVG circle params
                                        const size = viewMode === 'day' ? 36 : viewMode === 'week' ? 44 : 52;
                                        const strokeWidth = viewMode === 'day' ? 4 : 5;
                                        const radius = (size - strokeWidth) / 2;
                                        const circumference = 2 * Math.PI * radius;
                                        const strokeDashoffset = circumference - (percentage / 100) * circumference;

                                        // Color based on percentage
                                        const getStrokeColor = () => {
                                            if (hours === 0) return 'stroke-transparent';
                                            if (percentage > 105) return 'stroke-red-500';
                                            if (percentage >= 90) return 'stroke-emerald-500';
                                            return 'stroke-amber-400';
                                        };

                                        // Check if member is allocated (has non-zero target)
                                        // For day view: weekends should only show if within an active period
                                        const memberPeriodsList = activePeriods[member.id];
                                        const hasActivePeriod = memberPeriodsList && memberPeriodsList.length > 0;



                                        // Check if this day falls within any active period (including weekends)
                                        const isWithinAnyActivePeriod = hasActivePeriod && memberPeriodsList.some(p => {
                                            if (!p.range.from) return false;
                                            // Ensure dates are Date objects (might be strings from localStorage)
                                            const fromDate = p.range.from instanceof Date ? p.range.from : new Date(p.range.from as string);
                                            const toDate = p.range.to
                                                ? (p.range.to instanceof Date ? p.range.to : new Date(p.range.to as string))
                                                : fromDate;

                                            const result = isWithinInterval(period, {
                                                start: startOfDay(fromDate),
                                                end: endOfDay(toDate)
                                            });



                                            return result;
                                        });

                                        // Member is allocated if:
                                        // 1. No active periods defined (default to showing all)
                                        // 2. Has active periods AND this day is within one of them
                                        const isAllocated = hasActivePeriod ? isWithinAnyActivePeriod : true;



                                        return (
                                            <div
                                                key={period.toISOString()}
                                                className={cn(
                                                    "shrink-0 flex items-center justify-center border-r border-gray-100 dark:border-gray-800 last:border-0 relative",
                                                    viewMode === 'day' ? "w-12 h-12" : viewMode === 'week' ? "w-24 h-16" : "w-32 h-16",
                                                    isWknd && "bg-slate-200/80 dark:bg-slate-800/60",
                                                    isHolidayDay && "bg-amber-100/50 dark:bg-amber-900/30",
                                                    isVacationDay && "bg-emerald-100/50 dark:bg-emerald-900/30"
                                                )}
                                            >
                                                {isAllocated && (
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <div className={cn(
                                                                "relative flex items-center justify-center cursor-pointer",
                                                                isWknd && "opacity-40"
                                                            )}>
                                                                {/* Show icons for holidays/vacations, chart for work days */}
                                                                {isHolidayDay ? (
                                                                    /* Holiday Icon */
                                                                    <div className="flex items-center justify-center w-9 h-9 rounded-full bg-amber-100 dark:bg-amber-900/50 border-2 border-amber-300 dark:border-amber-600">
                                                                        <span className="text-lg">🎉</span>
                                                                    </div>
                                                                ) : isVacationDay ? (
                                                                    /* Vacation Icon */
                                                                    <div className="flex items-center justify-center w-9 h-9 rounded-full bg-emerald-100 dark:bg-emerald-900/50 border-2 border-emerald-300 dark:border-emerald-600">
                                                                        <span className="text-lg">🏖️</span>
                                                                    </div>
                                                                ) : (
                                                                    /* Regular Work Day - Pie Wedge Chart */
                                                                    (() => {
                                                                        const pct = target > 0 ? (hours / target) * 100 : 0;
                                                                        let glowColorClass = "";

                                                                        if (hours > target && Math.abs(hours - target) > 0.1) {
                                                                            // Over-logged: Brighter Emerald Glow
                                                                            glowColorClass = "bg-emerald-300 dark:bg-emerald-400";
                                                                        } else if (pct >= 0 && pct < 50 && !isWknd) {
                                                                            // Severe Under: Red Glow (Exclude Weekends)
                                                                            glowColorClass = "bg-red-400 dark:bg-red-500";
                                                                        } else if (pct >= 50 && pct < 90) {
                                                                            // Moderate Under: Amber Glow
                                                                            glowColorClass = "bg-amber-300 dark:bg-amber-400";
                                                                        }

                                                                        return (
                                                                            <div className="relative flex items-center justify-center">
                                                                                {/* Backdrop Glow Layer */}
                                                                                {glowColorClass && (
                                                                                    <div className={cn(
                                                                                        "absolute inset-1 rounded-full blur-sm animate-pulse",
                                                                                        glowColorClass
                                                                                    )} />
                                                                                )}

                                                                                {/* Chart Layer (Solid) */}
                                                                                <div className="relative z-10">
                                                                                    <DailyWorklogChart
                                                                                        hours={hours}
                                                                                        target={target}
                                                                                        size={size}
                                                                                        strokeWidth={strokeWidth}
                                                                                        isWeekend={isWknd}
                                                                                        showText={true}
                                                                                    />
                                                                                </div>
                                                                            </div>
                                                                        );
                                                                    })()
                                                                )}
                                                            </div>
                                                        </TooltipTrigger>
                                                        <TooltipContent side="top" className="text-xs max-w-[280px]">
                                                            <div className="font-semibold mb-1 border-b pb-1">
                                                                {viewMode === 'day' && format(period, 'MMM d, yyyy')}
                                                                {viewMode === 'week' && `Week of ${format(period, 'MMM d')}`}
                                                                {viewMode === 'month' && format(period, 'MMMM yyyy')}
                                                            </div>
                                                            {isHolidayDay ? (
                                                                <div className="text-amber-600 dark:text-amber-400">🎉 Holiday</div>
                                                            ) : isVacationDay ? (
                                                                <div className="text-emerald-600 dark:text-emerald-400">🏖️ Vacation</div>
                                                            ) : (
                                                                <div className="space-y-2">
                                                                    {taskBreakdown.length > 0 ? (
                                                                        <>
                                                                            {/* Group tasks by project */}
                                                                            {Object.entries(
                                                                                taskBreakdown.reduce((acc, task) => {
                                                                                    const project = task.projectName || 'Unknown Project';
                                                                                    if (!acc[project]) acc[project] = [];
                                                                                    acc[project].push(task);
                                                                                    return acc;
                                                                                }, {} as Record<string, typeof taskBreakdown>)
                                                                            ).map(([projectName, projectTasks]) => (
                                                                                <div key={projectName} className="space-y-1">
                                                                                    <div className="text-[10px] opacity-70 font-medium truncate" title={projectName}>
                                                                                        📁 {projectName}
                                                                                    </div>
                                                                                    {projectTasks.sort((a, b) => b.hours - a.hours).slice(0, 5).map((task) => (
                                                                                        <div key={task.taskId} className="flex items-start gap-2 pl-2">
                                                                                            <div className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 bg-indigo-400" />
                                                                                            <div className="flex-1 min-w-0 flex justify-between items-baseline gap-2">
                                                                                                <span className="font-medium truncate" title={task.taskName}>
                                                                                                    {task.taskName}
                                                                                                </span>
                                                                                                <span className="text-[11px] opacity-80 shrink-0">
                                                                                                    {task.hours.toFixed(1)}h
                                                                                                </span>
                                                                                            </div>
                                                                                        </div>
                                                                                    ))}
                                                                                </div>
                                                                            ))}
                                                                        </>
                                                                    ) : (
                                                                        <div>{member.name}: {hours.toFixed(2)} hours</div>
                                                                    )}
                                                                    <div className="pt-1 mt-1 border-t border-gray-500/20 flex justify-between font-bold">
                                                                        <span>Total</span>
                                                                        <span>{hours.toFixed(1)}h / {target}h ({percentage.toFixed(0)}%)</span>
                                                                    </div>
                                                                </div>
                                                            )}
                                                        </TooltipContent>
                                                    </Tooltip>
                                                )}
                                            </div>
                                        );
                                    })}
                                </TooltipProvider>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
