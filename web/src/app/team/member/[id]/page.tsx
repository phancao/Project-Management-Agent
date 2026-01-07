'use client';

import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useTeamDataContext, useTeamUsers, useTeamTasks } from "../../context/team-data-context";
import { Avatar, AvatarFallback, AvatarImage } from "~/components/ui/avatar";
import { Badge } from "~/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { ArrowLeft, Clock, CheckCircle2, CircleDashed, AlertCircle } from 'lucide-react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { useProjects } from "~/core/api/hooks/pm/use-projects";
import { MemberLoadingOverlay } from "../../components/member-loading-overlay";
import { useProviders } from "~/core/api/hooks/pm/use-providers";
import type { PMUser, extractShortId } from "~/core/api/pm/users";
import { extractShortId as extractId } from "~/core/api/pm/users";
import type { PMTask } from "~/core/api/pm/tasks";

// ...

export default function MemberPage() {
    const params = useParams();
    const router = useRouter();
    const searchParams = useSearchParams();
    const returnTab = searchParams.get('returnTab');
    const memberId = params.id as string; // Decode? It's typically raw string. OpenProject ID might contain colon.

    // Using context for data - assuming team data is already loaded or we force a load
    // Ideally we might want a specific useMember hook if we didn't want to load ALL team data,
    // but for now reusing the Team Context is consistent with the rest of the app.
    const { allMemberIds, isLoading: isContextLoading } = useTeamDataContext();
    const { teamMembers, isLoading: isLoadingUsers } = useTeamUsers(allMemberIds);
    const { teamTasks, isLoading: isLoadingTasks } = useTeamTasks(allMemberIds);

    const isLoading = isContextLoading || isLoadingUsers || isLoadingTasks;

    const member = teamMembers.find((m: PMUser) => m.id === decodeURIComponent(memberId || ''));

    // Filter tasks for this member using shortId for proper matching
    const memberShortId = member?.shortId || (member ? extractId(member.id) : '');
    const memberTasks = teamTasks.filter((t: PMTask) => {
        if (!t.assignee_id || !member) return false;
        const taskAssigneeShortId = extractId(t.assignee_id);
        return t.assignee_id === member.id ||
            t.assignee_id === memberShortId ||
            taskAssigneeShortId === memberShortId;
    });

    // Stats
    const totalAssigned = memberTasks.length;
    const completedTasks = memberTasks.filter((t: PMTask) => ['done', 'closed', 'rejected'].includes((t.status || '').toLowerCase())).length;
    const activeTasks = memberTasks.filter((t: PMTask) => !['done', 'closed', 'rejected'].includes((t.status || '').toLowerCase()));

    // Calculate Hours
    const totalEstimated = activeTasks.reduce((sum: number, t: PMTask) => sum + (t.estimated_hours || 0), 0);
    const totalSpent = activeTasks.reduce((sum: number, t: PMTask) => sum + (t.spent_hours || 0), 0);
    const remainingHours = Math.max(0, totalEstimated - totalSpent); // Simplified logic

    const { projects } = useProjects(); // Fetch projects for name lookup

    // Helper to get Project Name
    const getProjectName = (id?: string) => {
        if (!id) return 'Unassigned';
        const proj = projects.find(p => p.id === id);
        return proj ? proj.name : id.split(':').pop();
    };

    // Helper to parse Provider
    const getProviderName = (id: string) => {
        if (id.startsWith('openproject:')) return 'OpenProject';
        if (id.startsWith('jira:')) return 'Jira';
        if (id.startsWith('github:')) return 'GitHub';
        return 'System';
    };

    const { providers } = useProviders();

    // Helper to generate Task URL (External)
    const getTaskUrl = (task: PMTask) => {
        if (!task || !task.id) return '#';
        const id = task.id;
        const parts = id.split(':');

        // Format can be "provider_type:local_id" OR "provider_id:local_id"
        // ex: "ba599805-f7cd-40f6-91c3-e986b9c0207b:593" -> Provider ID is the UUID

        const prefix = parts[0];
        const localId = parts[parts.length - 1];

        // 1. Try to find provider by ID (prefix)
        let providerConfig = providers.find(p => p.id === prefix);

        // 2. If not found, try to find by TYPE (prefix)
        if (!providerConfig) {
            providerConfig = providers.find(p => p.provider_type === prefix);
        }

        // 3. If still not found, try to fallback (e.g. if prefix is 'github' but provider has specific ID)
        if (!providerConfig && prefix === 'github') {
            // Fallback for github if explicitly 'github:...'
            return `https://github.com/search?q=${localId}`;
        }

        if (providerConfig) {
            const type = providerConfig.provider_type;
            const baseUrl = providerConfig.base_url || 'https://openproject.bstarsolutions.com'; // User fallback

            if (type === 'openproject' || type === 'openproject_v13') {
                // Ensure no double slash if baseUrl ends with /
                const cleanBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
                return `${cleanBase}/work_packages/${localId}`;
            }

            if (type === 'github') {
                if (baseUrl.includes('github.com')) {
                    return `${baseUrl}/issues/${localId}`;
                }
            }
        }

        return '#';
    };

    if (isLoading) {
        return (
            <MemberLoadingOverlay
                isContextLoading={isContextLoading}
                isLoadingUsers={isLoadingUsers}
                isLoadingTasks={isLoadingTasks}
            />
        );
    }

    if (!member) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen gap-4">
                <h1 className="text-2xl font-bold">Member Not Found</h1>
                <p className="text-gray-500">Could not find member with ID: {memberId}</p>
                <Button variant="outline" onClick={() => router.back()}>
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Team
                </Button>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50/50 dark:bg-gray-950 p-6 md:p-10">
            <div className="max-w-5xl mx-auto space-y-8">
                {/* Header */}
                <div className="flex items-start justify-between">
                    <div className="flex items-center gap-6">
                        <Button
                            variant="ghost"
                            size="icon"
                            className="rounded-full"
                            onClick={() => {
                                if (returnTab === 'teams') {
                                    router.push('/team?tab=members'); // "Teams" tab is actually key="members"
                                } else if (returnTab === 'assignments') {
                                    router.push('/team?tab=assignments');
                                } else if (returnTab === 'worklogs') {
                                    router.push('/team?tab=worklogs');
                                } else if (returnTab === 'overview') {
                                    router.push('/team?tab=overview');
                                } else {
                                    router.back();
                                }
                            }}
                        >
                            <ArrowLeft className="w-5 h-5" />
                        </Button>
                        <Avatar className="w-20 h-20 border-4 border-white dark:border-gray-900 shadow-xl">
                            <AvatarImage src={member.avatar} />
                            <AvatarFallback className="text-xl bg-indigo-100 text-indigo-700">
                                {member.name[0]}
                            </AvatarFallback>
                        </Avatar>
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">{member.name}</h1>
                            <div className="flex items-center gap-2 mt-1">
                                <Badge variant="secondary" className="font-normal">{member.email}</Badge>
                                <Badge variant="outline" className="text-xs">ID: {member.id.split(':').pop()}</Badge>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <Card className="bg-white dark:bg-gray-900 shadow-sm border-l-4 border-l-indigo-500">
                        <CardContent className="p-4 flex items-center justify-between">
                            <div>
                                <p className="text-sm font-medium text-gray-500">Active Tasks</p>
                                <p className="text-2xl font-bold">{activeTasks.length}</p>
                            </div>
                            <CircleDashed className="w-8 h-8 text-indigo-100 dark:text-indigo-900" />
                        </CardContent>
                    </Card>
                    <Card className="bg-white dark:bg-gray-900 shadow-sm border-l-4 border-l-green-500">
                        <CardContent className="p-4 flex items-center justify-between">
                            <div>
                                <p className="text-sm font-medium text-gray-500">Completed</p>
                                <p className="text-2xl font-bold">{completedTasks}</p>
                            </div>
                            <CheckCircle2 className="w-8 h-8 text-green-100 dark:text-green-900" />
                        </CardContent>
                    </Card>
                    <Card className="bg-white dark:bg-gray-900 shadow-sm border-l-4 border-l-amber-500">
                        <CardContent className="p-4 flex items-center justify-between">
                            <div>
                                <p className="text-sm font-medium text-gray-500">Est. Workload</p>
                                <p className="text-2xl font-bold">{totalEstimated.toFixed(1)}h</p>
                            </div>
                            <Clock className="w-8 h-8 text-amber-100 dark:text-amber-900" />
                        </CardContent>
                    </Card>
                    <Card className="bg-white dark:bg-gray-900 shadow-sm border-l-4 border-l-purple-500">
                        <CardContent className="p-4 flex items-center justify-between">
                            <div>
                                <p className="text-sm font-medium text-gray-500">Remaining</p>
                                <p className="text-2xl font-bold">{remainingHours.toFixed(1)}h</p>
                            </div>
                            <AlertCircle className="w-8 h-8 text-purple-100 dark:text-purple-900" />
                        </CardContent>
                    </Card>
                </div>

                {/* Main Content: Tasks Table */}
                <Card className="overflow-hidden">
                    <CardHeader className="pb-2">
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle>Assignments & History</CardTitle>
                                <CardDescription>Comprehensive list of user tasks</CardDescription>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <Tabs defaultValue="active" className="w-full">
                            <TabsList className="mb-4">
                                <TabsTrigger value="active">Active ({activeTasks.length})</TabsTrigger>
                                <TabsTrigger value="all">All ({memberTasks.length})</TabsTrigger>
                            </TabsList>

                            {/* Shared Table Renderer */}
                            {['active', 'all'].map(currentTab => {
                                const currentTasks = currentTab === 'active' ? activeTasks : memberTasks;

                                // Sort: Active first, then by ID desc
                                const sortedTasks = [...currentTasks].sort((a, b) => {
                                    // Custom sort if needed, current implicit order often fine
                                    return 0;
                                });

                                return (
                                    <TabsContent key={currentTab} value={currentTab}>
                                        <div className="rounded-md border">
                                            <Table>
                                                <TableHeader>
                                                    <TableRow className="bg-muted/50">
                                                        <TableHead>Provider</TableHead>
                                                        <TableHead>Project</TableHead>
                                                        <TableHead className="w-[300px]">Task</TableHead>
                                                        <TableHead>Status</TableHead>
                                                        <TableHead className="text-right">Est.</TableHead>
                                                        <TableHead className="text-right">Spent</TableHead>
                                                        <TableHead className="text-right">Progress</TableHead>
                                                    </TableRow>
                                                </TableHeader>
                                                <TableBody>
                                                    {sortedTasks.length === 0 ? (
                                                        <TableRow>
                                                            <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                                                                No tasks found in this view.
                                                            </TableCell>
                                                        </TableRow>
                                                    ) : (
                                                        sortedTasks.map((task: PMTask) => (
                                                            <TableRow key={task.id} className="group hover:bg-muted/30">
                                                                <TableCell className="font-medium text-xs text-muted-foreground">
                                                                    <div className="flex items-center gap-1.5">
                                                                        <div className={`w-2 h-2 rounded-full ${getProviderName(task.id) === 'OpenProject' ? 'bg-blue-500' : 'bg-gray-400'}`} />
                                                                        {getProviderName(task.id)}
                                                                    </div>
                                                                </TableCell>
                                                                <TableCell>
                                                                    <Badge variant="outline" className="font-normal text-xs whitespace-nowrap">
                                                                        {getProjectName(task.project_id)}
                                                                    </Badge>
                                                                </TableCell>
                                                                <TableCell>
                                                                    <div className="flex flex-col">
                                                                        <a
                                                                            href={getTaskUrl(task)}
                                                                            target={getTaskUrl(task).startsWith('http') ? "_blank" : "_self"}
                                                                            rel="noopener noreferrer"
                                                                            className="font-medium truncate max-w-[280px] hover:underline hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors cursor-pointer"
                                                                            title={task.title || task.name}
                                                                        >
                                                                            {task.title || task.name}
                                                                        </a>
                                                                        <span className="text-[10px] text-muted-foreground">
                                                                            ID: <span className="font-mono">{task.id.split(':').pop()}</span>
                                                                        </span>
                                                                    </div>
                                                                </TableCell>
                                                                <TableCell>
                                                                    <span className={`text-[10px] px-2 py-1 rounded-full font-medium border ${(task.status || '').toLowerCase().includes('progress')
                                                                        ? 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-800'
                                                                        : (task.status || '').toLowerCase().includes('done') || (task.status || '').toLowerCase().includes('closed')
                                                                            ? 'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800'
                                                                            : 'bg-gray-50 text-gray-600 border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700'
                                                                        }`}>
                                                                        {task.status}
                                                                    </span>
                                                                </TableCell>
                                                                <TableCell className="text-right font-mono text-xs">
                                                                    {task.estimated_hours || '-'}
                                                                </TableCell>
                                                                <TableCell className="text-right font-mono text-xs">
                                                                    {task.spent_hours || '-'}
                                                                </TableCell>
                                                                <TableCell className="text-right">
                                                                    <div className="flex items-center justify-end gap-2">
                                                                        <div className="w-16 h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                                                                            <div
                                                                                className={`h-full rounded-full ${((task.spent_hours || 0) > (task.estimated_hours || 0)) && (task.estimated_hours || 0) > 0
                                                                                    ? 'bg-red-500' // Over budget
                                                                                    : 'bg-indigo-500'
                                                                                    }`}
                                                                                style={{
                                                                                    width: `${Math.min(100, Math.max(5, ((task.spent_hours || 0) / (task.estimated_hours || 1)) * 100))}%`
                                                                                }}
                                                                            />
                                                                        </div>
                                                                        <span className="text-[10px] text-muted-foreground w-8 text-right">
                                                                            {(task.estimated_hours && task.estimated_hours > 0)
                                                                                ? `${Math.round(((task.spent_hours || 0) / task.estimated_hours) * 100)}%`
                                                                                : '-'}
                                                                        </span>
                                                                    </div>
                                                                </TableCell>
                                                            </TableRow>
                                                        ))
                                                    )}
                                                </TableBody>
                                            </Table>
                                        </div>
                                    </TabsContent>
                                );
                            })}
                        </Tabs>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
