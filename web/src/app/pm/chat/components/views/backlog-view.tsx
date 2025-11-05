// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import type { DragEndEvent, DragStartEvent } from "@dnd-kit/core";
import { DndContext, DragOverlay, PointerSensor, closestCenter, useDroppable, useSensor, useSensors } from "@dnd-kit/core";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { ChevronDown, ChevronRight, Filter, GripVertical, Search, X } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { Button } from "~/components/ui/button";
import { Card } from "~/components/ui/card";
import { Input } from "~/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { useProjects } from "~/core/api/hooks/pm/use-projects";
import { useSprints } from "~/core/api/hooks/pm/use-sprints";
import type { Task } from "~/core/api/hooks/pm/use-tasks";
import { useTasks } from "~/core/api/hooks/pm/use-tasks";

import { TaskDetailsModal } from "../task-details-modal";

// Task card component with drag handle
function TaskCard({ task, onClick }: { task: Task; onClick: () => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: task.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      className="flex items-center gap-2 p-2 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700 hover:shadow-sm transition-shadow cursor-pointer"
    >
      <div
        {...listeners}
        className="cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 shrink-0"
      >
        <GripVertical className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0" onClick={onClick}>
        <div className="text-sm font-medium text-gray-900 dark:text-white truncate">
          {task.title}
        </div>
        {task.assigned_to && (
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {task.assigned_to}
          </div>
        )}
      </div>
      {task.priority && (
        <span className={`px-1.5 py-0.5 text-xs rounded shrink-0 ${
          task.priority === "high" || task.priority === "highest" || task.priority === "critical"
            ? "bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200"
            : task.priority === "medium"
            ? "bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200"
            : "bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200"
        }`}>
          {task.priority}
        </span>
      )}
    </div>
  );
}

// Epic sidebar component (placeholder for now)
function EpicSidebar({ 
  onEpicSelect, 
  tasks,
  onTaskUpdate: _onTaskUpdate 
}: { 
  onEpicSelect: (epicId: string | null) => void;
  tasks: Task[];
  onTaskUpdate: (taskId: string, updates: Partial<Task>) => Promise<void>;
}) {
  const [selectedEpic, setSelectedEpic] = useState<string | null>("all");
  const [expandedEpics, setExpandedEpics] = useState<Set<string>>(new Set());

  const toggleEpic = (epicId: string) => {
    setExpandedEpics(prev => {
      const next = new Set(prev);
      if (next.has(epicId)) {
        next.delete(epicId);
      } else {
        next.add(epicId);
      }
      return next;
    });
  };

  // Placeholder epics data - will be replaced with real API data later
  const epics = [
    { id: "epic-1", name: "Epic 1", color: "bg-yellow-400", issueCount: 5, completed: 2 },
    { id: "epic-2", name: "Epic 2", color: "bg-orange-400", issueCount: 3, completed: 1 },
  ];

  return (
    <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col h-full">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-gray-900 dark:text-white">EPICS</h3>
          <Button variant="ghost" size="sm" className="h-6 px-2">
            <X className="w-4 h-4" />
          </Button>
        </div>
        <Button variant="outline" size="sm" className="w-full">
          Create epic
        </Button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2">
        <EpicDropZone
          id="epic-all"
          label="All issues"
          isSelected={selectedEpic === "all"}
          onClick={() => {
            setSelectedEpic("all");
            onEpicSelect(null);
          }}
        />

        {epics.map((epic) => (
          <EpicDropZone
            key={epic.id}
            id={`epic-${epic.id}`}
            label={epic.name}
            color={epic.color}
            issueCount={tasks.filter(t => t.epic_id === epic.id).length}
            isSelected={selectedEpic === epic.id}
            isExpanded={expandedEpics.has(epic.id)}
            onClick={() => {
              toggleEpic(epic.id);
              setSelectedEpic(epic.id);
              onEpicSelect(epic.id);
            }}
          />
        ))}

        <EpicDropZone
          id="epic-none"
          label="Issues without epics"
          isSelected={false}
          onClick={() => {
            setSelectedEpic(null);
            onEpicSelect(null);
          }}
          className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700"
        />
      </div>
    </div>
  );
}

