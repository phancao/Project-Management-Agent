'use client';

import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "~/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "~/components/ui/avatar";
import { Badge } from "~/components/ui/badge";
import { ScrollArea } from "~/components/ui/scroll-area";
import { Input } from "~/components/ui/input";
import { GripVertical, Loader2, Users, ListTodo, Briefcase, Search, UserPlus, FolderKanban } from 'lucide-react';
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
import { useMemberProfile } from "../page";

// --- Draggable Member Item ---
function SortableMember({ member }: { member: PMUser }) {
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

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={cn(
                "group flex items-center gap-3 p-2.5 rounded-lg border shadow-sm mb-2 transition-all duration-200 relative",
                "bg-white dark:bg-gray-800/80 border-gray-100 dark:border-gray-700/50",
                "hover:border-indigo-200 dark:hover:border-indigo-800 hover:shadow-md",
                isDragging ? "opacity-30 grayscale" : "opacity-100"
            )}
        >
            {/* Drag Handle */}
            <div {...attributes} {...listeners} className="cursor-grab active:cursor-grabbing p-1">
                <GripVertical className="w-4 h-4 text-gray-300 group-hover:text-indigo-400 transition-colors" />
            </div>

            <button
                onClick={() => openMemberProfile(member.id)}
                className="flex flex-1 items-center gap-3 min-w-0 hover:opacity-80 transition-opacity text-left"
            >
                <Avatar className="w-9 h-9 border-2 border-white dark:border-gray-700 shadow-sm">
                    <AvatarImage src={member.avatar} />
                    <AvatarFallback className="bg-indigo-50 text-indigo-600 dark:bg-indigo-900/50 dark:text-indigo-300">
                        {member.name[0]}
                    </AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-800 dark:text-gray-100 truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-300 transition-colors">
                        {member.name}
                    </p>
                    <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                        <p className="text-[10px] text-muted-foreground truncate opacity-80">{member.email}</p>
                    </div>
                </div>
            </button>
        </div>
    );
}

// --- Status Badge Helper ---
function ProjectStatusBadge({ status }: { status?: string }) {
    if (!status) return null;
    const s = status.toLowerCase();
    let colorClass = "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400";
    if (s.includes('active') || s.includes('progress')) colorClass = "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 border-green-200 dark:border-green-800";
    if (s.includes('planning') || s.includes('new')) colorClass = "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 border-blue-200 dark:border-blue-800";
    if (s.includes('done') || s.includes('closed')) colorClass = "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 border-purple-200 dark:border-purple-800";

    return (
        <span className={cn("text-[10px] font-medium px-2 py-0.5 rounded-full border", colorClass)}>
            {status}
        </span>
    );
}

// --- Clickable Member Pill for Project Cards ---
function MemberPill({ member }: { member: PMUser }) {
    const { openMemberProfile } = useMemberProfile();
    return (
        <button
            onClick={() => openMemberProfile(member.id)}
            className="flex items-center gap-1.5 pl-1 pr-2 py-1 bg-white dark:bg-gray-800 rounded-full border border-gray-100 dark:border-gray-700 shadow-sm hover:scale-105 transition-transform hover:border-indigo-200"
            title={member.email}
        >
            <Avatar className="w-5 h-5">
                <AvatarImage src={member.avatar} />
                <AvatarFallback className="text-[9px]">{member.name[0]}</AvatarFallback>
            </Avatar>
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300 max-w-[80px] truncate">
                {member.name.split(' ')[0]}
            </span>
        </button>
    );
}

