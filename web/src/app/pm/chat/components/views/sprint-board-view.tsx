// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { DndContext, DragOverlay, PointerSensor, useSensor, useSensors, closestCenter, useDroppable } from "@dnd-kit/core";
import type { DragEndEvent, DragStartEvent } from "@dnd-kit/core";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Search, Filter } from "lucide-react";
import { useSearchParams, useRouter } from "next/navigation";
import { useState, useMemo, useEffect } from "react";

import { Card } from "~/components/ui/card";
import { Input } from "~/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { useProjects } from "~/core/api/hooks/pm/use-projects";
import type { Task } from "~/core/api/hooks/pm/use-tasks";
import { useMyTasks } from "~/core/api/hooks/pm/use-tasks";

import { TaskDetailsModal } from "../task-details-modal";

function TaskCard({ task, onClick }: { task: any; onClick: () => void }) {
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
      {...listeners}
      onClick={onClick}
      className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow cursor-pointer"
    >
      <div className="font-medium text-sm text-gray-900 dark:text-white mb-2">
        {task.title}
      </div>
      <div className="flex items-center gap-2 text-xs">
        {task.priority && (
          <span className={`px-2 py-0.5 rounded ${
            task.priority === "high" ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" :
            task.priority === "medium" ? "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200" :
            "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
          }`}>
            {task.priority}
          </span>
        )}
        {task.estimated_hours && (
          <span className="text-gray-500 dark:text-gray-400">
            ⏱️ {task.estimated_hours}h
          </span>
        )}
      </div>
    </div>
  );
}

