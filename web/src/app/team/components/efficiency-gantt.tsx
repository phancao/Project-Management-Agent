import { useMemo } from 'react';
import { format, eachDayOfInterval, isSameDay, isToday, isWeekend } from 'date-fns';
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
}

export function EfficiencyGantt({ members, timeEntries, startDate, endDate, isLoading }: EfficiencyGanttProps) {
    const days = useMemo(() => {
        return eachDayOfInterval({ start: startDate, end: endDate });
    }, [startDate, endDate]);

    // Aggregate hours per member per day
    const worklogMap = useMemo(() => {
        const map = new Map<string, number>();
        timeEntries.forEach(entry => {
            if (!entry.date) return;
            // Ensure date string consistency (YYYY-MM-DD)
            const dateStr = entry.date.split('T')[0];
            const key = `${entry.user_id}_${dateStr}`;
            const existing = map.get(key) || 0;
            map.set(key, existing + entry.hours);
        });
        return map;
    }, [timeEntries]);

    // Helper to get color status
    const getStatusColor = (hours: number) => {
        if (hours === 0) return 'bg-transparent';
        if (hours > 8.1) return 'bg-red-500 text-red-100'; // Overworked
        if (hours >= 7.5 && hours <= 8.1) return 'bg-emerald-500 text-emerald-100'; // Good
        return 'bg-amber-400 text-amber-900'; // Underworked
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
                    {/* Header */}
                    <div className="flex border-b border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50">
                        {/* Member Name Column Header */}
                        <div className="sticky left-0 w-48 shrink-0 p-3 text-xs font-semibold text-gray-500 uppercase tracking-wider bg-gray-50 dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800 z-10">
                            Team Member
                        </div>
                        {/* Days Header */}
                        {days.map(day => (
                            <div
                                key={day.toISOString()}
                                className={cn(
                                    "w-12 shrink-0 p-2 text-center text-xs border-r border-gray-100 dark:border-gray-800 last:border-0",
                                    isWeekend(day) ? "bg-gray-50 dark:bg-gray-900/50" : "",
                                    isToday(day) ? "bg-indigo-50/50 dark:bg-indigo-900/20" : ""
                                )}
                            >
                                <div className={cn("font-medium", isToday(day) ? "text-indigo-600 dark:text-indigo-400" : "text-gray-700 dark:text-gray-300")}>
                                    {format(day, 'd')}
                                </div>
                                <div className="text-[10px] text-gray-400 uppercase">
                                    {format(day, 'EEEEE')}
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Rows */}
                    <div className="divide-y divide-gray-100 dark:divide-gray-800">
                        {members.map(member => (
                            <div key={member.id} className="flex hover:bg-gray-50/50 dark:hover:bg-gray-900/30 transition-colors group">
                                {/* Member Name */}
                                <div className="sticky left-0 w-48 shrink-0 p-3 flex items-center gap-2 bg-white dark:bg-gray-950 group-hover:bg-gray-50 dark:group-hover:bg-gray-900/30 border-r border-gray-100 dark:border-gray-800 z-10">
                                    <div className="w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-xs font-medium">
                                        {member.name.charAt(0)}
                                    </div>
                                    <span className="text-sm font-medium text-gray-700 dark:text-gray-200 truncate" title={member.name}>
                                        {member.name}
                                    </span>
                                </div>

                                {/* Day Cells */}
                                <TooltipProvider delayDuration={0}>
                                    {days.map(day => {
                                        const dateKey = `${member.id}_${format(day, 'yyyy-MM-dd')}`;
                                        const hours = worklogMap.get(dateKey) || 0;
                                        const isWknd = isWeekend(day);

                                        return (
                                            <div
                                                key={day.toISOString()}
                                                className={cn(
                                                    "w-12 shrink-0 flex items-center justify-center border-r border-gray-100 dark:border-gray-800 last:border-0 relative",
                                                    isWknd ? "bg-gray-50/50 dark:bg-gray-900/20" : ""
                                                )}
                                            >
                                                {hours > 0 && (
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <div
                                                                className={cn(
                                                                    "w-full h-full flex items-center justify-center text-[10px] font-bold cursor-help transition-all",
                                                                    getStatusColor(hours)
                                                                )}
                                                            >
                                                                {Number.isInteger(hours) ? hours : hours.toFixed(1)}
                                                            </div>
                                                        </TooltipTrigger>
                                                        <TooltipContent side="top" className="text-xs">
                                                            <div className="font-semibold mb-1">{format(day, 'MMM d, yyyy')}</div>
                                                            <div>{member.name}: {hours.toFixed(2)} hours</div>
                                                            <div className="text-gray-400 mt-1 capitalize">
                                                                {hours > 8 ? 'Overloaded' : hours >= 7.5 ? 'Full Day' : 'Partial'}
                                                            </div>
                                                        </TooltipContent>
                                                    </Tooltip>
                                                )}
                                                {hours === 0 && isToday(day) && (
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