// --- Droppable Project Row (Table-based layout) ---
function DroppableProjectRow({ project, assignedMemberIds, members, taskCount }: { project: Project, assignedMemberIds?: Set<string>, members: PMUser[], taskCount: number }) {
    const { setNodeRef, isOver } = useDroppable({
        id: project.id,
    });

    const assignedMembers = assignedMemberIds
        ? Array.from(assignedMemberIds).map(id => members.find(m => m.id === id)).filter(Boolean) as PMUser[]
        : [];

    return (
        <div
            ref={setNodeRef}
            className={cn(
                "flex items-center gap-4 px-4 py-3 border-b border-gray-100 dark:border-gray-800 transition-all",
                isOver
                    ? "bg-indigo-50 dark:bg-indigo-900/20 ring-2 ring-indigo-500 ring-inset"
                    : "hover:bg-gray-50 dark:hover:bg-gray-800/50"
            )}
        >
            {/* Project Icon */}
            <div className={cn(
                "w-8 h-8 rounded-lg flex items-center justify-center shrink-0",
                assignedMembers.length > 0
                    ? "bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400"
                    : "bg-gray-100 dark:bg-gray-800 text-gray-400"
            )}>
                <FolderKanban className="w-4 h-4" />
            </div>

            {/* Project Name & Status */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <h3 className="font-medium text-sm text-gray-900 dark:text-gray-100 truncate" title={project.name}>
                        {project.name}
                    </h3>
                    {project.status && <ProjectStatusBadge status={project.status} />}
                </div>
                {taskCount > 0 && (
                    <p className="text-xs text-muted-foreground">{taskCount} tasks</p>
                )}
            </div>

            {/* Members */}
            <div className="flex items-center gap-1 min-w-[200px]">
                {assignedMembers.length > 0 ? (
                    <div className="flex items-center -space-x-2">
                        {assignedMembers.slice(0, 5).map(member => (
                            <MemberPill key={member.id} member={member} />
                        ))}
                        {assignedMembers.length > 5 && (
                            <span className="text-xs text-muted-foreground ml-2">+{assignedMembers.length - 5}</span>
                        )}
                    </div>
                ) : (
                    <span className={cn(
                        "text-xs px-3 py-1 rounded-full border-2 border-dashed",
                        isOver
                            ? "border-indigo-400 text-indigo-600 bg-indigo-50 dark:bg-indigo-900/30"
                            : "border-gray-200 dark:border-gray-700 text-gray-400"
                    )}>
                        {isOver ? "Drop here!" : "No members"}
                    </span>
                )}
            </div>

            {/* Member Count Badge */}
            <Badge
                variant={assignedMembers.length > 0 ? "default" : "secondary"}
                className={cn(
                    "text-[10px] shrink-0",
                    assignedMembers.length > 0 ? "bg-indigo-600" : ""
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
        // For prototyping purposes:
        // alert(`Assignments are read-only in this beta. (Dropped ${active.id} on ${over.id})`);
    }

    // --- Loading State ---
    if (isLoading) {
        const loadingItems = [
            { label: "Users", isLoading: isLoadingUsers || isFetchingUsers, count: usersCount },
            { label: "Tasks", isLoading: isLoadingTasks || isFetchingTasks, count: tasksCount },
            { label: "Projects", isLoading: loadingProjects, count: projects.length },
        ];
        const completedCount = loadingItems.filter(item => !item.isLoading).length;
        const progressPercent = Math.round((completedCount / loadingItems.length) * 100);

        return (
            <div className="h-[600px] w-full flex items-center justify-center p-4">
                <div className="bg-card border rounded-xl shadow-lg p-6 w-full max-w-sm">
                    {/* ... (Keep existing loading UI for consistency) ... */}
                    <div className="flex items-center gap-3 mb-4">
                        <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
                            <Users className="w-5 h-5 text-purple-600 dark:text-purple-400 animate-pulse" />
                        </div>
                        <div>
                            <h3 className="text-sm font-semibold">Initializing Workspace</h3>
                            <p className="text-xs text-muted-foreground">Gathering team data...</p>
                        </div>
                    </div>
                    {/* Simplified Spinner for brevity in rewrite */}
                    <div className="flex justify-center py-4">
                        <Loader2 className="w-6 h-6 animate-spin text-purple-500" />
                    </div>
                    <p className="text-[10px] text-muted-foreground text-center">
                        Syncing {loadingItems.find(i => i.isLoading)?.label || 'Metadata'}...
                    </p>
                </div>
            </div>
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
            <div className="flex gap-6 h-[calc(100vh-200px)] min-h-[600px]">
                {/* --- Sidebar: Team Members --- */}
                <Card className="w-[280px] shrink-0 h-full flex flex-col border-r shadow-none rounded-lg border bg-gray-50/50 dark:bg-gray-900/20">
                    <div className="p-4 border-b space-y-3 bg-white dark:bg-gray-900 shrink-0">
                        <div className="flex items-center justify-between">
                            <h3 className="font-semibold text-sm">Team Roster</h3>
                            <Badge variant="secondary" className="text-[10px] h-5">{filteredMembers.length}</Badge>
                        </div>
                        <div className="relative">
                            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                            <Input
                                placeholder="Filter members..."
                                className="h-9 pl-8 text-xs bg-gray-50 dark:bg-gray-800"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                        </div>
                    </div>

                    <ScrollArea className="flex-1 p-3">
                        <div className="space-y-1">
                            {filteredMembers.map((member: PMUser) => (
                                <SortableMember key={member.id} member={member} />
                            ))}
                            {filteredMembers.length === 0 && (
                                <div className="text-center py-8 text-muted-foreground text-xs">
                                    No members found.
                                </div>
                            )}
                        </div>
                    </ScrollArea>
                </Card>

                {/* --- Main: Project Table --- */}
                <div className="flex-1 h-full overflow-hidden">
                    <ScrollArea className="h-full">
                        <div className="pr-4 pb-10 space-y-4">
                            {/* Active Projects Section */}
                            {activeProjects.length > 0 && (
                                <Card className="overflow-hidden">
                                    <CardHeader className="py-3 bg-gradient-to-r from-indigo-50 to-white dark:from-indigo-900/20 dark:to-gray-900 border-b">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <Users className="w-4 h-4 text-indigo-600" />
                                                <CardTitle className="text-sm">Active Projects</CardTitle>
                                            </div>
                                            <Badge className="bg-indigo-600">{activeProjects.length}</Badge>
                                        </div>
                                        <CardDescription className="text-xs">Projects with team members assigned</CardDescription>
                                    </CardHeader>
                                    <CardContent className="p-0">
                                        {activeProjects.map(project => (
                                            <DroppableProjectRow
                                                key={project.id}
                                                project={project}
                                                assignedMemberIds={projectAssignments.get(project.id)}
                                                members={members}
                                                taskCount={projectTaskCounts.get(project.id) || 0}
                                            />
                                        ))}
                                    </CardContent>
                                </Card>
                            )}

                            {/* Available Projects Section */}
                            {availableProjects.length > 0 && (
                                <Card className="overflow-hidden">
                                    <CardHeader className="py-3 bg-gray-50 dark:bg-gray-900 border-b">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <Briefcase className="w-4 h-4 text-gray-400" />
                                                <CardTitle className="text-sm text-muted-foreground">Available Projects</CardTitle>
                                            </div>
                                            <Badge variant="secondary">{availableProjects.length}</Badge>
                                        </div>
                                        <CardDescription className="text-xs">Drop team members to assign</CardDescription>
                                    </CardHeader>
                                    <CardContent className="p-0">
                                        {availableProjects.map(project => (
                                            <DroppableProjectRow
                                                key={project.id}
                                                project={project}
                                                assignedMemberIds={projectAssignments.get(project.id)}
                                                members={members}
                                                taskCount={projectTaskCounts.get(project.id) || 0}
                                            />
                                        ))}
                                    </CardContent>
                                </Card>
                            )}
                        </div>
                    </ScrollArea>
                </div>
            </div>

            <DragOverlay>
                {activeMember ? (
                    <div className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 rounded-xl border-2 border-indigo-500 shadow-2xl skew-y-2 cursor-grabbing scale-105 w-[240px]">
                        <Avatar className="w-10 h-10 border-2 border-white shadow">
                            <AvatarImage src={activeMember.avatar} />
                            <AvatarFallback className="bg-indigo-100 text-indigo-700">{activeMember.name[0]}</AvatarFallback>
                        </Avatar>
                        <div>
                            <p className="font-bold text-sm text-gray-900 dark:text-white">{activeMember.name}</p>
                            <p className="text-[10px] text-green-500 font-medium">Ready to assign</p>
                        </div>
                    </div>
                ) : null}
            </DragOverlay>
        </DndContext>
    );
}

import { useDroppable } from '@dnd-kit/core';


