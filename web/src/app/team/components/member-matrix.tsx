'use client';

import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "~/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "~/components/ui/avatar";
import { Badge } from "~/components/ui/badge";
import { ScrollArea } from "~/components/ui/scroll-area";
import { Input } from "~/components/ui/input";
import { GripVertical, Users, ListTodo, Briefcase, Search, UserPlus, FolderKanban, Sparkles, Zap, Activity } from 'lucide-react';
import { WorkspaceLoading } from "~/components/ui/workspace-loading";
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    DragOverlay,
    type DragStartEvent,
    type DragEndEvent,
    useDroppable,
} from '@dnd-kit/core';
import {
    sortableKeyboardCoordinates,
    useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useTeamDataContext, useTeamUsers, useTeamTasks } from "../context/team-data-context";
import { useProjects, type Project } from "~/core/api/hooks/pm/use-projects";
import type { PMTask } from "~/core/api/pm/tasks";
import type { PMUser } from "~/core/api/pm/users";
import { cn } from "~/lib/utils";
import { useMemberProfile } from "../context/member-profile-context";

// --- Premium Draggable Member Item ---
function SortableMember({ member, index }: { member: PMUser; index: number }) {
    const { openMemberProfile } = useMemberProfile();
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({ id: member.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
    };

    // Color array for avatar rings
    const ringColors = [
        'ring-violet-500/60',
        'ring-blue-500/60',
        'ring-emerald-500/60',
        'ring-amber-500/60',
        'ring-rose-500/60',
        'ring-cyan-500/60',
    ];
    const ringColor = ringColors[index % ringColors.length];

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={cn(
                "group flex items-center gap-2 p-2.5 rounded-xl border transition-all duration-300 relative",
                "bg-white dark:bg-gradient-to-r dark:from-slate-800/80 dark:to-slate-900/80 backdrop-blur-sm",
                "border-gray-200 dark:border-slate-700/50 hover:border-indigo-300 dark:hover:border-indigo-500/50",
                "hover:shadow-lg hover:shadow-indigo-100 dark:hover:shadow-indigo-500/10",
                isDragging ? "opacity-30 scale-95 grayscale" : "opacity-100"
            )}
        >
            {/* Animated gradient border on hover */}
            <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-indigo-500/0 via-violet-500/0 to-indigo-500/0 group-hover:from-indigo-500/5 group-hover:via-violet-500/10 group-hover:to-indigo-500/5 transition-all duration-500" />

            {/* Drag Handle */}
            <div {...attributes} {...listeners} className="shrink-0 cursor-grab active:cursor-grabbing p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700/50 transition-colors z-10">
                <GripVertical className="w-4 h-4 text-gray-400 dark:text-slate-500 group-hover:text-indigo-500 dark:group-hover:text-indigo-400 transition-colors" />
            </div>

            <button
                onClick={() => openMemberProfile(member.id)}
                className="flex flex-1 items-center gap-2.5 min-w-0 transition-all text-left z-10"
            >
                <div className="relative shrink-0">
                    <Avatar className={cn(
                        "w-9 h-9 ring-2 ring-offset-1 ring-offset-white dark:ring-offset-slate-900 transition-all duration-300",
                        ringColor,
                        "group-hover:scale-105"
                    )}>
                        <AvatarImage src={member.avatar} />
                        <AvatarFallback className="bg-gradient-to-br from-indigo-500 to-violet-600 text-white font-semibold text-sm">
                            {member.name[0]}
                        </AvatarFallback>
                    </Avatar>
                    {/* Online indicator */}
                    <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-500 rounded-full border-2 border-white dark:border-slate-900" />
                </div>
                <div className="flex-1 min-w-0 overflow-hidden">
                    <p className="text-sm font-semibold text-gray-900 dark:text-slate-100 truncate group-hover:text-indigo-600 dark:group-hover:text-white transition-colors">
                        {member.name}
                    </p>
                    <p className="text-[11px] text-gray-500 dark:text-slate-400 truncate group-hover:text-gray-600 dark:group-hover:text-slate-300 transition-colors">
                        {member.email}
                    </p>
                </div>
            </button>
        </div>
    );
}


