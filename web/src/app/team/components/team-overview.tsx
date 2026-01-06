"use client"

import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { WorkloadCharts } from "./workload-charts";
import { useTeamDataContext } from "../context/team-data-context";
import { useMemo } from "react";
import type { PMTask } from "~/core/api/pm/tasks";

// Direct imports to avoid barrel file memory bloat
// @ts-expect-error - Lucide icons don't have direct type exports
import Users from "lucide-react/dist/esm/icons/users";
// @ts-expect-error - Lucide icons don't have direct type exports
import Clock from "lucide-react/dist/esm/icons/clock";
// @ts-expect-error - Lucide icons don't have direct type exports
import CheckCircle2 from "lucide-react/dist/esm/icons/check-circle-2";
// @ts-expect-error - Lucide icons don't have direct type exports
import AlertCircle from "lucide-react/dist/esm/icons/alert-circle";
// @ts-expect-error - Lucide icons don't have direct type exports
import TrendingUp from "lucide-react/dist/esm/icons/trending-up";

export function TeamOverview() {
    // Use centralized context - no duplicate API calls!
    const { teams, teamMembers: members, teamTasks: tasks, isLoading } = useTeamDataContext();

    const stats = useMemo(() => {
        if (isLoading || members.length === 0) {
            return {
                utilization: 0,
                activeProjects: 0,
                availableCapacity: 0
            };
        }

        // 1. Team Utilization
        // Assume standard capacity: 40 hours/week per member
        const totalCapacityHours = members.length * 40;

        // Sum estimated hours of assigned tasks (fallback to 4h if missing)
        const assignedHours = tasks.reduce((sum: number, task: PMTask) => {
            // Only count active tasks? Assuming 'tasks' from hook are relevant active tasks.
            // useTeamData fetches open tasks by default?
            // "listTasks({ limit: 2000, status: 'open' })" -> Yes.
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
    }, [members, tasks, isLoading]);

    if (isLoading) {
        return <div className="p-8 text-center text-muted-foreground">Loading overview...</div>;
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

