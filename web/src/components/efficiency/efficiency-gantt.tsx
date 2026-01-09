import { useMemo } from 'react';
import { format, eachDayOfInterval, eachWeekOfInterval, eachMonthOfInterval, startOfWeek, endOfWeek, startOfMonth, endOfMonth, isSameDay, isToday, isWeekend, isSameMonth, isSameWeek, differenceInBusinessDays } from 'date-fns';
import { cn } from '~/lib/utils';
import { type PMUser } from '~/core/api/pm/users';
import { type PMTimeEntry } from '~/core/api/pm/time-entries';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "~/components/ui/tooltip";

interface EfficiencyGanttProps {
    members: PMUser[];
    timeEntries: PMTimeEntry[];
    startDate: Date;
    endDate: Date;
    isLoading: boolean;
    viewMode: 'day' | 'week' | 'month';
}

export function EfficiencyGantt({ members, timeEntries, startDate, endDate, isLoading, viewMode }: EfficiencyGanttProps) {

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

    // 3. Helper: Get Target Hours for a Period (Business Days * 8)
    const getTargetHours = (periodStart: Date) => {
        let periodEnd;
        switch (viewMode) {
            case 'week':
                periodEnd = endOfWeek(periodStart, { weekStartsOn: 1 });
                break;
            case 'month':
                periodEnd = endOfMonth(periodStart);
                break;
            case 'day':
            default:
                return 8; // Constant target for day
        }

        // Return business days * 8
        // Note: differenceInBusinessDays returns days between, excluding weekends. +1 for inclusive start.
        // But we must handle partial periods if startDate/endDate clip the period?
        // For simplicity in this Gantt, let's assume standard Capacity for the full period column.
        // Or strictly strictly: filter weekends in range.
        const start = periodStart < startDate ? startDate : periodStart;
        const end = periodEnd > endDate ? endDate : periodEnd;

        // Use simple calc for full periods to match standard expectations (40h week, ~176h month)
        // If we clamp to user selection, the cells at edges might start partial.
        // Let's use the full period capacity for the visualization target to encourage full week work?
        // No, better to use standard constant for "Standard Week" = 40h.

        if (viewMode === 'week') return 40;

        if (viewMode === 'month') {
            // Exact business days in month
            const days = eachDayOfInterval({ start: periodStart, end: periodEnd });
            const businessDays = days.filter(d => !isWeekend(d)).length;
            return businessDays * 8;
        }

        return 8;
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
                                        const target = getTargetHours(period);
                                        const isWknd = viewMode === 'day' && isWeekend(period);

                                        return (
                                            <div
                                                key={period.toISOString()}
                                                className={cn(
                                                    "shrink-0 flex items-center justify-center border-r border-gray-100 dark:border-gray-800 last:border-0 relative p-1",
                                                    viewMode === 'day' ? "w-12" : viewMode === 'week' ? "w-24" : "w-32",
                                                    isWknd ? "bg-slate-200/80 dark:bg-slate-800/60" : ""
                                                )}
                                            >
                                                {hours > 0 && (
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <div className="w-full h-full relative flex items-center justify-start bg-gray-100 dark:bg-gray-800 rounded overflow-hidden">
                                                                {/* Progress Bar */}
                                                                <div
                                                                    className={cn(
                                                                        "h-full transition-all duration-300",
                                                                        getStatusColor(hours, target)
                                                                    )}
                                                                    style={{ width: `${Math.min((hours / target) * 100, 100)}%` }}
                                                                />

                                                                {/* Hours Overlay */}
                                                                <span className="absolute inset-0 flex items-center justify-center text-[10px] font-medium text-gray-700 dark:text-gray-300">
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
                                                                Target: {target}h ({((hours / target) * 100).toFixed(0)}%)
                                                            </div>
                                                        </TooltipContent>
                                                    </Tooltip>
                                                )}
                                                {hours === 0 && ((viewMode === 'day' && isToday(period)) || (viewMode === 'week' && isSameWeek(period, new Date(), { weekStartsOn: 1 })) || (viewMode === 'month' && isSameMonth(period, new Date()))) && (
                                                    <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
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