function Column({ column, tasks, onTaskClick }: { column: { id: string; title: string }; tasks: any[]; onTaskClick: (task: any) => void }) {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });
  
  return (
    <div className="flex flex-col">
      <div className="flex items-center justify-between p-3 bg-gray-100 dark:bg-gray-800 rounded-t-lg">
        <h3 className="font-semibold text-gray-900 dark:text-white">{column.title}</h3>
        <span className="px-2 py-1 bg-white dark:bg-gray-700 rounded text-sm font-medium text-gray-700 dark:text-gray-300">
          {tasks.length}
        </span>
      </div>
      <div 
        ref={setNodeRef}
        className={`flex-1 bg-gray-50 dark:bg-gray-900 rounded-b-lg p-3 min-h-[400px] border border-gray-200 dark:border-gray-700 overflow-y-auto ${isOver ? 'bg-blue-50 dark:bg-blue-950' : ''}`}
      >
        {tasks.length === 0 ? (
          <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
            No tasks
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

export function SprintBoardView() {
  const { tasks, loading, error } = useMyTasks();
  const { projects } = useProjects();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  
  // Get project filter from URL, fallback to local state
  const activeProjectId = searchParams.get('project');
  const initialProjectFilter = useMemo(() => {
    if (activeProjectId) {
      const project = projects.find(p => p.id === activeProjectId);
      return project ? project.name : "all";
    }
    return "all";
  }, [activeProjectId, projects]);
  
  const [projectFilter, setProjectFilter] = useState<string>(initialProjectFilter);
  
  // Sync project filter with URL when it changes
  useEffect(() => {
    if (initialProjectFilter !== "all") {
      setProjectFilter(initialProjectFilter);
    }
  }, [initialProjectFilter]);
  
  // Handle project filter changes to update URL
  const handleProjectFilterChange = (value: string) => {
    setProjectFilter(value);
    if (value === "all") {
      router.push('/pm/chat');
    } else {
      const project = projects.find(p => p.name === value);
      if (project) {
        router.push(`/pm/chat?project=${project.id}`);
      }
    }
  };
  
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );
  
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

    // Project filter
    if (projectFilter !== "all") {
      filtered = filtered.filter(t => t.project_name === projectFilter);
    }

    return filtered;
  }, [tasks, searchQuery, priorityFilter, projectFilter]);
  
  const hasActiveFilters = priorityFilter !== "all" || projectFilter !== "all" || searchQuery;

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over) return;

    const activeId = active.id as string;
    const overId = over.id as string;

    // Find the task
    const task = tasks.find(t => t.id === activeId);
    if (!task) return;

    // Map column IDs to status
    const statusMap: Record<string, string> = {
      'todo': 'todo',
      'in-progress': 'in_progress',
      'review': 'review',
      'done': 'completed',
    };

    const newStatus = statusMap[overId];
    if (!newStatus || newStatus === task.status) return;

    // Update task status via API
    fetch(resolveServiceURL(`pm/tasks/${task.id}`), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    }).catch(err => console.error('Failed to update task:', err));
  };

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
      
      // Refresh tasks
      window.dispatchEvent(new CustomEvent("pm_refresh", { 
        detail: { type: "pm_refresh" } 
      }));
    } catch (error) {
      console.error("Failed to update task:", error);
      throw error;
    }
  };

  // Group tasks by status
  const todoTasks = filteredTasks.filter(t => 
    !t.status || t.status === "None" || t.status.toLowerCase().includes("todo") || t.status.toLowerCase().includes("new")
  );
  const inProgressTasks = filteredTasks.filter(t => 
    t.status && (t.status.toLowerCase().includes("progress") || t.status.toLowerCase().includes("in_progress"))
  );
  const reviewTasks = filteredTasks.filter(t => 
    t.status && (t.status.toLowerCase().includes("review") || t.status.toLowerCase().includes("pending"))
  );
  const doneTasks = filteredTasks.filter(t => 
    t.status && (t.status.toLowerCase().includes("done") || t.status.toLowerCase().includes("completed") || t.status.toLowerCase().includes("closed"))
  );

  const columns = [
    { id: "todo", title: "To Do", tasks: todoTasks },
    { id: "in-progress", title: "In Progress", tasks: inProgressTasks },
    { id: "review", title: "Review", tasks: reviewTasks },
    { id: "done", title: "Done", tasks: doneTasks },
  ];

  const activeTask = activeId ? filteredTasks.find(t => t.id === activeId) : null;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">Loading board...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 px-4">
        <div className="text-red-500 font-semibold mb-2">Error loading tasks</div>
        <div className="text-red-400 text-sm text-center max-w-2xl">
          {error.message}
        </div>
        <div className="mt-4 text-xs text-muted-foreground">
          Tip: Check your PM provider configuration and verify the project exists.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">Sprint Board</h2>
          {hasActiveFilters && (
            <div className="flex flex-wrap items-center gap-2">
              {searchQuery && (
                <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-700">
                  <Search className="w-3.5 h-3.5 text-gray-500 dark:text-gray-400" />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {searchQuery}
                  </span>
                  <button
                    onClick={() => setSearchQuery("")}
                    className="ml-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                    aria-label="Remove search filter"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              )}
              {priorityFilter !== "all" && (
                <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-700">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize">
                    {priorityFilter}
                  </span>
                  <button
                    onClick={() => setPriorityFilter("all")}
                    className="ml-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                    aria-label="Remove priority filter"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              )}
              {projectFilter !== "all" && (
                <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-700">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {projectFilter}
                  </span>
                  <button
                    onClick={() => setProjectFilter("all")}
                    className="ml-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                    aria-label="Remove project filter"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          {filteredTasks.length} of {tasks.length} tasks
        </div>
      </div>

      {/* Filters */}
      <Card className="p-4">
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
            <Select value={projectFilter} onValueChange={handleProjectFilterChange}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Project" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Projects</SelectItem>
                {[...new Set(tasks.map(t => t.project_name).filter((n): n is string => !!n))].map(projectName => (
                  <SelectItem key={projectName} value={projectName}>{projectName}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        {/* Kanban Board */}
        <div className="grid grid-cols-4 gap-4">
          {columns.map((column) => (
            <Column key={column.id} column={{ id: column.id, title: column.title }} tasks={column.tasks} onTaskClick={handleTaskClick} />
          ))}
        </div>

        <DragOverlay>
          {activeTask ? <TaskCard task={activeTask} onClick={() => {}} /> : null}
        </DragOverlay>
      </DndContext>

      <TaskDetailsModal
        task={selectedTask}
        open={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedTask(null);
        }}
        onUpdate={handleUpdateTask}
      />
    </div>
  );
}
