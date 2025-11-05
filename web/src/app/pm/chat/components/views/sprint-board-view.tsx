// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { DndContext, DragOverlay, PointerSensor, useSensor, useSensors, closestCenter, useDroppable, DragOverEvent } from "@dnd-kit/core";
import type { DragEndEvent, DragStartEvent } from "@dnd-kit/core";
import { useSortable } from "@dnd-kit/sortable";
import { SortableContext, verticalListSortingStrategy, arrayMove } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Search, Filter, GripVertical } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useState, useMemo, useEffect } from "react";

import { Card } from "~/components/ui/card";
import { Input } from "~/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { resolveServiceURL } from "~/core/api/resolve-service-url";
import type { Task } from "~/core/api/hooks/pm/use-tasks";
import { useTasks, useMyTasks } from "~/core/api/hooks/pm/use-tasks";
import { usePriorities } from "~/core/api/hooks/pm/use-priorities";
import { useEpics } from "~/core/api/hooks/pm/use-epics";
import { useStatuses } from "~/core/api/hooks/pm/use-statuses";

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
      className="flex items-center gap-2 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow cursor-pointer"
    >
      <div
        {...listeners}
        className="cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 shrink-0"
      >
        <GripVertical className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0" onClick={onClick}>
        <div className="font-medium text-sm text-gray-900 dark:text-white mb-2">
          {task.title}
        </div>
        <div className="flex items-center gap-2 text-xs">
          {task.priority && (
            <span className={`px-2 py-0.5 rounded ${
              task.priority === "high" || task.priority === "highest" || task.priority === "critical"
                ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                : task.priority === "medium"
                ? "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200"
                : "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
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
    </div>
  );
}

function Column({ column, tasks, onTaskClick, activeColumnId, activeId }: { 
  column: { id: string; title: string }; 
  tasks: any[]; 
  onTaskClick: (task: any) => void;
  activeColumnId?: string | null;
  activeId?: string | null;
}) {
  const { setNodeRef, isOver } = useDroppable({ 
    id: column.id,
    data: {
      type: 'column',
      column: column.id,
    },
  });
  
  // Filter out the active task being dragged from the tasks list for display
  const displayTasks = tasks.filter(task => task.id !== activeId);
  const isActive = isOver || activeColumnId === column.id;
  
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
        className={`flex-1 rounded-b-lg p-3 min-h-[400px] border-2 overflow-y-auto transition-all duration-200 ${
          isActive
            ? 'bg-blue-100 dark:bg-blue-950 border-blue-500 dark:border-blue-500' 
            : 'bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800'
        }`}
      >
        {displayTasks.length === 0 ? (
          <div className={`text-sm text-gray-500 dark:text-gray-400 text-center py-8 font-medium ${isActive ? 'text-blue-700 dark:text-blue-300' : ''}`}>
            {isActive ? 'Drop here' : 'No tasks'}
          </div>
        ) : (
            <SortableContext items={displayTasks.map(t => t.id)} strategy={verticalListSortingStrategy}>
              <div className="space-y-2">
                {displayTasks.map((task) => (
                  <TaskCard key={task.id} task={task} onClick={() => onTaskClick(task)} />
                ))}
              </div>
            </SortableContext>
        )}
      </div>
    </div>
  );
}

export function SprintBoardView() {
  const searchParams = useSearchParams();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const [epicFilter, setEpicFilter] = useState<string | null>(null);
  const [activeColumnId, setActiveColumnId] = useState<string | null>(null);
  const [reorderedTasks, setReorderedTasks] = useState<Record<string, any[]>>({});
  
  // Get project from URL (if any)
  const activeProjectId = searchParams.get('project');
  
  // Use project-specific tasks if a project is selected, otherwise use "my tasks"
  const projectIdForTasks = useMemo(() => {
    if (!activeProjectId) return undefined;
    // Use the full project ID including provider_id so backend can identify the provider
    return activeProjectId;
  }, [activeProjectId]);
  
  const tasksHook = activeProjectId ? useTasks(projectIdForTasks) : useMyTasks();
  const { tasks, loading, error, refresh: refreshTasks } = tasksHook;
  
  // Fetch priorities, epics, and statuses from backend for the active project
  const { priorities: availablePrioritiesFromBackend } = usePriorities(activeProjectId ?? undefined);
  const { epics } = useEpics(activeProjectId ?? undefined);
  const { statuses: availableStatuses } = useStatuses(activeProjectId ?? undefined, "task");
  
  // Reset filters when project changes
  useEffect(() => {
    setSearchQuery("");
    setPriorityFilter("all");
    setEpicFilter(null);
  }, [activeProjectId]);
  
  // Use priorities from backend, with fallback to task data
  const availablePriorities = useMemo(() => {
    if (availablePrioritiesFromBackend && availablePrioritiesFromBackend.length > 0) {
      // Use backend priorities, store lowercase value for matching
      return availablePrioritiesFromBackend.map(priority => ({
        value: priority.name.toLowerCase(),
        label: priority.name
      }));
    }
    // Fallback: extract from tasks if backend doesn't have priorities
    const priorityMap = new Map<string, string>(); // lowercase -> original case
    tasks.forEach(task => {
      if (task.priority) {
        const lower = task.priority.toLowerCase();
        if (!priorityMap.has(lower)) {
          priorityMap.set(lower, task.priority);
        }
      }
    });
    return Array.from(priorityMap.entries()).map(([lower, original]) => ({ value: lower, label: original }));
  }, [availablePrioritiesFromBackend, tasks]);
  
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );
  
  // Filter tasks
  const filteredTasks = useMemo(() => {
    // Return empty array only if we're loading AND have no tasks yet (to prevent flash of stale data)
    // If we have tasks, always filter them even if loading is true (for real-time filtering)
    if (loading && (!tasks || tasks.length === 0)) return [];
    
    // If we have no tasks at all, return empty
    if (!tasks || tasks.length === 0) return [];
    
    let filtered = [...tasks]; // Create a copy to avoid mutating original

    // Search filter - search in title and description only
    const trimmedQuery = (searchQuery || "").trim();
    if (trimmedQuery) {
      const query = trimmedQuery.toLowerCase();
      filtered = filtered.filter(t => {
        if (!t) return false;
        const title = (t.title || "").toLowerCase();
        const description = (t.description || "").toLowerCase();
        // Search in title and description only
        const matches = title.includes(query) || description.includes(query);
        return matches;
      });
    }

    // Priority filter - match by exact priority (case-insensitive)
    if (priorityFilter && priorityFilter !== "all") {
      const filterPriorityLower = priorityFilter.toLowerCase();
      filtered = filtered.filter(t => {
        const taskPriority = (t.priority || "").toLowerCase();
        return taskPriority === filterPriorityLower;
      });
    }

    // Epic filter
    if (epicFilter && epicFilter !== "all") {
      filtered = filtered.filter(task => {
        if (epicFilter === "none") {
          return !task.epic_id;
        }
        return task.epic_id === epicFilter;
      });
    }

    return filtered;
  }, [tasks, searchQuery, priorityFilter, epicFilter, loading]);

  const handleDragStart = (event: DragStartEvent) => {
    console.log('[handleDragStart] Drag started:', event.active.id);
    setActiveId(event.active.id as string);
    // Find which column the task is currently in
    const task = tasks.find(t => t.id === event.active.id);
    if (task) {
      // Determine current column based on status
      const currentColumn = columns.find(col => {
        const colTasks = col.tasks;
        return colTasks.some(t => t.id === task.id);
      });
      if (currentColumn) {
        setActiveColumnId(currentColumn.id);
      }
    }
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    console.log('[handleDragOver] Drag over:', { active: active.id, over: over?.id });
    
    if (!over) {
      setActiveColumnId(null);
      setReorderedTasks({});
      return;
    }
    
    const activeId = active.id as string;
    let targetColumnId: string | null = null;
    
    // Check if we're over a column
    const overColumn = columns.find(col => col.id === over.id);
    if (overColumn) {
      targetColumnId = overColumn.id;
      
      // When dragging over an empty column, show the task at the end
      const columnTasks = getTasksForColumn(overColumn.id);
      const activeTask = tasks.find(t => t.id === activeId);
      
      if (activeTask && columnTasks.length > 0) {
        const tasksWithoutActive = columnTasks.filter(t => t.id !== activeId);
        setReorderedTasks({
          ...reorderedTasks,
          [overColumn.id]: [...tasksWithoutActive, activeTask]
        });
      } else if (activeTask && columnTasks.length === 0) {
        // Empty column - just add the task
        setReorderedTasks({
          ...reorderedTasks,
          [overColumn.id]: [activeTask]
        });
      }
    } else {
      // Check if we're over a task (which means we're in that task's column)
      const overTask = tasks.find(t => t.id === over.id);
      if (overTask) {
        const taskColumn = columns.find(col => {
          return col.tasks.some(t => t.id === overTask.id);
        });
        if (taskColumn) {
          targetColumnId = taskColumn.id;
          
          // Reorder tasks visually within the column to show where the task will be dropped
          const columnTasks = getTasksForColumn(taskColumn.id);
          const activeTask = tasks.find(t => t.id === activeId);
          
          if (activeTask) {
            // Remove active task from its current position
            const tasksWithoutActive = columnTasks.filter(t => t.id !== activeId);
            const overIndex = tasksWithoutActive.findIndex(t => t.id === over.id);
            
            if (overIndex >= 0) {
              // Insert active task at the position of the over task
              const newOrder = [...tasksWithoutActive];
              newOrder.splice(overIndex, 0, activeTask);
              setReorderedTasks({
                ...reorderedTasks,
                [taskColumn.id]: newOrder
              });
            } else if (tasksWithoutActive.length > 0) {
              // If we're over the column but not a specific task, add to end
              setReorderedTasks({
                ...reorderedTasks,
                [taskColumn.id]: [...tasksWithoutActive, activeTask]
              });
            }
          }
        }
      }
    }
    
    setActiveColumnId(targetColumnId);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    console.log('[handleDragEnd] Drag ended:', { active: active.id, over: over?.id });
    setActiveId(null);
    setActiveColumnId(null);
    setReorderedTasks({});

    if (!over) {
      console.log('[handleDragEnd] No drop target, cancelling');
      return;
    }

    const activeId = active.id as string;
    const overId = over.id as string;

    // Find the task being dragged
    const task = tasks.find(t => t.id === activeId);
    if (!task) return;

    // Determine which column we're dropping into
    // If we dropped on a task, find which column that task belongs to
    let targetColumnId: string | null = null;
    
    // Check if we dropped directly on a column
    const droppedOnColumn = columns.find(col => col.id === overId);
    if (droppedOnColumn) {
      targetColumnId = overId;
    } else {
      // We dropped on a task, find which column contains that task
      const droppedOnTask = tasks.find(t => t.id === overId);
      if (droppedOnTask) {
        const taskColumn = columns.find(col => {
          return col.tasks.some(t => t.id === droppedOnTask.id);
        });
        if (taskColumn) {
          targetColumnId = taskColumn.id;
        }
      }
    }

    if (!targetColumnId) {
      console.log('[handleDragEnd] Could not determine target column');
      return;
    }

    // Map column IDs to status keywords (try to match with backend statuses)
    const columnStatusMap: Record<string, string[]> = {
      'todo': ['todo', 'new', 'open', 'to do', 'to-do'],
      'in-progress': ['in progress', 'in_progress', 'inprogress', 'working', 'active'],
      'review': ['review', 'pending', 'in review', 'needs review'],
      'done': ['done', 'completed', 'closed', 'finished', 'resolved'],
    };

    // Try to find matching status from backend
    const columnKeywords = columnStatusMap[targetColumnId] || [];
    let newStatus: string | null = null;

    // First, try to find exact match in backend statuses
    if (availableStatuses && availableStatuses.length > 0) {
      const matchedStatus = availableStatuses.find(status => {
        const statusLower = status.name.toLowerCase();
        return columnKeywords.some(keyword => statusLower.includes(keyword) || keyword.includes(statusLower));
      });
      if (matchedStatus) {
        newStatus = matchedStatus.name;
      }
    }

    // Fallback to task status if no match found, or use a default mapping
    if (!newStatus) {
      // Use default mapping based on column
      const defaultMap: Record<string, string> = {
        'todo': 'todo',
        'in-progress': 'in_progress',
        'review': 'review',
        'done': 'completed',
      };
      newStatus = defaultMap[targetColumnId] || null;
    }

    if (!newStatus || newStatus === task.status) return;

    // Update task status via API
    try {
      await handleUpdateTask(activeId, { status: newStatus });
    } catch (err) {
      console.error('Failed to update task status:', err);
    }
  };

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
    setIsModalOpen(true);
  };

  const handleUpdateTask = async (taskId: string, updates: Partial<Task>) => {
    try {
      if (!activeProjectId) {
        throw new Error("Project ID is required to update a task");
      }
      
      const url = new URL(resolveServiceURL(`pm/tasks/${taskId}`));
      url.searchParams.set('project_id', activeProjectId);
      
      console.log(`[handleUpdateTask] Updating task ${taskId}`);
      console.log(`[handleUpdateTask] URL: ${url.toString()}`);
      console.log(`[handleUpdateTask] Updates:`, updates);
      
      const response = await fetch(url.toString(), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `Failed to update task: ${response.status} ${response.statusText}`;
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || errorMessage;
        } catch {
          if (errorText) {
            errorMessage = errorText;
          }
        }
        console.error(`[handleUpdateTask] Error: ${errorMessage}`);
        throw new Error(errorMessage);
      }
      
      const result = await response.json();
      console.log(`[handleUpdateTask] Success:`, result);
      
      // Update the selected task in the modal if it's the same task
      if (selectedTask && selectedTask.id === taskId) {
        setSelectedTask({
          ...selectedTask,
          ...result
        });
      }
      
      // Refresh tasks
      if (refreshTasks) {
        refreshTasks();
      } else {
        // Fallback for useMyTasks which doesn't have refresh
        window.dispatchEvent(new CustomEvent("pm_refresh", { 
          detail: { type: "pm_refresh" } 
        }));
      }
    } catch (error) {
      console.error("Failed to update task:", error);
      throw error;
    }
  };

  // Group tasks by status
  const getTasksForColumn = (columnId: string) => {
    if (reorderedTasks[columnId]) {
      return reorderedTasks[columnId];
    }
    
    switch(columnId) {
      case 'todo':
        return filteredTasks.filter(t => 
          !t.status || t.status === "None" || t.status.toLowerCase().includes("todo") || t.status.toLowerCase().includes("new")
        );
      case 'in-progress':
        return filteredTasks.filter(t => 
          t.status && (t.status.toLowerCase().includes("progress") || t.status.toLowerCase().includes("in_progress"))
        );
      case 'review':
        return filteredTasks.filter(t => 
          t.status && (t.status.toLowerCase().includes("review") || t.status.toLowerCase().includes("pending"))
        );
      case 'done':
        return filteredTasks.filter(t => 
          t.status && (t.status.toLowerCase().includes("done") || t.status.toLowerCase().includes("completed") || t.status.toLowerCase().includes("closed"))
        );
      default:
        return [];
    }
  };

  const todoTasks = getTasksForColumn('todo');
  const inProgressTasks = getTasksForColumn('in-progress');
  const reviewTasks = getTasksForColumn('review');
  const doneTasks = getTasksForColumn('done');

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
            {availablePriorities.length > 0 && (
              <Select value={priorityFilter} onValueChange={setPriorityFilter}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Priority" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Priority</SelectItem>
                  {availablePriorities.map(({ value, label }) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            {epics.length > 0 && (
              <Select 
                value={epicFilter ?? "all"} 
                onValueChange={(value) => setEpicFilter(value === "all" ? null : value)}
              >
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Epic" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Epics</SelectItem>
                  <SelectItem value="none">No Epic</SelectItem>
                  {epics.map((epic) => (
                    <SelectItem key={epic.id} value={epic.id}>
                      {epic.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </div>
      </Card>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        {/* Kanban Board */}
        <div className="grid grid-cols-4 gap-4">
          {columns.map((column) => (
            <Column 
              key={column.id} 
              column={{ id: column.id, title: column.title }} 
              tasks={column.tasks} 
              onTaskClick={handleTaskClick}
              activeColumnId={activeColumnId}
              activeId={activeId}
            />
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
        projectId={activeProjectId}
      />
    </div>
  );
}
