"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card"
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, Cell } from "recharts"
import { useTeamDataContext, useTeamUsers, useTeamTasks } from "../context/team-data-context"
import { Loader2 } from "lucide-react"

export function WorkloadCharts() {
    // Get essential data from context
    const { allMemberIds, isLoading: isContextLoading } = useTeamDataContext();

    // Load heavy data for this component
    const { teamMembers: members, isLoading: isLoadingUsers } = useTeamUsers(allMemberIds);
    const { teamTasks: tasks, isLoading: isLoadingTasks } = useTeamTasks(allMemberIds);

    const isLoading = isContextLoading || isLoadingUsers || isLoadingTasks;

    // Calculate workload per member
    const workloadData = members.map(member => {
        const memberTasks = tasks.filter(t => t.assignee_id === member.id);
        const taskCount = memberTasks.length;
        const capacity = 5;
        const utilization = Math.min((taskCount / capacity) * 100, 150);

        return {
            name: member.name,
            utilization: Math.round(utilization),
            tasks: taskCount
        };
    }).sort((a, b) => b.utilization - a.utilization).slice(0, 10);

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-8 text-muted-foreground gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Loading workload data...</span>
            </div>
        );
    }

    if (workloadData.length === 0) {
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
                    <CardTitle>Team Capacity</CardTitle>
                    <CardDescription>
                        Workload based on active task assignments
                    </CardDescription>
                </CardHeader>
                <CardContent className="pl-2">
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
                                tickFormatter={(value) => `${value}%`}
                            />
                            <Tooltip
                                cursor={{ fill: 'transparent' }}
                                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                            />
                            <Bar dataKey="utilization" radius={[4, 4, 0, 0]} maxBarSize={50}>
                                {workloadData.map((entry, index) => (
                                    <Cell
                                        key={`cell-${index}`}
                                        fill={
                                            entry.utilization > 100 ? "#ef4444" : // Red
                                                entry.utilization > 80 ? "#eab308" : // Yellow
                                                    "#22c55e" // Green
                                        }
                                    />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>

            <Card className="col-span-3">
                <CardHeader>
                    <CardTitle>Utilization Details</CardTitle>
                    <CardDescription>Most active contributors</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {workloadData.slice(0, 5).map(member => (
                            <div key={member.name} className="flex items-center">
                                <div className="flex-1 space-y-1">
                                    <p className="text-sm font-medium leading-none">{member.name}</p>
                                    <p className="text-xs text-muted-foreground">{member.tasks} active tasks</p>
                                </div>
                                <div className="font-bold text-sm">
                                    {member.utilization}%
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
