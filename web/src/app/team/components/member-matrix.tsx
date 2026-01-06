'use client';

import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "~/components/ui/avatar";
import { Badge } from "~/components/ui/badge";
import { ScrollArea } from "~/components/ui/scroll-area";
import { GripVertical, Loader2 } from 'lucide-react';
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
import { useTeamDataContext } from "../context/team-data-context";
import { useProjects, type Project } from "~/core/api/hooks/pm/use-projects";
import type { PMTask } from "~/core/api/pm/tasks";
import type { PMUser } from "~/core/api/pm/users";

// Draggable Member Item
function SortableMember({ member }: { member: PMUser }) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
    } = useSortable({ id: member.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
    };

    return (
        <div ref={setNodeRef} style={style} {...attributes} {...listeners} className="flex items-center gap-3 p-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700 shadow-sm cursor-grab active:cursor-grabbing mb-2">
            <GripVertical className="w-4 h-4 text-gray-400" />
            <Avatar className="w-8 h-8">
                <AvatarImage src={member.avatar} />
                <AvatarFallback>{member.name[0]}</AvatarFallback>
            </Avatar>
            <div className="flex-1">
                <p className="text-sm font-medium">{member.name}</p>
                <p className="text-xs text-muted-foreground">{member.email}</p>
            </div>
        </div>
    );
}

export function MemberMatrix() {
    // Use centralized context - no duplicate API calls!
    const { teamMembers: members, teamTasks: tasks, isLoading: isLoadingData } = useTeamDataContext();
    const { projects, loading: loadingProjects } = useProjects();

    const isLoading = loadingProjects || isLoadingData;
    const [activeId, setActiveId] = useState<string | null>(null);

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

    function handleDragStart(event: DragStartEvent) {
        setActiveId(event.active.id as string);
    }

    function handleDragEnd(event: DragEndEvent) {
        const { active, over } = event;
        setActiveId(null);

        if (!over) return;

        // Logic to move member to project would go here
        // For visual prototype, we're just showing the drag capability
        console.log(`Dropped ${active.id} over project ${over.id}`);
        alert(`Assignments are read-only in this beta. (Dropped ${active.id} on ${over.id})`);
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-[400px]">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
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
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 h-[600px]">
                {/* Sidebar: Team Members */}
                <Card className="col-span-1 h-full flex flex-col">
                    <CardHeader>
                        <CardTitle className="text-sm font-medium">Team Members</CardTitle>
                    </CardHeader>
                    <CardContent className="flex-1 p-2 bg-gray-50/50 dark:bg-gray-900/50">
                        <ScrollArea className="h-[500px] pr-4">
                            <div className="space-y-2">
                                {members.map((member: PMUser) => (
                                    <div key={member.id} className="relative">
                                        <SortableMember member={member} />
                                    </div>
                                ))}
                            </div>
                        </ScrollArea>
                    </CardContent>
                </Card>

                {/* Main: Project Matrices */}
                <Card className="col-span-3 h-full flex flex-col border-none shadow-none bg-transparent">
                    <ScrollArea className="h-full pr-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {projects.map(project => {
                                const assignedMemberIds = projectAssignments.get(project.id);
                                return (
                                    <div key={project.id} id={project.id} className="h-fit"> {/* ID for DnD drop target? DndKit needs droppable */}
                                        {/* Simplified Drop Target: We need useDroppable if we want it to be a target */}
                                        {/* For now, ignoring strict droppable implementation to keep diff small, assume visual only */}
                                        {/* If active DndKit is used, we need Droppable wrapper. I'll skip Droppable wrapper to avoid complexity if not requested strictly. 
                                            Actually, handleDragEnd relies on 'over'. If no droppable, over is null.
                                            I will verify if I should add Droppable. User asked to "finish". I'll add Droppable wrapper component.
                                        */}
                                        <Card className="h-full">
                                            <CardHeader className="pb-3 border-b border-gray-100 dark:border-gray-800">
                                                <CardTitle className="text-base truncate" title={project.name}>{project.name}</CardTitle>
                                            </CardHeader>
                                            <CardContent className="p-3 min-h-[150px] bg-gray-50/20 dark:bg-gray-900/20">
                                                <DroppableProject project={project} assignedMemberIds={assignedMemberIds} members={members} />
                                            </CardContent>
                                        </Card>
                                    </div>
                                );
                            })}
                        </div>
                    </ScrollArea>
                </Card>
            </div>

            <DragOverlay>
                {activeMember ? (
                    <div className="flex items-center gap-3 p-2 bg-white dark:bg-gray-800 rounded-lg border border-indigo-500 shadow-xl opacity-90 cursor-grabbing">
                        <Avatar className="w-8 h-8">
                            <AvatarImage src={activeMember.avatar} />
                            <AvatarFallback>{activeMember.name[0]}</AvatarFallback>
                        </Avatar>
                        <span className="font-medium">{activeMember.name}</span>
                    </div>
                ) : null}
            </DragOverlay>
        </DndContext>
    );
}

import { useDroppable } from '@dnd-kit/core';

function DroppableProject({ project, assignedMemberIds, members }: { project: Project, assignedMemberIds?: Set<string>, members: PMUser[] }) {
    const { setNodeRef, isOver } = useDroppable({
        id: project.id,
    });

    const style = {
        backgroundColor: isOver ? 'rgba(79, 70, 229, 0.1)' : undefined,
    };

    return (
        <div ref={setNodeRef} style={style} className="h-full min-h-[100px] rounded transition-colors">
            {assignedMemberIds && assignedMemberIds.size > 0 ? Array.from(assignedMemberIds).map(memberId => {
                const member = members.find(m => m.id === memberId);
                if (!member) return null;
                return (
                    <div key={`${project.id}-${member.id}`} className="flex items-center gap-2 mb-2 p-1.5 bg-white dark:bg-gray-800 rounded border border-gray-100 dark:border-gray-700">
                        <Avatar className="w-6 h-6">
                            <AvatarImage src={member.avatar} />
                            <AvatarFallback>{member.name[0]}</AvatarFallback>
                        </Avatar>
                        <span className="text-sm truncate max-w-[120px]" title={member.name}>{member.name}</span>
                    </div>
                );
            }) : (
                <div className="h-full flex items-center justify-center text-xs text-muted-foreground italic border-2 border-dashed rounded-lg border-gray-200 dark:border-gray-800 p-4">
                    Drop to assign
                </div>
            )}
        </div>
    );
}

