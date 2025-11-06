// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { DndContext, DragOverlay, PointerSensor, useSensor, useSensors, closestCorners, useDroppable } from "@dnd-kit/core";
import type { DragEndEvent, DragStartEvent, DragOverEvent } from "@dnd-kit/core";
import { useSortable } from "@dnd-kit/sortable";
import { SortableContext, verticalListSortingStrategy, horizontalListSortingStrategy, arrayMove } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Search, Filter, GripVertical, GripHorizontal, Settings2 } from "lucide-react";
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
import { usePMLoading } from "../../../context/pm-loading-context";
import { useProjectData } from "../../../hooks/use-project-data";
import { debug } from "../../../utils/debug";

import { TaskDetailsModal } from "../task-details-modal";

function TaskCard({ task, onClick, isColumnDragging }: { task: any; onClick: () => void; isColumnDragging?: boolean }) {
  // Ensure task.id is always a string for dnd-kit (OpenProject uses numeric IDs, JIRA uses string IDs)
  const taskId = String(task.id);
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: taskId,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    // Disable transitions when a column is being dragged to prevent task animations
    // When dragging a task, only animate opacity. When not dragging, animate position changes
    transition: isColumnDragging 
      ? 'none'  // No transition when columns are being dragged
      : (isDragging 
        ? 'opacity 0.2s ease-out' 
        : (transition || 'transform 300ms cubic-bezier(0.2, 0, 0, 1), opacity 300ms ease')),
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

function SortableColumn({ column, tasks, onTaskClick, activeColumnId, activeId, isDraggingColumn, isAnyColumnDragging, onColumnDragStateChange }: { 
  column: { id: string; title: string }; 
  tasks: any[]; 
  onTaskClick: (task: any) => void;
  activeColumnId?: string | null;
  activeId?: string | null;
  isDraggingColumn?: boolean;
  isAnyColumnDragging?: boolean;
  onColumnDragStateChange?: (columnId: string, isDragging: boolean) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: column.id,
    data: {
      type: 'column',
    },
  });
  
  // Notify parent when column drag state changes
  useEffect(() => {
    if (onColumnDragStateChange) {
      onColumnDragStateChange(column.id, isDragging);
    }
  }, [isDragging, column.id, onColumnDragStateChange]);

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
  
  // Debug logging for column drag state
  useEffect(() => {
    if (isDragging) {
      debug.dnd('SortableColumn: Column is being dragged', {
        columnId: column.id,
        columnTitle: column.title,
        isDraggingColumn,
        transform: CSS.Transform.toString(transform),
        transition
      });
    }
  }, [isDragging, column.id, column.title, isDraggingColumn, transform, transition]);
  
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
  
  // Only show active state for task dragging, not column dragging
  // When dragging a column, we only highlight if this is the target column (activeColumnId)
  // When dragging a task, we show highlight based on droppable zones
  const isActive = isDraggingColumn 
    ? activeColumnId === column.id  // For column dragging, only highlight target column
    : (isOver || isOverTop || isOverBottom || activeColumnId === column.id);  // For task dragging, use droppable zones

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
      className="flex flex-col h-full"
    >
      {/* Top drop zone - only show when dragging a task (not a column) */}
      {activeId && !isDraggingColumn && (
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
        className={`flex-1 rounded-b-lg p-3 min-h-0 border-2 overflow-y-auto transition-all duration-200 ${
          isActive && !isDraggingColumn
            ? 'bg-blue-50 dark:bg-blue-950 border-blue-500 dark:border-blue-500' 
            : 'bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800'
        }`}
        style={{
          overscrollBehavior: 'contain',
        }}
      >
        {displayTasks.length === 0 ? (
          <div className={`text-sm text-gray-500 dark:text-gray-400 text-center py-8 font-medium ${isActive && !isDraggingColumn ? 'text-blue-700 dark:text-blue-300' : ''}`}>
            {isActive && !isDraggingColumn ? 'Drop here' : 'No tasks'}
          </div>
        ) : (
          <>
            {/* Drop indicator at the top when dragging over (only for tasks, not columns) */}
            {isActive && activeId && !isDraggingColumn && (
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
                    <TaskCard key={taskIdStr} task={task} onClick={() => onTaskClick(task)} isColumnDragging={isAnyColumnDragging} />
                  );
                })}
              </div>
            </SortableContext>
            {/* Drop indicator at the bottom when dragging over (only for tasks, not columns) */}
            {isActive && activeId && !isDraggingColumn && (
              <div 
                className="h-2 bg-blue-500 dark:bg-blue-400 rounded-full mt-2 transition-opacity"
                style={{ pointerEvents: 'none' }}
              />
            )}
          </>
        )}
      </div>
      
      {/* Bottom drop zone - only show when dragging a task (not a column) */}
      {activeId && !isDraggingColumn && (
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
  // Log component render
  useEffect(() => {
    debug.render('SprintBoard component rendered');
  });
  
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
  
  // Ref for horizontal scrolling container (columns container)
  const columnsContainerRef = useRef<HTMLDivElement | null>(null);
  const horizontalScrollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  // Track which columns are currently being dragged (by their sortable isDragging state)
  // This helps us detect column drags even when the drag starts from a task inside the column
  const [draggingColumnIds, setDraggingColumnIds] = useState<Set<string>>(new Set());
  
  // Use the new useProjectData hook for cleaner project handling
  const { activeProjectId, projectIdForData: projectIdForTasks } = useProjectData();
  
  // Get loading state from context
  const { state: loadingState, setTasksState } = usePMLoading();
  
  // Only load tasks when filter data is ready (Step 3: after all requirements loaded)
  // IMPORTANT: Always pass projectIdForTasks to useTasks to prevent projectId from flipping
  // between valid and undefined, which causes race conditions
  const shouldLoadTasks = loadingState.canLoadTasks && activeProjectId;
  
  // Always use useTasks with projectIdForTasks (or undefined if no project)
  // This prevents the hook from switching between useTasks and useMyTasks, which causes
  // the effect to restart and mark previous fetches as stale
  const { tasks, loading, error, refresh: refreshTasks } = useTasks(projectIdForTasks ?? undefined);
  
  // Sync tasks state with loading context
  useEffect(() => {
    if (shouldLoadTasks) {
      setTasksState({
        loading,
        error,
        data: tasks,
      });
    } else {
      setTasksState({
        loading: false,
        error: null,
        data: null,
      });
    }
  }, [shouldLoadTasks, loading, error, tasks, setTasksState]);
  
  // Fetch priorities, epics, statuses, and sprints from backend for the active project
  const { priorities: availablePrioritiesFromBackend } = usePriorities(activeProjectId ?? undefined);
  const { epics } = useEpics(activeProjectId ?? undefined);
  const { statuses: availableStatuses, loading: statusesLoading, error: statusesError, refresh: refreshStatuses } = useStatuses(activeProjectId ?? undefined, "task");
  
  // Force refresh statuses when project changes to ensure they're loaded
  useEffect(() => {
    if (activeProjectId && !statusesLoading && availableStatuses.length === 0 && !statusesError) {
      // Project changed but statuses are empty and not loading, force a refresh
      debug.project('Project changed but statuses are empty, forcing refresh', { activeProjectId });
      const timeoutId = setTimeout(() => {
        refreshStatuses();
      }, 100);
      return () => clearTimeout(timeoutId);
    }
  }, [activeProjectId, statusesLoading, availableStatuses.length, statusesError, refreshStatuses]);
  const { sprints } = useSprints(activeProjectId || "");
  
  // Reset filters when project changes (but don't reset columnOrder - let it load from localStorage)
  useEffect(() => {
    setSearchQuery("");
    setPriorityFilter("all");
    setEpicFilter(null);
    setSprintFilter(null);
    // Clear visibleColumns immediately when project changes to prevent filtering out new columns
    // It will be repopulated from localStorage or set to all columns in the effect below
    setVisibleColumns(new Set());
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
    debug.filter('Filtering tasks', { tasksLength: tasks.length, loading });
    
    // Return empty array only if we're loading AND have no tasks yet (to prevent flash of stale data)
    // If we have tasks, always filter them even if loading is true (for real-time filtering)
    if (loading && (!tasks || tasks.length === 0)) {
      debug.filter('Returning empty (loading with no tasks)');
      return [];
    }
    
    // If we have no tasks at all, return empty
    if (!tasks || tasks.length === 0) {
      debug.filter('Returning empty (no tasks)');
      return [];
    }
    
    let filtered = [...tasks]; // Create a copy to avoid mutating original
    const initialCount = filtered.length;

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
      debug.filter(`After search filter (query: "${trimmedQuery}")`, { 
        filteredCount: filtered.length, 
        wasCount: initialCount 
      });
    }

    // Priority filter - match by exact priority (case-insensitive)
    if (priorityFilter && priorityFilter !== "all") {
      const filterPriorityLower = priorityFilter.toLowerCase();
      const beforeCount = filtered.length;
      filtered = filtered.filter(t => {
        const taskPriority = (t.priority || "").toLowerCase();
        return taskPriority === filterPriorityLower;
      });
      debug.filter(`After priority filter (${priorityFilter})`, { 
        filteredCount: filtered.length, 
        wasCount: beforeCount 
      });
    }

    // Epic filter
    if (epicFilter && epicFilter !== "all") {
      const beforeCount = filtered.length;
      filtered = filtered.filter(task => {
        if (epicFilter === "none") {
          return !task.epic_id;
        }
        return task.epic_id === epicFilter;
      });
      debug.filter(`After epic filter (${epicFilter})`, { 
        filteredCount: filtered.length, 
        wasCount: beforeCount 
      });
    }

    // Sprint filter
    if (sprintFilter && sprintFilter !== "all") {
      const beforeCount = filtered.length;
      filtered = filtered.filter(task => {
        if (sprintFilter === "none") {
          return !task.sprint_id;
        }
        return task.sprint_id === sprintFilter;
      });
      debug.filter(`After sprint filter (${sprintFilter})`, { 
        filteredCount: filtered.length, 
        wasCount: beforeCount 
      });
    }

    debug.filter('Final filtered tasks', { 
      filteredCount: filtered.length, 
      originalCount: initialCount,
      taskIds: filtered.length > 0 ? filtered.slice(0, 5).map(t => t.id) : []
    });
    
    return filtered;
  }, [tasks, searchQuery, priorityFilter, epicFilter, sprintFilter, loading]);

  // Auto-scroll horizontally when dragging columns near viewport edges
  // Only scroll when mouse is very close to edge and actively dragging
  useEffect(() => {
    if (!draggedColumnId || !columnsContainerRef.current) {
      // Clear any existing scroll interval when not dragging a column
      if (horizontalScrollIntervalRef.current) {
        debug.dnd('Clearing horizontal scroll interval (no drag)', { draggedColumnId, hasContainer: !!columnsContainerRef.current });
        clearInterval(horizontalScrollIntervalRef.current);
        horizontalScrollIntervalRef.current = null;
      }
      return;
    }
    
    const container = columnsContainerRef.current;
    let isDragging = true;
    
    debug.dnd('Setting up horizontal scroll for column drag', { 
      draggedColumnId, 
      containerScrollLeft: container.scrollLeft,
      containerScrollWidth: container.scrollWidth,
      containerClientWidth: container.clientWidth,
      canScrollLeft: container.scrollLeft > 0,
      canScrollRight: container.scrollLeft < container.scrollWidth - container.clientWidth
    });
    
    const handleMouseMove = (e: MouseEvent) => {
      if (!container || !isDragging) return;
      
      const viewportWidth = window.innerWidth;
      const mouseX = e.clientX;
      const scrollThreshold = 50; // Reduced threshold - only scroll when very close to edge
      const scrollSpeed = 10; // Reduced speed to be less aggressive
      
      // Check if mouse is near left or right edge of viewport
      const distanceFromLeft = mouseX;
      const distanceFromRight = viewportWidth - mouseX;
      const nearLeftEdge = distanceFromLeft < scrollThreshold;
      const nearRightEdge = distanceFromRight < scrollThreshold;
      const canScrollLeft = container.scrollLeft > 0;
      const canScrollRight = container.scrollLeft < container.scrollWidth - container.clientWidth;
      
      // Clear existing interval before starting a new one
      if (horizontalScrollIntervalRef.current) {
        clearInterval(horizontalScrollIntervalRef.current);
        horizontalScrollIntervalRef.current = null;
      }
      
      // Only scroll if we're very close to the edge and there's room to scroll
      if (nearLeftEdge && canScrollLeft) {
        debug.dnd('Starting horizontal scroll left', { 
          mouseX, 
          distanceFromLeft, 
          scrollLeft: container.scrollLeft,
          scrollSpeed 
        });
        // Scroll left
        horizontalScrollIntervalRef.current = setInterval(() => {
          if (container && container.scrollLeft > 0 && isDragging) {
            const newScrollLeft = Math.max(0, container.scrollLeft - scrollSpeed);
            container.scrollLeft = newScrollLeft;
            debug.dnd('Scrolling left', { oldScrollLeft: container.scrollLeft + scrollSpeed, newScrollLeft });
            // Stop if we've reached the beginning
            if (newScrollLeft === 0 && horizontalScrollIntervalRef.current) {
              debug.dnd('Reached left edge, stopping scroll');
              clearInterval(horizontalScrollIntervalRef.current);
              horizontalScrollIntervalRef.current = null;
            }
          } else if (horizontalScrollIntervalRef.current) {
            clearInterval(horizontalScrollIntervalRef.current);
            horizontalScrollIntervalRef.current = null;
          }
        }, 16); // ~60fps
      } else if (nearRightEdge && canScrollRight) {
        debug.dnd('Starting horizontal scroll right', { 
          mouseX, 
          distanceFromRight, 
          scrollLeft: container.scrollLeft,
          maxScroll: container.scrollWidth - container.clientWidth,
          scrollSpeed 
        });
        // Scroll right
        horizontalScrollIntervalRef.current = setInterval(() => {
          if (container && isDragging) {
            const maxScroll = container.scrollWidth - container.clientWidth;
            if (container.scrollLeft < maxScroll) {
              const newScrollLeft = Math.min(maxScroll, container.scrollLeft + scrollSpeed);
              container.scrollLeft = newScrollLeft;
              debug.dnd('Scrolling right', { oldScrollLeft: container.scrollLeft - scrollSpeed, newScrollLeft, maxScroll });
              // Stop if we've reached the end
              if (newScrollLeft >= maxScroll && horizontalScrollIntervalRef.current) {
                debug.dnd('Reached right edge, stopping scroll');
                clearInterval(horizontalScrollIntervalRef.current);
                horizontalScrollIntervalRef.current = null;
              }
            } else if (horizontalScrollIntervalRef.current) {
              clearInterval(horizontalScrollIntervalRef.current);
              horizontalScrollIntervalRef.current = null;
            }
          } else if (horizontalScrollIntervalRef.current) {
            clearInterval(horizontalScrollIntervalRef.current);
            horizontalScrollIntervalRef.current = null;
          }
        }, 16); // ~60fps
      }
    };
    
    const handleMouseUp = () => {
      debug.dnd('Mouse up detected, stopping horizontal scroll', { draggedColumnId });
      isDragging = false;
      if (horizontalScrollIntervalRef.current) {
        clearInterval(horizontalScrollIntervalRef.current);
        horizontalScrollIntervalRef.current = null;
      }
    };
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    
    return () => {
      debug.dnd('Cleaning up horizontal scroll listeners', { draggedColumnId });
      isDragging = false;
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      if (horizontalScrollIntervalRef.current) {
        clearInterval(horizontalScrollIntervalRef.current);
        horizontalScrollIntervalRef.current = null;
      }
    };
  }, [draggedColumnId]);

  const handleDragStart = (event: DragStartEvent) => {
    const activeIdStr = String(event.active.id);
    const activeData = event.active.data.current;
    
    // Check if this is the last column
    const isLastColumn = orderedColumns.length > 0 && orderedColumns[orderedColumns.length - 1]?.id === activeIdStr;
    
    debug.dnd('Drag started', { 
      activeId: activeIdStr, 
      dataType: activeData?.type, 
      activeData,
      isLastColumn,
      draggingColumnIds: Array.from(draggingColumnIds),
      totalColumns: orderedColumns.length,
      columnOrder: columnOrder,
      orderedColumns: orderedColumns.map(c => ({ id: c.id, title: c.title }))
    });
    
    // CRITICAL: Use a small delay to check if a column is being dragged
    // This handles the race condition where handleDragStart runs before column's isDragging becomes true
    // We'll check draggingColumnIds after a brief delay
    setTimeout(() => {
      if (draggingColumnIds.size > 0 && !draggedColumnId) {
        // Check if activeId matches any column being dragged
        const matchingColumnId = Array.from(draggingColumnIds).find(colId => {
          return colId === activeIdStr || availableStatuses?.some(s => String(s.id) === colId);
        });
        
        if (matchingColumnId) {
          debug.warn('CRITICAL: Detected column drag after delay (missed in initial handleDragStart)', {
            activeId: activeIdStr,
            matchingColumnId,
            draggingColumnIds: Array.from(draggingColumnIds)
          });
          // Set the dragged column ID and clear task drag state
          setDraggedColumnId(matchingColumnId);
          setActiveId(null);
          setReorderedTasks({});
        }
      }
    }, 50); // Small delay to allow column's isDragging to update
    
    // CRITICAL: Check for column drags FIRST, before checking for tasks
    // This prevents column drags from being misidentified as task drags
    // Priority order: 1) data.type === 'column', 2) activeId matches column ID, 3) task ID
    
    // Method 1: Check the data type - this is the most reliable indicator
    // Columns have data.type === 'column', tasks don't have a type set
    if (activeData?.type === 'column') {
      // It's definitely a column being dragged
      debug.dnd('Detected column drag (by data.type)', { 
        activeId: activeIdStr, 
        availableStatuses: availableStatuses?.map(s => s.id),
        isLastColumn,
        columnOrder,
        orderedColumns: orderedColumns.map(c => c.id)
      });
      if (availableStatuses && availableStatuses.some(s => String(s.id) === activeIdStr)) {
        debug.dnd('Setting draggedColumnId', { activeId: activeIdStr, isLastColumn });
        setDraggedColumnId(activeIdStr);
        setActiveId(null); // Clear any task drag state
        debug.dnd('Column drag state set', { draggedColumnId: activeIdStr });
        return;
      } else {
        debug.warn('Column ID not found in availableStatuses', { 
          activeId: activeIdStr,
          availableStatuses: availableStatuses?.map(s => s.id)
        });
      }
    }
    
    // Method 2: Check if activeId matches a column ID (status ID) BEFORE checking for tasks
    // This is important because if a task ID happens to match a column ID, we want to prioritize column
    if (availableStatuses && availableStatuses.some(s => String(s.id) === activeIdStr)) {
      // Check if it's also a task ID
      const isTaskId = tasks.some(t => String(t.id) === activeIdStr);
      // CRITICAL: Also check if this column is actually being dragged (from draggingColumnIds)
      // This handles the case where drag starts from a task inside the column
      const isColumnBeingDragged = draggingColumnIds.has(activeIdStr);
      
      debug.dnd('Checking if activeId is a column ID', { 
        activeId: activeIdStr, 
        isTaskId, 
        isLastColumn,
        isColumnBeingDragged,
        draggingColumnIds: Array.from(draggingColumnIds),
        availableStatuses: availableStatuses.map(s => s.id),
        taskIds: tasks.slice(0, 5).map(t => String(t.id))
      });
      
      // If it's a column ID AND the column is being dragged, prioritize column drag
      // This prevents column drags from being misidentified when dragging from column header
      // or when drag starts from a task inside the column
      if (isColumnBeingDragged || !isTaskId || activeData?.type === 'column') {
        // It's a column ID and either:
        // 1. The column is actively being dragged (isColumnBeingDragged)
        // 2. It's not also a task ID (!isTaskId)
        // 3. It's explicitly marked as column type (activeData?.type === 'column')
        debug.dnd('Detected column drag (by ID, priority check)', { 
          activeId: activeIdStr, 
          isLastColumn,
          isTaskId,
          isColumnBeingDragged,
          columnOrder,
          orderedColumns: orderedColumns.map(c => c.id)
        });
        setDraggedColumnId(activeIdStr);
        setActiveId(null);
        debug.dnd('Column drag state set (priority check)', { draggedColumnId: activeIdStr });
        return;
      }
    }
    
    // Method 3: Check if it's a task ID (only if it's NOT a column being dragged)
    const task = tasks.find(t => String(t.id) === activeIdStr);
    if (task) {
      // Double-check: Make sure this is NOT a column ID that's being dragged
      const isColumnId = availableStatuses?.some(s => String(s.id) === activeIdStr);
      const isColumnBeingDragged = isColumnId && draggingColumnIds.has(activeIdStr);
      
      if (isColumnId && !isColumnBeingDragged && activeData?.type !== 'column') {
        // This is ambiguous - it's both a task and column ID, but:
        // - data.type is not 'column'
        // - The column is not actively being dragged
        // In this case, treat as task
        debug.dnd('Ambiguous ID (both task and column), treating as task (no column type in data and column not being dragged)', { 
          activeId: activeIdStr,
          dataType: activeData?.type,
          isColumnBeingDragged,
          draggingColumnIds: Array.from(draggingColumnIds)
        });
      } else if (isColumnBeingDragged) {
        // The column is being dragged, so this is a column drag, not a task drag
        debug.dnd('Column is being dragged, treating as column drag (not task)', { 
          activeId: activeIdStr,
          isColumnBeingDragged
        });
        setDraggedColumnId(activeIdStr);
        setActiveId(null);
        return;
      }
      
      // It's a task being dragged (and not a column being dragged)
      debug.dnd('Detected task drag', { activeId: activeIdStr, isColumnId, isColumnBeingDragged });
      setActiveId(activeIdStr);
      setDraggedColumnId(null); // Clear any column drag state
      
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
    }
    
    // If we get here, we couldn't determine what's being dragged
    debug.warn('Could not determine drag type', { 
      activeIdStr, 
      activeData,
      isLastColumn,
      availableStatuses: availableStatuses?.map(s => s.id),
      taskIds: tasks.slice(0, 5).map(t => String(t.id))
    });
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    
    // CRITICAL FIX: If we haven't detected a column drag yet, but a column is being dragged,
    // update the state now. This handles the case where drag starts from a task inside the column.
    const activeIdStr = String(active.id);
    if (!draggedColumnId && draggingColumnIds.size > 0) {
      // Check if the activeId matches any of the columns being dragged
      const matchingColumnId = Array.from(draggingColumnIds).find(colId => {
        // Check if activeId matches the column ID, or if we're dragging over a column
        return colId === activeIdStr || (over && String(over.id) === colId);
      });
      
      if (matchingColumnId) {
        debug.warn('CRITICAL: Detected column drag in handleDragOver (missed in handleDragStart)', {
          activeId: activeIdStr,
          matchingColumnId,
          draggingColumnIds: Array.from(draggingColumnIds),
          activeData: active.data.current
        });
        // Set the dragged column ID and clear task drag state
        setDraggedColumnId(matchingColumnId);
        setActiveId(null);
        setReorderedTasks({});
      }
    }
    
    // Check if this is the last column being dragged
    const isLastColumn = draggedColumnId && orderedColumns.length > 0 && orderedColumns[orderedColumns.length - 1]?.id === draggedColumnId;
    const overColumnIndex = over ? orderedColumns.findIndex(c => c.id === over.id) : -1;
    const isOverLastColumn = overColumnIndex === orderedColumns.length - 1;
    
    debug.dnd('Drag over', { 
      activeId: active.id, 
      overId: over?.id, 
      draggedColumnId,
      draggingColumnIds: Array.from(draggingColumnIds),
      isLastColumn,
      isOverLastColumn,
      overColumnIndex,
      totalColumns: orderedColumns.length,
      overDataType: over?.data?.current?.type,
      overData: over?.data?.current
    });
    
    // Handle column reordering
    if (draggedColumnId) {
      if (!over || !availableStatuses) {
        debug.dnd('Drag over: No over target or no availableStatuses', { over: !!over, availableStatuses: !!availableStatuses, isLastColumn });
        setActiveColumnId(null);
        return;
      }
      
      const activeId = draggedColumnId;
      let overId: string | null = null;
      
      // Check if we're over a column (status ID) directly
      if (typeof over.id === 'string' && availableStatuses.some(s => s.id === over.id)) {
        overId = over.id;
        debug.dnd('Drag over: Found overId from over.id', { overId, activeId, isLastColumn });
      } else {
        // Check if we're over something inside a column - look at the data
        const overData = over.data.current;
        debug.dnd('Drag over: Checking overData', { overData, overDataType: overData?.type, overDataColumn: overData?.column, isLastColumn });
        if (overData?.type === 'column' && overData?.column) {
          overId = overData.column;
          debug.dnd('Drag over: Found overId from overData.column', { overId, activeId, isLastColumn });
        } else {
          debug.dnd('Drag over: Could not find overId from overData', { overData, isLastColumn });
        }
      }
      
      // Visual feedback: highlight the target column if it's different from the dragged column
      if (overId && overId !== activeId && availableStatuses.some(s => s.id === overId)) {
        debug.dnd('Drag over: Setting activeColumnId for visual feedback', { 
          overId, 
          activeId, 
          isLastColumn,
          overColumnIndex,
          activeColumnIndex: columnOrder.indexOf(activeId),
          containerScrollLeft: columnsContainerRef.current?.scrollLeft,
          containerScrollWidth: columnsContainerRef.current?.scrollWidth,
          containerClientWidth: columnsContainerRef.current?.clientWidth
        });
        setActiveColumnId(overId);
      } else {
        debug.dnd('Drag over: Clearing activeColumnId', { 
          overId, 
          activeId, 
          isLastColumn, 
          overColumnIndex,
          reason: !overId ? 'no overId' : overId === activeId ? 'same column' : 'invalid overId',
          overIdValid: overId && availableStatuses.some(s => s.id === overId)
        });
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
    
    // CRITICAL: Check if a column is being dragged (via draggingColumnIds) even if draggedColumnId is not set
    // This handles the case where handleDragStart missed the column drag detection
    const activeIdStr = String(active.id);
    if (!draggedColumnId && draggingColumnIds.size > 0) {
      // Find the column that's being dragged
      const matchingColumnId = Array.from(draggingColumnIds).find(colId => {
        return colId === activeIdStr || (availableStatuses?.some(s => String(s.id) === colId));
      });
      
      if (matchingColumnId) {
        debug.warn('CRITICAL: Detected column drag in handleDragEnd (missed in handleDragStart and handleDragOver)', {
          activeId: activeIdStr,
          matchingColumnId,
          draggingColumnIds: Array.from(draggingColumnIds)
        });
        // Don't process as task - this is a column drag
        setActiveId(null);
        setActiveColumnId(null);
        setReorderedTasks({});
        setDraggingColumnIds(new Set()); // Clear dragging state
        return; // Exit early, don't process as task drag
      }
    }
    
    // Check if this is the last column being dragged
    const isLastColumn = draggedColumnId && orderedColumns.length > 0 && orderedColumns[orderedColumns.length - 1]?.id === draggedColumnId;
    const activeColumnIndex = draggedColumnId ? columnOrder.indexOf(draggedColumnId) : -1;
    
    debug.dnd('Drag ended', { 
      activeId: active.id, 
      overId: over?.id, 
      draggedColumnId,
      draggingColumnIds: Array.from(draggingColumnIds),
      isLastColumn,
      activeColumnIndex,
      totalColumns: orderedColumns.length,
      columnOrderLength: columnOrder.length,
      overDataType: over?.data?.current?.type,
      overData: over?.data?.current
    });
    
    // Clear dragging column IDs on drag end
    setDraggingColumnIds(new Set());
    
    // Handle column reordering
    if (draggedColumnId) {
      const activeColumnId = draggedColumnId;
      debug.dnd('handleDragEnd: Processing column drag end', {
        activeColumnId,
        isLastColumn,
        activeColumnIndex,
        over: over ? { id: over.id, data: over.data?.current } : null,
        columnOrder,
        orderedColumns: orderedColumns.map(c => c.id),
        containerScrollLeft: columnsContainerRef.current?.scrollLeft
      });
      
      setDraggedColumnId(null);
      setActiveColumnId(null);
      
      if (over && availableStatuses) {
        debug.dnd('handleDragEnd: Has over target and availableStatuses', {
          overId: over.id,
          overDataType: over.data?.current?.type,
          overData: over.data?.current,
          availableStatuses: availableStatuses.map(s => s.id)
        });
        let overId: string | null = null;
        
        // Check if we dropped directly on a column (status ID)
        if (typeof over.id === 'string' && availableStatuses.some(s => s.id === over.id)) {
          overId = over.id;
          debug.dnd('Drag ended: Found overId from over.id', { overId, activeColumnId, isLastColumn });
        } else {
          // Check if we dropped on something inside a column - look at the data
          const overData = over.data.current;
          debug.dnd('Drag ended: Checking overData for overId', { overData, overDataType: overData?.type, overDataColumn: overData?.column, isLastColumn });
          if (overData?.type === 'column' && overData?.column) {
            overId = overData.column;
            debug.dnd('Drag ended: Found overId from overData.column', { overId, activeColumnId, isLastColumn });
          } else {
            // Try to find the column from the over.id by checking if it's a task or other element
            // that belongs to a column
            debug.dnd('Drag ended: Could not find overId from overData, trying alternative methods', { 
              overId: over.id, 
              overDataType: overData?.type,
              availableStatuses: availableStatuses.map(s => s.id)
            });
            
            // If over.id is a string, check if it matches any status ID
            if (typeof over.id === 'string') {
              const matchingStatus = availableStatuses.find(s => s.id === over.id);
              if (matchingStatus) {
                overId = matchingStatus.id;
                debug.dnd('Drag ended: Found overId by matching over.id with status', { overId, activeColumnId });
              }
            }
          }
        }
        
        debug.dnd('Drag ended: Final overId check', { 
          overId, 
          activeColumnId, 
          overIdValid: overId && availableStatuses.some(s => s.id === overId),
          isLastColumn,
          overIdIndex: overId ? columnOrder.indexOf(overId) : -1,
          activeColumnIndex: columnOrder.indexOf(activeColumnId),
          columnOrderLength: columnOrder.length,
          orderedColumnsLength: orderedColumns.length,
          containerScrollLeft: columnsContainerRef.current?.scrollLeft,
          containerScrollWidth: columnsContainerRef.current?.scrollWidth,
          containerClientWidth: columnsContainerRef.current?.clientWidth
        });
        
        if (overId && overId !== activeColumnId && availableStatuses.some(s => s.id === overId)) {
          // Ensure columnOrder is initialized (use current ordered columns if columnOrder is empty)
          let currentOrder = columnOrder;
          debug.dnd('Drag ended: Starting column reorder logic', {
            currentOrderLength: currentOrder.length,
            activeColumnId,
            overId,
            isLastColumn
          });
          
          if (currentOrder.length === 0 && availableStatuses) {
            // Try to load from localStorage first
            debug.dnd('Column order is empty, trying to load from localStorage', { activeProjectId });
            const savedOrder = loadColumnOrderFromStorage(activeProjectId);
            if (savedOrder && savedOrder.length > 0) {
              // Validate saved order
              const validStatusIds = new Set(availableStatuses.map(s => s.id));
              const validOrder = savedOrder.filter(id => validStatusIds.has(id));
              if (validOrder.length > 0) {
                currentOrder = validOrder;
                debug.dnd('Loaded column order from localStorage', { currentOrder });
              } else {
                // Fallback to default order
                const sortedStatuses = [...availableStatuses].sort((a, b) => {
                  if (a.is_default && !b.is_default) return -1;
                  if (!a.is_default && b.is_default) return 1;
                  return a.name.localeCompare(b.name);
                });
                currentOrder = sortedStatuses.map(s => s.id);
                debug.dnd('Using default column order (saved order invalid)', { currentOrder });
              }
            } else {
              // No saved order, use default
              const sortedStatuses = [...availableStatuses].sort((a, b) => {
                if (a.is_default && !b.is_default) return -1;
                if (!a.is_default && b.is_default) return 1;
                return a.name.localeCompare(b.name);
              });
              currentOrder = sortedStatuses.map(s => s.id);
              debug.dnd('Using default column order (no saved order)', { currentOrder });
            }
            setColumnOrder(currentOrder);
          }
          
          const oldIndex = currentOrder.indexOf(activeColumnId);
          const newIndex = currentOrder.indexOf(overId);
          
          debug.dnd('Column reordering: Index calculation', {
            oldIndex,
            newIndex,
            activeColumnId,
            overId,
            currentOrder,
            currentOrderLength: currentOrder.length,
            isLastColumn,
            isMovingToLast: newIndex === currentOrder.length - 1,
            isMovingFromLast: oldIndex === currentOrder.length - 1,
            activeColumnInOrder: currentOrder.includes(activeColumnId),
            overIdInOrder: currentOrder.includes(overId),
            containerScrollLeft: columnsContainerRef.current?.scrollLeft
          });
          
          if (oldIndex !== -1 && newIndex !== -1 && oldIndex !== newIndex) {
            const newOrder = arrayMove(currentOrder, oldIndex, newIndex);
            debug.dnd('Column reordering: Success - calling arrayMove', { 
              oldIndex, 
              newIndex, 
              activeColumnId, 
              overId, 
              currentOrder, 
              newOrder,
              activeProjectId,
              newOrderLength: newOrder.length,
              isLastColumn,
              movedFromIndex: oldIndex,
              movedToIndex: newIndex,
              beforeMove: currentOrder.map((id, idx) => ({ id, idx })),
              afterMove: newOrder.map((id, idx) => ({ id, idx }))
            });
            setColumnOrder(newOrder);
            // Save immediately after reordering (don't wait for useEffect)
            if (activeProjectId && newOrder.length > 0) {
              debug.dnd('Calling saveColumnOrderToStorage', { activeProjectId, newOrder });
              saveColumnOrderToStorage(activeProjectId, newOrder);
              debug.dnd('Column reordered and saved', { from: oldIndex, to: newIndex, activeColumnId, overId, newOrder });
            } else {
              debug.dnd('Column reordered but not saved (missing projectId or empty order)', { 
                activeProjectId, 
                newOrder, 
                newOrderLength: newOrder.length,
                hasProjectId: !!activeProjectId,
                hasOrder: newOrder.length > 0
              });
            }
          } else {
            debug.dnd('Column reorder skipped (invalid indices)', { 
              oldIndex, 
              newIndex, 
              activeColumnId, 
              overId, 
              currentOrder,
              isLastColumn,
              reason: oldIndex === -1 ? 'oldIndex not found' : newIndex === -1 ? 'newIndex not found' : 'indices are the same',
              activeColumnInOrder: currentOrder.includes(activeColumnId),
              overIdInOrder: currentOrder.includes(overId),
              currentOrderDetails: currentOrder.map((id, idx) => ({ id, idx, isActive: id === activeColumnId, isOver: id === overId }))
            });
          }
        } else {
          debug.dnd('Column reorder skipped: Invalid overId or conditions not met', {
            overId,
            activeColumnId,
            overIdValid: overId && availableStatuses.some(s => s.id === overId),
            isSameColumn: overId === activeColumnId,
            isLastColumn,
            over: over ? { id: over.id, data: over.data?.current } : null
          });
        }
      } else {
        debug.dnd('Column reorder skipped: No over target or availableStatuses', {
          hasOver: !!over,
          hasAvailableStatuses: !!availableStatuses,
          isLastColumn,
          over: over ? { id: over.id, data: over.data?.current } : null
        });
      }
      return;
    }
    
    // Handle task dragging
    // CRITICAL: First check if this is actually a column drag that wasn't detected in handleDragStart
    // This can happen if the drag starts from a child element or if handleDragStart failed to detect it
    const activeData = active.data.current;
    const activeId = String(active.id);
    
    // If active data has type 'column', it's definitely a column drag - DO NOT process as task
    if (activeData?.type === 'column') {
      debug.warn('Column drag detected in handleDragEnd but draggedColumnId was not set! This should not happen.', { 
        activeId, 
        activeData,
        draggedColumnId,
        availableStatuses: availableStatuses?.map(s => s.id)
      });
      // Don't process as task - just reset state and return
      setActiveId(null);
      setActiveColumnId(null);
      setReorderedTasks({});
      return;
    }
    
    // Also check if the activeId matches a column ID (status ID) - if so, it's a column drag
    if (availableStatuses && availableStatuses.some(s => String(s.id) === activeId)) {
      // Check if it's also a task ID - if not, it's definitely a column
      const isTaskId = tasks.some(t => String(t.id) === activeId);
      if (!isTaskId) {
        debug.warn('Column drag detected in handleDragEnd by ID check but draggedColumnId was not set! This should not happen.', { 
          activeId, 
          activeData,
          draggedColumnId,
          isTaskId
        });
        // Don't process as task - just reset state and return
        setActiveId(null);
        setActiveColumnId(null);
        setReorderedTasks({});
        return;
      }
    }
    
    // Only proceed with task dragging if we're certain it's not a column
    // If we're not sure, don't process it
    if (!activeId || activeId === 'undefined' || activeId === 'null') {
      debug.warn('Invalid activeId in handleDragEnd, skipping task drag processing', { activeId, activeData });
      setActiveId(null);
      setActiveColumnId(null);
      setReorderedTasks({});
      return;
    }
    
    // Now handle task dragging - we've confirmed it's not a column drag
    setActiveId(null);
    setActiveColumnId(null);
    setReorderedTasks({});

    if (!over) {
      debug.dnd('No drop target, cancelling task drag');
      return;
    }

    if (!availableStatuses) {
      debug.warn('No available statuses, cannot process task drag');
      return;
    }

    const overId = String(over.id);

    // Find the task being dragged
    // Convert to string for comparison (OpenProject uses numeric IDs, JIRA uses string IDs)
    const task = tasks.find(t => String(t.id) === activeId);
    if (!task) {
      debug.dnd('No task found for activeId', { activeId });
      return;
    }

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
      debug.dnd('Could not determine target column');
      return;
    }

    // Find the status corresponding to the target column ID
    const targetStatus = availableStatuses.find(status => status.id === targetColumnId);
    if (!targetStatus) {
      debug.warn('Cannot find status for column ID', { targetColumnId });
      return;
    }

    const newStatus = targetStatus.name;

    debug.dnd('Moving task', { from: task.status, to: newStatus, statusId: targetColumnId });

    // Don't update if status is the same
    if (newStatus === task.status) {
      debug.dnd('Task already has status, skipping update', { status: newStatus });
      return;
    }

    // Update task status via API
    // Always send the status name (not ID) to match manual editing behavior
    // The backend will look up the status by name, which works correctly
    
    // Verify the status exists in available statuses before sending
    const targetStatusExists = availableStatuses.some(s => s.id === targetColumnId);
    if (!targetStatusExists) {
      debug.error('Status ID not found in available statuses', { targetColumnId });
      toast.error('Invalid status', {
        description: `The selected status is not available.`,
        duration: 4000,
      });
      return;
    }

    // Always send the status name (not the ID) to match manual editing behavior
    // The backend will look up the status by name, which works correctly
    const statusValue = newStatus;
    
    debug.task('Updating task status', { taskId: activeId, statusValue, targetColumnId });
    
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
          debug.task('findMatchingStatusId', { statusName, normalized, foundId, matchingStatus: matching?.name });
          return foundId;
        };
        
        const actualStatusNormalized = normalizeStatusForComparison(actualStatus);
        const expectedStatusNormalized = normalizeStatusForComparison(newStatus);
        const originalStatusNormalized = normalizeStatusForComparison(originalStatus);
        
        // Check if the actual status matches the target column ID
        const actualStatusId = findMatchingStatusId(actualStatus);
        const statusMatchesTargetColumn = actualStatusId === targetColumnId;
        
        debug.task('Status ID matching', {
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
        
        debug.task('Status update result', {
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
        
        debug.task('Status change analysis', {
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
        });
        
        // IMPORTANT: Only show success if status actually changed AND matches expected
        // If status didn't change, it means the update was ignored by OpenProject
        if (!statusChanged) {
          debug.warn('Status did not change', { 
            expected: newStatus, 
            expectedNormalized: expectedStatusNormalized, 
            column: targetColumnId, 
            got: actualStatus, 
            gotNormalized: actualStatusNormalized, 
            gotColumn: actualStatusId, 
            original: originalStatus, 
            originalNormalized: originalStatusNormalized 
          });
          toast.error('Status update failed', {
            description: `The task status could not be changed from "${displayOriginal}" to "${displayExpected}". The status remains "${displayActual}". This may be due to workflow restrictions or permissions.`,
            duration: 6000,
          });
          return; // Exit early - don't show success
        }
        
        // If status changed but doesn't match the target column, it's a partial success
        if (statusChanged && !statusIdMatches && actualStatusId !== null) {
          debug.warn('Status changed but to different column', { expectedColumn: targetColumnId, gotColumn: actualStatusId });
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
          debug.task('Clearing reordered tasks', { sourceColumn: sourceStatusId, targetColumn: targetColumnId });
          
          setReorderedTasks(prev => {
            const updated = { ...prev };
            if (sourceStatusId) {
              delete updated[sourceStatusId];
            }
            if (targetColumnId) {
              delete updated[targetColumnId];
            }
            debug.task('Updated reorderedTasks', { keys: Object.keys(updated) });
            return updated;
          });
          
          // Clear activeId to ensure the task is no longer filtered out
          setActiveId(null);
          setActiveColumnId(null);
          
          // Status changed successfully to what we wanted
          // Note: We already verified the status matches immediately after the update above,
          // so we can confidently show success here. The task list will be refreshed by handleUpdateTask.
          toast.success('Task status updated', {
            description: `Task status changed from "${displayOriginal}" to "${displayActual}"`,
            duration: 3000,
          });
        } else {
          // Status changed but to something different than expected
          debug.warn('Status changed to unexpected value', { 
            expected: newStatus, 
            expectedNormalized: expectedStatusNormalized, 
            column: targetColumnId, 
            got: actualStatus, 
            gotNormalized: actualStatusNormalized, 
            gotColumn: actualStatusId, 
            original: originalStatus, 
            originalNormalized: originalStatusNormalized 
          });
          toast.error('Status update partially successful', {
            description: `Task status changed from "${displayOriginal}" to "${displayActual}" (expected "${displayExpected}"). The system may have applied a different status due to workflow rules.`,
            duration: 5000,
          });
        }
        
        // Note: handleUpdateTask already refreshes the task list, so we don't need to do it again here
      } catch (err) {
        // Catch and handle the error - show toast notification instead of console error
        const errorMessage = err instanceof Error ? err.message : String(err);
        let userFriendlyMessage = 'Failed to update task status';
        let description = errorMessage;
        
        // Make OpenProject permission errors more user-friendly
        if (errorMessage.includes('no valid transition exists') || 
            errorMessage.includes('no valid transition')) {
          userFriendlyMessage = 'Status transition not allowed';
          description = 'You do not have permission to change the task status from the current status to the target status based on your role. Please contact your administrator or try a different status transition.';
        } else if (errorMessage.includes('Status is invalid')) {
          userFriendlyMessage = 'Status change not allowed';
          description = 'This status change is not allowed. The status transition may be restricted by your role permissions or workflow rules.';
        } else if (errorMessage.includes('workflow') || errorMessage.includes('transition')) {
          userFriendlyMessage = 'Workflow restriction';
          description = 'This status transition is not allowed by the workflow rules. Please try a different status or contact your administrator.';
        }
        
        // Only log to debug if enabled (not to console.error to avoid noise)
        debug.error('Error updating task status', { 
          errorMessage, 
          userFriendlyMessage, 
          description,
          taskId: activeId,
          targetStatus: newStatus
        });
        
        // Show toast notification - this is the primary way to inform the user
        toast.error(userFriendlyMessage, {
          description: description,
          duration: 6000,
        });
        
        // Reset drag state on error
        setActiveId(null);
        setActiveColumnId(null);
        setReorderedTasks({});
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
    
    debug.api('Updating task', { taskId, url: url.toString(), updates });
    
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
        
        // Format OpenProject validation errors more clearly
        if (errorMessage.includes('OpenProject validation error')) {
          // Extract the actual error message after the prefix
          const match = errorMessage.match(/OpenProject validation error \(\d+\): (.+)/);
          if (match) {
            errorMessage = match[1];
          }
        }
      } catch {
        if (errorText) {
          errorMessage = errorText;
        }
      }
      
      // Create a custom error that won't be logged as an uncaught exception
      const error = new Error(errorMessage);
      // Mark it as handled so it doesn't show up in console as uncaught
      (error as any).isHandled = true;
      // Return a rejected promise instead of throwing to prevent Next.js from logging it
      return Promise.reject(error);
    }
    
    const result = await response.json();
    debug.api('Task update success', { result, taskStatus: result.status, expectedStatus: updates.status });
    
    // Check if the status actually changed
    if (updates.status && result.status) {
      const expectedStatus = String(updates.status);
      const actualStatus = String(result.status);
      if (expectedStatus !== actualStatus && !actualStatus.toLowerCase().includes(expectedStatus.toLowerCase())) {
        debug.warn('Status mismatch', { expected: expectedStatus, got: actualStatus });
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
        debug.task('Task 1 matching for column', {
          columnName: status.name,
          columnId: status.id,
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
    debug.column('Column distribution', {
      totalTasksInColumns,
      totalFilteredTasks: filteredTasks.length,
      availableStatuses: availableStatuses.length,
      columns: columns.map(col => ({ id: col.id, title: col.title, taskCount: col.tasks?.length || 0 })),
    });
    
    // Debug: Find unmatched tasks
    const matchedTaskIds = new Set(columns.flatMap(col => (col.tasks || []).map(t => t.id)));
    const unmatchedTasks = filteredTasks.filter(t => !matchedTaskIds.has(t.id));
    if (unmatchedTasks.length > 0) {
      debug.warn(`Found ${unmatchedTasks.length} unmatched tasks`, unmatchedTasks.map(t => ({
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
      debug.error('Failed to load column order from localStorage', error);
    }
    return null;
  }, []);

  const saveColumnOrderToStorage = useCallback((projectId: string | null, order: string[]) => {
    debug.storage('saveColumnOrderToStorage called', { projectId, orderLength: order.length, order, windowDefined: typeof window !== 'undefined' });
    if (typeof window === 'undefined' || !projectId || order.length === 0) {
      debug.storage('Cannot save column order', { projectId, orderLength: order.length, reason: !projectId ? 'no projectId' : order.length === 0 ? 'empty order' : 'window undefined' });
      return;
    }
    const key = getStorageKey(projectId);
    if (!key) {
      debug.storage('Cannot generate storage key for projectId', { projectId });
      return;
    }
    try {
      const orderString = JSON.stringify(order);
      localStorage.setItem(key, orderString);
      // Verify it was saved
      const saved = localStorage.getItem(key);
      const savedParsed = saved ? JSON.parse(saved) : null;
      debug.storage('Saved column order to localStorage', { 
        projectId, 
        key, 
        order, 
        saved: savedParsed,
        savedMatches: JSON.stringify(savedParsed) === JSON.stringify(order)
      });
      if (JSON.stringify(savedParsed) !== JSON.stringify(order)) {
        debug.error('Column order save verification failed!', { expected: order, actual: savedParsed });
      }
    } catch (error) {
      debug.error('Failed to save column order to localStorage', { error, projectId, order });
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
          debug.storage('Loaded column order from localStorage', { projectId: activeProjectId, finalOrder });
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
          debug.storage('Using default column order', { defaultOrder });
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
            debug.error('Failed to load column visibility from localStorage', error);
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
    debug.storage('useEffect for columnOrder change triggered', { 
      isLoadingFromStorage, 
      columnOrderLength: columnOrder.length, 
      activeProjectId, 
      availableStatusesLength: availableStatuses?.length 
    });
    
    if (isLoadingFromStorage) {
      // Don't save during initial load from localStorage
      debug.storage('Skipping save (loading from storage)', { isLoadingFromStorage });
      return;
    }
    
    if (columnOrder.length > 0 && activeProjectId && availableStatuses) {
      // Save if we have valid statuses in the order (less strict condition)
      // This ensures the order is saved even if not all statuses are present yet
      const statusIds = new Set(availableStatuses.map(s => s.id));
      const orderHasValidStatuses = columnOrder.length > 0 && columnOrder.some(id => statusIds.has(id));
      
      debug.storage('Checking if should save', { 
        orderHasValidStatuses, 
        columnOrder, 
        statusIds: Array.from(statusIds),
        allOrderIdsAreValid: columnOrder.every(id => statusIds.has(id))
      });
      
      if (orderHasValidStatuses) {
        // Only save if all statuses in the order are valid (but don't require all statuses to be in the order)
        const allOrderIdsAreValid = columnOrder.every(id => statusIds.has(id));
        if (allOrderIdsAreValid) {
          debug.storage('Calling saveColumnOrderToStorage from useEffect', { activeProjectId, columnOrder });
          saveColumnOrderToStorage(activeProjectId, columnOrder);
          debug.storage('Saved column order via useEffect (backup)', { activeProjectId, columnOrder });
        } else {
          debug.storage('Not saving: some order IDs are invalid', { 
            columnOrder, 
            statusIds: Array.from(statusIds),
            invalidIds: columnOrder.filter(id => !statusIds.has(id))
          });
        }
      } else {
        debug.storage('Not saving: no valid statuses in order', { columnOrder, statusIds: Array.from(statusIds) });
      }
    } else {
      debug.storage('Not saving: missing requirements', { 
        columnOrderLength: columnOrder.length, 
        activeProjectId, 
        availableStatusesLength: availableStatuses?.length 
      });
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
          debug.error('Failed to save column visibility to localStorage', error);
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleColumnsArray, activeProjectId, availableStatuses, isLoadingFromStorage]);

  // Track columnOrder changes for debugging
  useEffect(() => {
    debug.column('columnOrder state changed', {
      columnOrder,
      columnOrderLength: columnOrder.length,
      draggedColumnId,
      activeColumnId,
      containerScrollLeft: columnsContainerRef.current?.scrollLeft
    });
  }, [columnOrder, draggedColumnId, activeColumnId]);

  // Apply column order and visibility to columns
  const orderedColumns = useMemo(() => {
    debug.column('Computing orderedColumns', { 
      columnsLength: columns.length, 
      visibleColumnsSize: visibleColumns.size, 
      columnOrderLength: columnOrder.length,
      columnOrder,
      draggedColumnId,
      columns: columns.map(c => ({ id: c.id, title: c.title }))
    });
    
    // First filter by visibility
    let visibleCols = columns;
    if (visibleColumns.size > 0) {
      // Check if any of the visibleColumns IDs actually match current columns
      const columnIds = new Set(columns.map(col => col.id));
      const hasMatchingVisibleColumns = Array.from(visibleColumns).some(id => columnIds.has(id));
      
      if (hasMatchingVisibleColumns) {
        // Filter by visibility only if we have matching IDs
        visibleCols = columns.filter(col => visibleColumns.has(col.id));
        debug.column('After visibility filter', { 
          visibleColsLength: visibleCols.length, 
          visibleColumnsSize: visibleColumns.size 
        });
      } else {
        // If visibleColumns has no matching IDs (e.g., from a different project), show all columns
        debug.warn('visibleColumns has no matching IDs, showing all columns', { 
          visibleColumns: Array.from(visibleColumns).slice(0, 5), 
          columnIds: Array.from(columnIds).slice(0, 5) 
        });
        visibleCols = columns;
      }
    }
    
    // Then apply order
    if (columnOrder.length === 0) {
      debug.column('No column order, returning visible columns', { visibleColsLength: visibleCols.length });
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
    
    const result = [...ordered, ...newColumns];
    debug.column('Final orderedColumns', { 
      resultLength: result.length, 
      orderedLength: ordered.length, 
      newColumnsLength: newColumns.length,
      result: result.map(c => ({ id: c.id, title: c.title })),
      columnOrder,
      draggedColumnId,
      containerScrollLeft: columnsContainerRef.current?.scrollLeft
    });
    return result;
  }, [columns, columnOrder, visibleColumns, draggedColumnId]);

  // Use tasks instead of filteredTasks to ensure we can always find the dragged task
  const activeTask = activeId ? tasks.find(t => String(t.id) === String(activeId)) : null;

  // Show loading state only if we don't have the essential data yet
  // Allow rendering if we have tasks, even if statuses are still loading (optimistic rendering)
  // Statuses are not critical for initial render - we can show tasks even without statuses
  // Only show loading if we have NO tasks AND we're still loading, OR if filter data is loading
  const hasTasks = tasks.length > 0;
  const hasStatuses = availableStatuses.length > 0;
  
  // Only block rendering if:
  // 1. Filter data is loading (providers, projects, etc.)
  // 2. We're loading tasks AND we don't have any tasks yet
  // Don't block on statuses loading - we can render tasks without statuses
  const isLoading = loadingState.filterData.loading || 
                    (shouldLoadTasks && loading && !hasTasks);
  
  useEffect(() => {
    debug.state('Loading check', {
      filterDataLoading: loadingState.filterData.loading,
      shouldLoadTasks,
      loading,
      statusesLoading,
      hasTasks,
      hasStatuses,
      isLoading,
      tasksLength: tasks.length,
      availableStatusesLength: availableStatuses.length,
    });
  }, [isLoading, loadingState.filterData.loading, shouldLoadTasks, loading, statusesLoading, hasTasks, hasStatuses, tasks.length, availableStatuses.length]);
  
  if (isLoading) {
    debug.render('Showing loading state', {
      filterDataLoading: loadingState.filterData.loading,
      shouldLoadTasks,
      loading,
      statusesLoading,
      hasTasks,
      hasStatuses,
    });
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
  
  if (statusesError) {
    return (
      <div className="flex flex-col items-center justify-center py-20 px-4">
        <div className="text-red-500 font-semibold mb-2">Error loading statuses</div>
        <div className="text-red-400 text-sm text-center max-w-2xl">
          {statusesError.message}
        </div>
        <div className="mt-4 text-xs text-muted-foreground">
          Tip: Check your PM provider configuration and verify the project exists.
        </div>
        <Button 
          onClick={() => refreshStatuses()} 
          className="mt-4"
          variant="outline"
        >
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
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
      <Card className="p-4 mb-4 flex-shrink-0">
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
        {(() => {
          debug.render('Rendering board', { 
            orderedColumnsLength: orderedColumns.length, 
            columnsLength: columns.length, 
            availableStatusesLength: availableStatuses.length 
          });
          if (orderedColumns.length === 0) {
            debug.warn('orderedColumns is empty', { 
              columnsLength: columns.length, 
              visibleColumnsSize: visibleColumns.size, 
              columnOrderLength: columnOrder.length 
            });
          }
          return orderedColumns.length > 0 ? (
            <SortableContext 
              items={orderedColumns.map(col => col.id)} 
              strategy={horizontalListSortingStrategy}
            >
              <div 
                ref={columnsContainerRef}
                className="flex gap-4 overflow-x-auto flex-1 min-h-0"
                style={{
                  scrollBehavior: 'smooth',
                }}
              >
                {orderedColumns.map((column) => (
                  <div key={column.id} className="flex-shrink-0 w-80 h-full">
                    <SortableColumn 
                      column={{ id: column.id, title: column.title }} 
                      tasks={column.tasks || []} 
                      onTaskClick={handleTaskClick}
                      activeColumnId={activeColumnId}
                      activeId={activeId}
                      isDraggingColumn={draggedColumnId === column.id}
                      isAnyColumnDragging={!!draggedColumnId}
                      onColumnDragStateChange={(columnId, isDragging) => {
                        setDraggingColumnIds(prev => {
                          const next = new Set(prev);
                          if (isDragging) {
                            next.add(columnId);
                          } else {
                            next.delete(columnId);
                          }
                          debug.dnd('Column drag state changed', { columnId, isDragging, draggingColumnIds: Array.from(next) });
                          return next;
                        });
                      }}
                    />
                  </div>
                ))}
              </div>
            </SortableContext>
          ) : (
            <div className="flex items-center justify-center flex-1">
              <div className="text-gray-500 dark:text-gray-400">No statuses available for this project</div>
            </div>
          );
        })()}

        <DragOverlay>
          {activeTask ? <TaskCard task={activeTask} onClick={() => {}} isColumnDragging={false} /> : null}
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
