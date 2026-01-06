"use client"

import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { WorkloadCharts } from "./workload-charts";
import { useTeamDataContext, useTeamUsers, useTeamTasks } from "../context/team-data-context";
import { useMemo } from "react";
import type { PMTask } from "~/core/api/pm/tasks";
import { Loader2, BarChart3, Users, ListTodo } from "lucide-react";

export function TeamOverview() {
    // Get essential data from context
    const { teams, allMemberIds, isLoading: isContextLoading } = useTeamDataContext();

    // Load heavy data for this tab
    const { teamMembers: members, isLoading: isLoadingUsers, isFetching: isFetchingUsers, count: usersCount } = useTeamUsers(allMemberIds);
    const { teamTasks: tasks, isLoading: isLoadingTasks, isFetching: isFetchingTasks, count: tasksCount } = useTeamTasks(allMemberIds);

    const stats = useMemo(() => {
        if (isLoadingUsers || isLoadingTasks || members.length === 0) {
            return {
                utilization: 0,
                activeProjects: 0,
                availableCapacity: 0
            };
        }

        // 1. Team Utilization
        const totalCapacityHours = members.length * 40;
        const assignedHours = tasks.reduce((sum: number, task: PMTask) => {
            return sum + (task.estimated_hours || 4);
        }, 0);
        const utilization = Math.min(Math.round((assignedHours / totalCapacityHours) * 100), 100);

        // 2. Active Projects
        const uniqueProjects = new Set(tasks.map((t: PMTask) => t.project_id).filter(Boolean));

        // 3. Available Capacity
        const availableHours = Math.max(0, totalCapacityHours - assignedHours);

        return {
            utilization,
            activeProjects: uniqueProjects.size,
            availableCapacity: Math.round(availableHours)
        };
    }, [members, tasks, isLoadingUsers, isLoadingTasks]);

    const isLoading = isContextLoading || isLoadingUsers || isLoadingTasks || isFetchingUsers || isFetchingTasks;

    if (isLoading) {
        // Calculate loading progress
        const loadingItems = [
            { label: "Users", isLoading: isLoadingUsers || isFetchingUsers, count: usersCount },
            { label: "Tasks", isLoading: isLoadingTasks || isFetchingTasks, count: tasksCount },
        ];
        const completedCount = loadingItems.filter(item => !item.isLoading).length;
        const progressPercent = Math.round((completedCount / loadingItems.length) * 100);

        return (
            <div className="h-full w-full flex items-center justify-center bg-muted/20 p-4">
                <div className="bg-card border rounded-xl shadow-lg p-5 w-full max-w-sm">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                            <BarChart3 className="w-5 h-5 text-blue-600 dark:text-blue-400 animate-pulse" />
                        </div>
                        <div>
                            <h3 className="text-sm font-semibold">Loading Overview</h3>
                            <p className="text-xs text-muted-foreground">{progressPercent}% complete</p>
                        </div>
                    </div>

                    {/* Progress bar */}
                    <div className="w-full h-1.5 bg-muted rounded-full mb-4 overflow-hidden">
                        <div
                            className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-500 ease-out"
                            style={{ width: `${progressPercent}%` }}
                        />
                    </div>

                    <div className="space-y-2">
                        {loadingItems.map((item, index) => (
                            <div key={index} className="flex items-center justify-between py-1.5 px-2 bg-muted/30 rounded-md">
                                <div className="flex items-center gap-2">
                                    {index === 0 ? <Users className="w-3.5 h-3.5 text-blue-500" /> : <ListTodo className="w-3.5 h-3.5 text-green-500" />}
                                    <span className="text-xs font-medium">{item.label}</span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <span className={`text-xs font-mono tabular-nums ${item.isLoading ? 'text-blue-600 dark:text-blue-400' : 'text-green-600 dark:text-green-400'}`}>
                                        {item.isLoading ? (item.count > 0 ? item.count : "...") : item.count}
                                    </span>
                                    {item.isLoading ? (
                                        <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />
                                    ) : (
                                        <div className="w-3.5 h-3.5 text-green-500">✓</div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>

                    <p className="text-[10px] text-muted-foreground mt-3 text-center">
                        Calculating team metrics...
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="grid gap-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Team Utilization</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.utilization}%</div>
                        <p className="text-xs text-muted-foreground">Based on {members.length} members</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Active Projects</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.activeProjects}</div>
                        <p className="text-xs text-muted-foreground">Across {teams.length} teams</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Available Capacity</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.availableCapacity}h</div>
                        <p className="text-xs text-muted-foreground">Remaining this week (est)</p>
                    </CardContent>
                </Card>
            </div>

            <WorkloadCharts />
        </div>
    );
}