// --- Premium Status Badge ---
function ProjectStatusBadge({ status }: { status?: string }) {
    if (!status || status.toLowerCase() === 'none') return null;

    const s = status.toLowerCase();
    let colorClass = "bg-slate-700/50 text-slate-300 border-slate-600";
    let icon = null;

    if (s.includes('active') || s.includes('progress')) {
        colorClass = "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
        icon = <Activity className="w-3 h-3" />;
    }
    if (s.includes('planning') || s.includes('new')) {
        colorClass = "bg-blue-500/20 text-blue-400 border-blue-500/30";
        icon = <Sparkles className="w-3 h-3" />;
    }
    if (s.includes('done') || s.includes('closed')) {
        colorClass = "bg-violet-500/20 text-violet-400 border-violet-500/30";
    }

    return (
        <span className={cn("inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full border", colorClass)}>
            {icon}
            {status}
        </span>
    );
}

// --- Premium Clickable Member Pill ---
function MemberPill({ member, index }: { member: PMUser; index: number }) {
    const { openMemberProfile } = useMemberProfile();

    // Gradient colors for pills
    const gradients = [
        'from-violet-500 to-purple-600',
        'from-blue-500 to-cyan-600',
        'from-emerald-500 to-teal-600',
        'from-amber-500 to-orange-600',
        'from-rose-500 to-pink-600',
    ];
    const gradient = gradients[index % gradients.length];

    return (
        <button
            onClick={() => openMemberProfile(member.id)}
            className={cn(
                "group flex items-center gap-1.5 pl-1 pr-2.5 py-1 rounded-full",
                "bg-white dark:bg-slate-800/80 backdrop-blur-sm",
                "border border-gray-200 dark:border-slate-700/50 hover:border-indigo-300 dark:hover:border-slate-600",
                "shadow-md hover:shadow-lg hover:shadow-indigo-100 dark:hover:shadow-indigo-500/10",
                "hover:scale-105 transition-all duration-200",
                "hover:bg-gray-50 dark:hover:bg-slate-700/80"
            )}
            title={member.email}
            style={{ zIndex: 10 - index }}
        >
            <Avatar className="w-6 h-6 ring-1 ring-gray-200 dark:ring-slate-600 group-hover:ring-indigo-400 dark:group-hover:ring-indigo-500/50 transition-all">
                <AvatarImage src={member.avatar} />
                <AvatarFallback className={cn("text-[9px] font-bold text-white bg-gradient-to-br", gradient)}>
                    {member.name[0]}
                </AvatarFallback>
            </Avatar>
            <span className="text-xs font-medium text-gray-700 dark:text-slate-200 group-hover:text-indigo-600 dark:group-hover:text-white max-w-[70px] truncate transition-colors">
                {member.name.split(' ')[0]}
            </span>
        </button>
    );
}

