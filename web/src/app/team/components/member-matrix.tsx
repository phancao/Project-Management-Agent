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

import Link from 'next/link';

// --- Draggable Member Item ---
function SortableMember({ member }: { member: PMUser }) {
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
            {/* Drag Handle - Needs to be separate or the Link will interfere with Drag?
                Actually, putting Link *inside* non-drag areas is safer,
                OR using the whole item as drag handle but handling click carefully.
                Best pattern: Grip is drag handle. Content area is Link.
            */}
            <div {...attributes} {...listeners} className="cursor-grab active:cursor-grabbing p-1">
                <GripVertical className="w-4 h-4 text-gray-300 group-hover:text-indigo-400 transition-colors" />
            </div>

            <Link href={`/team/member/${encodeURIComponent(member.id)}?returnTab=assignments`} className="flex flex-1 items-center gap-3 min-w-0 hover:opacity-80 transition-opacity">
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
            </Link>
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

// --- Droppable Project Card ---
function DroppableProject({ project, assignedMemberIds, members }: { project: Project, assignedMemberIds?: Set<string>, members: PMUser[] }) {
    const { setNodeRef, isOver } = useDroppable({
        id: project.id,
    });

    return (
        <Card className={cn(
            "h-full transition-all duration-300 border overflow-hidden group",
            isOver ? "ring-2 ring-indigo-500 shadow-xl scale-[1.02] border-indigo-500" : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700"
        )}>
            {/* Glassmorphic Header */}
            <div className="relative bg-gradient-to-r from-gray-50 to-white dark:from-gray-900 dark:to-gray-800/50 p-3 border-b border-gray-100 dark:border-gray-800">
                <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5 min-w-0">
                        <div className={cn(
                            "w-8 h-8 rounded-lg flex items-center justify-center shadow-inner",
                            "bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700",
                            "text-gray-500 dark:text-gray-400"
                        )}>
                            <FolderKanban className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                            <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100 truncate" title={project.name}>
                                {project.name}
                            </h3>
                            {project.status && <ProjectStatusBadge status={project.status} />}
                        </div>
                    </div>
                </div>
            </div>

            {/* Content / Drop Zone */}
            <div
                ref={setNodeRef}
                className={cn(
                    "p-3 min-h-[140px] transition-colors relative",
                    isOver ? "bg-indigo-50/50 dark:bg-indigo-900/20" : "bg-white dark:bg-gray-900/20"
                )}
            >
                {/* Active Member Grid */}
                {assignedMemberIds && assignedMemberIds.size > 0 ? (
                    <div className="flex flex-wrap gap-2">
                        {Array.from(assignedMemberIds).map(memberId => {
                            const member = members.find(m => m.id === memberId);
                            if (!member) return null;
                            return (
                                <Link
                                    key={`${project.id}-${member.id}`}
                                    href={`/team/member/${encodeURIComponent(member.id)}?returnTab=assignments`}
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
                                </Link>
                            );
                        })}
                    </div>
                ) : (
                    <div className={cn(
                        "h-full flex flex-col items-center justify-center p-4 border-2 border-dashed rounded-lg transition-all",
                        isOver
                            ? "border-indigo-400 bg-indigo-50/30 dark:border-indigo-500/50"
                            : "border-gray-100 dark:border-gray-800/50 text-gray-300 dark:text-gray-700"
                    )}>
                        <UserPlus className={cn("w-6 h-6 mb-2 transition-colors", isOver ? "text-indigo-500" : "text-gray-300 dark:text-gray-700")} />
                        <span className={cn("text-xs font-medium", isOver ? "text-indigo-600" : "text-muted-foreground")}>
                            {isOver ? "Drop to assign!" : "Drop members here"}
                        </span>
                    </div>
                )}

                {/* Visual Overlay for Dragging Over */}
                {isOver && (
                    <div className="absolute inset-0 bg-indigo-500/5 pointer-events-none animate-pulse" />
                )}
            </div>
        </Card>
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
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 h-[750px] overflow-hidden">
                {/* --- Sidebar: Team Members --- */}
                <Card className="col-span-1 h-full flex flex-col border-r shadow-none rounded-none md:rounded-lg md:border bg-gray-50/50 dark:bg-gray-900/20">
                    <div className="p-4 border-b space-y-3 bg-white dark:bg-gray-900">
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

                {/* --- Main: Project Grid --- */}
                <div className="col-span-3 h-full flex flex-col">
                    <ScrollArea className="h-full pr-4 pb-20">
                        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 pb-10">
                            {projects.map(project => {
                                const assignedMemberIds = projectAssignments.get(project.id);
                                return (
                                    <div key={project.id} className="h-full">
                                        <DroppableProject
                                            project={project}
                                            assignedMemberIds={assignedMemberIds}
                                            members={members}
                                        />
                                    </div>
                                );
                            })}
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


