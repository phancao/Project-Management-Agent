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
import { useMemberProfile } from "../page";
import { useProjects } from "~/core/api/hooks/pm/use-projects";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

// Color palette for pie chart
const PIE_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#10b981'];

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
                            <MemberAvatar key={member.id} member={member} />
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

// Clickable avatar that opens member profile dialog
function MemberAvatar({ member }: { member: PMUser }) {
    const { openMemberProfile } = useMemberProfile();
    return (
        <button
            onClick={() => openMemberProfile(member.id)}
            className="focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 rounded-full"
        >
            <Avatar className="w-7 h-7 border-2 border-background hover:opacity-80 transition-opacity cursor-pointer">
                <AvatarImage src={member.avatar} />
                <AvatarFallback className="text-[10px]">{member.name?.[0] || "?"}</AvatarFallback>
            </Avatar>
        </button>
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

    // Team Experience - aggregate spent hours by project per team
    const { projects } = useProjects();
    const getProjectName = (id?: string) => {
        if (!id) return 'Unassigned';
        const proj = projects.find(p => p.id === id);
        return proj ? proj.name : id.split(':').pop() || id;
    };

    // Per-team experience breakdown
    const perTeamExperience = useMemo(() => {
        return teams.map(team => {
            const teamTasks = allTasks.filter(t =>
                t.assignee_id && team.memberIds.includes(t.assignee_id)
            );
            const projectMap = new Map<string, { id: string; name: string; hours: number; taskCount: number }>();
            teamTasks.forEach((task: PMTask) => {
                const projectId = task.project_id || 'unassigned';
                const projectName = getProjectName(projectId);
                const existing = projectMap.get(projectId) || { id: projectId, name: projectName, hours: 0, taskCount: 0 };
                existing.hours += task.spent_hours || 0;
                existing.taskCount += 1;
                projectMap.set(projectId, existing);
            });
            const experience = Array.from(projectMap.values())
                .filter(p => p.hours > 0 || p.taskCount > 0)
                .sort((a, b) => b.hours - a.hours);
            return {
                teamId: team.id,
                teamName: team.name,
                experience,
                totalHours: experience.reduce((sum, p) => sum + p.hours, 0),
            };
        }).filter(t => t.experience.length > 0);
    }, [teams, allTasks, projects]);

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

            {/* Team Experience Section - Same layout as Team Workload */}
            {perTeamExperience.map((teamData) => (
                <div key={teamData.teamId} className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
                    {/* Main Chart Card - col-span-5 */}
                    <Card className="col-span-5">
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle className="flex items-center gap-2">
                                        <Briefcase className="w-5 h-5" />
                                        {teamData.teamName}
                                    </CardTitle>
                                    <CardDescription>
                                        {teamData.totalHours.toFixed(0)}h logged across {teamData.experience.length} projects
                                    </CardDescription>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="pt-0">
                            <div className="flex gap-6 items-center">
                                {/* Larger Pie chart */}
                                <div className="w-56 h-56 shrink-0">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <PieChart>
                                            <Pie
                                                data={teamData.experience.slice(0, 8).map((p: { name: string; hours: number }) => ({ name: p.name, value: p.hours }))}
                                                cx="50%"
                                                cy="50%"
                                                innerRadius={55}
                                                outerRadius={100}
                                                dataKey="value"
                                                strokeWidth={1}
                                            >
                                                {teamData.experience.slice(0, 8).map((_: unknown, i: number) => (
                                                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                                                ))}
                                            </Pie>
                                            <Tooltip formatter={(value) => typeof value === 'number' ? `${value.toFixed(1)}h` : value} />
                                        </PieChart>
                                    </ResponsiveContainer>
                                </div>
                                {/* Project badges */}
                                <div className="flex-1 flex flex-wrap gap-2 content-start">
                                    {teamData.experience.slice(0, 10).map((proj: { id: string; name: string; hours: number; taskCount: number }, idx: number) => (
                                        <span
                                            key={proj.id}
                                            className="inline-flex items-center gap-1.5 bg-gray-100 dark:bg-gray-800 rounded-full px-3 py-1 text-xs hover:bg-indigo-100 dark:hover:bg-indigo-900/30 transition-colors cursor-default"
                                            title={`${proj.name}: ${proj.hours.toFixed(1)}h across ${proj.taskCount} tasks`}
                                            style={{ borderLeft: `3px solid ${PIE_COLORS[idx % PIE_COLORS.length]}` }}
                                        >
                                            <span className="font-medium text-gray-700 dark:text-gray-300 max-w-[100px] truncate">{proj.name}</span>
                                            <span className="font-bold text-indigo-600 dark:text-indigo-400">{proj.hours.toFixed(0)}h</span>
                                        </span>
                                    ))}
                                    {teamData.experience.length > 10 && (
                                        <span className="text-xs text-muted-foreground px-2">+{teamData.experience.length - 10} more</span>
                                    )}
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Details Card - col-span-2 */}
                    <Card className="col-span-2">
                        <CardHeader>
                            <CardTitle>Project Details</CardTitle>
                            <CardDescription>All projects ({teamData.experience.length})</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
                                {teamData.experience.map((proj: { id: string; name: string; hours: number; taskCount: number }, idx: number) => (
                                    <div key={proj.id} className="flex items-center">
                                        <div
                                            className="w-2 h-2 rounded-full shrink-0 mr-2"
                                            style={{ backgroundColor: PIE_COLORS[idx % PIE_COLORS.length] }}
                                        />
                                        <div className="flex-1 space-y-0.5 min-w-0">
                                            <p className="text-sm font-medium leading-none truncate">{proj.name}</p>
                                            <p className="text-xs text-muted-foreground">
                                                {proj.taskCount} tasks
                                            </p>
                                        </div>
                                        <div className="font-bold text-sm text-indigo-600 dark:text-indigo-400 shrink-0">
                                            {proj.hours.toFixed(0)}h
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            ))}

            <WorkloadCharts />
        </div>
    );
}
