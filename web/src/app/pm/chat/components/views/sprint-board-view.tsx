// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { DndContext, DragOverlay, PointerSensor, useSensor, useSensors, closestCorners, useDroppable } from "@dnd-kit/core";
import type { DragEndEvent, DragStartEvent, DragOverEvent } from "@dnd-kit/core";
import { useSortable } from "@dnd-kit/sortable";
import { SortableContext, verticalListSortingStrategy, horizontalListSortingStrategy, arrayMove } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Search, Filter, GripVertical, GripHorizontal, Settings2 } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useState, useMemo, useEffect, useCallback, useRef } from "react";
import { toast } from "sonner";

import { Card } from "~/components/ui/card";
import { Input } from "~/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Button } from "~/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "~/components/ui/dialog";
import { Checkbox } from "~/components/ui/checkbox";
import { Label } from "~/components/ui/label";
import { resolveServiceURL } from "~/core/api/resolve-service-url";
import type { Task } from "~/core/api/hooks/pm/use-tasks";
import { useTasks, useMyTasks } from "~/core/api/hooks/pm/use-tasks";
import { usePriorities } from "~/core/api/hooks/pm/use-priorities";
import { useEpics } from "~/core/api/hooks/pm/use-epics";
import { useStatuses } from "~/core/api/hooks/pm/use-statuses";
import { useSprints } from "~/core/api/hooks/pm/use-sprints";

import { TaskDetailsModal } from "../task-details-modal";

