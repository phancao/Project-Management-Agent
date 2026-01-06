"use client"

import { useMemo, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card"
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, Legend, ReferenceLine, Cell } from "recharts"
import { useTeamDataContext, useTeamUsers, useTeamTasks, useTeamTimeEntries } from "../context/team-data-context"
import { Loader2, Info, ChevronLeft, ChevronRight } from "lucide-react"
import { Popover, PopoverContent, PopoverTrigger } from "~/components/ui/popover"
import { Button } from "~/components/ui/button"

// Helper to get start of week (Monday) with offset
function getWeekStart(weekOffset: number = 0): Date {
    const d = new Date()
    const day = d.getDay()
    const diff = d.getDate() - day + (day === 0 ? -6 : 1)
    d.setDate(diff + (weekOffset * 7))
    d.setHours(0, 0, 0, 0)
    return d
}

// Format date as YYYY-MM-DD (local timezone)
function formatDateKey(date: Date): string {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
}

// Format date for display
function formatDateDisplay(date: Date): string {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

// Statuses considered "completed/waiting" (dev work done, not active work remaining)
const COMPLETED_STATUSES = [
    'done', 'closed', 'rejected', 'cancelled', 'passed',
    'ready4sit', 'developed', 'confirmed', 'specified' // Dev work done, pending review/test
];

export function WorkloadCharts() {
    // Week navigation state
    const [weekOffset, setWeekOffset] = useState(0)

    // Get selected week's date range
    const weekRange = useMemo(() => {
        const start = getWeekStart(weekOffset)
        const end = new Date(start)
        end.setDate(end.getDate() + 6)
        return {
            start: formatDateKey(start),
            end: formatDateKey(end),
            startDate: start,
            endDate: end,
            displayRange: `${formatDateDisplay(start)} - ${formatDateDisplay(end)}`
        }
    }, [weekOffset])

    const isCurrentWeek = weekOffset === 0

    // Get essential data from context
    const { allMemberIds, isLoading: isContextLoading } = useTeamDataContext();

    // Load members, tasks, and time entries
    const { teamMembers: members, isLoading: isLoadingUsers } = useTeamUsers(allMemberIds);
    const { teamTasks: tasks, isLoading: isLoadingTasks } = useTeamTasks(allMemberIds);
    const { teamTimeEntries: timeEntries, isLoading: isLoadingTimeEntries, isFetching: isFetchingTimeEntries } = useTeamTimeEntries(
        allMemberIds,
        { startDate: weekRange.start, endDate: weekRange.end }
    );

    // Initial loading (no data yet)
    const isLoading = isContextLoading || isLoadingUsers || isLoadingTasks || isLoadingTimeEntries;
    // Refetching (have data, loading new data - e.g., switching weeks)
    const isFetching = isFetchingTimeEntries && !isLoadingTimeEntries;

    // Calculate expected hours based on current day of the week
    // Mon=8h, Tue=16h, Wed=24h, Thu=32h, Fri=40h, Sat/Sun=40h
    const expectedHoursToday = useMemo(() => {
        const today = new Date();
        const dayOfWeek = today.getDay(); // 0=Sun, 1=Mon, ..., 6=Sat
        const weekdayNumber = dayOfWeek === 0 ? 5 : dayOfWeek; // Sun counts as end of week
        return Math.min(weekdayNumber * 8, 40); // 8h per day, max 40h
    }, []);

    // Calculate workload per member:
    // - Time Spent: Actual logged hours this week
    // - Time Remaining: Sum of (estimated_hours - logged_hours) for each incomplete task
    const workloadData = useMemo(() => {
        return members.map(member => {
            // 1. Time Spent this week (from time entries)
            const memberTimeEntries = timeEntries.filter(te => te.user_id === member.id);
            const timeSpent = memberTimeEntries.reduce((sum, te) => sum + (te.hours || 0), 0);

            // 2. Get incomplete tasks assigned to this member
            const memberTasks = tasks.filter(t =>
                t.assignee_id === member.id &&
                !COMPLETED_STATUSES.includes((t.status || '').toLowerCase())
            );

            // 3. Calculate time remaining for each task
            // Time Remaining = Estimated Hours - Time Already Spent on that task
            // For simplicity, we use total logged hours as a proxy (not per-task tracking)
            // A better approach would track spent per task_id, but we'll estimate
            const totalEstimated = memberTasks.reduce((sum, t) => sum + (t.estimated_hours || 4), 0);

            // Time remaining = total estimated - time spent (minimum 0)
            const timeRemaining = Math.max(0, totalEstimated - timeSpent);

            // Total workload = spent + remaining
            const totalWorkload = timeSpent + timeRemaining;

            // Behind schedule: spent less than expected for today
            const behindSchedule = timeSpent < expectedHoursToday;

            // Status: over 40h = overassigned, under 40h = has free time
            const status = totalWorkload > 40 ? 'overassigned' :
                totalWorkload < 32 ? 'underloaded' : 'optimal';

            return {
                name: member.name.split(' ').slice(0, 2).join(' '), // First 2 words
                fullName: member.name,
                timeSpent: Math.round(timeSpent * 10) / 10,
                timeRemaining: Math.round(timeRemaining * 10) / 10,
                totalWorkload: Math.round(totalWorkload * 10) / 10,
                taskCount: memberTasks.length,
                status,
                behindSchedule,
                expectedHours: expectedHoursToday
            };
        }).sort((a, b) => b.totalWorkload - a.totalWorkload).slice(0, 10);
    }, [members, tasks, timeEntries, expectedHoursToday]);

    // Show loading state or empty state
    const showLoadingOverlay = isLoading || isFetching;

    if (workloadData.length === 0 && !isLoading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Team Workload</CardTitle>
                    <CardDescription>Capacity distribution across team members</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="h-[300px] flex items-center justify-center text-muted-foreground border-2 border-dashed rounded-lg">
                        No team members or tasks found.
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
            <Card className="col-span-4">
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle>Team Workload</CardTitle>
                            <CardDescription>
                                Time Spent + Time Remaining (40h = full capacity)
                            </CardDescription>
                        </div>
                        <div className="flex items-center gap-2">
                            {/* Week navigation */}
                            <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-1">
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-7 w-7"
                                    onClick={() => setWeekOffset(prev => prev - 1)}
                                >
                                    <ChevronLeft className="h-4 w-4" />
                                </Button>
                                <span className="text-sm font-medium px-2 min-w-[140px] text-center">
                                    {weekRange.displayRange}
                                </span>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-7 w-7"
                                    onClick={() => setWeekOffset(prev => prev + 1)}
                                    disabled={isCurrentWeek}
                                >
                                    <ChevronRight className="h-4 w-4" />
                                </Button>
                            </div>
                            {!isCurrentWeek && (
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setWeekOffset(0)}
                                >
                                    Today
                                </Button>
                            )}
                            <Popover>
                                <PopoverTrigger asChild>
                                    <Button variant="ghost" size="icon" className="h-8 w-8">
                                        <Info className="h-4 w-4 text-muted-foreground" />
                                    </Button>
                                </PopoverTrigger>
                                <PopoverContent className="w-80" align="end">
                                    <div className="space-y-2">
                                        <h4 className="font-semibold">Workload Chart</h4>
                                        <p className="text-sm text-muted-foreground">
                                            Shows each member&apos;s total workload as stacked bars for the selected week.
                                        </p>
                                        <div className="text-sm space-y-1">
                                            <p><strong>Bars:</strong></p>
                                            <div className="flex items-center gap-2">
                                                <div className="w-3 h-3 rounded bg-emerald-500" />
                                                <span className="text-muted-foreground">Time Spent (logged hours)</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <div className="w-3 h-3 rounded bg-blue-500" />
                                                <span className="text-muted-foreground">Time Remaining (estimated - spent)</span>
                                            </div>
                                            <div className="flex items-center gap-2 pt-1">
                                                <div className="w-3 h-3 rounded border-2 border-red-500" />
                                                <span className="text-muted-foreground">Red border = behind schedule</span>
                                            </div>
                                        </div>
                                        <div className="text-sm space-y-1 pt-2">
                                            <p><strong>Interpretation:</strong></p>
                                            <p className="text-muted-foreground">
                                                • Total &gt; 40h: Overassigned (may need OT)<br />
                                                • Total ≈ 40h: Optimal workload<br />
                                                • Total &lt; 32h: Has free capacity
                                            </p>
                                        </div>
                                    </div>
                                </PopoverContent>
                            </Popover>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="pl-2 relative">
                    {/* Loading overlay for initial load and week transitions */}
                    {showLoadingOverlay && (
                        <div className="absolute inset-0 bg-background/50 backdrop-blur-sm flex items-center justify-center z-10 rounded-lg">
                            <Loader2 className="w-6 h-6 animate-spin text-primary" />
                        </div>
                    )}
                    <ResponsiveContainer width="100%" height={350}>
                        <BarChart data={workloadData} barCategoryGap="20%">
                            <XAxis
                                dataKey="name"
                                stroke="#888888"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                                interval={0}
                                angle={-20}
                                textAnchor="end"
                                height={60}
                            />
                            <YAxis
                                stroke="#888888"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                                tickFormatter={(value) => `${value}h`}
                                domain={[0, 'auto']}
                            />
                            <Tooltip
                                cursor={{ fill: 'rgba(0,0,0,0.1)' }}
                                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                formatter={(value, name) => [
                                    `${value ?? 0}h`,
                                    name === 'timeSpent' ? 'Time Spent' : 'Time Remaining'
                                ]}
                                labelFormatter={(label) => workloadData.find(d => d.name === label)?.fullName || label}
                            />
                            <Legend
                                content={() => (
                                    <div className="flex justify-center gap-6 mt-2 text-sm">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded" style={{ backgroundColor: '#10b981' }} />
                                            <span>Time Spent</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded" style={{ backgroundColor: '#3b82f6' }} />
                                            <span>Time Remaining</span>
                                        </div>
                                    </div>
                                )}
                            />
                            {/* Expected hours for today reference line */}
                            <ReferenceLine y={workloadData[0]?.expectedHours || 0} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: `${workloadData[0]?.expectedHours || 0}h expected`, position: 'right', fill: '#f59e0b', fontSize: 11 }} />
                            {/* 40h reference line */}
                            <ReferenceLine y={40} stroke="#ef4444" strokeDasharray="5 5" label={{ value: '40h', position: 'right', fill: '#ef4444' }} />
                            {/* Stacked bars with red border for behind schedule */}
                            <Bar dataKey="timeSpent" stackId="workload" radius={[0, 0, 0, 0]} maxBarSize={50}>
                                {workloadData.map((entry, index) => (
                                    <Cell
                                        key={`spent-${index}`}
                                        fill="#10b981"
                                        stroke={entry.behindSchedule ? "#ef4444" : "transparent"}
                                        strokeWidth={entry.behindSchedule ? 3 : 0}
                                    />
                                ))}
                            </Bar>
                            <Bar dataKey="timeRemaining" stackId="workload" radius={[4, 4, 0, 0]} maxBarSize={50}>
                                {workloadData.map((entry, index) => (
                                    <Cell
                                        key={`remaining-${index}`}
                                        fill="#3b82f6"
                                        stroke={entry.behindSchedule ? "#ef4444" : "transparent"}
                                        strokeWidth={entry.behindSchedule ? 3 : 0}
                                    />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>

            <Card className="col-span-3">
                <CardHeader>
                    <CardTitle>Workload Details</CardTitle>
                    <CardDescription>All team members ({workloadData.length})</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
                        {workloadData.map(member => (
                            <div key={member.name} className="flex items-center">
                                <div className="flex-1 space-y-1">
                                    <p className="text-sm font-medium leading-none">{member.fullName}</p>
                                    <p className="text-xs text-muted-foreground">
                                        {member.taskCount} tasks • {member.timeSpent}h spent
                                    </p>
                                </div>
                                <div className={`font-bold text-sm ${member.status === 'overassigned' ? 'text-red-500' :
                                    member.status === 'underloaded' ? 'text-amber-500' :
                                        'text-green-500'
                                    }`}>
                                    {member.totalWorkload}h
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
