"use client";

import { useMemo, useState } from "react";
import { useTeamDataContext, useTeamUsers, useTeamTasks } from "../context/team-data-context";
import { useProjects } from "~/core/api/hooks/pm/use-projects";
import { CapacityChart } from "./planning/capacity-chart";
import { AllocationGrid } from "./planning/allocation-grid";
import { Loader2, CalendarRange, AlertCircle } from "lucide-react";
import type { PMTask } from "~/core/api/pm/tasks";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";

// --- Helper Functions ---

// Get Monday of current week
function getWeekStart(date: Date = new Date()): Date {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    d.setDate(diff);
    d.setHours(0, 0, 0, 0);
    return d;
}

// Format simplistic week label "Week 2 (Nov 4)"
function formatWeekLabel(start: Date, index: number): string {
    if (index === 0) return "This Week";
    if (index === 1) return "Next Week";
    return `${start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
}

// Get load from task (Prefer remaining, fallback to estimated)
function getTaskLoad(task: PMTask): number {
    if (task.status === 'done' || task.status === 'completed' || task.status === 'cancelled') return 0;
    // If we have remaining hours, use that. Otherwise use total estimated.
    // For planning, usually we care about "Remaining Effort"
    return task.remaining_hours ?? task.estimated_hours ?? 0;
}

// Check if task falls in week
function isTaskInWeek(task: PMTask, weekStart: Date, weekEnd: Date): boolean {
    if (!task.deadline) return false;
    const due = new Date(task.deadline);
    return due >= weekStart && due <= weekEnd;
}

export function CapacityPlanningView() {
    // 1. Context Hooks
    const { allMemberIds, isLoading: isContextLoading } = useTeamDataContext();
    const { teamMembers: members, isLoading: isLoadingUsers } = useTeamUsers(allMemberIds);
    const { teamTasks: tasks, isLoading: isLoadingTasks } = useTeamTasks(allMemberIds);
    const { projects, loading: isLoadingProjects } = useProjects();

    const [planningHorizon, setPlanningHorizon] = useState<string>("6"); // weeks

    // 2. Data Processing
    const planningData = useMemo(() => {
        if (isLoadingUsers || isLoadingTasks || isLoadingProjects) return null;

        const weeksCount = parseInt(planningHorizon);
        const currentWeekStart = getWeekStart();

        const chartData: any[] = [];
        const totalTeamCapacity = members.length * 40; // Default 40h/week/member

        // Initialize Grid Members
        const memberMap = new Map<string, { id: string; name: string; avatar?: string; allocations: number[] }>();
        members.forEach(m => {
            memberMap.set(m.id, {
                id: m.id,
                name: m.name,
                avatar: m.avatar,
                allocations: Array(weeksCount).fill(0)
            });
        });

        // Iterate Weeks
        for (let i = 0; i < weeksCount; i++) {
            const weekStart = new Date(currentWeekStart);
            weekStart.setDate(weekStart.getDate() + (i * 7));
            const weekEnd = new Date(weekStart);
            weekEnd.setDate(weekEnd.getDate() + 6);
            weekEnd.setHours(23, 59, 59, 999);

            // Chart Data Point
            const weekLabel = formatWeekLabel(weekStart, i);
            const chartPoint: any = { week: weekLabel, capacity: totalTeamCapacity };

            // 3. Distribute Tasks
            tasks.forEach(task => {
                if (isTaskInWeek(task, weekStart, weekEnd) && task.assignee_id) {
                    const load = getTaskLoad(task);
                    const projectId = task.project_id || 'unassigned';

                    // Add to Chart (Project aggregates)
                    chartPoint[projectId] = (chartPoint[projectId] || 0) + load;

                    // Add to Grid (Member aggregates)
                    const memberStats = memberMap.get(task.assignee_id);
                    if (memberStats) {
                        memberStats.allocations[i] += load;
                    }
                }
            });

            chartData.push(chartPoint);
        }

        // Finalize Grid Data (Convert hours to %)
        const memberData = Array.from(memberMap.values()).map(m => ({
            ...m,
            allocations: m.allocations.map(hours => Math.round((hours / 40) * 100))
        }));

        // Project Metadata for Chart Colors
        const projectMetadata = projects.map(p => ({
            id: p.id,
            name: p.name,
            color: '#6366f1' // Default Indigo, need proper project color logic if available
        }));
        // Add Unassigned pseudo-project
        projectMetadata.push({ id: 'unassigned', name: 'No Project', color: '#9ca3af' });

        return { chartData, memberData, projectMetadata, totalTeamCapacity };

    }, [members, tasks, projects, planningHorizon, isLoadingUsers, isLoadingTasks, isLoadingProjects]);

    // 3. Loading State
    const isLoading = isContextLoading || isLoadingUsers || isLoadingTasks || isLoadingProjects;

    if (isLoading) {
        return (
            <div className="h-[600px] flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
            </div>
        );
    }

    if (!planningData || planningData.memberData.length === 0) {
        return (
            <div className="text-center py-12">
                <CalendarRange className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No data available for planning</h3>
                <p className="text-muted-foreground mt-2">Try adding members to your teams or assigning tasks with due dates.</p>
            </div>
        );
    }

    // Generate week labels for grid header
    const weekLabels = planningData.chartData.map(d => d.week);

    return (
        <div className="space-y-8 animate-in fade-in-50 duration-500">
            {/* Header Controls */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-lg font-semibold tracking-tight">Capacity Overview</h2>
                    <p className="text-sm text-muted-foreground">Predictive analysis based on task deadlines.</p>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-muted-foreground">Horizon:</span>
                    <Select value={planningHorizon} onValueChange={setPlanningHorizon}>
                        <SelectTrigger className="w-[140px]">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="4">Next 4 Weeks</SelectItem>
                            <SelectItem value="6">Next 6 Weeks</SelectItem>
                            <SelectItem value="8">Next 8 Weeks</SelectItem>
                            <SelectItem value="12">Next 12 Weeks</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </div>

            <div className="bg-blue-50/50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-lg p-4 flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5 shrink-0" />
                <div>
                    <h4 className="text-sm font-medium text-blue-800 dark:text-blue-300">Beta Feature</h4>
                    <p className="text-sm text-blue-700 dark:text-blue-400 mt-1">
                        This view calculates capacity based on <strong>Task Deadlines</strong>. Tasks without deadlines are excluded.
                        Default capacity is set to 40h/week per member.
                    </p>
                </div>
            </div>

            {/* 1. Demand Chart */}
            <CapacityChart
                data={planningData.chartData}
                projects={planningData.projectMetadata}
                totalCapacity={planningData.totalTeamCapacity}
            />

            {/* 2. Allocation Matrix */}
            <AllocationGrid
                weeks={weekLabels}
                members={planningData.memberData}
            />
        </div>
    );
}
