"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "~/components/ui/card";
import { WorkloadCharts } from "./workload-charts";
import { useTeamDataContext, useTeamUsers, useTeamTasks, useTeamTimeEntries } from "../context/team-data-context";
import { useMemo, useState } from "react";
import type { PMTask } from "~/core/api/pm/tasks";
import type { PMUser } from "~/core/api/pm/users";
import { BarChart3, Users, ListTodo, TrendingUp, Briefcase, Clock, ChevronLeft, ChevronRight, CalendarIcon } from "lucide-react";
import { WorkspaceLoading } from "~/components/ui/workspace-loading";
import { Avatar, AvatarFallback, AvatarImage } from "~/components/ui/avatar";
import { Badge } from "~/components/ui/badge";
import { Progress } from "~/components/ui/progress";
import { useMemberProfile } from "../context/member-profile-context";
import { useProjects } from "~/core/api/hooks/pm/use-projects";
import { useCardGlow, useStatCardGlow } from "~/core/hooks/use-theme-colors";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { Button } from "~/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "~/components/ui/popover";
import { Calendar } from "~/components/ui/calendar";

// Color palette for pie chart
const PIE_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#10b981'];

// Helper to get start of week (Monday) with offset
function getWeekStart(weekOffset: number = 0): Date {
    const d = new Date()
    const day = d.getDay()
    const diff = d.getDate() - day + (day === 0 ? -6 : 1)
    d.setDate(diff + (weekOffset * 7))
    d.setHours(0, 0, 0, 0)
    return d
}