// Epic drop zone component
function EpicDropZone({
  id,
  label,
  color,
  issueCount,
  isSelected,
  isExpanded,
  onClick,
  className = ""
}: {
  id: string;
  label: string;
  color?: string;
  issueCount?: number;
  isSelected: boolean;
  isExpanded?: boolean;
  onClick: () => void;
  className?: string;
}) {
  const { setNodeRef, isOver } = useDroppable({ id });

  return (
    <div
      ref={setNodeRef}
      onClick={onClick}
      className={`p-2 rounded cursor-pointer mb-1 transition-colors ${
        isOver 
          ? "bg-blue-100 dark:bg-blue-900 border-2 border-blue-400" 
          : isSelected 
          ? "bg-blue-50 dark:bg-blue-950" 
          : "hover:bg-gray-100 dark:hover:bg-gray-700"
      } ${className}`}
    >
      <div className="flex items-center gap-2">
        {isExpanded !== undefined && (
          isExpanded ? (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400" />
          )
        )}
        {color && <div className={`w-3 h-3 rounded ${color}`}></div>}
        <span className="text-sm font-medium text-gray-900 dark:text-white flex-1 truncate">
          {label}
        </span>
        {issueCount !== undefined && (
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {issueCount}
          </span>
        )}
      </div>
      {isOver && (
        <div className="mt-1 text-xs text-blue-600 dark:text-blue-400 font-medium">
          Drop to link to epic
        </div>
      )}
    </div>
  );
}

