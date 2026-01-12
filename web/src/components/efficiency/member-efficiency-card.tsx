'use client';

import { useMemo, useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { type PMUser } from '~/core/api/pm/users';
import { type PMTimeEntry } from '~/core/api/pm/time-entries';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip as RechartsTooltip } from "recharts";
import { DailyWorkloadCalendar } from './daily-workload-calendar';
import { useCardGlow } from '~/core/hooks/use-theme-colors';
import { type MemberPeriod } from './member-duration-manager';
import { addMonths, subMonths, startOfMonth, endOfMonth, format, parseISO, isSameMonth, isSameYear, startOfDay, endOfDay, isWithinInterval } from 'date-fns';
import { ChevronLeft, ChevronRight } from "lucide-react";

interface MemberEfficiencyCardProps {
    member: PMUser;
    timeEntries: PMTimeEntry[];
    dateRange: { from: Date; to: Date };
    activityColors: string[];
    activePeriods?: MemberPeriod[];
}

export function MemberEfficiencyCard({ member, timeEntries, dateRange, activityColors, activePeriods }: MemberEfficiencyCardProps) {
    const cardGlow = useCardGlow();
    // currentMonth represents the START of the 2-month window
    const [currentMonth, setCurrentMonth] = useState<Date>(() => startOfMonth(dateRange.from));

    // Update current month if global date range changes significantly
    useEffect(() => {
        if (dateRange.from && !isSameMonth(currentMonth, dateRange.from)) {
            setCurrentMonth(startOfMonth(dateRange.from));
        }
        // eslint-disable-next-line
    }, [dateRange.from]);

    const handlePrevMonth = () => setCurrentMonth(prev => subMonths(prev, 1));
    const handleNextMonth = () => setCurrentMonth(prev => addMonths(prev, 1));

    // Define the two months to display
    const firstMonthDate = startOfMonth(currentMonth);
    const secondMonthDate = startOfMonth(addMonths(currentMonth, 1));

    // 1. STATS ENTRIES: Filter for Global Date Range (for Total Hours & Pie Chart)
    const statsEntries = useMemo(() => {
        // Safety check for dateRange
        if (!dateRange.from || !dateRange.to) return [];

        return timeEntries.filter(e => {
            if (e.user_id !== member.id) return false;
            // Filter by Global Range
            if (e.date && (parseISO(e.date) < dateRange.from || parseISO(e.date) > dateRange.to)) return false;

            // Check active periods
            if (activePeriods && activePeriods.length > 0) {
                const entryDate = parseISO(e.date);
                const isActive = activePeriods.some(p => {
                    if (!p.range.from) return false;
                    const start = startOfDay(new Date(p.range.from));
                    // Handle ongoing periods
                    const end = p.range.to
                        ? endOfDay(new Date(p.range.to))
                        : new Date(8640000000000000);

                    return isWithinInterval(entryDate, { start, end });
                });
                if (!isActive) return false;
            }
            return true;
        });
    }, [timeEntries, member.id, dateRange, activePeriods]);

    const totalHours = statsEntries.reduce((acc, curr) => acc + curr.hours, 0);

    // Aggregate for Main Pie Chart (Uses statsEntries - Global context)
    const activityData = useMemo(() => {
        const activityMap: Record<string, number> = {};

        statsEntries.forEach((entry) => {
            const activityName = entry.activity_type || "Unknown";
            activityMap[activityName] = (activityMap[activityName] || 0) + entry.hours;
        });

        return Object.entries(activityMap)
            .map(([name, hours], index) => ({
                name,
                hours,
                percentage: totalHours > 0 ? ((hours / totalHours) * 100).toFixed(1) : "0",
                color: activityColors[index % activityColors.length],
            }))
            .sort((a, b) => b.hours - a.hours);
    }, [statsEntries, activityColors, totalHours]);


    // 2. CALENDAR ENTRIES: Filter for Local 2-Month Window (for DailyWorkloadCalendar)
    const calendarVisibleEntries = useMemo(() => {
        const windowStart = startOfMonth(currentMonth);
        const windowEnd = endOfMonth(addMonths(currentMonth, 1));

        return timeEntries.filter(e => {
            if (e.user_id !== member.id) return false;
            if (!e.date) return false;
            const entryDate = parseISO(e.date);

            // Window bounds
            if (entryDate < windowStart || entryDate > windowEnd) return false;

            // Active periods check (reuse same logic)
            if (activePeriods && activePeriods.length > 0) {
                const isActive = activePeriods.some(p => {
                    if (!p.range.from) return false;
                    const start = startOfDay(new Date(p.range.from));
                    const end = p.range.to
                        ? endOfDay(new Date(p.range.to))
                        : new Date(8640000000000000);
                    return isWithinInterval(entryDate, { start, end });
                });
                if (!isActive) return false;
            }
            return true;
        });
    }, [timeEntries, member.id, currentMonth, activePeriods]);

    // Helper to format the range text (e.g. "Oct - Nov 2025" or "Dec 2025 - Jan 2026")
    const rangeLabel = useMemo(() => {
        if (isSameYear(firstMonthDate, secondMonthDate)) {
            return `${format(firstMonthDate, 'MMM')} - ${format(secondMonthDate, 'MMM yyyy')}`;
        }
        return `${format(firstMonthDate, 'MMM yyyy')} - ${format(secondMonthDate, 'MMM yyyy')}`;
    }, [firstMonthDate, secondMonthDate]);

    return (
        <Card className={cardGlow.className}>
            <CardHeader className="pb-2 pt-4 px-4 border-b border-border/50">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-sm">
                            {member.name.charAt(0)}
                        </div>
                        <div>
                            <CardTitle className="text-base leading-none">{member.name}</CardTitle>
                            <CardDescription className="text-xs mt-1">
                                {member.email}
                            </CardDescription>
                        </div>
                    </div>

                    {/* Month Navigation Controls - Compact */}
                    <div className="flex items-center gap-1 bg-background/50 p-0.5 rounded-md border text-xs">
                        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handlePrevMonth}>
                            <ChevronLeft className="h-3 w-3" />
                        </Button>
                        <div className="min-w-[140px] text-center font-medium px-2">
                            {rangeLabel}
                        </div>
                        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleNextMonth}>
                            <ChevronRight className="h-3 w-3" />
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="p-4">
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">

                    {/* LEFT COLUMN: Aggregate Pie Chart (Reduced Width) */}
                    <div className="lg:col-span-4 flex flex-col min-h-[180px] border-r border-border/50 pr-4">
                        <div className="flex items-center justify-between mb-2">
                            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                                Distribution
                            </h4>
                            <span className="text-xs font-bold">{totalHours.toFixed(1)}h Total</span>
                        </div>

                        {activityData.length > 0 ? (
                            <div className="flex flex-col sm:flex-row items-center gap-4 h-full pt-2">
                                {/* Chart - Responsive with aspect ratio */}
                                <div className="relative w-full sm:w-[45%] aspect-square shrink-0">
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
                                            <RechartsTooltip
                                                contentStyle={{
                                                    backgroundColor: "var(--card)",
                                                    borderColor: "var(--border)",
                                                    borderRadius: "8px",
                                                    color: "var(--foreground)",
                                                    fontSize: "12px",
                                                    padding: "8px"
                                                }}
                                                itemStyle={{ color: "var(--foreground)" }}
                                                formatter={(value, name) => [`${Number(value).toFixed(1)}h`, name]}
                                            />
                                        </PieChart>
                                    </ResponsiveContainer>
                                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                                        <span className="text-xl font-bold">{totalHours.toFixed(0)}</span>
                                        <span className="text-[10px] text-muted-foreground uppercase">Hours</span>
                                    </div>
                                </div>

                                {/* Compact Legend - Takes remaining space */}
                                <div className="flex-1 w-full space-y-1.5 py-1 max-h-[200px] overflow-y-auto custom-scrollbar">
                                    {activityData.map((item) => (
                                        <div key={item.name} className="flex items-center justify-between text-xs group">
                                            <div className="flex items-center gap-2 overflow-hidden flex-1">
                                                <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                                                <span className="text-foreground/90 font-medium truncate group-hover:text-primary transition-colors" title={item.name}>{item.name}</span>
                                            </div>
                                            <div className="flex items-center gap-2 shrink-0">
                                                <span className="text-muted-foreground text-[10px] font-mono">{Number(item.hours).toFixed(1)}h</span>
                                                <span className="font-bold text-[10px] min-w-[32px] text-right">{item.percentage}%</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ) : (
                            <div className="flex-1 flex items-center justify-center text-muted-foreground text-xs italic">
                                No data
                            </div>
                        )}
                    </div>

                    {/* RIGHT COLUMN: 2-Month Daily Calendar Grid */}
                    <div className="lg:col-span-8">
                        <div className="grid grid-cols-2 gap-4">
                            {/* Month 1 */}
                            <div>
                                <div className="mb-2 text-xs font-semibold text-center text-muted-foreground border-b border-border/50 pb-1">
                                    {format(firstMonthDate, 'MMMM yyyy')}
                                </div>
                                <DailyWorkloadCalendar
                                    dateRange={{ from: startOfMonth(firstMonthDate), to: endOfMonth(firstMonthDate) }}
                                    timeEntries={calendarVisibleEntries} // Pass local window entries
                                    activityColors={activityColors}
                                    activePeriods={activePeriods}
                                />
                            </div>

                            {/* Month 2 */}
                            <div>
                                <div className="mb-2 text-xs font-semibold text-center text-muted-foreground border-b border-border/50 pb-1">
                                    {format(secondMonthDate, 'MMMM yyyy')}
                                </div>
                                <DailyWorkloadCalendar
                                    dateRange={{ from: startOfMonth(secondMonthDate), to: endOfMonth(secondMonthDate) }}
                                    timeEntries={calendarVisibleEntries}
                                    activityColors={activityColors}
                                    activePeriods={activePeriods}
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card >
    );
}
