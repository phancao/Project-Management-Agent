// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { DndContext, DragOverlay, PointerSensor, useSensor, useSensors, closestCenter, useDroppable, DragOverEvent } from "@dnd-kit/core";
import type { DragEndEvent, DragStartEvent } from "@dnd-kit/core";
import { useSortable } from "@dnd-kit/sortable";
import { SortableContext, verticalListSortingStrategy, horizontalListSortingStrategy, arrayMove } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Search, Filter, GripVertical, GripHorizontal } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useState, useMemo, useEffect, useCallback } from "react";

import { Card } from "~/components/ui/card";
import { Input } from "~/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { resolveServiceURL } from "~/core/api/resolve-service-url";
import type { Task } from "~/core/api/hooks/pm/use-tasks";
import { useTasks, useMyTasks } from "~/core/api/hooks/pm/use-tasks";
import { usePriorities } from "~/core/api/hooks/pm/use-priorities";
import { useEpics } from "~/core/api/hooks/pm/use-epics";
import { useStatuses } from "~/core/api/hooks/pm/use-statuses";
import { useSprints } from "~/core/api/hooks/pm/use-sprints";

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

function SortableColumn({ column, tasks, onTaskClick, activeColumnId, activeId, isDraggingColumn }: { 
  column: { id: string; title: string }; 
  tasks: any[]; 
  onTaskClick: (task: any) => void;
  activeColumnId?: string | null;
  activeId?: string | null;
  isDraggingColumn?: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: column.id,
    data: {
      type: 'column',
    },
  });

  const { setNodeRef: setDroppableRef, isOver } = useDroppable({ 
    id: column.id,
    data: {
      type: 'column',
      column: column.id,
    },
  });

  // Combine refs for both sortable and droppable
  const combinedRef = (node: HTMLDivElement | null) => {
    setNodeRef(node);
    setDroppableRef(node);
  };

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };
  
  // Filter out the active task being dragged from the tasks list for display
  const displayTasks = tasks.filter(task => task.id !== activeId);
  const isActive = isOver || activeColumnId === column.id;
  
  return (
    <div 
      ref={combinedRef}
      style={style}
      className="flex flex-col"
    >
      <div className="flex items-center justify-between p-3 bg-gray-100 dark:bg-gray-800 rounded-t-lg">
        <div className="flex items-center gap-2 flex-1">
          <div
            {...attributes}
            {...listeners}
            className="cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 shrink-0"
          >
            <GripHorizontal className="w-4 h-4" />
          </div>
          <h3 className="font-semibold text-gray-900 dark:text-white">{column.title}</h3>
        </div>
        <span className="px-2 py-1 bg-white dark:bg-gray-700 rounded text-sm font-medium text-gray-700 dark:text-gray-300">
          {tasks.length}
        </span>
      </div>
      <div 
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
  const [sprintFilter, setSprintFilter] = useState<string | null>(null);
  const [activeColumnId, setActiveColumnId] = useState<string | null>(null);
  const [reorderedTasks, setReorderedTasks] = useState<Record<string, any[]>>({});
  const [columnOrder, setColumnOrder] = useState<string[]>([]);
  const [draggedColumnId, setDraggedColumnId] = useState<string | null>(null);
  
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
  
  // Fetch priorities, epics, statuses, and sprints from backend for the active project
  const { priorities: availablePrioritiesFromBackend } = usePriorities(activeProjectId ?? undefined);
  const { epics } = useEpics(activeProjectId ?? undefined);
  const { statuses: availableStatuses } = useStatuses(activeProjectId ?? undefined, "task");
  const { sprints } = useSprints(activeProjectId ?? undefined);
  
  // Reset filters when project changes (but don't reset columnOrder - let it load from localStorage)
  useEffect(() => {
    setSearchQuery("");
    setPriorityFilter("all");
    setEpicFilter(null);
    setSprintFilter(null);
    // Note: columnOrder will be loaded from localStorage in the effect below
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

    // Sprint filter
    if (sprintFilter && sprintFilter !== "all") {
      filtered = filtered.filter(task => {
        if (sprintFilter === "none") {
          return !task.sprint_id;
        }
        return task.sprint_id === sprintFilter;
      });
    }

    return filtered;
  }, [tasks, searchQuery, priorityFilter, epicFilter, sprintFilter, loading]);

  const handleDragStart = (event: DragStartEvent) => {
    console.log('[handleDragStart] Drag started:', event.active.id);
    const activeIdStr = event.active.id as string;
    
    // Check if we're dragging a column (status ID)
    if (availableStatuses && availableStatuses.some(s => s.id === activeIdStr)) {
      setDraggedColumnId(activeIdStr);
      return;
    }
    
    // Otherwise, it's a task being dragged
    setActiveId(activeIdStr);
    const task = tasks.find(t => t.id === activeIdStr);
    if (task && availableStatuses) {
      // Find the status that matches this task's status
      const currentStatus = availableStatuses.find(status => {
        const taskStatusLower = (task.status || "").toLowerCase();
        const statusNameLower = status.name.toLowerCase();
        return taskStatusLower === statusNameLower || 
               taskStatusLower.includes(statusNameLower) || 
               statusNameLower.includes(taskStatusLower);
      });
      if (currentStatus) {
        // Use status ID as column ID
        setActiveColumnId(currentStatus.id);
      }
    }
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    console.log('[handleDragOver] Drag over:', { active: active.id, over: over?.id, draggedColumnId });
    
    // Handle column reordering
    if (draggedColumnId) {
      if (!over || !availableStatuses) {
        setActiveColumnId(null);
        return;
      }
      
      const activeId = draggedColumnId;
      let overId: string | null = null;
      
      // Check if we're over a column (status ID) directly
      if (typeof over.id === 'string' && availableStatuses.some(s => s.id === over.id)) {
        overId = over.id;
      } else {
        // Check if we're over something inside a column - look at the data
        const overData = over.data.current;
        if (overData?.type === 'column' && overData?.column) {
          overId = overData.column;
        }
      }
      
      // Visual feedback: highlight the target column if it's different from the dragged column
      if (overId && overId !== activeId && availableStatuses.some(s => s.id === overId)) {
        setActiveColumnId(overId);
      } else {
        setActiveColumnId(null);
      }
      return;
    }
    
    if (!over || !availableStatuses) {
      setActiveColumnId(null);
      setReorderedTasks({});
      return;
    }
    
    const activeId = active.id as string;
    let targetColumnId: string | null = null;
    
    // Check if we're over a column (column ID is status ID)
    const overStatus = availableStatuses.find(status => status.id === over.id);
    if (overStatus) {
      targetColumnId = overStatus.id;
      
      // When dragging over an empty column, show the task at the end
      const columnTasks = getTasksForColumn(overStatus.id);
      const activeTask = tasks.find(t => t.id === activeId);
      
      if (activeTask && columnTasks.length > 0) {
        const tasksWithoutActive = columnTasks.filter(t => t.id !== activeId);
        setReorderedTasks({
          ...reorderedTasks,
          [overStatus.id]: [...tasksWithoutActive, activeTask]
        });
      } else if (activeTask && columnTasks.length === 0) {
        // Empty column - just add the task
        setReorderedTasks({
          ...reorderedTasks,
          [overStatus.id]: [activeTask]
        });
      }
    } else {
      // Check if we're over a task (which means we're in that task's column)
      const overTask = tasks.find(t => t.id === over.id);
      if (overTask && availableStatuses) {
        // Find which status this task belongs to
        const taskStatus = availableStatuses.find(status => {
          const taskStatusLower = (overTask.status || "").toLowerCase();
          const statusNameLower = status.name.toLowerCase();
          return taskStatusLower === statusNameLower || 
                 taskStatusLower.includes(statusNameLower) || 
                 statusNameLower.includes(taskStatusLower);
        });
        if (taskStatus) {
          targetColumnId = taskStatus.id;
          
          // Reorder tasks visually within the column to show where the task will be dropped
          const columnTasks = getTasksForColumn(taskStatus.id);
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
                [taskStatus.id]: newOrder
              });
            } else if (tasksWithoutActive.length > 0) {
              // If we're over the column but not a specific task, add to end
              setReorderedTasks({
                ...reorderedTasks,
                [taskStatus.id]: [...tasksWithoutActive, activeTask]
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
    console.log('[handleDragEnd] Drag ended:', { active: active.id, over: over?.id, draggedColumnId });
    
    // Handle column reordering
    if (draggedColumnId) {
      const activeColumnId = draggedColumnId;
      setDraggedColumnId(null);
      setActiveColumnId(null);
      
      if (over && availableStatuses) {
        let overId: string | null = null;
        
        // Check if we dropped directly on a column (status ID)
        if (typeof over.id === 'string' && availableStatuses.some(s => s.id === over.id)) {
          overId = over.id;
        } else {
          // Check if we dropped on something inside a column - look at the data
          const overData = over.data.current;
          if (overData?.type === 'column' && overData?.column) {
            overId = overData.column;
          }
        }
        
        if (overId && overId !== activeColumnId && availableStatuses.some(s => s.id === overId)) {
          // Ensure columnOrder is initialized (use current ordered columns if columnOrder is empty)
          let currentOrder = columnOrder;
          if (currentOrder.length === 0 && availableStatuses) {
            // Initialize from current column order (sorted by default, then name)
            const sortedStatuses = [...availableStatuses].sort((a, b) => {
              if (a.is_default && !b.is_default) return -1;
              if (!a.is_default && b.is_default) return 1;
              return a.name.localeCompare(b.name);
            });
            currentOrder = sortedStatuses.map(s => s.id);
            setColumnOrder(currentOrder);
          }
          
          const oldIndex = currentOrder.indexOf(activeColumnId);
          const newIndex = currentOrder.indexOf(overId);
          
          if (oldIndex !== -1 && newIndex !== -1 && oldIndex !== newIndex) {
            const newOrder = arrayMove(currentOrder, oldIndex, newIndex);
            setColumnOrder(newOrder);
            console.log('[handleDragEnd] Column reordered:', { from: oldIndex, to: newIndex, activeColumnId, overId, newOrder });
          } else {
            console.log('[handleDragEnd] Column reorder skipped:', { oldIndex, newIndex, activeColumnId, overId, currentOrder });
          }
        }
      }
      return;
    }
    
    // Handle task dragging
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
    // Column IDs are now status IDs, so we can directly use them
    let targetColumnId: string | null = null;
    
    // Check if we dropped directly on a column (status ID)
    if (availableStatuses) {
      const droppedOnStatus = availableStatuses.find(status => status.id === overId);
      if (droppedOnStatus) {
        targetColumnId = droppedOnStatus.id;
      } else {
        // We dropped on a task, find which status that task belongs to
        const droppedOnTask = tasks.find(t => t.id === overId);
        if (droppedOnTask) {
          const taskStatus = availableStatuses.find(status => {
            const taskStatusLower = (droppedOnTask.status || "").toLowerCase();
            const statusNameLower = status.name.toLowerCase();
            return taskStatusLower === statusNameLower || 
                   taskStatusLower.includes(statusNameLower) || 
                   statusNameLower.includes(taskStatusLower);
          });
          if (taskStatus) {
            targetColumnId = taskStatus.id;
          }
        }
      }
    }

    if (!targetColumnId || !availableStatuses) {
      console.log('[handleDragEnd] Could not determine target column');
      return;
    }

    // Find the status corresponding to the target column ID
    const targetStatus = availableStatuses.find(status => status.id === targetColumnId);
    if (!targetStatus) {
      console.warn(`[handleDragEnd] Cannot find status for column ID '${targetColumnId}'`);
      return;
    }

    const newStatus = targetStatus.name;

    console.log(`[handleDragEnd] Moving task from '${task.status}' to '${newStatus}' (status ID: ${targetColumnId})`);

    // Don't update if status is the same
    if (newStatus === task.status) {
      console.log(`[handleDragEnd] Task already has status '${newStatus}', skipping update`);
      return;
    }

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

  // Helper function to get tasks for a status column (used by both handleDragOver and columns)
  const getTasksForColumn = useCallback((statusId: string) => {
    if (reorderedTasks[statusId]) {
      return reorderedTasks[statusId];
    }
    
    if (!availableStatuses) {
      return [];
    }
    
    // Find the status by ID
    const status = availableStatuses.find(s => s.id === statusId);
    if (!status) {
      return [];
    }
    
    // Match tasks to this status by comparing status names
    const matchedTasks = filteredTasks.filter(task => {
      const taskStatusLower = (task.status || "").toLowerCase().trim();
      const statusNameLower = status.name.toLowerCase().trim();
      
      // Normalize status names (replace underscores, dashes, spaces)
      const normalizeStatus = (s: string) => s.replace(/[_\s-]/g, '').toLowerCase();
      const normalizedTaskStatus = normalizeStatus(taskStatusLower || "");
      const normalizedStatusName = normalizeStatus(statusNameLower || "");
      
      // Try multiple matching strategies
      const matches = 
        // Exact match (case-insensitive)
        taskStatusLower === statusNameLower ||
        // Normalized match (handles "in_progress" vs "in progress" vs "in-progress")
        normalizedTaskStatus === normalizedStatusName ||
        // Partial match (either direction)
        taskStatusLower.includes(statusNameLower) ||
        statusNameLower.includes(taskStatusLower) ||
        // Handle tasks with no status - assign to first status if it's the default
        (!task.status && status.is_default);
      
      return matches;
    });
    
    // Debug logging for unmatched tasks
    if (matchedTasks.length === 0 && filteredTasks.length > 0) {
      const unmatchedSample = filteredTasks.slice(0, 3).map(t => ({
        id: t.id,
        title: t.title,
        status: t.status
      }));
      console.log(`[getTasksForColumn] Status "${status.name}" (${statusId}): No tasks matched. Sample task statuses:`, unmatchedSample);
    }
    
    return matchedTasks;
  }, [availableStatuses, filteredTasks, reorderedTasks]);

  // Create columns dynamically based on available statuses
  const columns = useMemo(() => {
    if (!availableStatuses || availableStatuses.length === 0) {
      return [];
    }
    
    // Sort statuses: default first, then by name (or you could use a custom order)
    const sortedStatuses = [...availableStatuses].sort((a, b) => {
      // Put default status first
      if (a.is_default && !b.is_default) return -1;
      if (!a.is_default && b.is_default) return 1;
      // Then sort by name
      return a.name.localeCompare(b.name);
    });
    
    const columns = sortedStatuses.map(status => ({
      id: status.id,
      title: status.name,
      tasks: getTasksForColumn(status.id),
    }));
    
    // Debug: Log total tasks distributed across columns
    const totalTasksInColumns = columns.reduce((sum, col) => sum + col.tasks.length, 0);
    console.log(`[SprintBoard] Total tasks in columns: ${totalTasksInColumns}, Total filtered tasks: ${filteredTasks.length}, Available statuses:`, availableStatuses.map(s => s.name));
    
    // Debug: Find unmatched tasks
    const matchedTaskIds = new Set(columns.flatMap(col => col.tasks.map(t => t.id)));
    const unmatchedTasks = filteredTasks.filter(t => !matchedTaskIds.has(t.id));
    if (unmatchedTasks.length > 0) {
      console.warn(`[SprintBoard] Found ${unmatchedTasks.length} unmatched tasks:`, unmatchedTasks.map(t => ({
        id: t.id,
        title: t.title,
        status: t.status
      })));
    }
    
    return columns;
  }, [availableStatuses, getTasksForColumn, filteredTasks]);

  // Helper functions for localStorage persistence
  const getStorageKey = (projectId: string | null) => {
    if (!projectId) return null;
    return `sprint-board-column-order-${projectId}`;
  };

  const loadColumnOrderFromStorage = useCallback((projectId: string | null): string[] | null => {
    if (typeof window === 'undefined' || !projectId) return null;
    const key = getStorageKey(projectId);
    if (!key) return null;
    try {
      const saved = localStorage.getItem(key);
      if (saved) {
        const order = JSON.parse(saved);
        if (Array.isArray(order) && order.length > 0) {
          return order;
        }
      }
    } catch (error) {
      console.error('[SprintBoard] Failed to load column order from localStorage:', error);
    }
    return null;
  }, []);

  const saveColumnOrderToStorage = useCallback((projectId: string | null, order: string[]) => {
    if (typeof window === 'undefined' || !projectId || order.length === 0) return;
    const key = getStorageKey(projectId);
    if (!key) return;
    try {
      localStorage.setItem(key, JSON.stringify(order));
      console.log('[SprintBoard] Saved column order to localStorage:', { projectId, order });
    } catch (error) {
      console.error('[SprintBoard] Failed to save column order to localStorage:', error);
    }
  }, []);

  // Track the last loaded project ID to avoid re-loading on every render
  const [lastLoadedProjectId, setLastLoadedProjectId] = useState<string | null>(null);
  // Track if we're currently loading from localStorage to avoid saving during initial load
  const [isLoadingFromStorage, setIsLoadingFromStorage] = useState(false);

  // Load column order from localStorage when project or statuses change
  useEffect(() => {
    if (availableStatuses && availableStatuses.length > 0 && activeProjectId) {
      // Only load if project changed or we haven't loaded yet
      if (lastLoadedProjectId !== activeProjectId) {
        setIsLoadingFromStorage(true);
        // Try to load saved order from localStorage
        const savedOrder = loadColumnOrderFromStorage(activeProjectId);
        
        if (savedOrder && savedOrder.length > 0) {
          // Validate that all saved status IDs still exist in availableStatuses
          const validStatusIds = new Set(availableStatuses.map(s => s.id));
          const validOrder = savedOrder.filter(id => validStatusIds.has(id));
          
          // Add any missing statuses (new statuses that weren't in the saved order)
          const missingStatuses = availableStatuses
            .filter(s => !validOrder.includes(s.id))
            .sort((a, b) => {
              if (a.is_default && !b.is_default) return -1;
              if (!a.is_default && b.is_default) return 1;
              return a.name.localeCompare(b.name);
            });
          
          const finalOrder = [...validOrder, ...missingStatuses.map(s => s.id)];
          setColumnOrder(finalOrder);
          setLastLoadedProjectId(activeProjectId);
          console.log('[SprintBoard] Loaded column order from localStorage:', { projectId: activeProjectId, finalOrder });
          // Reset loading flag after a brief delay to allow state to settle
          setTimeout(() => setIsLoadingFromStorage(false), 100);
        } else {
          // No saved order, use default (sorted by default first, then name)
          const sortedStatuses = [...availableStatuses].sort((a, b) => {
            if (a.is_default && !b.is_default) return -1;
            if (!a.is_default && b.is_default) return 1;
            return a.name.localeCompare(b.name);
          });
          const defaultOrder = sortedStatuses.map(s => s.id);
          setColumnOrder(defaultOrder);
          setLastLoadedProjectId(activeProjectId);
          console.log('[SprintBoard] Using default column order:', defaultOrder);
          // Reset loading flag after a brief delay to allow state to settle
          setTimeout(() => setIsLoadingFromStorage(false), 100);
        }
      }
    } else if (!activeProjectId && lastLoadedProjectId) {
      // Clear column order when no project is selected
      setColumnOrder([]);
      setLastLoadedProjectId(null);
    }
  }, [availableStatuses, activeProjectId, lastLoadedProjectId, loadColumnOrderFromStorage]);

  // Save column order to localStorage whenever it changes (but not during initial load)
  useEffect(() => {
    if (isLoadingFromStorage) {
      // Don't save during initial load from localStorage
      return;
    }
    
    if (columnOrder.length > 0 && activeProjectId && availableStatuses) {
      // Only save if we have all statuses in the order
      const statusIds = new Set(availableStatuses.map(s => s.id));
      const orderHasAllStatuses = columnOrder.every(id => statusIds.has(id)) &&
                                   availableStatuses.every(s => columnOrder.includes(s.id));
      
      if (orderHasAllStatuses) {
        saveColumnOrderToStorage(activeProjectId, columnOrder);
      }
    }
  }, [columnOrder, activeProjectId, availableStatuses, isLoadingFromStorage, saveColumnOrderToStorage]);

  // Apply column order to columns
  const orderedColumns = useMemo(() => {
    if (columnOrder.length === 0) {
      return columns;
    }
    
    // Create a map for quick lookup
    const columnMap = new Map(columns.map(col => [col.id, col]));
    
    // Return columns in the order specified by columnOrder
    const ordered = columnOrder
      .map(id => columnMap.get(id))
      .filter((col): col is typeof columns[0] => col !== undefined);
    
    // Add any columns that weren't in the order (new statuses)
    const orderedIds = new Set(columnOrder);
    const newColumns = columns.filter(col => !orderedIds.has(col.id));
    
    return [...ordered, ...newColumns];
  }, [columns, columnOrder]);

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
            {sprints.length > 0 && (
              <Select 
                value={sprintFilter ?? "all"} 
                onValueChange={(value) => setSprintFilter(value === "all" ? null : value)}
              >
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Sprint" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Sprints</SelectItem>
                  <SelectItem value="none">No Sprint</SelectItem>
                  {sprints.map((sprint) => (
                    <SelectItem key={sprint.id} value={sprint.id}>
                      {sprint.name}
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
        {orderedColumns.length > 0 ? (
          <SortableContext 
            items={orderedColumns.map(col => col.id)} 
            strategy={horizontalListSortingStrategy}
          >
            <div className="flex gap-4 overflow-x-auto pb-4">
              {orderedColumns.map((column) => (
                <div key={column.id} className="flex-shrink-0 w-80">
                  <SortableColumn 
                    column={{ id: column.id, title: column.title }} 
                    tasks={column.tasks} 
                    onTaskClick={handleTaskClick}
                    activeColumnId={activeColumnId}
                    activeId={activeId}
                    isDraggingColumn={draggedColumnId === column.id}
                  />
                </div>
              ))}
            </div>
          </SortableContext>
        ) : (
          <div className="flex items-center justify-center py-20">
            <div className="text-gray-500 dark:text-gray-400">No statuses available for this project</div>
          </div>
        )}

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
