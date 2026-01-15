'use client';

import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "~/components/ui/card";
import { type PMUser } from '~/core/api/pm/users';
import { type PMTimeEntry } from '~/core/api/pm/time-entries';
import { type PMTask } from '~/core/api/pm/tasks';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip as RechartsTooltip } from "recharts";
import { useCardGlow } from '~/core/hooks/use-theme-colors';
import { type MemberPeriod } from './member-duration-manager';
import { eachDayOfInterval, format, parseISO, startOfDay, endOfDay, isWithinInterval, isWeekend, isSameDay } from 'date-fns';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "~/components/ui/tooltip";
import { DailyWorklogChart } from './daily-worklog-chart';
import { cn } from "~/lib/utils";
import { ExternalLink } from 'lucide-react';

interface MemberEfficiencyCardProps {
    member: PMUser;
    timeEntries: PMTimeEntry[];
    tasks?: PMTask[];  // Tasks for looking up task names
    dateRange: { from: Date; to: Date };
    activityColors: string[];
    activePeriods?: MemberPeriod[];
    isLoading?: boolean;
}

export function MemberEfficiencyCard({ member, timeEntries, tasks = [], dateRange, activityColors, activePeriods, isLoading }: MemberEfficiencyCardProps) {
    const cardGlow = useCardGlow();

    // Generate all days in the date range for horizontal scroll
    const days = useMemo(() => {
        if (!dateRange.from || !dateRange.to) return [];
        return eachDayOfInterval({ start: dateRange.from, end: dateRange.to });
    }, [dateRange]);

    // Filter time entries for this member within date range and active periods
    const memberEntries = useMemo(() => {
        if (!dateRange.from || !dateRange.to) return [];

        return timeEntries.filter(e => {
            if (e.user_id !== member.id) return false;
            if (!e.date) return false;
            const entryDate = parseISO(e.date);
            if (entryDate < dateRange.from || entryDate > dateRange.to) return false;

            // Check active periods
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
    }, [timeEntries, member.id, dateRange, activePeriods]);

    const totalHours = memberEntries.reduce((acc, curr) => acc + curr.hours, 0);

    // Aggregate for Main Pie Chart
    const activityData = useMemo(() => {
        const activityMap: Record<string, number> = {};

        memberEntries.forEach((entry) => {
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
    }, [memberEntries, activityColors, totalHours]);

    // Build task lookup map for quick name resolution
    const taskMap = useMemo(() => {
        const map = new Map<string, PMTask>();
        tasks.forEach(t => map.set(t.id, t));
        return map;
    }, [tasks]);

    // Build daily data map for quick lookup
    const dailyData = useMemo(() => {
        const map = new Map<string, {
            total: number;
            breakdown: { name: string, hours: number, color: string }[];
            taskBreakdown: { taskId: string, taskName: string, hours: number, activityType: string }[];
        }>();

        days.forEach(day => {
            const dayKey = format(day, 'yyyy-MM-dd');
            const dayEntries = memberEntries.filter(e => e.date && isSameDay(parseISO(e.date), day));
            const totalHours = dayEntries.reduce((sum, e) => sum + e.hours, 0);

            if (totalHours === 0) {
                map.set(dayKey, { total: 0, breakdown: [], taskBreakdown: [] });
                return;
            }

            // Group by activity for Tooltip (existing behavior)
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

            // Group by task for detailed view with task names
            const taskGroups: Record<string, { hours: number, activityType: string, taskNameFromLinks?: string, projectNameFromLinks?: string }> = {};
            dayEntries.forEach(e => {
                const taskId = e.task_id || 'no-task';
                if (!taskGroups[taskId]) {
                    taskGroups[taskId] = {
                        hours: 0,
                        activityType: e.activity_type || 'Unknown',
                        // Store task name from HAL links (always available in time entry)
                        taskNameFromLinks: e._links?.workPackage?.title,
                        projectNameFromLinks: e._links?.project?.title
                    };
                }
                taskGroups[taskId].hours += e.hours;
            });

            const taskBreakdown = Object.entries(taskGroups).map(([taskId, data]) => {
                const task = taskMap.get(taskId);
                return {
                    taskId,
                    // Use _links.workPackage.title first, then task lookup, then fallback
                    taskName: data.taskNameFromLinks || task?.name || task?.title || (taskId === 'no-task' ? 'General Work' : `Task ${taskId.split(':').pop()}`),
                    projectName: data.projectNameFromLinks || 'Unknown Project',
                    hours: data.hours,
                    activityType: data.activityType
                };
            }).sort((a, b) => b.hours - a.hours);

            map.set(dayKey, { total: totalHours, breakdown, taskBreakdown });
        });

        return map;
    }, [days, memberEntries, activityColors, taskMap]);

    // Group days by month for calendar grid layout
    const monthCalendars = useMemo(() => {
        const calendars: { month: string; monthKey: string; days: Date[]; startOffset: number }[] = [];
        let currentMonthKey = '';
        let currentMonthDays: Date[] = [];

        days.forEach(day => {
            const monthKey = format(day, 'yyyy-MM');
            const monthLabel = format(day, 'MMM yyyy');

            if (monthKey !== currentMonthKey) {
                // Save previous month
                if (currentMonthDays.length > 0 && calendars.length > 0) {
                    calendars[calendars.length - 1]!.days = currentMonthDays;
                }
                // Start new month
                const dayOfWeek = day.getDay(); // 0=Sun, 1=Mon...
                const startOffset = dayOfWeek === 0 ? 6 : dayOfWeek - 1; // Monday=0
                calendars.push({
                    month: monthLabel,
                    monthKey,
                    days: [],
                    startOffset
                });
                currentMonthKey = monthKey;
                currentMonthDays = [day];
            } else {
                currentMonthDays.push(day);
            }
        });

        // Add last month's days
        if (currentMonthDays.length > 0 && calendars.length > 0) {
            calendars[calendars.length - 1]!.days = currentMonthDays;
        }

        return calendars;
    }, [days]);

    const weekDays = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];

    // Check if a day is within active periods
    const isDayActive = (day: Date): boolean => {
        if (!activePeriods || activePeriods.length === 0) return true;
        return activePeriods.some(p => {
            if (!p.range.from) return false;
            const start = startOfDay(new Date(p.range.from));
            const end = p.range.to
                ? endOfDay(new Date(p.range.to))
                : new Date(8640000000000000);
            return isWithinInterval(day, { start, end });
        });
    };

    return (
        <Card className={cardGlow.className}>
            <CardHeader className="pb-2 pt-4 px-4 border-b border-border/50">
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
            </CardHeader>
            <CardContent className="p-4">
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">

                    {/* LEFT COLUMN: Aggregate Pie Chart */}
                    <div className="lg:col-span-3 flex flex-col min-h-[180px] border-r border-border/50 pr-4">
                        <div className="flex items-center justify-between mb-2">
                            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                                Distribution
                            </h4>
                            <span className="text-xs font-bold">{totalHours.toFixed(1)}h Total</span>
                        </div>

                        {activityData.length > 0 ? (
                            <div className="flex flex-col sm:flex-row items-center gap-4 h-full pt-2">
                                {/* Chart */}
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
                                                formatter={(value, name, item) => [
                                                    `${Number(value).toFixed(1)}h (${item.payload.percentage ?? 0}%)`,
                                                    name
                                                ]}
                                            />
                                        </PieChart>
                                    </ResponsiveContainer>
                                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                                        <span className="text-xl font-bold">{totalHours.toFixed(0)}</span>
                                        <span className="text-[10px] text-muted-foreground uppercase">Hours</span>
                                    </div>
                                </div>

                                {/* Legend */}
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

                    {/* RIGHT COLUMN: Horizontal Scroll Monthly Calendars */}
                    <div className="lg:col-span-9 overflow-hidden">
                        <div className="overflow-x-auto">
                            <div className="flex gap-4 min-w-max p-1">
                                {monthCalendars.map(calendar => (
                                    <div
                                        key={calendar.monthKey}
                                        className="shrink-0 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden bg-card"
                                    >
                                        {/* Month Header */}
                                        <div className="text-center text-sm font-semibold py-2 px-4 bg-gray-100/70 dark:bg-gray-900/70 border-b border-gray-200 dark:border-gray-700">
                                            {calendar.month}
                                        </div>

                                        {/* Weekday Headers */}
                                        <div className="grid grid-cols-7 gap-0.5 px-1.5 pt-1.5 pb-1">
                                            {weekDays.map((d, i) => (
                                                <div key={i} className="w-10 text-center text-[10px] font-semibold text-muted-foreground">
                                                    {d}
                                                </div>
                                            ))}
                                        </div>

                                        {/* Calendar Grid */}
                                        <div className="grid grid-cols-7 gap-0.5 px-1.5 pb-1.5">
                                            {/* Empty cells for offset */}
                                            {[...Array(calendar.startOffset)].map((_, i) => (
                                                <div key={`empty-${i}`} className="w-10 h-10" />
                                            ))}

                                            {/* Days */}
                                            <TooltipProvider delayDuration={0}>
                                                {calendar.days.map(day => {
                                                    const dayKey = format(day, 'yyyy-MM-dd');
                                                    const data = dailyData.get(dayKey);
                                                    const isWknd = isWeekend(day);
                                                    const isActive = isDayActive(day);
                                                    const hours = data?.total || 0;
                                                    const target = 8;
                                                    const pct = target > 0 ? (hours / target) * 100 : 0;

                                                    let glowColorClass = "";
                                                    if (hours > target && Math.abs(hours - target) > 0.1) {
                                                        glowColorClass = "bg-emerald-300 dark:bg-emerald-400";
                                                    } else if (pct >= 0 && pct < 50 && !isWknd && hours > 0) {
                                                        glowColorClass = "bg-red-400 dark:bg-red-500";
                                                    } else if (pct >= 50 && pct < 90) {
                                                        glowColorClass = "bg-amber-300 dark:bg-amber-400";
                                                    }

                                                    return (
                                                        <div
                                                            key={dayKey}
                                                            className={cn(
                                                                "relative w-10 h-10 flex flex-col items-center justify-center rounded-md border text-xs transition-colors",
                                                                isWknd ? "bg-gray-50/50 dark:bg-gray-900/20 border-gray-100 dark:border-gray-800" : "bg-card border-border",
                                                                !isActive && "opacity-40 bg-gray-50 dark:bg-gray-900/10 border-dashed"
                                                            )}
                                                        >
                                                            {/* Date Label */}
                                                            <div className={cn(
                                                                "absolute top-0.5 left-1 text-[9px] font-medium leading-none",
                                                                isWknd || !isActive ? "text-gray-400" : "text-gray-500"
                                                            )}>
                                                                {format(day, 'd')}
                                                            </div>

                                                            {/* Chart - Only show when not loading */}
                                                            {isActive && !isLoading && (
                                                                <Tooltip>
                                                                    <TooltipTrigger asChild>
                                                                        <div className={cn(
                                                                            "relative flex items-center justify-center cursor-pointer mt-1",
                                                                            isWknd && "opacity-60"
                                                                        )}>
                                                                            {/* Glow */}
                                                                            {glowColorClass && (
                                                                                <div className={cn(
                                                                                    "absolute inset-0 rounded-full blur-sm animate-pulse",
                                                                                    glowColorClass
                                                                                )} />
                                                                            )}
                                                                            {/* Chart */}
                                                                            <div className="relative z-10">
                                                                                <DailyWorklogChart
                                                                                    hours={hours}
                                                                                    target={target}
                                                                                    size={28}
                                                                                    strokeWidth={3}
                                                                                    isWeekend={isWknd}
                                                                                    showText={true}
                                                                                />
                                                                            </div>
                                                                        </div>
                                                                    </TooltipTrigger>
                                                                    <TooltipContent className="text-xs z-50 max-w-[280px]">
                                                                        <div className="font-semibold mb-1 border-b pb-1">{format(day, 'EEE, MMM d')}</div>
                                                                        <div className="space-y-2">
                                                                            {data && data.taskBreakdown && data.taskBreakdown.length > 0 ? (
                                                                                <>
                                                                                    {/* Group tasks by project */}
                                                                                    {Object.entries(
                                                                                        data.taskBreakdown.reduce((acc, item) => {
                                                                                            const project = item.projectName || 'Unknown Project';
                                                                                            if (!acc[project]) acc[project] = [];
                                                                                            acc[project].push(item);
                                                                                            return acc;
                                                                                        }, {} as Record<string, typeof data.taskBreakdown>)
                                                                                    ).map(([projectName, projectTasks]) => (
                                                                                        <div key={projectName} className="space-y-1">
                                                                                            <div className="text-[10px] opacity-70 font-medium truncate" title={projectName}>
                                                                                                📁 {projectName}
                                                                                            </div>
                                                                                            {projectTasks.sort((a, b) => b.hours - a.hours).map((item, i) => (
                                                                                                <div key={i} className="flex items-start gap-2 pl-2">
                                                                                                    <div className="w-1.5 h-1.5 rounded-full mt-1 shrink-0" style={{ background: activityColors[i % activityColors.length] }} />
                                                                                                    <div className="flex-1 min-w-0 flex justify-between items-baseline gap-2">
                                                                                                        <span className="font-medium truncate" title={item.taskName}>
                                                                                                            {item.taskName}
                                                                                                        </span>
                                                                                                        <span className="text-[11px] opacity-80 shrink-0">
                                                                                                            {item.hours.toFixed(1)}h
                                                                                                        </span>
                                                                                                    </div>
                                                                                                </div>
                                                                                            ))}
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
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