// Format date for display
function formatDateDisplay(date: Date): string {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
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

export function TeamOverview({ configuredMemberIds, providerId }: { configuredMemberIds?: string[], providerId?: string }) {
    // Get configurable glow classes from theme settings
    const cardGlow = useCardGlow();
    const statCardGlow = useStatCardGlow();

    // Week navigation state for Project Distribution
    const [weekOffset, setWeekOffset] = useState(0)
    const [datePickerOpen, setDatePickerOpen] = useState(false)
    const isCurrentWeek = weekOffset === 0

    // Helper to compute week offset from a specific date
    const getWeekOffsetForDate = (date: Date): number => {
        const currentWeekStart = getWeekStart(0)
        const targetWeekStart = new Date(date)
        const day = targetWeekStart.getDay()
        const diff = targetWeekStart.getDate() - day + (day === 0 ? -6 : 1)
        targetWeekStart.setDate(diff)
        targetWeekStart.setHours(0, 0, 0, 0)
        const diffTime = targetWeekStart.getTime() - currentWeekStart.getTime()
        return Math.round(diffTime / (7 * 24 * 60 * 60 * 1000))
    }

    // Handle date selection from calendar
    const handleDateSelect = (date: Date | undefined) => {
        if (date) setWeekOffset(getWeekOffsetForDate(date))
        setDatePickerOpen(false)
    }

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

    // Get essential data from context
    const { teams: contextTeams, allMemberIds: contextAllMemberIds, isLoading: isContextLoading } = useTeamDataContext();

    // Determine effective teams and member IDs based on configuration
    const { effectiveTeams, effectiveMemberIds } = useMemo(() => {
        // Check if configuredMemberIds is DEFINED (not undefined/null)
        if (configuredMemberIds) {
            if (configuredMemberIds.length > 0) {
                // If custom members are selected, create a synthetic team
                return {
                    effectiveTeams: [{
                        id: 'custom-view',
                        name: 'Selected Team',
                        memberIds: configuredMemberIds,
                        projectId: '', // N/A
                        createdAt: '', // N/A
                        updatedAt: ''  // N/A
                    }],
                    effectiveMemberIds: configuredMemberIds
                };
            } else {
                // EXPLICITLY EMPTY selection -> Show nothing (do not fall back to default)
                return {
                    effectiveTeams: [],
                    effectiveMemberIds: []
                };
            }
        }

        // Undefined/null configuration -> Fallback to default context (all teams)
        return {
            effectiveTeams: contextTeams,
            effectiveMemberIds: contextAllMemberIds
        };
    }, [configuredMemberIds, contextTeams, contextAllMemberIds]);

    // Load heavy data for this tab (using effective IDs)
    // Note: useTeamUsers doesn't strictly need providerId as it loads by ID, but we could enforce it if needed.
    // However, tasks and time entries absolutely need the provider context if supplied.
    const { allUsers, teamMembers: members, isLoading: isLoadingUsers, isFetching: isFetchingUsers, count: usersCount } = useTeamUsers(effectiveMemberIds);

    // Pass providerId explicitly to ensure data is fetched from the correct source
    const { allTasks, teamTasks: tasks, isLoading: isLoadingTasks, isFetching: isFetchingTasks, count: tasksCount } = useTeamTasks(effectiveMemberIds, { status: 'open', providerId });
    // [NEW] Fetch ALL history (including closed tasks) for Team Experience aggregation
    const { allTasks: allHistoryTasks, isLoading: isLoadingHistoryTasks } = useTeamTasks(effectiveMemberIds, { status: 'all', providerId });
    // Load time entries for current week to calculate utilization
    const { teamTimeEntries, isLoading: isLoadingTimeEntries } = useTeamTimeEntries(
        effectiveMemberIds,
        { startDate: weekRange.start, endDate: weekRange.end, providerId }
    );

    // Calculate stats per team
    const teamStats = useMemo((): TeamStats[] => {
        if (isLoadingUsers || isLoadingTasks || isLoadingTimeEntries) {
            return [];
        }

        return effectiveTeams.map(team => {
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
    }, [effectiveTeams, allUsers, allTasks, teamTimeEntries, isLoadingUsers, isLoadingTasks, isLoadingTimeEntries]);

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

    // Per-team project distribution based on WORKLOGS (time entries)
    const perTeamExperience = useMemo(() => {
        return effectiveTeams.map(team => {
            // Group time entries by project for this team's members
            const teamEntries = teamTimeEntries.filter(te => team.memberIds.includes(te.user_id));
            const projectMap = new Map<string, { id: string; name: string; hours: number; entryCount: number }>();

            teamEntries.forEach(entry => {
                // Use project_id directly from time entry (enriched by backend)
                const projectId = entry.project_id || 'unassigned';
                const projectName = getProjectName(projectId);
                const existing = projectMap.get(projectId) || { id: projectId, name: projectName, hours: 0, entryCount: 0 };
                existing.hours += entry.hours || 0;
                existing.entryCount += 1;
                projectMap.set(projectId, existing);
            });

            const distribution = Array.from(projectMap.values())
                .filter(p => p.hours > 0)
                .sort((a, b) => b.hours - a.hours);
            return {
                teamId: team.id,
                teamName: team.name,
                distribution,
                totalHours: distribution.reduce((sum, p) => sum + p.hours, 0),
            };
        }).filter(t => t.distribution.length > 0);
    }, [effectiveTeams, teamTimeEntries, projects]);

    const isLoading = isContextLoading || isLoadingUsers || isLoadingTasks || isFetchingUsers || isFetchingTasks || isLoadingHistoryTasks;

    if (isLoading) {
        return (
            <WorkspaceLoading
                title="Loading Overview"
                subtitle="Calculating team metrics..."
                items={[
                    { label: "Users", isLoading: isLoadingUsers || isFetchingUsers, count: usersCount },
                    { label: "Tasks", isLoading: isLoadingTasks || isFetchingTasks, count: tasksCount },
                ]}
                icon={<BarChart3 className="w-6 h-6 text-white" />}
            />
        );
    }

    if (effectiveTeams.length === 0) {
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
                <Card className={`bg-gradient-to-br from-indigo-500/10 to-purple-500/10 ${statCardGlow.className}`}>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2 mb-2">
                            <Users className="w-4 h-4 text-indigo-500" />
                            <span className="text-xs text-muted-foreground">Total Members</span>
                        </div>
                        <div className="text-2xl font-bold">{aggregateStats.totalMembers}</div>
                    </CardContent>
                </Card>
                <Card className={`bg-gradient-to-br from-blue-500/10 to-cyan-500/10 ${statCardGlow.className}`}>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2 mb-2">
                            <ListTodo className="w-4 h-4 text-blue-500" />
                            <span className="text-xs text-muted-foreground">Total Tasks</span>
                        </div>
                        <div className="text-2xl font-bold">{aggregateStats.totalTasks}</div>
                    </CardContent>
                </Card>
                <Card className={`bg-gradient-to-br from-green-500/10 to-emerald-500/10 ${statCardGlow.className}`}>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2 mb-2">
                            <TrendingUp className="w-4 h-4 text-green-500" />
                            <span className="text-xs text-muted-foreground">Avg Utilization</span>
                        </div>
                        <div className="text-2xl font-bold">{aggregateStats.avgUtilization}%</div>
                    </CardContent>
                </Card>
                <Card className={`bg-gradient-to-br from-purple-500/10 to-pink-500/10 ${statCardGlow.className}`}>
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
                    <Card className={`col-span-5 ${cardGlow.className}`}>
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle className="flex items-center gap-2">
                                        <Briefcase className="w-5 h-5" />
                                        Project Distribution
                                    </CardTitle>
                                    <CardDescription>
                                        {teamData.totalHours.toFixed(0)}h logged across {teamData.distribution.length} projects
                                    </CardDescription>
                                </div>
                                {/* Date range picker */}
                                <div className="flex items-center gap-2">
                                    <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-1">
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-7 w-7"
                                            onClick={() => setWeekOffset(prev => prev - 1)}
                                        >
                                            <ChevronLeft className="h-4 w-4" />
                                        </Button>
                                        <Popover open={datePickerOpen} onOpenChange={setDatePickerOpen}>
                                            <PopoverTrigger asChild>
                                                <Button
                                                    variant="ghost"
                                                    className="h-7 px-2 min-w-[140px] text-center text-sm font-medium hover:bg-muted"
                                                >
                                                    <CalendarIcon className="h-3 w-3 mr-1.5 text-muted-foreground" />
                                                    {weekRange.displayRange}
                                                </Button>
                                            </PopoverTrigger>
                                            <PopoverContent className="w-auto p-0" align="center">
                                                <Calendar
                                                    mode="single"
                                                    selected={weekRange.startDate}
                                                    defaultMonth={weekRange.startDate}
                                                    onSelect={handleDateSelect}
                                                    initialFocus
                                                />
                                            </PopoverContent>
                                        </Popover>
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
                                                data={teamData.distribution.slice(0, 8).map((p: { name: string; hours: number }) => ({ name: p.name, value: p.hours }))}
                                                cx="50%"
                                                cy="50%"
                                                innerRadius={55}
                                                outerRadius={100}
                                                dataKey="value"
                                                strokeWidth={1}
                                            >
                                                {teamData.distribution.slice(0, 8).map((_: unknown, i: number) => (
                                                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                                                ))}
                                            </Pie>
                                            <Tooltip formatter={(value) => typeof value === 'number' ? `${value.toFixed(1)}h` : value} />
                                        </PieChart>
                                    </ResponsiveContainer>
                                </div>
                                {/* Project badges */}
                                <div className="flex-1 flex flex-wrap gap-2 content-start">
                                    {teamData.distribution.slice(0, 10).map((proj: { id: string; name: string; hours: number; entryCount: number }, idx: number) => (
                                        <span
                                            key={proj.id}
                                            className="inline-flex items-center gap-1.5 bg-gray-100 dark:bg-gray-800 rounded-full px-3 py-1 text-xs hover:bg-indigo-100 dark:hover:bg-indigo-900/30 transition-colors cursor-default"
                                            title={`${proj.name}: ${proj.hours.toFixed(1)}h (${proj.entryCount} entries)`}
                                            style={{ borderLeft: `3px solid ${PIE_COLORS[idx % PIE_COLORS.length]}` }}
                                        >
                                            <span className="font-medium text-gray-700 dark:text-gray-300 max-w-[100px] truncate">{proj.name}</span>
                                            <span className="font-bold text-indigo-600 dark:text-indigo-400">{proj.hours.toFixed(0)}h</span>
                                        </span>
                                    ))}
                                    {teamData.distribution.length > 10 && (
                                        <span className="text-xs text-muted-foreground px-2">+{teamData.distribution.length - 10} more</span>
                                    )}
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Details Card - col-span-2 */}
                    <Card className={`col-span-2 ${cardGlow.className}`}>
                        <CardHeader>
                            <CardTitle>Project Details</CardTitle>
                            <CardDescription>All projects ({teamData.distribution.length})</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
                                {teamData.distribution.map((proj: { id: string; name: string; hours: number; entryCount: number }, idx: number) => (
                                    <div key={proj.id} className="flex items-center">
                                        <div
                                            className="w-2 h-2 rounded-full shrink-0 mr-2"
                                            style={{ backgroundColor: PIE_COLORS[idx % PIE_COLORS.length] }}
                                        />
                                        <div className="flex-1 space-y-0.5 min-w-0">
                                            <p className="text-sm font-medium leading-none truncate">{proj.name}</p>
                                            <p className="text-xs text-muted-foreground">
                                                {proj.entryCount} entries
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

            <WorkloadCharts effectiveMemberIds={effectiveMemberIds} effectiveTeams={effectiveTeams} />
        </div>
    );
}