// Sprint section component (vertical list)
function SprintSection({ sprint, tasks, onTaskClick }: { sprint: { id: string; name: string; start_date?: string; end_date?: string; status: string }; tasks: Task[]; onTaskClick: (task: Task) => void }) {
  const { setNodeRef, isOver } = useDroppable({ id: `sprint-${sprint.id}` });
  
  // Map sprint status to determine if it's active, closed, or future
  const isActive = sprint.status === "active";
  const isClosed = sprint.status === "closed";
  const isFuture = sprint.status === "future";
  
  return (
    <div className="mb-4">
      <div className={`p-3 rounded-t-lg border border-b-0 ${
        isActive 
          ? "bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800" 
          : isClosed
          ? "bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700 opacity-75"
          : isFuture
          ? "bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800"
          : "bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700"
      }`}>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">{sprint.name}</h3>
            {sprint.start_date && sprint.end_date && (
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                {new Date(sprint.start_date).toLocaleDateString()} • {new Date(sprint.end_date).toLocaleDateString()}
              </p>
            )}
            {!sprint.start_date && !sprint.end_date && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                <Button variant="ghost" size="sm" className="h-4 px-1 text-xs">
                  Add dates
                </Button>
              </p>
            )}
          </div>
          <span className="px-2 py-1 bg-white dark:bg-gray-800 rounded text-sm font-medium text-gray-700 dark:text-gray-300">
            {tasks.length} {tasks.length === 1 ? "issue" : "issues"}
          </span>
        </div>
      </div>
      <div 
        ref={setNodeRef}
        className={`p-3 rounded-b-lg border-2 border-dashed transition-colors min-h-[100px] ${
          isOver 
            ? "border-blue-400 bg-blue-50 dark:bg-blue-950" 
            : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
        }`}
      >
        {tasks.length === 0 ? (
          <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
            {isOver ? "Drop task here" : (
              <div>
                <Button variant="outline" size="sm" className="mt-2">
                  + Create issue
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            {tasks.map((task) => (
              <TaskCard key={task.id} task={task} onClick={() => onTaskClick(task)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Backlog section component
function BacklogSection({ tasks, onTaskClick }: { tasks: Task[]; onTaskClick: (task: Task) => void }) {
  const { setNodeRef, isOver } = useDroppable({ id: "backlog" });
  
  return (
    <div className="mt-4">
      <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-t-lg border border-b-0 border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900 dark:text-white">Backlog</h3>
          <span className="px-2 py-1 bg-white dark:bg-gray-800 rounded text-sm font-medium text-gray-700 dark:text-gray-300">
            {tasks.length} {tasks.length === 1 ? "issue" : "issues"}
          </span>
        </div>
      </div>
      <div 
        ref={setNodeRef}
        className={`p-3 rounded-b-lg border-2 border-dashed transition-colors min-h-[150px] ${
          isOver 
            ? "border-blue-400 bg-blue-50 dark:bg-blue-950" 
            : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
        }`}
      >
        {tasks.length === 0 ? (
          <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
            {isOver ? "Drop task here to remove from sprint" : "No tasks in backlog"}
          </div>
        ) : (
          <div className="space-y-2">
            {tasks.map((task) => (
              <TaskCard key={task.id} task={task} onClick={() => onTaskClick(task)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function BacklogView() {
  const { projects } = useProjects();
  const searchParams = useSearchParams();
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [selectedEpic, setSelectedEpic] = useState<string | null>(null);
  
  // Get active project from URL
  const activeProjectId = searchParams.get('project');
  const activeProject = useMemo(() => {
    if (!activeProjectId) return null;
    const parts = activeProjectId.split(':');
    const projectId = parts.length > 1 ? parts[1] : activeProjectId;
    return projects.find(p => {
      const pParts = p.id.split(':');
      const pId = pParts.length > 1 ? pParts[1] : p.id;
      return pId === projectId || p.id === activeProjectId;
    });
  }, [activeProjectId, projects]);
  
  // Fetch sprints for the active project - use full project ID (with provider_id)
  const projectIdForSprints = useMemo(() => {
    if (!activeProject) return null;
    // Use the full project ID including provider_id so backend can identify the provider
    return activeProject.id;
  }, [activeProject]);
  
  // Fetch tasks for the active project - use full project ID (with provider_id)
  const { tasks, loading, error } = useTasks(projectIdForSprints ?? undefined);
  // Fetch all sprints (active, closed, future) - no state filter to show all
  const { sprints, loading: sprintsLoading } = useSprints(projectIdForSprints ?? "", undefined);
  
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
    setIsModalOpen(true);
  };

  const handleUpdateTask = async (taskId: string, updates: Partial<Task>) => {
    try {
      const response = await fetch(resolveServiceURL(`pm/tasks/${taskId}`), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (!response.ok) throw new Error('Failed to update task');
      
      window.dispatchEvent(new CustomEvent("pm_refresh", { 
        detail: { type: "pm_refresh" } 
      }));
    } catch (error) {
      console.error("Failed to update task:", error);
      throw error;
    }
  };

  // Filter tasks
  const filteredTasks = useMemo(() => {
    let filtered = tasks;

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(t => 
        t.title.toLowerCase().includes(query) ||
        (t.description?.toLowerCase().includes(query)) ||
        (t.project_name?.toLowerCase().includes(query))
      );
    }

    // Status filter
    if (statusFilter !== "all") {
      filtered = filtered.filter(t => {
        const status = t.status?.toLowerCase() || "";
        if (statusFilter === "todo") {
          return !status || status === "none" || status.includes("todo") || status.includes("new");
        }
        if (statusFilter === "in-progress") {
          return status.includes("progress") || status.includes("in_progress");
        }
        if (statusFilter === "done") {
          return status.includes("done") || status.includes("completed") || status.includes("closed");
        }
        return status === statusFilter;
      });
    }

    // Priority filter
    if (priorityFilter !== "all") {
      filtered = filtered.filter(t => {
        const priority = t.priority?.toLowerCase() || "";
        if (priorityFilter === "high") {
          return priority === "high" || priority === "highest" || priority === "critical";
        }
        if (priorityFilter === "low") {
          return priority === "low" || priority === "lowest";
        }
        return priority === priorityFilter;
      });
    }

    return filtered;
  }, [tasks, searchQuery, statusFilter, priorityFilter]);

  // Filter tasks by selected epic
  const epicFilteredTasks = useMemo(() => {
    if (!selectedEpic) return filteredTasks;
    if (selectedEpic === "all") return filteredTasks;
    // Filter by epic_id
    return filteredTasks.filter(task => task.epic_id === selectedEpic);
  }, [filteredTasks, selectedEpic]);

  // Group tasks by sprint
  const tasksInSprints = useMemo(() => {
    const grouped: Record<string, Task[]> = {};
    sprints.forEach(sprint => {
      grouped[sprint.id] = epicFilteredTasks.filter(task => task.sprint_id === sprint.id);
    });
    return grouped;
  }, [sprints, epicFilteredTasks]);

  // Backlog tasks (tasks not in any sprint)
  const backlogTasks = useMemo(() => {
    const sprintIds = new Set(sprints.map(s => s.id));
    return epicFilteredTasks.filter(task => !task.sprint_id || !sprintIds.has(task.sprint_id));
  }, [epicFilteredTasks, sprints]);

  // Handle drag end - assign task to sprint, epic, or remove from sprint
  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over) return;

    const taskId = active.id as string;
    const overId = over.id as string;

    // Check if dropped on backlog (remove from sprint)
    if (overId === "backlog") {
      try {
        await handleUpdateTask(taskId, { sprint_id: undefined });
      } catch (error) {
        console.error("Failed to remove task from sprint:", error);
      }
      return;
    }

    // Check if dropped on an epic
    if (typeof overId === "string" && overId.startsWith("epic-")) {
      const epicId = overId.replace("epic-", "");
      
      // Handle "all" or "none" epic drops
      if (epicId === "all" || epicId === "none") {
        // Remove from epic
        try {
          await handleUpdateTask(taskId, { epic_id: undefined });
        } catch (error) {
          console.error("Failed to remove task from epic:", error);
        }
      } else {
        // Assign to epic
        try {
          await handleUpdateTask(taskId, { epic_id: epicId });
        } catch (error) {
          console.error("Failed to assign task to epic:", error);
        }
      }
      return;
    }

    // Check if dropped on a sprint
    if (typeof overId === "string" && overId.startsWith("sprint-")) {
      const sprintId = overId.replace("sprint-", "");
      
      try {
        await handleUpdateTask(taskId, { sprint_id: sprintId });
      } catch (error) {
        console.error("Failed to assign task to sprint:", error);
      }
    }
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const draggedTask = useMemo(() => {
    if (!activeId) return null;
    return tasks.find(t => t.id === activeId);
  }, [activeId, tasks]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">Loading backlog...</div>
      </div>
    );
  }

  if (error) {
    const isProjectUnavailable = error.message.includes("no longer available") || error.message.includes("410");
    const isNotFound = error.message.includes("not found") || error.message.includes("404");
    const isAuthError = error.message.includes("Authentication") || error.message.includes("401") || error.message.includes("403");
    
    return (
      <div className="flex flex-col items-center justify-center py-20 px-4">
        <div className="text-red-500 font-semibold mb-2">
          {isProjectUnavailable ? "Project No Longer Available" : 
           isNotFound ? "Project Not Found" :
           isAuthError ? "Authentication Error" :
           "Error Loading Tasks"}
        </div>
        <div className="text-red-400 text-sm text-center max-w-2xl mb-4">
          {error.message}
        </div>
        <div className="mt-4 text-xs text-muted-foreground text-center max-w-xl">
          {isProjectUnavailable ? (
            <>
              This project may have been deleted, archived, or is no longer accessible in your PM provider.
              <br />
              Please verify the project exists or select a different project.
            </>
          ) : isNotFound ? (
            <>
              The requested project could not be found.
              <br />
              Please check the project ID or select a different project.
            </>
          ) : isAuthError ? (
            <>
              Unable to authenticate with your PM provider.
              <br />
              Please check your PM provider configuration and credentials.
            </>
          ) : (
            <>
              Check your PM provider configuration and verify the project exists.
              <br />
              If the problem persists, try refreshing the page or selecting a different project.
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
      onDragStart={handleDragStart}
    >
      <div className="flex h-full">
        {/* Left Sidebar - Epics */}
        <EpicSidebar 
          onEpicSelect={setSelectedEpic}
          tasks={tasks}
          onTaskUpdate={handleUpdateTask}
        />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Top Header with Filters */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Backlog</h2>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm">Only My Issues</Button>
                <Button variant="ghost" size="sm">Recently Updated</Button>
              </div>
            </div>

            {/* Filters */}
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="text"
                    placeholder="Search tasks..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                   <SelectTrigger className="w-[140px]">
                     <Filter className="w-4 h-4 mr-2" />
                     <SelectValue placeholder="Status" />
                   </SelectTrigger>
                   <SelectContent>
                     <SelectItem value="all">All Status</SelectItem>
                     <SelectItem value="todo">To Do</SelectItem>
                     <SelectItem value="in-progress">In Progress</SelectItem>
                     <SelectItem value="done">Done</SelectItem>
                   </SelectContent>
                 </Select>
                 <Select value={priorityFilter} onValueChange={setPriorityFilter}>
                   <SelectTrigger className="w-[140px]">
                     <SelectValue placeholder="Priority" />
                   </SelectTrigger>
                   <SelectContent>
                     <SelectItem value="all">All Priority</SelectItem>
                     <SelectItem value="high">High</SelectItem>
                     <SelectItem value="medium">Medium</SelectItem>
                     <SelectItem value="low">Low</SelectItem>
                   </SelectContent>
                 </Select>
              </div>
            </div>
          </div>

          {/* Sprints and Backlog - Scrollable */}
          <div className="flex-1 overflow-y-auto p-6">
            {!activeProjectId ? (
              <Card className="p-6">
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                  Please select a project to view sprints
                </div>
              </Card>
            ) : sprintsLoading ? (
              <Card className="p-6">
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                  Loading sprints...
                </div>
              </Card>
            ) : (
              <div>
                {/* Sprints - stacked vertically */}
                {sprints.map((sprint) => (
                  <SprintSection
                    key={sprint.id}
                    sprint={sprint}
                    tasks={tasksInSprints[sprint.id] ?? []}
                    onTaskClick={handleTaskClick}
                  />
                ))}

                {/* Backlog - at the bottom */}
                <BacklogSection
                  tasks={backlogTasks}
                  onTaskClick={handleTaskClick}
                />
              </div>
            )}
          </div>
        </div>
      </div>

      <DragOverlay>
        {draggedTask ? (
          <div className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-lg opacity-90">
            <div className="font-medium text-sm text-gray-900 dark:text-white">
              {draggedTask.title}
            </div>
          </div>
        ) : null}
      </DragOverlay>

      <TaskDetailsModal
        task={selectedTask}
        open={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedTask(null);
        }}
        onUpdate={handleUpdateTask}
      />
    </DndContext>
  );
}

