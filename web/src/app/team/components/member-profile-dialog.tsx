'use client';

import { useMemo, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "~/components/ui/dialog";
import { Avatar, AvatarFallback, AvatarImage } from "~/components/ui/avatar";
import { Badge } from "~/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Clock, CheckCircle2, CircleDashed, AlertCircle, ExternalLink, GripHorizontal, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from "~/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { useProjects } from "~/core/api/hooks/pm/use-projects";
import { useProviders } from "~/core/api/hooks/pm/use-providers";
import { useTeamDataContext, useTeamUsers, useTeamTasks } from "../context/team-data-context";
import { extractShortId } from "~/core/api/pm/users";
import type { PMUser } from "~/core/api/pm/users";
import type { PMTask } from "~/core/api/pm/tasks";
import { Loader2 } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

// Color palette for pie chart
const PIE_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#10b981'];

interface MemberProfileDialogProps {
    memberId: string | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function MemberProfileDialog({ memberId, open, onOpenChange }: MemberProfileDialogProps) {
    const { allMemberIds, isLoading: isContextLoading } = useTeamDataContext();
    const { teamMembers, isLoading: isLoadingUsers } = useTeamUsers(allMemberIds);
    const { teamTasks, isLoading: isLoadingTasks } = useTeamTasks(allMemberIds);
    const { projects } = useProjects();
    const { providers } = useProviders();

    const isLoading = isContextLoading || isLoadingUsers || isLoadingTasks;

    const member = useMemo(() =>
        teamMembers.find((m: PMUser) => m.id === memberId),
        [teamMembers, memberId]
    );

    // Filter tasks for this member using shortId for proper matching
    const memberShortId = member?.shortId || (member ? extractShortId(member.id) : '');
    const memberTasks = useMemo(() =>
        teamTasks.filter((t: PMTask) => {
            if (!t.assignee_id || !member) return false;
            const taskAssigneeShortId = extractShortId(t.assignee_id);
            return t.assignee_id === member.id ||
                t.assignee_id === memberShortId ||
                taskAssigneeShortId === memberShortId;
        }),
        [teamTasks, member, memberShortId]
    );

    // Stats
    const completedTasks = memberTasks.filter((t: PMTask) =>
        ['done', 'closed', 'rejected'].includes((t.status || '').toLowerCase())
    ).length;
    const activeTasks = memberTasks.filter((t: PMTask) =>
        !['done', 'closed', 'rejected'].includes((t.status || '').toLowerCase())
    );

    // Calculate Hours
    const totalEstimated = activeTasks.reduce((sum: number, t: PMTask) => sum + (t.estimated_hours || 0), 0);
    const totalSpent = activeTasks.reduce((sum: number, t: PMTask) => sum + (t.spent_hours || 0), 0);
    const remainingHours = Math.max(0, totalEstimated - totalSpent);

    // Helper to get Project Name (defined before projectAchievements which uses it)
    const getProjectName = (id?: string) => {
        if (!id) return 'Unassigned';
        const proj = projects.find(p => p.id === id);
        return proj ? proj.name : id.split(':').pop();
    };

    // Project Achievements - Group all tasks by project and sum spent hours
    const projectAchievements = useMemo(() => {
        const projectMap = new Map<string, { id: string; name: string; hours: number; taskCount: number }>();
        memberTasks.forEach(task => {
            const projectId = task.project_id || 'unassigned';
            const projectName = getProjectName(projectId) || 'Unassigned';
            const existing = projectMap.get(projectId) || { id: projectId, name: projectName, hours: 0, taskCount: 0 };
            existing.hours += task.spent_hours || 0;
            existing.taskCount += 1;
            projectMap.set(projectId, existing);
        });
        return Array.from(projectMap.values())
            .filter(p => p.hours > 0 || p.taskCount > 0)
            .sort((a, b) => b.hours - a.hours);
    }, [memberTasks, projects]);

    // Week navigation state for date-grouped view  
    const [weekOffset, setWeekOffset] = useState(0);

    // Helper to get week date range
    const weekRange = useMemo(() => {
        const today = new Date();
        const day = today.getDay();
        const diff = today.getDate() - day + (day === 0 ? -6 : 1); // Monday
        const start = new Date(today);
        start.setDate(diff + (weekOffset * 7));
        start.setHours(0, 0, 0, 0);
        const end = new Date(start);
        end.setDate(end.getDate() + 6);
        return { start, end };
    }, [weekOffset]);

    // Format date for display
    const formatDateDisplay = (date: Date) => {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    };

    // Group tasks by status for categorized view
    const tasksByStatus = useMemo(() => {
        const statusOrder = ['In progress', 'New', 'Specified', 'Developed', 'Ready4SIT', 'Passed', 'Other'];
        const grouped = new Map<string, PMTask[]>();

        memberTasks.forEach(task => {
            const status = task.status || 'Other';
            // Normalize status for grouping
            let statusKey = statusOrder.find(s => status.toLowerCase().includes(s.toLowerCase())) || 'Other';
            if (!grouped.has(statusKey)) {
                grouped.set(statusKey, []);
            }
            grouped.get(statusKey)?.push(task);
        });

        // Sort by status order
        return Array.from(grouped.entries()).sort((a, b) => {
            const aIdx = statusOrder.indexOf(a[0]);
            const bIdx = statusOrder.indexOf(b[0]);
            return (aIdx === -1 ? 999 : aIdx) - (bIdx === -1 ? 999 : bIdx);
        });
    }, [memberTasks]);

    // Helper to generate Task URL
    const getTaskUrl = (task: PMTask) => {
        if (!task || !task.id) return '#';
        const id = task.id;
        const parts = id.split(':');
        const localId = parts[parts.length - 1]; // Always the last part

        // [DEBUG] Log provider matching
        console.log('[TASK_URL_DEBUG]', {
            taskId: id,
            localId,
            providersCount: providers.length,
            providerIds: providers.map(p => p.id),
        });

        // Try multiple matching strategies:
        // 1. Match entire prefix (before last colon) against provider ID
        // 2. Match first part against provider type
        // 3. Check if task ID starts with any provider ID
        let providerConfig = null;

        // Strategy 1: Exact prefix match on provider ID
        const prefixWithoutLocalId = parts.slice(0, -1).join(':');
        providerConfig = providers.find(p => p.id === prefixWithoutLocalId);

        // Strategy 2: First part matches provider type
        if (!providerConfig) {
            const firstPart = parts[0];
            providerConfig = providers.find(p => p.provider_type === firstPart);
        }

        // Strategy 3: Task ID starts with provider ID
        if (!providerConfig) {
            providerConfig = providers.find(p => id.startsWith(p.id + ':'));
        }

        // Strategy 4: Just use first provider if only one exists
        if (!providerConfig && providers.length === 1) {
            providerConfig = providers[0];
        }

        console.log('[TASK_URL_DEBUG] Match result:', {
            matchedProvider: providerConfig ? { id: providerConfig.id, type: providerConfig.provider_type, base: providerConfig.base_url } : 'NOT_FOUND'
        });

        if (providerConfig) {
            const type = providerConfig.provider_type;
            const baseUrl = providerConfig.base_url || 'https://openproject.bstarsolutions.com';

            if (type === 'openproject' || type === 'openproject_v13') {
                const cleanBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
                return `${cleanBase}/work_packages/${localId}`;
            }
        }

        return '#';
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent
                className="w-[90vw] max-w-[900px] h-[85vh] overflow-hidden flex flex-col p-0 resize"
                style={{ minWidth: '700px', minHeight: '400px' }}
            >
                {isLoading ? (
                    <div className="flex items-center justify-center h-64">
                        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
                    </div>
                ) : !member ? (
                    <div className="text-center py-12">
                        <p className="text-muted-foreground">Member not found</p>
                    </div>
                ) : (
                    <>
                        {/* Header */}
                        <DialogHeader className="shrink-0 p-6 pb-4 border-b">
                            <div className="flex items-center gap-4">
                                <Avatar className="w-14 h-14 border-2 border-white dark:border-gray-800 shadow-lg">
                                    <AvatarImage src={member.avatar} />
                                    <AvatarFallback className="text-lg bg-indigo-100 text-indigo-700">
                                        {member.name[0]}
                                    </AvatarFallback>
                                </Avatar>
                                <div className="min-w-0 flex-1">
                                    <DialogTitle className="text-xl truncate">{member.name}</DialogTitle>
                                    <DialogDescription className="flex items-center gap-2 mt-1 flex-wrap">
                                        <Badge variant="secondary" className="font-normal text-xs">{member.email}</Badge>
                                        <Badge variant="outline" className="text-[10px]">ID: {member.id.split(':').pop()}</Badge>
                                    </DialogDescription>
                                </div>
                            </div>
                        </DialogHeader>

                        {/* Content - Flex column to fill available space */}
                        <div className="flex-1 overflow-hidden flex flex-col p-6 pt-4 gap-4">
                            {/* Stats Grid - Fixed height */}
                            <div className="grid grid-cols-4 gap-2 shrink-0">
                                <div className="bg-gradient-to-br from-indigo-50 to-white dark:from-indigo-950/30 dark:to-gray-900 rounded-xl p-3 border border-indigo-100 dark:border-indigo-900/50">
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="text-[10px] font-medium text-indigo-600 dark:text-indigo-400 uppercase tracking-wide">Active</span>
                                        <CircleDashed className="w-4 h-4 text-indigo-400" />
                                    </div>
                                    <p className="text-2xl font-bold text-gray-900 dark:text-white">{activeTasks.length}</p>
                                </div>
                                <div className="bg-gradient-to-br from-green-50 to-white dark:from-green-950/30 dark:to-gray-900 rounded-xl p-3 border border-green-100 dark:border-green-900/50">
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="text-[10px] font-medium text-green-600 dark:text-green-400 uppercase tracking-wide">Done</span>
                                        <CheckCircle2 className="w-4 h-4 text-green-400" />
                                    </div>
                                    <p className="text-2xl font-bold text-gray-900 dark:text-white">{completedTasks}</p>
                                </div>
                                <div className="bg-gradient-to-br from-amber-50 to-white dark:from-amber-950/30 dark:to-gray-900 rounded-xl p-3 border border-amber-100 dark:border-amber-900/50">
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="text-[10px] font-medium text-amber-600 dark:text-amber-400 uppercase tracking-wide">Estimated</span>
                                        <Clock className="w-4 h-4 text-amber-400" />
                                    </div>
                                    <p className="text-2xl font-bold text-gray-900 dark:text-white">{totalEstimated.toFixed(0)}h</p>
                                </div>
                                <div className="bg-gradient-to-br from-purple-50 to-white dark:from-purple-950/30 dark:to-gray-900 rounded-xl p-3 border border-purple-100 dark:border-purple-900/50">
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="text-[10px] font-medium text-purple-600 dark:text-purple-400 uppercase tracking-wide">Remaining</span>
                                        <AlertCircle className="w-4 h-4 text-purple-400" />
                                    </div>
                                    <p className="text-2xl font-bold text-gray-900 dark:text-white">{remainingHours.toFixed(0)}h</p>
                                </div>
                            </div>

                            {/* Experience Section - Hashtags + Pie Chart */}
                            {projectAchievements.length > 0 && (
                                <div className="shrink-0">
                                    <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                                        Experience ({projectAchievements.length} projects)
                                    </h3>
                                    <div className="flex gap-4 items-start">
                                        {/* Pie chart - left side */}
                                        <div className="w-28 h-28 shrink-0">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <PieChart>
                                                    <Pie
                                                        data={projectAchievements.slice(0, 8).map((p) => ({ name: p.name, value: p.hours }))}
                                                        cx="50%"
                                                        cy="50%"
                                                        innerRadius={25}
                                                        outerRadius={50}
                                                        dataKey="value"
                                                        strokeWidth={1}
                                                    >
                                                        {projectAchievements.slice(0, 8).map((_, i) => (
                                                            <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                                                        ))}
                                                    </Pie>
                                                    <Tooltip formatter={(value) => typeof value === 'number' ? `${value.toFixed(1)}h` : value} />
                                                </PieChart>
                                            </ResponsiveContainer>
                                        </div>
                                        {/* Hashtag badges - right side */}
                                        <div className="flex-1 flex flex-wrap gap-1.5 content-start">
                                            {projectAchievements.map((proj, idx) => (
                                                <span
                                                    key={proj.id}
                                                    className="inline-flex items-center gap-1.5 bg-gray-100 dark:bg-gray-800 rounded-full px-2.5 py-1 text-xs hover:bg-indigo-100 dark:hover:bg-indigo-900/30 transition-colors cursor-default"
                                                    title={`${proj.name}: ${proj.hours.toFixed(1)}h across ${proj.taskCount} tasks`}
                                                    style={{ borderLeft: `3px solid ${PIE_COLORS[idx % PIE_COLORS.length]}` }}
                                                >
                                                    <span className="font-medium text-gray-700 dark:text-gray-300 max-w-[80px] truncate">{proj.name}</span>
                                                    <span className="font-bold text-indigo-600 dark:text-indigo-400">{proj.hours.toFixed(0)}h</span>
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Tasks Card - Flex grow to fill remaining space */}
                            <Card className="flex-1 flex flex-col min-h-0 overflow-hidden border-0 shadow-none">
                                <CardContent className="p-0 flex-1 flex flex-col min-h-0 overflow-hidden">
                                    <Tabs defaultValue="active" className="flex-1 flex flex-col min-h-0">
                                        <div className="flex items-center justify-between px-3 py-1 shrink-0 border-b">
                                            <span className="text-xs font-semibold text-muted-foreground uppercase">Assignments</span>
                                            <TabsList className="h-6">
                                                <TabsTrigger value="active" className="text-[10px] px-2 py-0.5">Active ({activeTasks.length})</TabsTrigger>
                                                <TabsTrigger value="all" className="text-[10px] px-2 py-0.5">All ({memberTasks.length})</TabsTrigger>
                                                <TabsTrigger value="bystatus" className="text-[10px] px-2 py-0.5">By Status</TabsTrigger>
                                            </TabsList>
                                        </div>

                                        <TabsContent value="active" className="mt-0 flex-1 overflow-auto">
                                            <TaskTable tasks={activeTasks} getProjectName={getProjectName} getTaskUrl={getTaskUrl} />
                                        </TabsContent>

                                        <TabsContent value="all" className="mt-0 flex-1 overflow-auto">
                                            <TaskTable tasks={memberTasks} getProjectName={getProjectName} getTaskUrl={getTaskUrl} />
                                        </TabsContent>

                                        <TabsContent value="bystatus" className="mt-0 flex-1 overflow-auto">
                                            {/* Status-grouped tasks */}
                                            <div className="p-3 space-y-3">
                                                {tasksByStatus.length === 0 ? (
                                                    <p className="text-center text-sm text-muted-foreground py-8">No tasks</p>
                                                ) : (
                                                    tasksByStatus.map(([statusKey, tasks]: [string, PMTask[]]) => (
                                                        <div key={statusKey} className="space-y-1">
                                                            <div className="flex items-center gap-2 sticky top-0 bg-background py-1">
                                                                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${statusKey.toLowerCase().includes('progress') ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' :
                                                                    statusKey.toLowerCase().includes('new') ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                                                                        statusKey.toLowerCase().includes('passed') ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                                                                            'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                                                                    }`}>
                                                                    {statusKey}
                                                                </span>
                                                                <Badge variant="outline" className="text-[10px]">{tasks.length}</Badge>
                                                            </div>
                                                            <div className="space-y-1 pl-2">
                                                                {tasks.slice(0, 10).map((task: PMTask) => (
                                                                    <div key={task.id} className="flex items-center gap-2 py-1 text-xs">
                                                                        <Badge variant="outline" className="text-[9px] shrink-0 max-w-[80px] truncate">
                                                                            {getProjectName(task.project_id)}
                                                                        </Badge>
                                                                        <a
                                                                            href={getTaskUrl(task)}
                                                                            target="_blank"
                                                                            rel="noopener noreferrer"
                                                                            className="flex-1 truncate hover:text-indigo-600"
                                                                        >
                                                                            {task.title || task.name}
                                                                        </a>
                                                                        <span className="text-[10px] text-muted-foreground font-mono shrink-0">
                                                                            {task.estimated_hours || 0}h
                                                                        </span>
                                                                    </div>
                                                                ))}
                                                                {tasks.length > 10 && (
                                                                    <p className="text-[10px] text-muted-foreground pl-2">+{tasks.length - 10} more</p>
                                                                )}
                                                            </div>
                                                        </div>
                                                    ))
                                                )}
                                            </div>
                                        </TabsContent>
                                    </Tabs>
                                </CardContent>
                            </Card>
                        </div>
                    </>
                )}

                {/* Resize Handle Indicator */}
                <div className="absolute bottom-1 right-1 text-gray-300 dark:text-gray-700 pointer-events-none">
                    <GripHorizontal className="w-4 h-4 rotate-[-45deg]" />
                </div>
            </DialogContent>
        </Dialog>
    );
}

// Separate component for the task table
function TaskTable({
    tasks,
    getProjectName,
    getTaskUrl
}: {
    tasks: PMTask[];
    getProjectName: (id?: string) => string | undefined;
    getTaskUrl: (task: PMTask) => string;
}) {
    if (tasks.length === 0) {
        return (
            <div className="text-center py-8 text-muted-foreground text-sm">
                No tasks found.
            </div>
        );
    }

    return (
        <Table>
            <TableHeader>
                <TableRow className="bg-muted/50">
                    <TableHead className="text-xs">Project</TableHead>
                    <TableHead className="text-xs">Task</TableHead>
                    <TableHead className="text-xs">Status</TableHead>
                    <TableHead className="text-xs text-right w-16">Est.</TableHead>
                    <TableHead className="text-xs text-right w-16">Spent</TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {tasks.map((task: PMTask) => (
                    <TableRow key={task.id} className="group hover:bg-muted/30">
                        <TableCell className="py-2">
                            <Badge variant="outline" className="font-normal text-[10px] whitespace-nowrap max-w-[120px] truncate block">
                                {getProjectName(task.project_id)}
                            </Badge>
                        </TableCell>
                        <TableCell className="py-2">
                            <a
                                href={getTaskUrl(task)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs font-medium hover:text-indigo-600 dark:hover:text-indigo-400 line-clamp-1"
                                title={task.title || task.name}
                            >
                                {task.title || task.name}
                                {getTaskUrl(task) !== '#' && (
                                    <ExternalLink className="w-3 h-3 inline ml-1 opacity-50" />
                                )}
                            </a>
                        </TableCell>
                        <TableCell className="py-2">
                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium whitespace-nowrap ${(task.status || '').toLowerCase().includes('progress')
                                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                                : (task.status || '').toLowerCase().includes('done') || (task.status || '').toLowerCase().includes('closed')
                                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                    : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                                }`}>
                                {task.status}
                            </span>
                        </TableCell>
                        <TableCell className="py-2 text-right text-xs font-mono">
                            {task.estimated_hours || '-'}
                        </TableCell>
                        <TableCell className="py-2 text-right text-xs font-mono">
                            {task.spent_hours || '-'}
                        </TableCell>
                    </TableRow>
                ))}
            </TableBody>
        </Table>
    );
}
