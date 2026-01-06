"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "~/components/ui/card";
import { WorkloadCharts } from "./workload-charts";
import { useTeamDataContext, useTeamUsers, useTeamTasks, useTeamTimeEntries } from "../context/team-data-context";
import { useMemo } from "react";
import type { PMTask } from "~/core/api/pm/tasks";
import type { PMUser } from "~/core/api/pm/users";
import { Loader2, BarChart3, Users, ListTodo, TrendingUp, Briefcase, Clock } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "~/components/ui/avatar";
import { Badge } from "~/components/ui/badge";
import { Progress } from "~/components/ui/progress";
import Link from "next/link";

// Helper to get start of current week (Monday)
function getWeekStart(): Date {
    const d = new Date()
    const day = d.getDay()
    const diff = d.getDate() - day + (day === 0 ? -6 : 1)
    d.setDate(diff)
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

interface TeamStats {
    teamId: string;
    teamName: string;
    members: PMUser[];
    tasks: PMTask[];
    utilization: number;
    activeProjects: number;
    availableCapacity: number;
    totalTasks: number;
}

function TeamStatsCard({ stats }: { stats: TeamStats }) {
    const utilizationColor = stats.utilization > 100 ? "text-red-500" :
        stats.utilization > 80 ? "text-yellow-500" :
            "text-green-500";

    const utilizationBg = stats.utilization > 100 ? "bg-red-500" :
        stats.utilization > 80 ? "bg-yellow-500" :
            "bg-green-500";

    return (
        <Card className="overflow-hidden">
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg flex items-center justify-center">
                            <Users className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                        </div>
                        <div>
                            <CardTitle className="text-base">{stats.teamName}</CardTitle>
                            <CardDescription>{stats.members.length} members</CardDescription>
                        </div>
                    </div>
                    <Badge variant={stats.utilization > 100 ? "destructive" : stats.utilization > 80 ? "secondary" : "default"}>
                        {stats.utilization}% utilized
                    </Badge>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Utilization Progress Bar */}
                <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>Capacity</span>
                        <span className={utilizationColor}>{stats.utilization}%</span>
                    </div>
                    <Progress value={Math.min(stats.utilization, 100)} className="h-2" />
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-3 gap-3 pt-2">
                    <div className="text-center p-2 bg-muted/30 rounded-lg">
                        <ListTodo className="w-4 h-4 mx-auto mb-1 text-blue-500" />
                        <div className="text-lg font-bold">{stats.totalTasks}</div>
                        <div className="text-[10px] text-muted-foreground">Tasks</div>
                    </div>
                    <div className="text-center p-2 bg-muted/30 rounded-lg">
                        <Briefcase className="w-4 h-4 mx-auto mb-1 text-purple-500" />
                        <div className="text-lg font-bold">{stats.activeProjects}</div>
                        <div className="text-[10px] text-muted-foreground">Projects</div>
                    </div>
                    <div className="text-center p-2 bg-muted/30 rounded-lg">
                        <Clock className="w-4 h-4 mx-auto mb-1 text-green-500" />
                        <div className="text-lg font-bold">{stats.availableCapacity}h</div>
                        <div className="text-[10px] text-muted-foreground">Available</div>
                    </div>
                </div>

                {/* Team Members Avatars */}
                <div className="flex items-center gap-1 pt-2">
                    <div className="flex -space-x-2">
                        {stats.members.slice(0, 5).map((member) => (
                            <Link key={member.id} href={`/team/member/${encodeURIComponent(member.id)}?returnTab=overview`}>
                                <Avatar className="w-7 h-7 border-2 border-background hover:opacity-80 transition-opacity">
                                    <AvatarImage src={member.avatar} />
                                    <AvatarFallback className="text-[10px]">{member.name?.[0] || "?"}</AvatarFallback>
                                </Avatar>
                            </Link>
                        ))}
                        {stats.members.length > 5 && (
                            <div className="w-7 h-7 rounded-full bg-muted border-2 border-background flex items-center justify-center text-[10px] font-medium">
                                +{stats.members.length - 5}
                            </div>
                        )}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

export function TeamOverview() {
    // Get current week's date range
    const weekRange = useMemo(() => {
        const start = getWeekStart()
        const end = new Date(start)
        end.setDate(end.getDate() + 6)
        return { start: formatDateKey(start), end: formatDateKey(end) }
    }, [])

    // Get essential data from context
    const { teams, allMemberIds, isLoading: isContextLoading } = useTeamDataContext();

    // Load heavy data for this tab
    const { allUsers, teamMembers: members, isLoading: isLoadingUsers, isFetching: isFetchingUsers, count: usersCount } = useTeamUsers(allMemberIds);
    const { allTasks, teamTasks: tasks, isLoading: isLoadingTasks, isFetching: isFetchingTasks, count: tasksCount } = useTeamTasks(allMemberIds);
    // Load time entries for current week to calculate utilization
    const { teamTimeEntries, isLoading: isLoadingTimeEntries } = useTeamTimeEntries(
        allMemberIds,
        { startDate: weekRange.start, endDate: weekRange.end }
    );

    // Calculate stats per team
    const teamStats = useMemo((): TeamStats[] => {
        if (isLoadingUsers || isLoadingTasks || isLoadingTimeEntries) {
            return [];
        }

        return teams.map(team => {
            // Get members for this team
            const teamMembers = allUsers.filter(u => team.memberIds.includes(u.id));

            // Get tasks assigned to this team's members
            const teamTasks = allTasks.filter(t =>
                t.assignee_id && team.memberIds.includes(t.assignee_id)
            );

            // Calculate utilization from LOGGED HOURS this week
            // Formula: Logged Hours / (Members × 40h) × 100%
            const teamMemberIds = team.memberIds;
            const teamLoggedEntries = teamTimeEntries.filter(te => teamMemberIds.includes(te.user_id));
            const loggedHours = teamLoggedEntries.reduce((sum, te) => sum + (te.hours || 0), 0);
            const totalCapacityHours = teamMembers.length * 40;
            const utilization = totalCapacityHours > 0
                ? Math.round((loggedHours / totalCapacityHours) * 100)
                : 0;

            // Count unique projects
            const uniqueProjects = new Set(teamTasks.map((t: PMTask) => t.project_id).filter(Boolean));

            // Available hours = Capacity - Logged
            const availableHours = Math.max(0, totalCapacityHours - loggedHours);

            return {
                teamId: team.id,
                teamName: team.name,
                members: teamMembers,
                tasks: teamTasks,
                utilization,
                activeProjects: uniqueProjects.size,
                availableCapacity: Math.round(availableHours),
                totalTasks: teamTasks.length,
            };
        });
    }, [teams, allUsers, allTasks, teamTimeEntries, isLoadingUsers, isLoadingTasks, isLoadingTimeEntries]);

    // Aggregate stats for summary
    const aggregateStats = useMemo(() => {
        if (teamStats.length === 0) {
            return { totalMembers: 0, totalTasks: 0, avgUtilization: 0, totalProjects: 0 };
        }
        const totalMembers = teamStats.reduce((sum, t) => sum + t.members.length, 0);
        const totalTasks = teamStats.reduce((sum, t) => sum + t.totalTasks, 0);
        const totalProjects = new Set(tasks.map((t: PMTask) => t.project_id).filter(Boolean)).size;
        const avgUtilization = Math.round(teamStats.reduce((sum, t) => sum + t.utilization, 0) / teamStats.length);
        return { totalMembers, totalTasks, avgUtilization, totalProjects };
    }, [teamStats, tasks]);

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

    if (teams.length === 0) {
        return (
            <Card className="p-8 text-center">
                <Users className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                <h3 className="text-lg font-semibold mb-2">No Teams Yet</h3>
                <p className="text-sm text-muted-foreground">
                    Create your first team in the Teams tab to see stats here.
                </p>
            </Card>
        );
    }

    return (
        <div className="grid gap-6">
            {/* Aggregate Summary Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border-indigo-200 dark:border-indigo-900">
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2 mb-2">
                            <Users className="w-4 h-4 text-indigo-500" />
                            <span className="text-xs text-muted-foreground">Total Members</span>
                        </div>
                        <div className="text-2xl font-bold">{aggregateStats.totalMembers}</div>
                    </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border-blue-200 dark:border-blue-900">
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2 mb-2">
                            <ListTodo className="w-4 h-4 text-blue-500" />
                            <span className="text-xs text-muted-foreground">Total Tasks</span>
                        </div>
                        <div className="text-2xl font-bold">{aggregateStats.totalTasks}</div>
                    </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-green-500/10 to-emerald-500/10 border-green-200 dark:border-green-900">
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2 mb-2">
                            <TrendingUp className="w-4 h-4 text-green-500" />
                            <span className="text-xs text-muted-foreground">Avg Utilization</span>
                        </div>
                        <div className="text-2xl font-bold">{aggregateStats.avgUtilization}%</div>
                    </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 border-purple-200 dark:border-purple-900">
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2 mb-2">
                            <Briefcase className="w-4 h-4 text-purple-500" />
                            <span className="text-xs text-muted-foreground">Active Projects</span>
                        </div>
                        <div className="text-2xl font-bold">{aggregateStats.totalProjects}</div>
                    </CardContent>
                </Card>
            </div>

            {/* Per-Team Stats Cards */}
            <div>
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Users className="w-5 h-5" />
                    Team Stats ({teams.length} teams)
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {teamStats.map(stats => (
                        <TeamStatsCard key={stats.teamId} stats={stats} />
                    ))}
                </div>
            </div>

            <WorkloadCharts />
        </div>
    );
}
