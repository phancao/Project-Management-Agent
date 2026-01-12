
'use client';

import { useMemo } from 'react';
import { format, eachDayOfInterval, isSameDay, isWeekend, isToday, startOfMonth, getDay, endOfMonth, isWithinInterval, startOfDay, endOfDay } from 'date-fns';
import { cn } from "~/lib/utils";
import { type PMTimeEntry } from '~/core/api/pm/time-entries';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "~/components/ui/tooltip";
import { DailyWorklogChart } from './daily-worklog-chart';
import { type MemberPeriod } from './member-duration-manager';

interface DailyWorkloadCalendarProps {
    dateRange: { from: Date; to: Date };
    timeEntries: PMTimeEntry[];
    activityColors: string[];
    activePeriods?: MemberPeriod[];
    overallDateRange?: { from: Date; to: Date };
}

function parseISO(date: string): Date {
    return new Date(date);
}

export function DailyWorkloadCalendar({ dateRange, timeEntries, activityColors, activePeriods, overallDateRange }: DailyWorkloadCalendarProps) {
    const days = useMemo(() => {
        if (!dateRange.from || !dateRange.to) return [];
        return eachDayOfInterval({ start: dateRange.from, end: dateRange.to });
    }, [dateRange]);

    // Calculate offset for the first day (Monday start)
    const startOffset = useMemo(() => {
        if (!dateRange.from) return 0;
        // getDay returns 0 for Sunday, 1 for Monday...
        // We want Monday (1) to be index 0.
        // So: Mon(1)->0, Tue(2)->1... Sun(0)->6
        const day = getDay(dateRange.from);
        return day === 0 ? 6 : day - 1;
    }, [dateRange.from]);

    // Pre-process daily data
    const dailyData = useMemo(() => {
        const map = new Map<string, { total: number; breakdown: { name: string, hours: number, color: string }[] }>();

        days.forEach(day => {
            const dayKey = format(day, 'yyyy-MM-dd');
            const dayEntries = timeEntries.filter(e => e.date && isSameDay(parseISO(e.date), day));
            const totalHours = dayEntries.reduce((sum, e) => sum + e.hours, 0);

            if (totalHours === 0) {
                map.set(dayKey, { total: 0, breakdown: [] });
                return;
            }

            // Group by activity for Tooltip
            const activityGroups: Record<string, number> = {};
            dayEntries.forEach(e => {
                const type = e.activity_type || "Unknown";
                activityGroups[type] = (activityGroups[type] || 0) + e.hours;
            });

            const breakdown = Object.entries(activityGroups).map(([name, hours], index) => ({
                name,
                hours,
                color: activityColors[index % activityColors.length] || '#ccc'
            }));

            map.set(dayKey, { total: totalHours, breakdown });
        });

        return map;
    }, [days, timeEntries, activityColors]);

    const weekDays = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];

    return (
        <div className="w-full">
            {/* Header Row */}
            <div className="grid grid-cols-7 mb-2">
                {weekDays.map((d, i) => (
                    <div key={i} className="text-center text-[10px] font-semibold text-muted-foreground">
                        {d}
                    </div>
                ))}
            </div>

            {/* Calendar Grid */}
            <div className="grid grid-cols-7 gap-1 text-center">
                {/* Empty Cells for Offset */}
                {[...Array(startOffset)].map((_, i) => (
                    <div key={`empty-${i}`} className="w-full max-w-[48px] mx-auto aspect-square" />
                ))}

                {/* Days */}
                <TooltipProvider delayDuration={0}>
                    {days.map(day => {
                        const dayKey = format(day, 'yyyy-MM-dd');
                        const data = dailyData.get(dayKey);
                        const isWknd = isWeekend(day);
                        const isTdy = isToday(day);
                        const totalHours = data?.total || 0;

                        // Check if day is within active periods
                        let isActive = true;

                        // 1. Check member specific active periods
                        if (activePeriods && activePeriods.length > 0) {
                            isActive = activePeriods.some(p => {
                                if (!p.range.from) return false;
                                const start = startOfDay(new Date(p.range.from));
                                // Handle ongoing periods (no end date) -> Set to far future
                                const end = p.range.to
                                    ? endOfDay(new Date(p.range.to))
                                    : new Date(8640000000000000); // Max safe integer date

                                const inside = isWithinInterval(day, { start, end });
                                return inside;
                            });
                        }

                        // 2. Check global date range limit
                        if (isActive && overallDateRange) {
                            if (!isWithinInterval(day, { start: startOfDay(overallDateRange.from), end: endOfDay(overallDateRange.to) })) {
                                isActive = false;
                            }
                        }

                        return (
                            <div
                                key={dayKey}
                                className={cn(
                                    "relative w-full max-w-[48px] mx-auto aspect-square flex flex-col items-center justify-center rounded-md border text-xs transition-colors",
                                    isWknd ? "bg-gray-50/50 dark:bg-gray-900/20 border-gray-100 dark:border-gray-800" : "bg-card border-border",
                                    isTdy && "ring-1 ring-primary ring-offset-1 border-primary/50",
                                    !isActive && "opacity-40 bg-gray-50 dark:bg-gray-900/10 border-dashed"
                                )}
                            >
                                {/* Date Label */}
                                <div className={cn(
                                    "absolute top-0.5 left-1 text-[10px] font-medium leading-none",
                                    isWknd || !isActive ? "text-gray-400" : "text-gray-500"
                                )}>
                                    {format(day, 'd')}
                                </div>

                                {/* Chart - Centered (Only if Active) */}
                                {isActive && (
                                    <Tooltip>
                                        <TooltipTrigger asChild>
                                            <div className="mt-2 cursor-pointer hover:scale-105 transition-transform">
                                                {(() => {
                                                    const hours = totalHours;
                                                    const target = 8; // Default to 8h standard
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
                                                                    hours={totalHours}
                                                                    size={28}
                                                                    strokeWidth={3}
                                                                    isWeekend={isWknd}
                                                                    showText={true}
                                                                />
                                                            </div>
                                                        </div>
                                                    );
                                                })()}
                                            </div>
                                        </TooltipTrigger>
                                        <TooltipContent className="text-xs z-50">
                                            <div className="font-semibold mb-1 border-b pb-1">{format(day, 'EEE, MMM d')}</div>
                                            <div className="space-y-1">
                                                {data && data.breakdown.length > 0 ? (
                                                    <>
                                                        {data.breakdown.map((item, i) => (
                                                            <div key={i} className="flex items-center gap-2">
                                                                <div className="w-2 h-2 rounded-full" style={{ background: item.color }} />
                                                                <span>{item.name}: {item.hours.toFixed(1)}h</span>
                                                            </div>
                                                        ))}
                                                        <div className="pt-1 mt-1 border-t border-gray-500/20 flex justify-between font-bold">
                                                            <span>Total</span>
                                                            <span>{data.total.toFixed(1)}h</span>
                                                        </div>
                                                    </>
                                                ) : (
                                                    <span className="text-gray-400 italic">No activity logged</span>
                                                )}
                                            </div>
                                        </TooltipContent>
                                    </Tooltip>
                                )}
                            </div>
                        );
                    })}
                </TooltipProvider>
            </div>
        </div>
    );
}