// --- Premium Droppable Project Row ---
function DroppableProjectRow({
    project,
    assignedMemberIds,
    members,
    taskCount,
    index
}: {
    project: Project;
    assignedMemberIds?: Set<string>;
    members: PMUser[];
    taskCount: number;
    index: number;
}) {
    const { setNodeRef, isOver } = useDroppable({
        id: project.id,
    });

    const assignedMembers = assignedMemberIds
        ? Array.from(assignedMemberIds).map(id => members.find(m => m.id === id)).filter(Boolean) as PMUser[]
        : [];

    // Activity level based on task count
    const getActivityLevel = () => {
        if (taskCount >= 100) return { color: 'from-rose-500 to-orange-500', label: 'High Activity' };
        if (taskCount >= 50) return { color: 'from-amber-500 to-yellow-500', label: 'Active' };
        if (taskCount >= 10) return { color: 'from-emerald-500 to-teal-500', label: 'Moderate' };
        return { color: 'from-slate-500 to-slate-600', label: 'Low' };
    };

    const activity = getActivityLevel();

    return (
        <div
            ref={setNodeRef}
            className={cn(
                "group relative flex items-center gap-4 px-4 py-4 transition-all duration-300",
                "border-b border-gray-100 dark:border-slate-800/50",
                isOver
                    ? "bg-indigo-50 dark:bg-indigo-500/10 ring-2 ring-indigo-400 dark:ring-indigo-500/50 ring-inset"
                    : "hover:bg-gray-50 dark:hover:bg-slate-800/30",
                "hover:translate-x-1"
            )}
        >
            {/* Left activity indicator bar */}
            <div className={cn(
                "absolute left-0 top-2 bottom-2 w-1 rounded-r-full bg-gradient-to-b transition-all duration-300",
                activity.color,
                "group-hover:w-1.5 group-hover:shadow-lg",
                isOver && "w-2 shadow-indigo-500/50"
            )} />

            {/* Project Icon */}
            <div className={cn(
                "w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-all duration-300",
                "shadow-lg",
                assignedMembers.length > 0
                    ? "bg-gradient-to-br from-indigo-500 to-violet-600 text-white"
                    : "bg-gray-100 dark:bg-slate-800 text-gray-400 dark:text-slate-400 border border-gray-200 dark:border-slate-700",
                "group-hover:scale-110 group-hover:shadow-indigo-200 dark:group-hover:shadow-indigo-500/20"
            )}>
                <FolderKanban className="w-5 h-5" />
            </div>

            {/* Project Name & Info */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-sm text-gray-900 dark:text-slate-100 truncate group-hover:text-indigo-600 dark:group-hover:text-white transition-colors" title={project.name}>
                        {project.name}
                    </h3>
                    {project.status && project.status.toLowerCase() !== 'none' && (
                        <ProjectStatusBadge status={project.status} />
                    )}
                </div>
                <div className="flex items-center gap-3">
                    <p className="text-xs text-gray-500 dark:text-slate-400 flex items-center gap-1.5">
                        <ListTodo className="w-3 h-3" />
                        <span className="font-medium text-gray-700 dark:text-slate-300">{taskCount}</span> tasks
                    </p>
                    {taskCount >= 50 && (
                        <span className="flex items-center gap-1 text-[10px] text-amber-600 dark:text-amber-400/80">
                            <Zap className="w-3 h-3" />
                            {activity.label}
                        </span>
                    )}
                </div>
            </div>

            {/* Members Section */}
            <div className="flex items-center gap-2 min-w-[240px] justify-end">
                {assignedMembers.length > 0 ? (
                    <div className="flex items-center">
                        <div className="flex items-center -space-x-1">
                            {assignedMembers.slice(0, 4).map((member, idx) => (
                                <MemberPill key={member.id} member={member} index={idx} />
                            ))}
                        </div>
                        {assignedMembers.length > 4 && (
                            <span className="ml-3 text-xs font-semibold text-indigo-600 dark:text-indigo-400 bg-indigo-100 dark:bg-indigo-500/20 px-2 py-1 rounded-full border border-indigo-200 dark:border-indigo-500/30">
                                +{assignedMembers.length - 4}
                            </span>
                        )}
                    </div>
                ) : (
                    <span className={cn(
                        "flex items-center gap-2 text-xs px-4 py-2 rounded-xl border-2 border-dashed transition-all duration-300",
                        isOver
                            ? "border-indigo-400 text-indigo-500 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-500/10 scale-105"
                            : "border-gray-300 dark:border-slate-700 text-gray-400 dark:text-slate-500 hover:border-gray-400 dark:hover:border-slate-600 hover:text-gray-500 dark:hover:text-slate-400"
                    )}>
                        <UserPlus className="w-4 h-4" />
                        {isOver ? "Release to assign" : "Drop to assign"}
                    </span>
                )}
            </div>

            {/* Member Count Badge */}
            <Badge
                variant={assignedMembers.length > 0 ? "default" : "secondary"}
                className={cn(
                    "text-xs shrink-0 h-8 w-8 rounded-full flex items-center justify-center font-bold transition-all",
                    assignedMembers.length > 0
                        ? "bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/30 group-hover:scale-110"
                        : "bg-gray-100 dark:bg-slate-800 text-gray-500 dark:text-slate-400 border border-gray-200 dark:border-slate-700"
                )}
            >
                {assignedMembers.length}
            </Badge>
        </div>
    );
}


export function MemberMatrix() {
    // Get essential data from context
    const { allMemberIds, isLoading: isContextLoading } = useTeamDataContext();

    // Load heavy data (Users, Tasks, Projects)
    const { teamMembers: members, isLoading: isLoadingUsers, isFetching: isFetchingUsers, count: usersCount } = useTeamUsers(allMemberIds);
    const { teamTasks: tasks, isLoading: isLoadingTasks, isFetching: isFetchingTasks, count: tasksCount } = useTeamTasks(allMemberIds);
    const { projects, loading: loadingProjects } = useProjects();

    const isLoading = isContextLoading || loadingProjects || isLoadingUsers || isLoadingTasks || isFetchingUsers || isFetchingTasks;

    // State
    const [activeId, setActiveId] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState("");

    // Sensors
    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    // Map Assignments: Project ID -> Set of Member IDs
    const projectAssignments = useMemo(() => {
        const map = new Map<string, Set<string>>();
        tasks.forEach((task: PMTask) => {
            if (task.project_id && task.assignee_id) {
                if (!map.has(task.project_id)) {
                    map.set(task.project_id, new Set());
                }
                map.get(task.project_id)?.add(task.assignee_id);
            }
        });
        return map;
    }, [tasks]);

    // Filter Members
    const filteredMembers = useMemo(() => {
        if (!searchQuery.trim()) return members;
        const q = searchQuery.toLowerCase();
        return members.filter((m: PMUser) =>
            m.name.toLowerCase().includes(q) ||
            m.email.toLowerCase().includes(q)
        );
    }, [members, searchQuery]);

    // Sort Projects: Projects with team members first, then by name
    const sortedProjects = useMemo(() => {
        return [...projects].sort((a, b) => {
            const aHasMembers = projectAssignments.has(a.id) && (projectAssignments.get(a.id)?.size || 0) > 0;
            const bHasMembers = projectAssignments.has(b.id) && (projectAssignments.get(b.id)?.size || 0) > 0;

            // Projects with members come first
            if (aHasMembers && !bHasMembers) return -1;
            if (!aHasMembers && bHasMembers) return 1;

            // Within same category, sort by member count (descending), then by name
            if (aHasMembers && bHasMembers) {
                const aCount = projectAssignments.get(a.id)?.size || 0;
                const bCount = projectAssignments.get(b.id)?.size || 0;
                if (aCount !== bCount) return bCount - aCount;
            }

            return a.name.localeCompare(b.name);
        });
    }, [projects, projectAssignments]);

    // Task count per project
    const projectTaskCounts = useMemo(() => {
        const counts = new Map<string, number>();
        tasks.forEach((task: PMTask) => {
            if (task.project_id) {
                counts.set(task.project_id, (counts.get(task.project_id) || 0) + 1);
            }
        });
        return counts;
    }, [tasks]);

    // Split into active (with members) and available (without)
    const { activeProjects, availableProjects } = useMemo(() => {
        const active: typeof projects = [];
        const available: typeof projects = [];
        sortedProjects.forEach(p => {
            const hasMembers = projectAssignments.has(p.id) && (projectAssignments.get(p.id)?.size || 0) > 0;
            if (hasMembers) {
                active.push(p);
            } else {
                available.push(p);
            }
        });
        return { activeProjects: active, availableProjects: available };
    }, [sortedProjects, projectAssignments]);

    function handleDragStart(event: DragStartEvent) {
        setActiveId(event.active.id as string);
    }

    function handleDragEnd(event: DragEndEvent) {
        const { active, over } = event;
        setActiveId(null);

        if (!over) return;

        // Logic to move member to project would go here
        console.log(`Dropped ${active.id} over project ${over.id}`);
    }

    // --- Premium Loading State ---
    if (isLoading) {
        return (
            <WorkspaceLoading
                title="Initializing Workspace"
                subtitle="Gathering team data..."
                items={[
                    { label: "Users", isLoading: isLoadingUsers || isFetchingUsers, count: usersCount },
                    { label: "Tasks", isLoading: isLoadingTasks || isFetchingTasks, count: tasksCount },
                    { label: "Projects", isLoading: loadingProjects, count: projects.length },
                ]}
                icon={<Users className="w-6 h-6 text-white" />}
            />
        );
    }

    const activeMember = activeId ? members.find((m: PMUser) => m.id === activeId) : null;

    return (
        <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
        >
            <div className="flex gap-4 h-[calc(100vh-220px)] min-h-[600px] overflow-hidden">
                {/* --- Premium Sidebar: Team Members --- */}
                <Card className="w-[340px] shrink-0 h-full flex flex-col border border-gray-200 dark:border-0 shadow-lg dark:shadow-2xl dark:shadow-indigo-500/5 rounded-2xl overflow-hidden bg-white dark:bg-gradient-to-b dark:from-slate-900 dark:to-slate-950">
                    {/* Glassmorphic Header */}
                    <div className="relative p-4 border-b border-gray-100 dark:border-slate-800/50 space-y-4 shrink-0 bg-gradient-to-r from-indigo-50 dark:from-indigo-500/10 via-violet-50/50 dark:via-violet-500/5 to-transparent">
                        {/* Subtle animated background */}
                        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-indigo-100/50 dark:from-indigo-500/10 via-transparent to-transparent" />

                        <div className="relative flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                                    <Users className="w-4 h-4 text-white" />
                                </div>
                                <h3 className="font-bold text-base text-gray-900 dark:text-white">Team Roster</h3>
                            </div>
                            <Badge className="bg-indigo-100 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/30 text-xs font-bold">
                                {filteredMembers.length}
                            </Badge>
                        </div>

                        <div className="relative">
                            <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400 dark:text-slate-500" />
                            <Input
                                placeholder="Filter members..."
                                className="h-10 pl-10 text-sm bg-gray-50 dark:bg-slate-800/50 border-gray-200 dark:border-slate-700/50 text-gray-700 dark:text-slate-200 placeholder:text-gray-400 dark:placeholder:text-slate-500 focus:border-indigo-300 dark:focus:border-indigo-500/50 focus:ring-indigo-200 dark:focus:ring-indigo-500/20 rounded-xl"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto">
                        <div className="space-y-2 p-3">
                            {filteredMembers.map((member: PMUser, index: number) => (
                                <SortableMember key={member.id} member={member} index={index} />
                            ))}
                            {filteredMembers.length === 0 && (
                                <div className="text-center py-12 text-gray-400 dark:text-slate-500">
                                    <Users className="w-10 h-10 mx-auto mb-3 opacity-30" />
                                    <p className="text-sm font-medium">No members found</p>
                                    <p className="text-xs mt-1">Try a different search term</p>
                                </div>
                            )}
                        </div>
                    </div>
                </Card>

                {/* --- Main: Premium Project Table --- */}
                <div className="flex-1 h-full overflow-hidden">
                    <ScrollArea className="h-full">
                        <div className="pr-4 pb-10 space-y-6">
                            {/* Active Projects Section */}
                            {activeProjects.length > 0 && (
                                <Card className="overflow-hidden border border-gray-200 dark:border-0 shadow-lg dark:shadow-2xl dark:shadow-indigo-500/10 rounded-2xl bg-white dark:bg-gradient-to-b dark:from-slate-900 dark:to-slate-950">
                                    <CardHeader className="py-4 px-6 bg-gradient-to-r from-indigo-50 dark:from-indigo-500/10 via-violet-50/50 dark:via-violet-500/5 to-transparent border-b border-gray-100 dark:border-slate-800/50">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                                                    <Users className="w-5 h-5 text-white" />
                                                </div>
                                                <div>
                                                    <CardTitle className="text-base font-bold text-gray-900 dark:text-white">Active Projects</CardTitle>
                                                    <CardDescription className="text-xs text-gray-500 dark:text-slate-400">Projects with team members assigned</CardDescription>
                                                </div>
                                            </div>
                                            <Badge className="bg-indigo-500 text-white font-bold px-3 py-1 shadow-lg shadow-indigo-500/30">
                                                {activeProjects.length}
                                            </Badge>
                                        </div>
                                    </CardHeader>
                                    <CardContent className="p-0">
                                        {activeProjects.map((project, index) => (
                                            <DroppableProjectRow
                                                key={project.id}
                                                project={project}
                                                assignedMemberIds={projectAssignments.get(project.id)}
                                                members={members}
                                                taskCount={projectTaskCounts.get(project.id) || 0}
                                                index={index}
                                            />
                                        ))}
                                    </CardContent>
                                </Card>
                            )}

                            {/* Available Projects Section */}
                            {availableProjects.length > 0 && (
                                <Card className="overflow-hidden border border-gray-200 dark:border-0 shadow-lg dark:shadow-xl rounded-2xl bg-white dark:bg-gradient-to-b dark:from-slate-900/80 dark:to-slate-950/80">
                                    <CardHeader className="py-4 px-6 bg-gray-50 dark:bg-slate-800/30 border-b border-gray-100 dark:border-slate-800/50">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 rounded-xl bg-gray-100 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 flex items-center justify-center">
                                                    <Briefcase className="w-5 h-5 text-gray-400 dark:text-slate-400" />
                                                </div>
                                                <div>
                                                    <CardTitle className="text-base font-semibold text-gray-700 dark:text-slate-300">Available Projects</CardTitle>
                                                    <CardDescription className="text-xs text-gray-400 dark:text-slate-500">Drop team members to assign</CardDescription>
                                                </div>
                                            </div>
                                            <Badge variant="secondary" className="bg-gray-100 dark:bg-slate-800 text-gray-500 dark:text-slate-400 border border-gray-200 dark:border-slate-700 font-bold">
                                                {availableProjects.length}
                                            </Badge>
                                        </div>
                                    </CardHeader>
                                    <CardContent className="p-0">
                                        {availableProjects.map((project, index) => (
                                            <DroppableProjectRow
                                                key={project.id}
                                                project={project}
                                                assignedMemberIds={projectAssignments.get(project.id)}
                                                members={members}
                                                taskCount={projectTaskCounts.get(project.id) || 0}
                                                index={index}
                                            />
                                        ))}
                                    </CardContent>
                                </Card>
                            )}
                        </div>
                    </ScrollArea>
                </div>
            </div>

            {/* Premium Drag Overlay */}
            <DragOverlay>
                {activeMember ? (
                    <div className="flex items-center gap-3 p-4 bg-gradient-to-r from-indigo-600 to-violet-600 rounded-2xl border-2 border-white/20 shadow-2xl shadow-indigo-500/50 cursor-grabbing scale-105 w-[260px] backdrop-blur-sm">
                        <Avatar className="w-12 h-12 ring-2 ring-white/30 ring-offset-2 ring-offset-indigo-600 shadow-lg">
                            <AvatarImage src={activeMember.avatar} />
                            <AvatarFallback className="bg-white text-indigo-700 font-bold">{activeMember.name[0]}</AvatarFallback>
                        </Avatar>
                        <div>
                            <p className="font-bold text-base text-white">{activeMember.name}</p>
                            <p className="text-xs text-indigo-200 flex items-center gap-1">
                                <Sparkles className="w-3 h-3" />
                                Ready to assign
                            </p>
                        </div>
                    </div>
                ) : null}
            </DragOverlay>
        </DndContext>
    );
}
