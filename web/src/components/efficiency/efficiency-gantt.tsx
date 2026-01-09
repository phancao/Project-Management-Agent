import { useMemo } from 'react';
import { format, eachDayOfInterval, eachWeekOfInterval, eachMonthOfInterval, startOfWeek, endOfWeek, startOfMonth, endOfMonth, isSameDay, isToday, isWeekend, isSameMonth, isSameWeek, differenceInBusinessDays, isWithinInterval, startOfDay, endOfDay } from 'date-fns';
import { cn } from '~/lib/utils';
import { type PMUser } from '~/core/api/pm/users';
import { type PMTimeEntry } from '~/core/api/pm/time-entries';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "~/components/ui/tooltip";
import { type MemberPeriod, type Holiday } from './member-duration-manager';

interface EfficiencyGanttProps {
    members: PMUser[];
    timeEntries: PMTimeEntry[];
    startDate: Date;
    endDate: Date;
    isLoading: boolean;
    viewMode: 'day' | 'week' | 'month';
    activePeriods?: Record<string, MemberPeriod[]>;
    holidays?: Holiday[];
}

export function EfficiencyGantt({ members, timeEntries, startDate, endDate, isLoading, viewMode, activePeriods = {}, holidays = [] }: EfficiencyGanttProps) {

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
        return holidays.some(h => isSameDay(h.date, day));
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


    // 4. Aggregate hours per member per period
    const worklogMap = useMemo(() => {
        const map = new Map<string, number>();
        timeEntries.forEach(entry => {
            if (!entry.date) return;
            const entryDate = new Date(entry.date); // parseISO handled by new Date usually or explicit parse
            // Using split for performance on ISO strings if available, but date-fns parse safe
            // Let's just use string split if 'day', else parse

            const keyDate = new Date(entry.date);
            const periodKey = getPeriodKey(keyDate);
            const key = `${entry.user_id}_${periodKey}`;

            const existing = map.get(key) || 0;
            map.set(key, existing + entry.hours);
        });
        return map;
    }, [timeEntries, viewMode]);

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
                                <div className="sticky left-0 w-48 shrink-0 p-3 flex items-center gap-2 bg-white dark:bg-gray-950 group-hover:bg-gray-100 dark:group-hover:bg-gray-900 border-r border-gray-100 dark:border-gray-800 z-10">
                                    <div className="w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-xs font-medium">
                                        {member.name.charAt(0)}
                                    </div>
                                    <span className="text-sm font-medium text-gray-700 dark:text-gray-200 truncate" title={member.name}>
                                        {member.name}
                                    </span>
                                </div>

                                {/* Period Cells */}
                                <TooltipProvider delayDuration={0}>
                                    {periods.map(period => {
                                        const dateKey = `${member.id}_${getPeriodKey(period)}`;
                                        const hours = worklogMap.get(dateKey) || 0;
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
                                        // For day view: also check for active periods if not a non-working day
                                        const memberPeriodsList = activePeriods[member.id];
                                        const hasActivePeriod = memberPeriodsList && memberPeriodsList.length > 0;
                                        const isAllocated = hasActivePeriod ? target > 0 || isNonWorkingDay : true;

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
                                                                isNonWorkingDay && "opacity-30"
                                                            )}>
                                                                {/* Pie Wedge Chart - hours out of 8 */}
                                                                <svg width={size} height={size} className="transform -rotate-90">
                                                                    {/* Background circle (outline) */}
                                                                    <circle
                                                                        cx={size / 2}
                                                                        cy={size / 2}
                                                                        r={radius - 2}
                                                                        fill="none"
                                                                        strokeWidth={2}
                                                                        className="stroke-gray-300 dark:stroke-gray-600"
                                                                    />
                                                                    {/* Pie wedge for hours logged (out of 8h max) */}
                                                                    {hours > 0 && (() => {
                                                                        const hoursAngle = Math.min((hours / 8) * 360, 360);
                                                                        const startAngle = 0;
                                                                        const endAngle = hoursAngle;
                                                                        const largeArc = endAngle > 180 ? 1 : 0;
                                                                        const cx = size / 2;
                                                                        const cy = size / 2;
                                                                        const r = radius - 4;

                                                                        // Handle full circle case
                                                                        if (hours >= 8) {
                                                                            return (
                                                                                <circle
                                                                                    cx={cx}
                                                                                    cy={cy}
                                                                                    r={r}
                                                                                    className={cn(
                                                                                        "transition-all duration-500",
                                                                                        percentage > 105 ? "fill-red-500" : percentage >= 90 ? "fill-emerald-500" : "fill-amber-400"
                                                                                    )}
                                                                                />
                                                                            );
                                                                        }

                                                                        const x1 = cx;
                                                                        const y1 = cy - r;
                                                                        const x2 = cx + r * Math.sin((endAngle * Math.PI) / 180);
                                                                        const y2 = cy - r * Math.cos((endAngle * Math.PI) / 180);

                                                                        return (
                                                                            <path
                                                                                d={`M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`}
                                                                                className={cn(
                                                                                    "transition-all duration-500",
                                                                                    percentage > 105 ? "fill-red-500" : percentage >= 90 ? "fill-emerald-500" : "fill-amber-400"
                                                                                )}
                                                                            />
                                                                        );
                                                                    })()}
                                                                    {/* Clock tick marks (8 ticks for 8 hours) */}
                                                                    {[...Array(8)].map((_, i) => {
                                                                        const angle = (i / 8) * 360;
                                                                        const tickOuterRadius = size / 2 - 1;
                                                                        const tickInnerRadius = tickOuterRadius - 5;
                                                                        const x1 = size / 2 + tickInnerRadius * Math.cos((angle * Math.PI) / 180);
                                                                        const y1 = size / 2 + tickInnerRadius * Math.sin((angle * Math.PI) / 180);
                                                                        const x2 = size / 2 + tickOuterRadius * Math.cos((angle * Math.PI) / 180);
                                                                        const y2 = size / 2 + tickOuterRadius * Math.sin((angle * Math.PI) / 180);
                                                                        return (
                                                                            <line
                                                                                key={i}
                                                                                x1={x1}
                                                                                y1={y1}
                                                                                x2={x2}
                                                                                y2={y2}
                                                                                strokeWidth={1.5}
                                                                                className="stroke-gray-600 dark:stroke-gray-400"
                                                                            />
                                                                        );
                                                                    })}
                                                                </svg>
                                                                {/* Hours text in center */}
                                                                <span className={cn(
                                                                    "absolute inset-0 flex items-center justify-center text-[10px] font-bold",
                                                                    hours === 0 && !isNonWorkingDay ? "text-red-500" : "text-gray-700 dark:text-gray-200"
                                                                )}>
                                                                    {Number.isInteger(hours) ? hours : hours.toFixed(1)}
                                                                </span>
                                                            </div>
                                                        </TooltipTrigger>
                                                        <TooltipContent side="top" className="text-xs">
                                                            <div className="font-semibold mb-1">
                                                                {viewMode === 'day' && format(period, 'MMM d, yyyy')}
                                                                {viewMode === 'week' && `Week of ${format(period, 'MMM d')}`}
                                                                {viewMode === 'month' && format(period, 'MMMM yyyy')}
                                                            </div>
                                                            <div>{member.name}: {hours.toFixed(2)} hours</div>
                                                            <div className="text-gray-400 mt-1 capitalize">
                                                                Target: {target}h ({percentage.toFixed(0)}%)
                                                            </div>
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