function TaskCard({ task, onClick }: { task: any; onClick: () => void }) {
  // Ensure task.id is always a string for dnd-kit (OpenProject uses numeric IDs, JIRA uses string IDs)
  const taskId = String(task.id);
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: taskId,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    // Always use smooth transitions - dnd-kit provides the transition string
    // When dragging, only animate opacity. When not dragging, animate position changes
    transition: isDragging 
      ? 'opacity 0.2s ease-out' 
      : (transition || 'transform 300ms cubic-bezier(0.2, 0, 0, 1), opacity 300ms ease'),
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
        style={{
          touchAction: 'none',
          userSelect: 'none',
          WebkitUserSelect: 'none',
          zIndex: 10,
          position: 'relative',
        }}
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

  // Make the entire column droppable
  const { setNodeRef: setDroppableRef, isOver } = useDroppable({ 
    id: column.id,
    data: {
      type: 'column',
      column: column.id,
    },
  });

  // Separate droppable zones for top and bottom of column (easier to drop)
  const { setNodeRef: setTopDropRef, isOver: isOverTop } = useDroppable({
    id: `${column.id}-top-drop`,
    data: {
      type: 'column',
      column: column.id,
      position: 'top',
    },
  });

  const { setNodeRef: setBottomDropRef, isOver: isOverBottom } = useDroppable({
    id: `${column.id}-bottom-drop`,
    data: {
      type: 'column',
      column: column.id,
      position: 'bottom',
    },
  });

  // Separate ref for the scrollable content area (for auto-scroll)
  const scrollAreaRef = useRef<HTMLDivElement | null>(null);
  const setScrollAreaRef = (node: HTMLDivElement | null) => {
    scrollAreaRef.current = node;
  };

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
  // Convert both to strings for comparison (OpenProject uses numeric IDs, JIRA uses string IDs)
  // Memoize to ensure stable reference and prevent unnecessary re-initializations
  const displayTasks = useMemo(() => {
    return tasks.filter(task => String(task.id) !== String(activeId));
  }, [tasks, activeId]);
  
  // Memoize the items array for SortableContext to ensure stable reference
  // Use a stable string representation of task IDs to prevent unnecessary recalculations
  const sortableItems = useMemo(() => {
    const items = displayTasks.map(t => String(t.id));
    // Return empty array if no items to prevent initialization issues
    return items;
  }, [displayTasks]);
  
  // Track when items first become available to ensure proper SortableContext initialization
  // This ensures SortableContext remounts once when items first load, fixing the first-item drag issue
  // The issue occurs because dnd-kit needs SortableContext to be initialized with items present,
  // but on first render, the context might initialize before all TaskCard components have mounted
  const [sortableInitKey, setSortableInitKey] = useState(0);
  const prevItemsLengthRef = useRef(0);
  const isInitialMountRef = useRef(true);
  
  useEffect(() => {
    // On initial mount, if items are already present, we need to remount after a brief delay
    // to ensure all TaskCard components have mounted and registered with dnd-kit
    if (isInitialMountRef.current) {
      isInitialMountRef.current = false;
      if (sortableItems.length > 0) {
        // Use requestAnimationFrame to ensure DOM is ready and all components have mounted
        requestAnimationFrame(() => {
          setSortableInitKey(prev => prev + 1);
        });
      }
    } else if (sortableItems.length > 0 && prevItemsLengthRef.current === 0) {
      // When items first become available after being empty, force SortableContext remount
      setSortableInitKey(prev => prev + 1);
    }
    prevItemsLengthRef.current = sortableItems.length;
  }, [sortableItems.length]);
  
  const isActive = isOver || isOverTop || isOverBottom || activeColumnId === column.id;

  // Auto-scroll when dragging over the column near edges
  const scrollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  useEffect(() => {
    if (!isActive || !activeId || !scrollAreaRef.current) {
      // Clear any existing scroll interval when not active
      if (scrollIntervalRef.current) {
        clearInterval(scrollIntervalRef.current);
        scrollIntervalRef.current = null;
      }
      return;
    }
    
    const scrollArea = scrollAreaRef.current;
    
    const handleMouseMove = (e: MouseEvent) => {
      if (!scrollArea) return;
      
      const rect = scrollArea.getBoundingClientRect();
      const mouseY = e.clientY;
      const scrollThreshold = 100; // Distance from edge to trigger scroll
      const scrollSpeed = 10; // Pixels to scroll per interval
      
      // Check if mouse is near top or bottom edge
      const distanceFromTop = mouseY - rect.top;
      const distanceFromBottom = rect.bottom - mouseY;
      
      // Clear existing interval before starting a new one
      if (scrollIntervalRef.current) {
        clearInterval(scrollIntervalRef.current);
        scrollIntervalRef.current = null;
      }
      
      if (distanceFromTop < scrollThreshold && scrollArea.scrollTop > 0) {
        // Scroll up
        scrollIntervalRef.current = setInterval(() => {
          if (scrollArea && scrollArea.scrollTop > 0) {
            scrollArea.scrollTop = Math.max(0, scrollArea.scrollTop - scrollSpeed);
          } else if (scrollIntervalRef.current) {
            clearInterval(scrollIntervalRef.current);
            scrollIntervalRef.current = null;
          }
        }, 16); // ~60fps
      } else if (distanceFromBottom < scrollThreshold && 
                 scrollArea.scrollTop < scrollArea.scrollHeight - scrollArea.clientHeight) {
        // Scroll down
        scrollIntervalRef.current = setInterval(() => {
          if (scrollArea && scrollArea.scrollTop < scrollArea.scrollHeight - scrollArea.clientHeight) {
            scrollArea.scrollTop = Math.min(
              scrollArea.scrollHeight - scrollArea.clientHeight,
              scrollArea.scrollTop + scrollSpeed
            );
          } else if (scrollIntervalRef.current) {
            clearInterval(scrollIntervalRef.current);
            scrollIntervalRef.current = null;
          }
        }, 16); // ~60fps
      }
    };
    
    document.addEventListener('mousemove', handleMouseMove);
    
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      if (scrollIntervalRef.current) {
        clearInterval(scrollIntervalRef.current);
        scrollIntervalRef.current = null;
      }
    };
  }, [isActive, activeId]);
  
  return (
    <div 
      ref={combinedRef}
      style={style}
      className="flex flex-col"
    >
      {/* Top drop zone - only show when dragging over it to avoid blocking first task */}
      {activeId && (
        <div 
          ref={setTopDropRef}
          className={`transition-all ${
            isOverTop
              ? 'h-8 bg-blue-200 dark:bg-blue-800 border-2 border-blue-500 dark:border-blue-400 rounded-t-lg'
              : 'h-0 pointer-events-none'
          }`}
          style={{
            pointerEvents: isOverTop ? 'auto' : 'none',
          }}
        >
          {isOverTop && (
            <div className="h-full flex items-center justify-center">
              <div className="text-xs font-medium text-blue-700 dark:text-blue-300">Drop here</div>
            </div>
          )}
        </div>
      )}
      
      <div 
        {...attributes}
        {...listeners}
        className={`flex items-center justify-between p-3 rounded-t-lg transition-colors ${
          isActive && !isDraggingColumn
            ? 'bg-blue-100 dark:bg-blue-900' 
            : 'bg-gray-100 dark:bg-gray-800'
        }`}
        style={{
          touchAction: 'none',
          userSelect: 'none',
          WebkitUserSelect: 'none',
          cursor: isDragging ? 'grabbing' : 'grab',
        }}
      >
        <div className="flex items-center gap-2 flex-1">
          <div className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 shrink-0">
            <GripHorizontal className="w-4 h-4" />
          </div>
          <h3 className="font-semibold text-gray-900 dark:text-white">
            {column.title}
          </h3>
        </div>
        <span className="px-2 py-1 bg-white dark:bg-gray-700 rounded text-sm font-medium text-gray-700 dark:text-gray-300">
          {tasks.length}
        </span>
      </div>
      <div 
        ref={setScrollAreaRef}
        className={`flex-1 rounded-b-lg p-3 min-h-[400px] max-h-[600px] border-2 overflow-y-auto transition-all duration-200 ${
          isActive && !isDraggingColumn
            ? 'bg-blue-50 dark:bg-blue-950 border-blue-500 dark:border-blue-500' 
            : 'bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800'
        }`}
        style={{
          overscrollBehavior: 'contain',
        }}
      >
        {displayTasks.length === 0 ? (
          <div className={`text-sm text-gray-500 dark:text-gray-400 text-center py-8 font-medium ${isActive ? 'text-blue-700 dark:text-blue-300' : ''}`}>
            {isActive ? 'Drop here' : 'No tasks'}
          </div>
        ) : (
          <>
            {/* Drop indicator at the top when dragging over */}
            {isActive && activeId && (
              <div 
                className="h-2 bg-blue-500 dark:bg-blue-400 rounded-full mb-2 transition-opacity"
                style={{ pointerEvents: 'none' }}
              />
            )}
            <SortableContext 
              key={`sortable-${column.id}-${sortableInitKey}`}
              items={sortableItems} 
              strategy={verticalListSortingStrategy}
            >
              <div 
                className="space-y-2"
                style={{
                  // Force browser to use GPU acceleration for smoother animations
                  transform: 'translateZ(0)',
                  willChange: activeId ? 'contents' : 'auto',
                  paddingTop: '0.5rem', // Ensure first task has space for drag handle
                }}
              >
                {displayTasks.map((task) => {
                  // Use String(task.id) for key to match useSortable id and ensure stable keys
                  const taskIdStr = String(task.id);
                  return (
                    <TaskCard key={taskIdStr} task={task} onClick={() => onTaskClick(task)} />
                  );
                })}
              </div>
            </SortableContext>
            {/* Drop indicator at the bottom when dragging over */}
            {isActive && activeId && (
              <div 
                className="h-2 bg-blue-500 dark:bg-blue-400 rounded-full mt-2 transition-opacity"
                style={{ pointerEvents: 'none' }}
              />
            )}
          </>
        )}
      </div>
      
      {/* Bottom drop zone - always visible when dragging */}
      {activeId && (
        <div 
          ref={setBottomDropRef}
          className={`h-8 transition-all ${
            isOverBottom || (isActive && activeId)
              ? 'bg-blue-200 dark:bg-blue-800 border-2 border-blue-500 dark:border-blue-400 rounded-b-lg'
              : 'bg-transparent'
          }`}
        >
          {isOverBottom && (
            <div className="h-full flex items-center justify-center">
              <div className="text-xs font-medium text-blue-700 dark:text-blue-300">Drop here</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function SprintBoardView() {
  const searchParams = useSearchParams();
  const DEBUG_DND = false;
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
  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(new Set());
  const [isColumnManagerOpen, setIsColumnManagerOpen] = useState(false);
  
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
  const { sprints } = useSprints(activeProjectId || "");
  
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
    const activeIdStr = String(event.active.id);
    const activeData = event.active.data.current;
    
    console.log('[handleDragStart] Drag started:', { 
      activeId: activeIdStr, 
      dataType: activeData?.type,
      activeData 
    });
    
    // Check the data type first to distinguish between tasks and columns
    // Columns have data.type === 'column', tasks don't have a type set
    if (activeData?.type === 'column') {
      // It's a column being dragged
      console.log('[handleDragStart] Detected column drag:', activeIdStr);
      if (availableStatuses && availableStatuses.some(s => String(s.id) === activeIdStr)) {
        console.log('[handleDragStart] Setting draggedColumnId:', activeIdStr);
        setDraggedColumnId(activeIdStr);
        return;
      } else {
        console.warn('[handleDragStart] Column ID not found in availableStatuses:', activeIdStr);
      }
    } else {
      // It's likely a task - check if it exists in the tasks array
      const task = tasks.find(t => String(t.id) === activeIdStr);
      
      if (task) {
        console.log('[handleDragStart] Detected task drag:', activeIdStr);
        // It's a task being dragged - set activeId immediately
        setActiveId(activeIdStr);
        
        if (availableStatuses) {
          // Find the status that matches this task's status
          const currentStatus = availableStatuses.find(status => {
            const taskStatusLower = (task.status || "").toLowerCase();
            const statusNameLower = status.name.toLowerCase();
            return taskStatusLower === statusNameLower || 
                   taskStatusLower.includes(statusNameLower) || 
                   statusNameLower.includes(taskStatusLower);
          });
          if (currentStatus) {
            // Use status ID as column ID for highlighting
            setActiveColumnId(currentStatus.id);
          }
        }
        return;
      } else {
        console.log('[handleDragStart] Not a task, checking if it might be a column without data.type');
        // Fallback: check if it's a column by ID even without data.type
        if (availableStatuses && availableStatuses.some(s => String(s.id) === activeIdStr)) {
          console.log('[handleDragStart] Fallback: Setting draggedColumnId:', activeIdStr);
          setDraggedColumnId(activeIdStr);
          return;
        }
      }
    }
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    if (DEBUG_DND) console.log('[handleDragOver] Drag over:', { active: active.id, over: over?.id, draggedColumnId });
    
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
      // Clear reordered tasks for all columns when not over any column
      // Convert to string for comparison (OpenProject uses numeric IDs, JIRA uses string IDs)
      const activeTask = tasks.find(t => String(t.id) === String(active.id));
      if (activeTask) {
        // Find source column and clear its reordered state
        const sourceStatus = availableStatuses.find(status => {
          const taskStatusLower = (activeTask.status || "").toLowerCase();
          const statusNameLower = status.name.toLowerCase();
          return taskStatusLower === statusNameLower || 
                 taskStatusLower.includes(statusNameLower) || 
                 statusNameLower.includes(taskStatusLower);
        });
        
        if (sourceStatus) {
          // Restore original order for source column
          const newReorderedTasks = { ...reorderedTasks };
          delete newReorderedTasks[sourceStatus.id];
          setReorderedTasks(newReorderedTasks);
        }
      }
      setActiveColumnId(null);
      return;
    }
    
    const activeId = active.id as string;
    let targetColumnId: string | null = null;
    
    // Check if we're over a column directly (column ID is status ID)
    const overStatus = availableStatuses.find(status => status.id === over.id);
    if (overStatus) {
      targetColumnId = overStatus.id;
    } else {
      // Check if we're over something inside a column - look at the data
      const overData = over.data.current;
      if (overData?.type === 'column' && overData?.column) {
        targetColumnId = overData.column;
      } else {
        // Check if we're over a task (which means we're in that task's column)
        // Convert to string for comparison (OpenProject uses numeric IDs, JIRA uses string IDs)
        const overTask = tasks.find(t => String(t.id) === String(over.id));
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
          }
        }
      }
    }
    
    // Update visual reordering if we have a target column
    if (targetColumnId) {
      const targetStatus = availableStatuses.find(status => status.id === targetColumnId);
      if (targetStatus) {
        const columnTasks = getTasksForColumn(targetStatus.id);
        // Convert to string for comparison (OpenProject uses numeric IDs, JIRA uses string IDs)
        const activeTask = tasks.find(t => String(t.id) === String(activeId));
        
        if (activeTask) {
          // Find the source column (where the task currently is)
          const sourceStatus = availableStatuses.find(status => {
            const taskStatusLower = (activeTask.status || "").toLowerCase();
            const statusNameLower = status.name.toLowerCase();
            return taskStatusLower === statusNameLower || 
                   taskStatusLower.includes(statusNameLower) || 
                   statusNameLower.includes(taskStatusLower);
          });
          
          // Prepare new reordered tasks state - preserve existing reordered tasks
          const newReorderedTasks = { ...reorderedTasks };
          
          // Get base tasks for target column (without the active task)
          const baseTargetTasks = filteredTasks.filter(task => {
            // Convert to string for comparison (OpenProject uses numeric IDs, JIRA uses string IDs)
            if (String(task.id) === String(activeId)) return false;
            const taskStatusLower = (task.status || "").toLowerCase().trim();
            const statusNameLower = targetStatus.name.toLowerCase().trim();
            const normalizeStatus = (s: string) => s.replace(/[_\s-]/g, '').toLowerCase();
            const normalizedTaskStatus = normalizeStatus(taskStatusLower || "");
            const normalizedStatusName = normalizeStatus(statusNameLower || "");
            return taskStatusLower === statusNameLower ||
                   normalizedTaskStatus === normalizedStatusName ||
                   taskStatusLower.includes(statusNameLower) ||
                   statusNameLower.includes(taskStatusLower);
          });
          
          // Get base tasks for source column (without the active task)
          let baseSourceTasks: any[] = [];
          if (sourceStatus && sourceStatus.id !== targetColumnId) {
            baseSourceTasks = filteredTasks.filter(task => {
              // Convert to string for comparison (OpenProject uses numeric IDs, JIRA uses string IDs)
              if (String(task.id) === String(activeId)) return false;
              const taskStatusLower = (task.status || "").toLowerCase().trim();
              const statusNameLower = sourceStatus.name.toLowerCase().trim();
              const normalizeStatus = (s: string) => s.replace(/[_\s-]/g, '').toLowerCase();
              const normalizedTaskStatus = normalizeStatus(taskStatusLower || "");
              const normalizedStatusName = normalizeStatus(statusNameLower || "");
              return taskStatusLower === statusNameLower ||
                     normalizedTaskStatus === normalizedStatusName ||
                     taskStatusLower.includes(statusNameLower) ||
                     statusNameLower.includes(taskStatusLower);
            });
          }
          
          // Determine insertion position in target column
          let targetOrder: any[];
          // Convert to string for comparison (OpenProject uses numeric IDs, JIRA uses string IDs)
          const overTask = tasks.find(t => String(t.id) === String(over.id));
          
          // Check if we're over a task in the target column
          if (overTask && overTask.status) {
            const taskStatusMatch = availableStatuses.find(status => {
              const taskStatusLower = (overTask.status || "").toLowerCase();
              const statusNameLower = status.name.toLowerCase();
              return taskStatusLower === statusNameLower || 
                     taskStatusLower.includes(statusNameLower) || 
                     statusNameLower.includes(taskStatusLower);
            });
            
            if (taskStatusMatch?.id === targetColumnId) {
              // Insert at the position of the over task
              // Convert to string for comparison (OpenProject uses numeric IDs, JIRA uses string IDs)
              const overIndex = baseTargetTasks.findIndex(t => String(t.id) === String(over.id));
              if (overIndex >= 0) {
                targetOrder = [...baseTargetTasks];
                targetOrder.splice(overIndex, 0, activeTask);
              } else {
                targetOrder = [...baseTargetTasks, activeTask];
              }
            } else {
              targetOrder = [...baseTargetTasks, activeTask];
            }
          } else {
            targetOrder = baseTargetTasks.length === 0 
              ? [activeTask]
              : [...baseTargetTasks, activeTask];
          }
          
          newReorderedTasks[targetColumnId] = targetOrder;
          
          // Update source column (remove task) - only if different from target
          if (sourceStatus && sourceStatus.id !== targetColumnId) {
            newReorderedTasks[sourceStatus.id] = baseSourceTasks;
          }
          
          // Update both columns simultaneously for smooth animation
          // Use requestAnimationFrame to ensure DOM updates happen before state change
          requestAnimationFrame(() => {
            setReorderedTasks(newReorderedTasks);
          });
        }
      }
    }
    
    setActiveColumnId(targetColumnId);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (DEBUG_DND) console.log('[handleDragEnd] Drag ended:', { active: active.id, over: over?.id, draggedColumnId });
    
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
            if (DEBUG_DND) console.log('[handleDragEnd] Column reordered:', { from: oldIndex, to: newIndex, activeColumnId, overId, newOrder });
          } else {
            if (DEBUG_DND) console.log('[handleDragEnd] Column reorder skipped:', { oldIndex, newIndex, activeColumnId, overId, currentOrder });
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
      if (DEBUG_DND) console.log('[handleDragEnd] No drop target, cancelling');
      return;
    }

    const activeId = active.id as string;
    const overId = over.id as string;

    // Find the task being dragged
    // Convert to string for comparison (OpenProject uses numeric IDs, JIRA uses string IDs)
    const task = tasks.find(t => String(t.id) === String(activeId));
    if (!task) return;

    // Determine which column we're dropping into
    // Column IDs are now status IDs, so we can directly use them
    let targetColumnId: string | null = null;
    
    // Check if we dropped on a top/bottom drop zone
    if (typeof overId === 'string' && (overId.endsWith('-top-drop') || overId.endsWith('-bottom-drop'))) {
      // Extract the column ID from the drop zone ID
      const columnId = overId.replace(/-top-drop$/, '').replace(/-bottom-drop$/, '');
      if (availableStatuses?.some(s => s.id === columnId)) {
        targetColumnId = columnId;
      }
    } else if (availableStatuses) {
      // Check if we dropped directly on a column (status ID)
      const droppedOnStatus = availableStatuses.find(status => status.id === overId);
      if (droppedOnStatus) {
        targetColumnId = droppedOnStatus.id;
      } else {
        // Check if we're over something inside a column - look at the data
        const overData = over.data.current;
        if (overData?.type === 'column' && overData?.column) {
          targetColumnId = overData.column;
        } else {
          // We dropped on a task, find which status that task belongs to
          // Convert to string for comparison (OpenProject uses numeric IDs, JIRA uses string IDs)
          const droppedOnTask = tasks.find(t => String(t.id) === String(overId));
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
    }

    if (!targetColumnId || !availableStatuses) {
      if (DEBUG_DND) console.log('[handleDragEnd] Could not determine target column');
      return;
    }

    // Find the status corresponding to the target column ID
    const targetStatus = availableStatuses.find(status => status.id === targetColumnId);
    if (!targetStatus) {
      console.warn(`[handleDragEnd] Cannot find status for column ID '${targetColumnId}'`);
      return;
    }

    const newStatus = targetStatus.name;

    if (DEBUG_DND) console.log(`[handleDragEnd] Moving task from '${task.status}' to '${newStatus}' (status ID: ${targetColumnId})`);

    // Don't update if status is the same
    if (newStatus === task.status) {
      if (DEBUG_DND) console.log(`[handleDragEnd] Task already has status '${newStatus}', skipping update`);
      return;
    }

    // Update task status via API
    // Always send the status name (not ID) to match manual editing behavior
    // The backend will look up the status by name, which works correctly
    
    // Verify the status exists in available statuses before sending
    const targetStatusExists = availableStatuses.some(s => s.id === targetColumnId);
    if (!targetStatusExists) {
      console.error(`[handleDragEnd] Status ID '${targetColumnId}' not found in available statuses`);
      toast.error('Invalid status', {
        description: `The selected status is not available.`,
        duration: 4000,
      });
      return;
    }

    // Always send the status name (not the ID) to match manual editing behavior
    // The backend will look up the status by name, which works correctly
    const statusValue = newStatus;
    
    console.log(`[handleDragEnd] Updating task ${activeId} status to: ${statusValue} (status name from column ID: ${targetColumnId})`);
    
    // Handle the update and catch errors to show toast notification instead of console error
    try {
        // Get the original task status before update
        const originalTask = tasks.find(t => String(t.id) === String(activeId));
        const originalStatus = originalTask?.status || 'No status';
        
        const result = await handleUpdateTask(activeId, { 
          status: statusValue,
        });
        
        // Get the actual status returned from OpenProject/JIRA
        const actualStatus = result?.status || null;
        
        // Normalize status values for comparison (handle null, undefined, empty string, "No status", etc.)
        const normalizeStatusForComparison = (status: string | null | undefined): string => {
          if (!status) return '';
          const normalized = status.toLowerCase().trim();
          // Treat "new", "no status", empty string as the same
          if (normalized === '' || normalized === 'new' || normalized === 'no status' || normalized === 'none') {
            return '';
          }
          return normalized;
        };
        
        // Also try to match status by checking if it's in the available statuses
        // This handles cases where the status name might be slightly different
        const findMatchingStatusId = (statusName: string | null | undefined): string | null => {
          if (!statusName || !availableStatuses) return null;
          const normalized = normalizeStatusForComparison(statusName);
          // First try exact match
          let matching = availableStatuses.find(s => {
            const sNormalized = normalizeStatusForComparison(s.name);
            return sNormalized === normalized;
          });
          // If no exact match, try partial match
          if (!matching) {
            matching = availableStatuses.find(s => {
              const sNormalized = normalizeStatusForComparison(s.name);
              return sNormalized.includes(normalized) || normalized.includes(sNormalized);
            });
          }
          const foundId = matching?.id || null;
          console.log(`[handleDragEnd] findMatchingStatusId: statusName="${statusName}", normalized="${normalized}", foundId="${foundId}", matchingStatus="${matching?.name}"`);
          return foundId;
        };
        
        const actualStatusNormalized = normalizeStatusForComparison(actualStatus);
        const expectedStatusNormalized = normalizeStatusForComparison(newStatus);
        const originalStatusNormalized = normalizeStatusForComparison(originalStatus);
        
        // Check if the actual status matches the target column ID
        const actualStatusId = findMatchingStatusId(actualStatus);
        const statusMatchesTargetColumn = actualStatusId === targetColumnId;
        
        console.log(`[handleDragEnd] Status ID matching:`, {
          actualStatus,
          actualStatusId,
          targetColumnId,
          statusMatchesTargetColumn,
          availableStatuses: availableStatuses?.map(s => ({ id: s.id, name: s.name })),
        });
        
        // Display-friendly status names
        const displayStatus = (status: string | null | undefined): string => {
          if (!status || status === '' || status.toLowerCase().trim() === 'new' || status.toLowerCase().trim() === 'no status') {
            return 'No status';
          }
          return status;
        };
        
        const displayOriginal = displayStatus(originalStatus);
        const displayActual = displayStatus(actualStatus);
        const displayExpected = displayStatus(newStatus);
        
        console.log(`[handleDragEnd] Status update result:`, {
          original: originalStatus,
          originalNormalized: originalStatusNormalized,
          expected: newStatus,
          expectedNormalized: expectedStatusNormalized,
          expectedColumnId: targetColumnId,
          actual: actualStatus,
          actualNormalized: actualStatusNormalized,
          actualStatusId: actualStatusId,
          statusMatchesTargetColumn,
          resultObject: result,
        });
        
        // Check if the status actually changed to what we expected
        // First, check if status changed at all
        const statusChanged = actualStatusNormalized !== originalStatusNormalized;
        // Check if status name matches
        const statusNameMatches = actualStatusNormalized === expectedStatusNormalized;
        // Check if status ID matches the target column
        const statusIdMatches = statusMatchesTargetColumn;
        // Overall match: both name and ID should match (or at least one if ID is not available)
        const statusMatchesExpected = statusNameMatches && (statusIdMatches || actualStatusId === null);
        
        console.log(`[handleDragEnd] Status change analysis:`, {
          statusChanged,
          statusNameMatches,
          statusIdMatches,
          statusMatchesExpected,
          statusMatchesTargetColumn,
          originalStatusNormalized,
          expectedStatusNormalized,
          actualStatusNormalized,
          targetColumnId,
          actualStatusId,
          comparison: {
            'actual === expected (name)': actualStatusNormalized === expectedStatusNormalized,
            'actualId === targetColumnId': actualStatusId === targetColumnId,
            'actual !== original': actualStatusNormalized !== originalStatusNormalized,
          }
        });
        
        // IMPORTANT: Only show success if status actually changed AND matches expected
        // If status didn't change, it means the update was ignored by OpenProject
        if (!statusChanged) {
          console.warn(`[handleDragEnd] Status did not change. Expected: ${newStatus} (${expectedStatusNormalized}, column: ${targetColumnId}), Got: ${actualStatus} (${actualStatusNormalized}, column: ${actualStatusId}), Original: ${originalStatus} (${originalStatusNormalized})`);
          toast.error('Status update failed', {
            description: `The task status could not be changed from "${displayOriginal}" to "${displayExpected}". The status remains "${displayActual}". This may be due to workflow restrictions or permissions.`,
            duration: 6000,
          });
          return; // Exit early - don't show success
        }
        
        // If status changed but doesn't match the target column, it's a partial success
        if (statusChanged && !statusIdMatches && actualStatusId !== null) {
          console.warn(`[handleDragEnd] Status changed but to different column. Expected column: ${targetColumnId}, Got column: ${actualStatusId}`);
          toast.error('Status update partially successful', {
            description: `Task status changed from "${displayOriginal}" to "${displayActual}" but may not be in the expected column. The system may have applied a different status due to workflow rules.`,
            duration: 5000,
          });
          return;
        }
        
        if (statusChanged && statusMatchesExpected) {
          // Clear reordered tasks for the source and target columns to force UI update
          // This ensures the task moves to the correct column after status change
          // We need to clear both columns so the UI recalculates based on the refreshed task list
          const sourceStatusId = findMatchingStatusId(originalStatus);
          console.log(`[handleDragEnd] Clearing reordered tasks for source column: ${sourceStatusId}, target column: ${targetColumnId}`);
          
          setReorderedTasks(prev => {
            const updated = { ...prev };
            if (sourceStatusId) {
              delete updated[sourceStatusId];
            }
            if (targetColumnId) {
              delete updated[targetColumnId];
            }
            console.log(`[handleDragEnd] Updated reorderedTasks:`, Object.keys(updated));
            return updated;
          });
          
          // Capture task ID before clearing activeId
          const updatedTaskId = activeId;
          
          // Also clear activeId to ensure the task is no longer filtered out
          setActiveId(null);
          setActiveColumnId(null);
          
          // Wait a bit for the refresh to complete, then verify the task status
          // This ensures we show the correct notification based on what actually happened
          setTimeout(() => {
            // Use the captured task ID and check the current tasks state
            const refreshedTask = tasks.find(t => String(t.id) === String(updatedTaskId));
            if (refreshedTask) {
              const refreshedStatus = refreshedTask.status || '';
              const refreshedStatusNormalized = normalizeStatusForComparison(refreshedStatus);
              const refreshedStatusId = findMatchingStatusId(refreshedStatus);
              
              console.log(`[handleDragEnd] After refresh - Task status check:`, {
                taskId: updatedTaskId,
                refreshedStatus,
                refreshedStatusNormalized,
                refreshedStatusId,
                expectedStatusNormalized,
                targetColumnId,
                matches: refreshedStatusNormalized === expectedStatusNormalized && refreshedStatusId === targetColumnId,
              });
              
              // If the refreshed task status doesn't match what we expected, show a warning
              if (refreshedStatusNormalized !== expectedStatusNormalized || refreshedStatusId !== targetColumnId) {
                console.warn(`[handleDragEnd] Task status after refresh doesn't match expected. Expected: ${newStatus} (${targetColumnId}), Got: ${refreshedStatus} (${refreshedStatusId})`);
                toast.error('Status update may not have been applied', {
                  description: `The task status was updated to "${displayActual}", but after refreshing, the status appears to be "${displayStatus(refreshedStatus)}". Please check the task status in OpenProject.`,
                  duration: 6000,
                });
              } else {
                console.log(`[handleDragEnd] Task status verified after refresh - status is correct: ${refreshedStatus}`);
              }
            } else {
              console.warn(`[handleDragEnd] Task ${updatedTaskId} not found in refreshed task list`);
            }
          }, 1500); // Wait 1.5 seconds for refresh to complete
          
          // Status changed successfully to what we wanted
          toast.success('Task status updated', {
            description: `Task status changed from "${displayOriginal}" to "${displayActual}"`,
            duration: 3000,
          });
        } else {
          // Status changed but to something different than expected
          console.warn(`[handleDragEnd] Status changed to unexpected value. Expected: ${newStatus} (${expectedStatusNormalized}, column: ${targetColumnId}), Got: ${actualStatus} (${actualStatusNormalized}, column: ${actualStatusId}), Original: ${originalStatus} (${originalStatusNormalized})`);
          toast.error('Status update partially successful', {
            description: `Task status changed from "${displayOriginal}" to "${displayActual}" (expected "${displayExpected}"). The system may have applied a different status due to workflow rules.`,
            duration: 5000,
          });
        }
        
        // Note: handleUpdateTask already refreshes the task list, so we don't need to do it again here
      } catch (err) {
        // Catch and handle the error - show toast notification instead of console error
        console.error('[handleDragEnd] Error updating task:', err);
        const errorMessage = err instanceof Error ? err.message : String(err);
        let userFriendlyMessage = 'Failed to update task status';
        let description = errorMessage;
        
        // Make OpenProject permission errors more user-friendly
        if (errorMessage.includes('no valid transition exists')) {
          userFriendlyMessage = 'Status transition not allowed';
          description = 'You do not have permission to change the task status from the current status to the target status. Please contact your administrator or try a different status.';
        } else if (errorMessage.includes('Status is invalid')) {
          userFriendlyMessage = 'Status change not allowed';
          description = 'This status change is not allowed. The status transition may be restricted by your role permissions.';
        } else if (errorMessage.includes('OpenProject validation error')) {
          // Extract the actual error message after the prefix
          const match = errorMessage.match(/OpenProject validation error \(\d+\): (.+)/);
          if (match) {
            description = match[1];
            if (description.includes('no valid transition exists')) {
              userFriendlyMessage = 'Status transition not allowed';
              description = 'You do not have permission to change the task status from the current status to the target status. Please contact your administrator or try a different status.';
            }
          }
        }
        
        // Show toast notification instead of console error
        console.log('[handleDragEnd] Showing error toast:', userFriendlyMessage, description);
        toast.error(userFriendlyMessage, {
          description: description,
          duration: 6000,
        });
      }
  };

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
    setIsModalOpen(true);
  };

  const handleUpdateTask = async (taskId: string, updates: Partial<Task>): Promise<Task> => {
    if (!activeProjectId) {
      const error = new Error("Project ID is required to update a task");
      // Return a rejected promise instead of throwing to prevent Next.js from logging it
      return Promise.reject(error);
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
        // Try to extract detailed error message from various possible formats
        errorMessage = errorData.detail || 
                      errorData.message || 
                      errorData.error || 
                      (errorData.errors && Array.isArray(errorData.errors) && errorData.errors[0]?.message) ||
                      errorMessage;
      } catch {
        if (errorText) {
          errorMessage = errorText;
        }
      }
      // Return a rejected promise instead of throwing to prevent Next.js from logging it
      return Promise.reject(new Error(errorMessage));
    }
    
    const result = await response.json();
    console.log(`[handleUpdateTask] Success:`, result);
    console.log(`[handleUpdateTask] Task status in response:`, result.status);
    console.log(`[handleUpdateTask] Expected status:`, updates.status);
    
    // Check if the status actually changed
    if (updates.status && result.status) {
      const expectedStatus = String(updates.status);
      const actualStatus = String(result.status);
      if (expectedStatus !== actualStatus && !actualStatus.toLowerCase().includes(expectedStatus.toLowerCase())) {
        console.warn(`[handleUpdateTask] Status mismatch! Expected: ${expectedStatus}, Got: ${actualStatus}`);
      }
    }
    
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
    
    // Return the updated task
    return result as Task;
  };

  // Helper function to get tasks for a status column (used by both handleDragOver and columns)
  const getTasksForColumn = useCallback((statusId: string) => {
    if (!availableStatuses) {
      return [];
    }
    
    // Find the status by ID
    const status = availableStatuses.find(s => s.id === statusId);
    if (!status) {
      return [];
    }
    
    // Get base tasks for this status
    const baseTasks = filteredTasks.filter(task => {
      const taskStatus = task.status || "";
      const taskStatusLower = taskStatus.toLowerCase().trim();
      const statusNameLower = status.name.toLowerCase().trim();
      
      // Check if there's a status column named "none" in available statuses
      const hasNoneStatus = availableStatuses.some(s => 
        s.name.toLowerCase().trim() === "none"
      );
      
      // Handle tasks with no status (null, undefined, empty string)
      // Only treat "none" as "no status" if there's no "none" status column
      const hasNoStatus = !task.status || taskStatusLower === "" || 
        (taskStatusLower === "none" && !hasNoneStatus) ||
        (taskStatusLower === "new" && !hasNoneStatus);
      
      // If task has no status, assign to default status column
      if (hasNoStatus) {
        return status.is_default;
      }
      
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
        statusNameLower.includes(taskStatusLower);
      
      // Debug logging for specific task (task ID 1)
      if (task.id === "1" || task.id === 1) {
        console.log(`[getTasksForColumn] Task 1 matching for column "${status.name}" (ID: ${status.id}):`, {
          taskStatus,
          taskStatusLower,
          statusNameLower,
          hasNoStatus,
          matches,
          normalizedTaskStatus,
          normalizedStatusName,
        });
      }
      
      return matches;
    });
    
    // If we have reordered tasks for this column, use them (but filter out the active dragging task)
    const reordered = reorderedTasks[statusId];
    if (reordered) {
      // Filter out active task if it's being dragged (it will be shown in DragOverlay)
      if (activeId) {
        // Convert to string for comparison (OpenProject uses numeric IDs, JIRA uses string IDs)
        return reordered.filter(t => String(t.id) !== String(activeId));
      }
      return reordered;
    }
    
    // Return base tasks (also filter out active task if dragging)
    if (activeId) {
      // Convert to string for comparison (OpenProject uses numeric IDs, JIRA uses string IDs)
      return baseTasks.filter(t => String(t.id) !== String(activeId));
    }
    return baseTasks;
  }, [availableStatuses, filteredTasks, reorderedTasks, activeId]);

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
    
    const columns = sortedStatuses.map(status => {
      // Map "New" status name to "No status" for display
      const displayName = status.name.toLowerCase().trim() === "new" 
        ? "No status" 
        : status.name;
      
      return {
        id: status.id,
        title: displayName,
        tasks: getTasksForColumn(status.id) || [],
      };
    });
    
    // Debug: Log total tasks distributed across columns
    const totalTasksInColumns = columns.reduce((sum, col) => sum + (col.tasks?.length || 0), 0);
    if (DEBUG_DND) console.log(`[SprintBoard] Total tasks in columns: ${totalTasksInColumns}, Total filtered tasks: ${filteredTasks.length}, Available statuses:`, availableStatuses.map(s => s.name));
    
    // Debug: Find unmatched tasks
    const matchedTaskIds = new Set(columns.flatMap(col => (col.tasks || []).map(t => t.id)));
    const unmatchedTasks = filteredTasks.filter(t => !matchedTaskIds.has(t.id));
    if (DEBUG_DND && unmatchedTasks.length > 0) {
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

  const getVisibilityStorageKey = (projectId: string | null) => {
    if (!projectId) return null;
    return `sprint-board-column-visibility-${projectId}`;
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

  // Load column order and visibility from localStorage when project or statuses change
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

        // Load column visibility from localStorage
        const key = getVisibilityStorageKey(activeProjectId);
        if (key) {
          try {
            const saved = localStorage.getItem(key);
            if (saved) {
              const visibility = JSON.parse(saved);
              if (Array.isArray(visibility) && visibility.every((id): id is string => typeof id === 'string')) {
                const validStatusIds = new Set(availableStatuses.map(s => s.id));
                const validVisibility = new Set(
                  visibility.filter(id => validStatusIds.has(id))
                );
                if (validVisibility.size > 0) {
                  setVisibleColumns(validVisibility);
                } else {
                  setVisibleColumns(new Set(availableStatuses.map(s => s.id)));
                }
              }
            } else {
              setVisibleColumns(new Set(availableStatuses.map(s => s.id)));
            }
          } catch (error) {
            console.error('[SprintBoard] Failed to load column visibility from localStorage:', error);
            setVisibleColumns(new Set(availableStatuses.map(s => s.id)));
          }
        }
      }
    } else if (!activeProjectId && lastLoadedProjectId) {
      // Clear column order and visibility when no project is selected
      setColumnOrder([]);
      setVisibleColumns(new Set());
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

  // Convert Set to sorted array for stable comparison in useEffect
  const visibleColumnsArray = useMemo(() => {
    return Array.from(visibleColumns).sort();
  }, [visibleColumns]);

  // Save column visibility to localStorage whenever it changes (but not during initial load)
  useEffect(() => {
    if (isLoadingFromStorage) {
      return;
    }
    if (visibleColumns.size === 0) {
      return;
    }
    if (activeProjectId && availableStatuses) {
      const key = getVisibilityStorageKey(activeProjectId);
      if (key) {
        try {
          localStorage.setItem(key, JSON.stringify(Array.from(visibleColumns)));
        } catch (error) {
          console.error('[SprintBoard] Failed to save column visibility to localStorage:', error);
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleColumnsArray, activeProjectId, availableStatuses, isLoadingFromStorage]);

  // Apply column order and visibility to columns
  const orderedColumns = useMemo(() => {
    // First filter by visibility
    let visibleCols = columns;
    if (visibleColumns.size > 0) {
      visibleCols = columns.filter(col => visibleColumns.has(col.id));
    }
    
    // Then apply order
    if (columnOrder.length === 0) {
      return visibleCols;
    }
    
    // Create a map for quick lookup
    const columnMap = new Map(visibleCols.map(col => [col.id, col]));
    
    // Return columns in the order specified by columnOrder
    const ordered = columnOrder
      .map(id => columnMap.get(id))
      .filter((col): col is typeof columns[0] => col !== undefined);
    
    // Add any visible columns that weren't in the order (new statuses)
    const orderedIds = new Set(columnOrder);
    const newColumns = visibleCols.filter(col => !orderedIds.has(col.id));
    
    return [...ordered, ...newColumns];
  }, [columns, columnOrder, visibleColumns]);

  // Use tasks instead of filteredTasks to ensure we can always find the dragged task
  const activeTask = activeId ? tasks.find(t => String(t.id) === String(activeId)) : null;

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
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Sprint Board</h2>
          {availableStatuses && availableStatuses.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsColumnManagerOpen(true)}
              className="gap-2"
            >
              <Settings2 className="w-4 h-4" />
              Columns
            </Button>
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
            {sprints && sprints.length > 0 && (
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

      {/* Column Management Dialog */}
      <Dialog open={isColumnManagerOpen} onOpenChange={setIsColumnManagerOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Manage Columns</DialogTitle>
            <DialogDescription>
              Select which columns to display on the board. At least one column must be visible.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4 max-h-[60vh] overflow-y-auto">
            {availableStatuses && availableStatuses.length > 0 ? (
              availableStatuses
                .sort((a, b) => {
                  if (a.is_default && !b.is_default) return -1;
                  if (!a.is_default && b.is_default) return 1;
                  return a.name.localeCompare(b.name);
                })
                .map((status) => {
                  const isVisible = visibleColumns.size === 0 || visibleColumns.has(status.id);
                  const visibleCount = visibleColumns.size === 0 
                    ? (availableStatuses?.length || 0)
                    : visibleColumns.size;
                  const isLastVisible = visibleCount === 1 && isVisible;
                  
                  return (
                    <div
                      key={status.id}
                      className="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
                    >
                      <Checkbox
                        id={`column-${status.id}`}
                        checked={isVisible}
                        disabled={isLastVisible}
                        onCheckedChange={(checked) => {
                          if (!availableStatuses) return;
                          const currentVisible = visibleColumns.size === 0
                            ? new Set(availableStatuses.map(s => s.id))
                            : new Set(visibleColumns);
                          
                          if (checked) {
                            currentVisible.add(status.id);
                            setVisibleColumns(currentVisible);
                          } else {
                            if (currentVisible.size > 1) {
                              currentVisible.delete(status.id);
                              setVisibleColumns(currentVisible);
                            }
                          }
                        }}
                      />
                      <Label
                        htmlFor={`column-${status.id}`}
                        className={`flex-1 cursor-pointer ${isLastVisible ? 'opacity-50' : ''}`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-medium">
                            {status.name.toLowerCase().trim() === "new" ? "No status" : status.name}
                          </span>
                          {status.is_default && (
                            <span className="text-xs text-gray-500 dark:text-gray-400">(default)</span>
                          )}
                        </div>
                      </Label>
                    </div>
                  );
                })
            ) : (
              <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                No statuses available
              </div>
            )}
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button
              variant="outline"
              onClick={() => {
                if (availableStatuses) {
                  setVisibleColumns(new Set(availableStatuses.map(s => s.id)));
                }
              }}
            >
              Show All
            </Button>
            <Button
              variant="outline"
              onClick={() => setIsColumnManagerOpen(false)}
            >
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
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
                    tasks={column.tasks || []} 
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
