// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { DndContext, DragOverlay, PointerSensor, useSensor, useSensors, closestCorners, useDroppable, type CollisionDetection } from "@dnd-kit/core";
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
import {
  getOrderId,
  createOrderIdsFromStatusIds,
  getStatusIdsFromOrderIds,
  getStatusIdFromOrderId,
  getOrderIdFromStatusId,
  detectDragType,
  extractTargetColumn,
  normalizeStatus,
  findMatchingStatusId,
  formatTaskUpdateError,
  type DragInfo,
} from "./sprint-board-helpers";

type DragMeasurements = {
  taskWidth: number | null;
  taskHeight: number | null;
  columnWidth: number | null;
  columnHeight: number | null;
};

function TaskCard({ task, onClick, isColumnDragging }: { task: any; onClick: () => void; isColumnDragging?: boolean }) {
  // Ensure task.id is always a string for dnd-kit (OpenProject uses numeric IDs, JIRA uses string IDs)
  const taskId = String(task.id);
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: taskId,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition: isColumnDragging
      ? 'none'
      : (isDragging
        ? 'opacity 160ms ease, box-shadow 160ms ease'
        : (transition || 'transform 260ms cubic-bezier(0.22, 1, 0.36, 1), opacity 220ms ease, box-shadow 220ms ease')),
    opacity: isDragging ? 0 : 1,
    zIndex: isDragging ? 10 : undefined,
    willChange: isColumnDragging ? undefined : 'transform, opacity, box-shadow',
    pointerEvents: isDragging ? 'none' : undefined,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      data-task-id={taskId}
      className="flex items-center gap-2 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow cursor-pointer w-full"
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

function TaskPlaceholder({ isActive, height }: { isActive?: boolean; height?: number | null }) {
  return (
    <div
      className={`flex items-center gap-2 rounded-lg border-2 border-dashed px-3 py-4 text-sm font-medium transition-all w-full ${
        isActive
          ? 'border-blue-500 bg-blue-50/70 text-blue-600 dark:border-blue-400 dark:bg-blue-900/40 dark:text-blue-200'
          : 'border-gray-300 bg-white/60 text-gray-400 dark:border-gray-600 dark:bg-gray-800/40 dark:text-gray-400'
      }`}
      style={{
        minHeight: height ? `${height}px` : '72px',
        height: height ? `${height}px` : undefined,
      }}
      aria-hidden="true"
    >
      <span>Drop here</span>
    </div>
  );
}

function TaskDragPreview({ task, width, height }: { task: any; width?: number | null; height?: number | null }) {
  return (
    <div
      className="flex items-center gap-2 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-xl"
      style={{
        width: width ? `${width}px` : '100%',
        height: height ? `${height}px` : undefined,
        boxShadow: '0 18px 35px -15px rgba(15, 23, 42, 0.45)',
        transform: 'translateZ(0)',
      }}
    >
      <div className="text-gray-400 dark:text-gray-500">
        <GripVertical className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm text-gray-900 dark:text-white mb-1 line-clamp-2">
          {task?.title}
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          {task?.priority && (
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
          {task?.estimated_hours && (
            <span className="text-gray-500 dark:text-gray-400">
              ⏱️ {task.estimated_hours}h
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function SortableColumn({ column, tasks, onTaskClick, activeColumnId, activeId, isDraggingColumn, isAnyColumnDragging, onColumnDragStateChange, orderId, placeholderHeight }: { 
  column: { id: string; title: string }; 
  tasks: any[]; 
  onTaskClick: (task: any) => void;
  activeColumnId?: string | null;
  activeId?: string | null;
  isDraggingColumn?: boolean;
  isAnyColumnDragging?: boolean;
  onColumnDragStateChange?: (columnId: string, isDragging: boolean) => void;
  orderId?: string; // NEW: Order ID for dragging (separate from status ID)
  placeholderHeight?: number | null;
}) {
  // Use orderId for dragging if provided, otherwise fall back to column.id (status ID)
  const dragId = orderId || column.id;
  
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: dragId, // NEW: Use order ID for dragging
    data: {
      type: 'column',
      statusId: column.id, // Keep status ID in data for task operations
      orderId: orderId || column.id, // Include order ID in data
    },
  });
  
  // Notify parent when column drag state changes
  // Use a ref to track previous isDragging state to avoid unnecessary calls
  const prevIsDraggingRef = useRef(isDragging);
  useEffect(() => {
    // Only call callback if isDragging actually changed
    if (prevIsDraggingRef.current !== isDragging && onColumnDragStateChange) {
      prevIsDraggingRef.current = isDragging;
      // Use orderId for drag state change if provided, otherwise use column.id
      onColumnDragStateChange(orderId || column.id, isDragging);
    }
  }, [isDragging, column.id, orderId, onColumnDragStateChange]);

  // Make the entire column droppable
  // NEW: Use orderId for droppable zones if provided
  const { setNodeRef: setDroppableRef, isOver } = useDroppable({ 
    id: dragId, // Use order ID for droppable
    data: {
      type: 'column',
      column: dragId, // Use order ID
      statusId: column.id, // Keep status ID for task operations
      orderId: orderId || column.id,
    },
  });

  // Separate droppable zones for top and bottom of column (easier to drop)
  const { setNodeRef: setTopDropRef, isOver: isOverTop } = useDroppable({
    id: `${dragId}-top-drop`, // Use order ID
    data: {
      type: 'column',
      column: dragId, // Use order ID
      statusId: column.id, // Keep status ID for task operations
      orderId: orderId || column.id,
      position: 'top',
    },
  });

  const { setNodeRef: setBottomDropRef, isOver: isOverBottom } = useDroppable({
    id: `${dragId}-bottom-drop`, // Use order ID
    data: {
      type: 'column',
      column: dragId, // Use order ID
      statusId: column.id, // Keep status ID for task operations
      orderId: orderId || column.id,
      position: 'bottom',
    },
  });

  // Separate ref for the scrollable content area (for auto-scroll)
  const scrollAreaRef = useRef<HTMLDivElement | null>(null);
  const setScrollAreaRef = (node: HTMLDivElement | null) => {
    scrollAreaRef.current = node;
  };

  // CRITICAL: The sortable ref should be on the entire column container for proper transformation
  // But the drag listeners should only be on the grab handle to allow task dragging
  // We'll apply the sortable ref to the outer container, and listeners to the grab handle
  const columnContainerRef = (node: HTMLDivElement | null) => {
    setNodeRef(node);
  };
  
  const droppableContainerRef = (node: HTMLDivElement | null) => {
    setDroppableRef(node);
  };

  // Enhanced animation styles for column dragging
  // Combine dnd-kit transform with scale effect during dragging
  const sortableTransform = CSS.Transform.toString(transform);
  const columnStyle = {
    transform: sortableTransform,
    // Smooth transitions: when dragging, use dnd-kit's transition; when not dragging, use smooth reordering animation
    transition: isDragging 
      ? transition || 'transform 160ms ease, opacity 160ms ease, box-shadow 160ms ease' // Use dnd-kit's transition during drag
      : 'transform 280ms cubic-bezier(0.2, 0, 0, 1), opacity 220ms ease, box-shadow 220ms ease', // Smooth animation when reordering
    opacity: isDragging ? 1 : (isAnyColumnDragging ? 0.94 : 1),
    // Add shadow effects during dragging for better visual feedback
    boxShadow: isDragging 
      ? '0 20px 40px -25px rgba(15, 23, 42, 0.55)'
      : (isAnyColumnDragging ? '0 12px 32px -20px rgba(30, 41, 59, 0.35)' : undefined),
    zIndex: isDragging ? 60 : 1,
    willChange: 'transform, opacity, box-shadow',
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
  
  // Memoize the items array for SortableContext to ensure stable reference
  // Use a stable string representation of task IDs to prevent unnecessary recalculations
  const sortableItems = useMemo(() => {
    const items = tasks
      .filter(task => !task?.__placeholder)
      .map(t => String(t.id));
    // Return empty array if no items to prevent initialization issues
    return items;
  }, [tasks]);
  
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
      ref={columnContainerRef}
      style={columnStyle}
      {...attributes}
      className="flex flex-col h-full"
      data-column-id={column.id}
      data-order-id={dragId}
      data-dnd-type="column"
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
        className={`flex items-center justify-between p-3 rounded-t-lg transition-colors ${
          isActive && !isDraggingColumn
            ? 'bg-blue-100 dark:bg-blue-900' 
            : 'bg-gray-100 dark:bg-gray-800'
        }`}
        data-column-id={column.id}
        data-order-id={dragId}
      >
        <div className="flex items-center gap-2 flex-1">
          {/* Column grab handle - only this area is draggable for columns */}
          <div 
            {...listeners}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 shrink-0 cursor-grab active:cursor-grabbing"
            style={{
              touchAction: 'none',
              userSelect: 'none',
              WebkitUserSelect: 'none',
              padding: '4px',
              margin: '-4px',
            }}
          >
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
        ref={droppableContainerRef}
        className={`flex-1 rounded-b-lg p-3 min-h-0 border-2 overflow-y-auto transition-all duration-200 ${
          isActive && !isDraggingColumn
            ? 'bg-blue-50 dark:bg-blue-950 border-blue-500 dark:border-blue-500' 
            : 'bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800'
        }`}
        style={{
          overscrollBehavior: 'contain',
        }}
      >
        {tasks.length === 0 ? (
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
                {tasks.map((task) => {
                  const isPlaceholder = Boolean(task?.__placeholder);
                  if (isPlaceholder) {
                    return (
                      <TaskPlaceholder
                        key={String(task.id)}
                        isActive={isActive && !isDraggingColumn}
                        height={placeholderHeight}
                      />
                    );
                  }

                  // Use String(task.id) for key to match useSortable id and ensure stable keys
                  const taskIdStr = String(task.id);
                  return (
                    <TaskCard
                      key={taskIdStr}
                      task={task}
                      onClick={() => onTaskClick(task)}
                      isColumnDragging={isAnyColumnDragging}
                    />
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

function ColumnDragPreview({ column, tasks, width, height, taskHeight }: { column: { id: string; title: string }; tasks: any[]; width?: number | null; height?: number | null; taskHeight?: number | null }) {
  const previewTasks = (tasks || []).slice(0, 3);

  return (
    <div
      className="flex flex-col h-full pointer-events-none"
      style={{
        width: width ? `${width}px` : '20rem',
        height: height ? `${height}px` : undefined,
        boxShadow: '0 20px 45px -25px rgba(15, 23, 42, 0.45)',
        borderRadius: '0.75rem',
        overflow: 'hidden',
        backgroundColor: 'transparent',
      }}
    >
      <div className="flex items-center justify-between p-3 rounded-t-lg bg-gray-100 dark:bg-gray-800">
        <div className="flex items-center gap-2 flex-1">
          <div className="text-gray-400 dark:text-gray-500">
            <GripHorizontal className="w-4 h-4" />
          </div>
          <h3 className="font-semibold text-gray-900 dark:text-white truncate">
            {column.title}
          </h3>
        </div>
        <span className="px-2 py-1 bg-white dark:bg-gray-700 rounded text-sm font-medium text-gray-700 dark:text-gray-300">
          {tasks?.length ?? 0}
        </span>
      </div>
      <div className="flex-1 rounded-b-lg border-2 border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 p-3 space-y-2">
        {previewTasks.length > 0 ? (
          previewTasks.map((task) => (
            <TaskDragPreview key={task.id} task={task} height={taskHeight} />
          ))
        ) : (
          <TaskPlaceholder isActive={false} height={taskHeight} />
        )}
      </div>
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
  // Column Order ID system: Separate visual ordering from status IDs
  // columnOrderIds: Array of order IDs (e.g., ['order-0', 'order-1', 'order-2'])
  // orderIdToStatusIdMap: Maps order ID to status ID (e.g., { 'order-0': '1', 'order-1': '3' })
  const [columnOrderIds, setColumnOrderIds] = useState<string[]>([]);
  const [orderIdToStatusIdMap, setOrderIdToStatusIdMap] = useState<Map<string, string>>(new Map());
  
  // Legacy columnOrder for backward compatibility during migration
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
  // Use a ref to track dragging columns for immediate access (no state update delay)
  const draggingColumnIdsRef = useRef<Set<string>>(new Set());
  // Ref to store timeout for delayed column drag detection
  const delayedCheckTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  // Ref to track draggedColumnId for immediate access (no state update delay)
  const draggedColumnIdRef = useRef<string | null>(null);
  // Track the last valid target column ID during drag to provide stability
  const lastTargetColumnIdRef = useRef<string | null>(null);
  // Track measured dimensions for overlays so they can match source size
  const [dragDimensions, setDragDimensions] = useState<DragMeasurements>({
    taskWidth: null,
    taskHeight: null,
    columnWidth: null,
    columnHeight: null,
  });

  const resetDragDimensions = useCallback(() => {
    setDragDimensions({
      taskWidth: null,
      taskHeight: null,
      columnWidth: null,
      columnHeight: null,
    });
  }, []);

  const updateDragDimensions = useCallback((updates: Partial<DragMeasurements>) => {
    setDragDimensions(prev => ({ ...prev, ...updates }));
  }, []);

  const clearTaskDragState = useCallback(() => {
    setActiveId(null);
    setActiveColumnId(null);
    setReorderedTasks({});
    resetDragDimensions();
  }, [resetDragDimensions]);
  
  // Memoize the callback to prevent infinite loops
  const handleColumnDragStateChange = useCallback((columnId: string, isDragging: boolean) => {
    setDraggingColumnIds(prev => {
      // Check if the state would actually change
      const wouldAdd = isDragging && !prev.has(columnId);
      const wouldRemove = !isDragging && prev.has(columnId);
      
      // Only update if state would change
      if (!wouldAdd && !wouldRemove) {
        return prev; // Return same reference to prevent unnecessary re-renders
      }
      
      const next = new Set(prev);
      if (isDragging) {
        next.add(columnId);
      } else {
        next.delete(columnId);
      }
      // Also update ref for immediate access
      draggingColumnIdsRef.current = next;
      debug.dnd('Column drag state changed', { columnId, isDragging, draggingColumnIds: Array.from(next) });
      return next;
    });
  }, []);
  
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

  // Custom collision detection that ignores the dragged column
  // This is needed because dnd-kit considers the dragged item to be "over" itself
  const customCollisionDetection: CollisionDetection = useCallback((args) => {
    const { active, droppableContainers, pointerCoordinates } = args;
    const activeId = String(active.id);
    
    // First, try to find collisions using closestCorners
    const collisions = closestCorners(args);
    
    debug.dnd('Custom collision detection', {
      activeId,
      allCollisions: collisions.map(c => String(c.id)),
      collisionsCount: collisions.length,
      pointerCoordinates: pointerCoordinates ? { x: pointerCoordinates.x, y: pointerCoordinates.y } : null
    });
    
    // Filter out the dragged column itself and its droppable zones
    const filteredCollisions = collisions.filter(collision => {
      const collisionId = String(collision.id);
      // If this is the dragged column, skip it
      if (collisionId === activeId) {
        return false;
      }
      // If this is a droppable zone of the dragged column, skip it
      if (collisionId === `${activeId}-top-drop` || collisionId === `${activeId}-bottom-drop`) {
        return false;
      }
      return true;
    });
    
    // PRIORITY 1: Use pointer-based detection to find the column directly under the pointer
    // This is the most accurate method, especially when there are many columns and horizontal scrolling
    if (pointerCoordinates && columnsContainerRef.current) {
      const container = columnsContainerRef.current;
      const pointerX = pointerCoordinates.x;
      const pointerY = pointerCoordinates.y;
      
      // Find which column the pointer is actually over by checking DOM positions
      // Use data-order-id for matching (order IDs are used for dragging)
      const columnElements = container.querySelectorAll('[data-order-id]');
      let columnUnderPointer: { id: string; distance: number } | null = null;
      
      for (const columnEl of columnElements) {
        const orderId = columnEl.getAttribute('data-order-id');
        if (orderId && orderId !== activeId) {
          const columnRect = columnEl.getBoundingClientRect();
          
          // Check if pointer is within the column's bounds (both X and Y)
          if (pointerX >= columnRect.left && pointerX <= columnRect.right &&
              pointerY >= columnRect.top && pointerY <= columnRect.bottom) {
            const columnCenterX = columnRect.left + columnRect.width / 2;
            const distance = Math.abs(pointerX - columnCenterX);
            
            // If pointer is directly over this column, use it (prefer closest to center)
            if (!columnUnderPointer || distance < columnUnderPointer.distance) {
              columnUnderPointer = { id: orderId, distance };
            }
          }
        }
      }
      
      // If we found a column directly under the pointer, prioritize it
      if (columnUnderPointer) {
        // Check if this column is in the filtered collisions (it should be)
        const matchingCollision = filteredCollisions.find(c => {
          const collisionId = String(c.id);
          // Match column ID directly, or match droppable zones (top-drop/bottom-drop)
          return collisionId === columnUnderPointer!.id || 
                 collisionId === `${columnUnderPointer!.id}-top-drop` || 
                 collisionId === `${columnUnderPointer!.id}-bottom-drop`;
        });
        
        if (matchingCollision) {
          debug.dnd('Using pointer-based collision detection (column directly under pointer)', {
            activeId,
            orderId: columnUnderPointer.id,
            distance: columnUnderPointer.distance,
            collisionId: String(matchingCollision.id),
            allFilteredCollisions: filteredCollisions.map(c => String(c.id))
          });
          // Return the matching collision, prioritizing the column ID over droppable zones
          const columnCollision = filteredCollisions.find(c => String(c.id) === columnUnderPointer!.id);
          return columnCollision ? [columnCollision] : [matchingCollision];
        }
      }
      
      // PRIORITY 2: If pointer is not directly over any column, find the closest one horizontally
      // This handles edge cases when dragging near column boundaries
      // Use a smaller threshold (200px) to avoid selecting columns that are too far away
      let closestColumnByDistance: { id: string; distance: number } | null = null;
      
      for (const columnEl of columnElements) {
        const orderId = columnEl.getAttribute('data-order-id');
        if (orderId && orderId !== activeId) {
          const columnRect = columnEl.getBoundingClientRect();
          const columnCenterX = columnRect.left + columnRect.width / 2;
          const distance = Math.abs(pointerX - columnCenterX);
          
          // Only consider columns that are reasonably close horizontally
          // Check if the pointer is within a reasonable horizontal range of the column
          const horizontalRange = columnRect.width * 1.5; // 1.5x the column width
          if (distance < horizontalRange) {
            if (!closestColumnByDistance || distance < closestColumnByDistance.distance) {
              closestColumnByDistance = { id: orderId, distance };
            }
          }
        }
      }
      
      // If we found a close column (within reasonable distance), use it
      // But only if it's also in the filtered collisions
      if (closestColumnByDistance && closestColumnByDistance.distance < 200) { // 200px threshold (reduced from 500px)
        const matchingCollision = filteredCollisions.find(c => {
          const collisionId = String(c.id);
          return collisionId === closestColumnByDistance!.id || 
                 collisionId === `${closestColumnByDistance!.id}-top-drop` || 
                 collisionId === `${closestColumnByDistance!.id}-bottom-drop`;
        });
        
        if (matchingCollision) {
          debug.dnd('Using closest column by distance (pointer not directly over)', {
            activeId,
            closestOrderId: closestColumnByDistance.id,
            distance: closestColumnByDistance.distance,
            collisionId: String(matchingCollision.id),
            allFilteredCollisions: filteredCollisions.map(c => String(c.id))
          });
          // Return the matching collision, prioritizing the column ID over droppable zones
          const columnCollision = filteredCollisions.find(c => String(c.id) === closestColumnByDistance!.id);
          return columnCollision ? [columnCollision] : [matchingCollision];
        }
      }
    }
    
    debug.dnd('Filtered collisions (fallback to closestCorners)', {
      activeId,
      filteredCollisions: filteredCollisions.map(c => String(c.id)),
      filteredCount: filteredCollisions.length
    });
    
    // PRIORITY 3: Fall back to filtered collisions from closestCorners
    // If we have filtered collisions, return them (but prioritize column IDs over droppable zones)
    if (filteredCollisions.length > 0) {
      // Sort collisions to prioritize column IDs over droppable zones
      const sortedCollisions = filteredCollisions.sort((a, b) => {
        const aId = String(a.id);
        const bId = String(b.id);
        const aIsZone = aId.endsWith('-top-drop') || aId.endsWith('-bottom-drop');
        const bIsZone = bId.endsWith('-top-drop') || bId.endsWith('-bottom-drop');
        
        // Column IDs come before droppable zones
        if (aIsZone && !bIsZone) return 1;
        if (!aIsZone && bIsZone) return -1;
        return 0;
      });
      
      return sortedCollisions;
    }
    
    // If no collisions found (excluding the dragged column), return empty array
    // This will allow the drag to continue but won't trigger any drop actions
    return [];
  }, []);
  
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
    const taskIds = new Set(tasks.map(t => String(t.id)));
    const dragInfo = detectDragType(event, columnOrderIds, taskIds);
    resetDragDimensions();
    
    debug.dnd('Drag started', { 
      activeId: dragInfo.id,
      dragType: dragInfo.type,
      orderId: dragInfo.orderId,
      statusId: dragInfo.statusId,
    });
    
    if (dragInfo.type === 'column' && dragInfo.orderId) {
      // Column drag
      try {
        const columnElement = document.querySelector(`[data-order-id="${dragInfo.orderId}"]`);
        if (columnElement instanceof HTMLElement) {
          const rect = columnElement.getBoundingClientRect();
          updateDragDimensions({ columnWidth: rect.width, columnHeight: rect.height });
        }
      } catch (error) {
        debug.warn('Failed to measure column width', { error, dragInfo });
      }
      setDraggedColumnId(dragInfo.orderId);
      draggedColumnIdRef.current = dragInfo.orderId;
      lastTargetColumnIdRef.current = null;
      setActiveId(null);
    } else if (dragInfo.type === 'task') {
      // Task drag
      try {
        const taskElement = document.querySelector(`[data-task-id="${dragInfo.id}"]`);
        if (taskElement instanceof HTMLElement) {
          const rect = taskElement.getBoundingClientRect();
          updateDragDimensions({ taskWidth: rect.width, taskHeight: rect.height });
        }
      } catch (error) {
        debug.warn('Failed to measure task width', { error, dragInfo });
      }
      setActiveId(dragInfo.id);
      setDraggedColumnId(null);
      draggedColumnIdRef.current = null;
    } else {
      // Unknown - default to task drag
      debug.warn('Could not determine drag type, defaulting to task drag', { dragInfo });
      setActiveId(dragInfo.id);
      setDraggedColumnId(null);
      draggedColumnIdRef.current = null;
      lastTargetColumnIdRef.current = null;
      setReorderedTasks({});
    }
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    
    // Handle column reordering
    if (draggedColumnId) {
      if (!over || !availableStatuses) {
        setActiveColumnId(null);
        return;
      }
      
      const activeOrderId = draggedColumnId;
      const { orderId: overOrderId } = extractTargetColumn(
        String(over.id),
        over.data.current,
        columnOrderIds,
        orderIdToStatusIdMap,
        availableStatuses,
        tasks
      );
      
      // Visual feedback: highlight target column
      if (overOrderId && overOrderId !== activeOrderId && columnOrderIds.includes(overOrderId)) {
        const overStatusId = getStatusIdFromOrderId(overOrderId, orderIdToStatusIdMap);
        if (overStatusId) {
          setActiveColumnId(overStatusId);
        }
        lastTargetColumnIdRef.current = overOrderId;
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

    // Handle task dragging - extract target column
    const activeId = active.id as string;
    const { statusId: targetColumnId } = extractTargetColumn(
      String(over.id),
      over.data.current,
      columnOrderIds,
      orderIdToStatusIdMap,
      availableStatuses,
      tasks
    );
    
    // Update visual reordering if we have a target column
    if (targetColumnId) {
      const targetStatus = availableStatuses.find(status => status.id === targetColumnId);
      if (targetStatus) {
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
          
          // Prepare new reordered tasks state focused on affected columns
          const newReorderedTasks: Record<string, any[]> = {};
          
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
          const placeholderTask = {
            id: `placeholder-${String(activeId)}`,
            __placeholder: true,
            originalId: String(activeId),
            title: activeTask.title,
          };
          
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
                targetOrder.splice(overIndex, 0, placeholderTask);
              } else {
                targetOrder = [...baseTargetTasks, placeholderTask];
              }
            } else {
              targetOrder = [...baseTargetTasks, placeholderTask];
            }
          } else {
            const overIdStr = over ? String(over.id) : "";
            if (overIdStr.endsWith('-top-drop')) {
              targetOrder = [placeholderTask, ...baseTargetTasks];
            } else if (overIdStr.endsWith('-bottom-drop')) {
              targetOrder = [...baseTargetTasks, placeholderTask];
            } else {
              targetOrder = baseTargetTasks.length === 0 
                ? [placeholderTask]
                : [...baseTargetTasks, placeholderTask];
            }
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

          setActiveColumnId(targetColumnId);

          return;
        }
      }
    }
    
    setActiveColumnId(targetColumnId);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    
    // Detect drag type using helper
    const taskIds = new Set(tasks.map(t => String(t.id)));
    const dragInfo = detectDragType(event, columnOrderIds, taskIds);
    
    // Use ref for immediate access to draggedColumnId (no state update delay)
    const currentDraggedColumnId = draggedColumnIdRef.current || draggedColumnId;
    
    // If it's a column drag but draggedColumnId wasn't set, set it now
    if (dragInfo.type === 'column' && dragInfo.orderId && !currentDraggedColumnId) {
      debug.warn('Column drag detected in handleDragEnd (missed in handleDragStart)', {
        dragInfo,
        draggedColumnId,
      });
      setDraggedColumnId(dragInfo.orderId);
      draggedColumnIdRef.current = dragInfo.orderId;
      lastTargetColumnIdRef.current = null;
    }
    
    // Use the detected or existing draggedColumnId
    const finalDraggedColumnId = currentDraggedColumnId || (dragInfo.type === 'column' && dragInfo.orderId ? dragInfo.orderId : null);
    
    debug.dnd('Drag ended', { 
      activeId: active.id,
      dragType: dragInfo.type,
      draggedColumnId: finalDraggedColumnId,
      overId: over?.id,
    });
    
    // Clear dragging column IDs on drag end
    setDraggingColumnIds(new Set());
    draggingColumnIdsRef.current = new Set();
    
    // Handle column reordering
    if (finalDraggedColumnId) {
      const activeOrderId = finalDraggedColumnId; // This is now an order ID
      debug.dnd('handleDragEnd: Processing column drag end', {
        activeOrderId,
        over: over ? { id: over.id, data: over.data?.current } : null,
      });
      
      setDraggedColumnId(null);
      draggedColumnIdRef.current = null;
      setActiveColumnId(null);
      resetDragDimensions();
      
      if (over && availableStatuses) {
        // Extract target column using helper
        const { orderId: overOrderId } = extractTargetColumn(
          String(over.id),
          over.data.current,
          columnOrderIds,
          orderIdToStatusIdMap,
          availableStatuses,
          tasks
        );
        
        // Use last valid target as fallback if needed
        const lastTargetOrderId = lastTargetColumnIdRef.current;
        let finalOverOrderId = overOrderId || lastTargetOrderId || activeOrderId;
        
        // Validate finalOverOrderId
        if (finalOverOrderId && !columnOrderIds.includes(finalOverOrderId)) {
          finalOverOrderId = activeOrderId;
        }
        
        // Reorder using order IDs
        if (finalOverOrderId && finalOverOrderId !== activeOrderId && columnOrderIds.includes(finalOverOrderId) && columnOrderIds.includes(activeOrderId)) {
          // Ensure columnOrderIds is initialized
          let currentOrderIds = columnOrderIds;
          let currentMapping = orderIdToStatusIdMap;
          
          if (currentOrderIds.length === 0 && availableStatuses) {
            // Try to load from localStorage first
            debug.dnd('Column order is empty, trying to load from localStorage', { activeProjectId });
            const savedOrder = loadColumnOrderFromStorage(activeProjectId);
            if (savedOrder && savedOrder.length > 0) {
              // Validate saved order - convert to strings for comparison
              const validStatusIds = new Set(availableStatuses.map(s => String(s.id)));
              const validOrder = savedOrder.filter(id => validStatusIds.has(String(id))).map(id => String(id));
              if (validOrder.length > 0) {
                // Convert status IDs to order IDs
                const { orderIds, mapping } = createOrderIdsFromStatusIds(validOrder);
                currentOrderIds = orderIds;
                currentMapping = mapping;
                debug.dnd('Loaded column order from localStorage and converted to order IDs', { 
                  statusIds: validOrder, 
                  orderIds: currentOrderIds,
                  mappingSize: currentMapping.size
                });
              } else {
                // Fallback to default order (sorted by status ID) - convert IDs to strings
                const sortedStatuses = [...availableStatuses].sort((a, b) => {
                  const aId = typeof a.id === 'number' ? a.id : Number(a.id);
                  const bId = typeof b.id === 'number' ? b.id : Number(b.id);
                  
                  // If both are valid numbers, compare numerically
                  if (!isNaN(aId) && !isNaN(bId)) {
                    return aId - bId;
                  }
                  
                  // Otherwise, compare as strings
                  return String(a.id).localeCompare(String(b.id));
                });
                const statusIds = sortedStatuses.map(s => String(s.id));
                const { orderIds, mapping } = createOrderIdsFromStatusIds(statusIds);
                currentOrderIds = orderIds;
                currentMapping = mapping;
                debug.dnd('Using default column order (saved order invalid, sorted by status ID)', { 
                  statusIds,
                  orderIds: currentOrderIds,
                  mappingSize: currentMapping.size
                });
              }
            } else {
              // No saved order, use default (sorted by status ID) - convert IDs to strings
              const sortedStatuses = [...availableStatuses].sort((a, b) => {
                const aId = typeof a.id === 'number' ? a.id : Number(a.id);
                const bId = typeof b.id === 'number' ? b.id : Number(b.id);
                
                // If both are valid numbers, compare numerically
                if (!isNaN(aId) && !isNaN(bId)) {
                  return aId - bId;
                }
                
                // Otherwise, compare as strings
                return String(a.id).localeCompare(String(b.id));
              });
              const statusIds = sortedStatuses.map(s => String(s.id));
              const { orderIds, mapping } = createOrderIdsFromStatusIds(statusIds);
              currentOrderIds = orderIds;
              currentMapping = mapping;
              debug.dnd('Using default column order (no saved order, sorted by status ID)', { 
                statusIds,
                orderIds: currentOrderIds,
                mappingSize: currentMapping.size
              });
            }
            // Update state with the new order IDs and mapping
            setColumnOrderIds(currentOrderIds);
            setOrderIdToStatusIdMap(currentMapping);
            // Also update legacy columnOrder for backward compatibility
            const statusIds = getStatusIdsFromOrderIds(currentOrderIds, currentMapping);
            setColumnOrder(statusIds);
          }
          
          // Use order IDs for index calculation
          const oldIndex = currentOrderIds.indexOf(activeOrderId);
          const newIndex = currentOrderIds.indexOf(finalOverOrderId);
          
          debug.dnd('Column reordering: Index calculation', {
            oldIndex,
            newIndex,
            activeOrderId,
            finalOverOrderId,
            currentOrderIdsLength: currentOrderIds.length,
          });
          
          if (oldIndex !== -1 && newIndex !== -1 && oldIndex !== newIndex) {
            const newOrderIds = arrayMove(currentOrderIds, oldIndex, newIndex);
            debug.dnd('Column reordering: Success', { 
              oldIndex, 
              newIndex, 
              activeOrderId,
              finalOverOrderId,
              newOrderIdsLength: newOrderIds.length,
            });
            
            // Update state with new order IDs
            setColumnOrderIds(newOrderIds);
            
            // Convert order IDs back to status IDs for localStorage and legacy columnOrder
            const newStatusIds = getStatusIdsFromOrderIds(newOrderIds, currentMapping);
            setColumnOrder(newStatusIds);
            
            // Save immediately after reordering (don't wait for useEffect)
            if (activeProjectId && newStatusIds.length > 0) {
              debug.dnd('Calling saveColumnOrderToStorage with status IDs', { activeProjectId, newStatusIds, newOrderIds });
              saveColumnOrderToStorage(activeProjectId, newStatusIds);
              debug.dnd('Column reordered and saved', { 
                from: oldIndex, 
                to: newIndex, 
                activeOrderId,
                finalOverOrderId,
              });
              // Clear the last target column ref after successful reorder
              lastTargetColumnIdRef.current = null;
            } else {
              debug.dnd('Column reordered but not saved (missing projectId or empty order)', { 
                activeProjectId, 
                newStatusIds, 
                newOrderIds,
                newStatusIdsLength: newStatusIds.length,
                hasProjectId: !!activeProjectId,
                hasOrder: newStatusIds.length > 0
              });
            }
          } else {
            debug.dnd('Column reorder skipped (invalid indices)', { 
              oldIndex, 
              newIndex, 
              activeOrderId,
              finalOverOrderId,
              reason: oldIndex === -1 ? 'oldIndex not found' : newIndex === -1 ? 'newIndex not found' : 'indices are the same',
            });
          }
        } else {
          debug.dnd('Column reorder skipped: Invalid conditions', {
            finalOverOrderId,
            activeOrderId,
          });
          lastTargetColumnIdRef.current = null;
        }
      } else {
        debug.dnd('Column reorder skipped: No over target or availableStatuses', {
          hasOver: !!over,
          hasAvailableStatuses: !!availableStatuses,
        });
        // Clear the last target column ref since reordering was skipped
        lastTargetColumnIdRef.current = null;
      }
      return;
    }
    
    // Handle task dragging
    // If this was detected as a column drag, don't process as task
    if (dragInfo.type === 'column') {
      debug.warn('Column drag detected in handleDragEnd but draggedColumnId was not set! This should not happen.', { 
        dragInfo,
        draggedColumnId,
      });
      clearTaskDragState();
      return;
    }
    
    // Only proceed with task dragging if we're certain it's a task
    const activeIdStr = dragInfo.id;
    if (!activeIdStr || activeIdStr === 'undefined' || activeIdStr === 'null' || dragInfo.type !== 'task') {
      debug.warn('Invalid or non-task drag in handleDragEnd, skipping task drag processing', { 
        activeId: activeIdStr, 
        dragInfo 
      });
      clearTaskDragState();
      return;
    }
    
    // Now handle task dragging - we've confirmed it's not a column drag
    clearTaskDragState();

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
    const task = tasks.find(t => String(t.id) === activeIdStr);
    if (!task) {
      debug.dnd('No task found for activeId', { activeId: activeIdStr });
      return;
    }

    // Determine which column we're dropping into using helper function
    const { orderId: overOrderId, statusId: targetColumnId } = extractTargetColumn(
      overId,
      over.data.current,
      columnOrderIds,
      orderIdToStatusIdMap,
      availableStatuses,
      tasks
    );
    
    debug.dnd('Task drag: Target column extracted', { overId, overOrderId, targetColumnId });

    if (!targetColumnId || !availableStatuses) {
      debug.error('Could not determine target column', { 
        targetColumnId, 
        hasAvailableStatuses: !!availableStatuses,
        overId,
        overOrderId,
        over: over ? { id: over.id, data: over.data?.current } : null
      });
      return;
    }

    // Find the status corresponding to the target column ID
    const targetStatus = availableStatuses.find(status => String(status.id) === String(targetColumnId));
    if (!targetStatus) {
      debug.error('Cannot find status for column ID', { 
        targetColumnId, 
        availableStatuses: availableStatuses.map(s => ({ id: s.id, name: s.name })),
        overId,
        overOrderId
      });
      toast.error('Invalid status', {
        description: `The target status could not be found.`,
        duration: 4000,
      });
      return;
    }

    const newStatus = targetStatus.name;
    
    if (!newStatus) {
      debug.error('Target status has no name', { targetStatus, targetColumnId });
      toast.error('Invalid status', {
        description: `The target status is invalid.`,
        duration: 4000,
      });
      return;
    }

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
        // Validate inputs before attempting update
        if (!activeId || activeId === 'undefined' || activeId === 'null') {
          debug.error('Invalid task ID for update', { activeId, taskId: task?.id });
          toast.error('Invalid task', {
            description: 'Cannot update task: invalid task ID.',
            duration: 4000,
          });
          return;
        }
        
        if (!statusValue || statusValue.trim() === '') {
          debug.error('Invalid status value for update', { statusValue, newStatus, targetStatus });
          toast.error('Invalid status', {
            description: 'Cannot update task: invalid status value.',
            duration: 4000,
          });
          return;
        }
        
        // Get the original task status before update
        const originalTask = tasks.find(t => String(t.id) === String(activeId));
        if (!originalTask) {
          debug.error('Task not found for update', { activeId, taskIds: tasks.map(t => String(t.id)).slice(0, 5) });
          toast.error('Task not found', {
            description: 'Cannot update task: task not found in current list.',
            duration: 4000,
          });
          return;
        }
        
        const originalStatus = originalTask?.status || 'No status';
        
        debug.task('Calling handleUpdateTask', { 
          taskId: activeId, 
          statusValue, 
          targetColumnId,
          originalStatus,
          newStatus
        });
        
        const result = await handleUpdateTask(activeId, { 
          status: statusValue,
        });
        
        if (!result) {
          debug.error('handleUpdateTask returned null/undefined', { activeId, statusValue });
          toast.error('Update failed', {
            description: 'The task update did not return a result. Please try again.',
            duration: 4000,
          });
          return;
        }
        
        // Get the actual status returned from OpenProject/JIRA
        const actualStatus = result?.status || null;
        
        
        const actualStatusNormalized = normalizeStatus(actualStatus);
        const expectedStatusNormalized = normalizeStatus(newStatus);
        const originalStatusNormalized = normalizeStatus(originalStatus);
        
        // Check if the actual status matches the target column ID
        const actualStatusId = findMatchingStatusId(actualStatus, availableStatuses);
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
        // Use helper function to format error message
        const { message: userFriendlyMessage, description } = formatTaskUpdateError(err);
        
        // Log detailed error information for debugging
        debug.error('Error updating task status', { 
          error: err,
          errorMessage: err instanceof Error ? err.message : String(err),
          errorStack: err instanceof Error ? err.stack : undefined,
          userFriendlyMessage, 
          description,
          taskId: activeId,
          task: task ? { id: task.id, title: task.title, status: task.status } : null,
          targetStatus: newStatus,
          targetColumnId,
          statusValue,
        });
        
        // Show toast notification
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
    
    // If we have reordered tasks for this column, use them (includes placeholder when applicable)
    const reordered = reorderedTasks[statusId];
    if (reordered) {
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

  // Helper functions for Column Order ID system are now imported from helpers

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

  // Helper function to reset column order to default (sorted by status ID)
  const resetColumnOrderToDefault = useCallback((projectId: string | null, statuses: typeof availableStatuses) => {
    if (!statuses || statuses.length === 0) return;
    
    // Sort by status ID (numeric if possible, otherwise string)
    const sortedStatuses = [...statuses].sort((a, b) => {
      const aId = typeof a.id === 'number' ? a.id : Number(a.id);
      const bId = typeof b.id === 'number' ? b.id : Number(b.id);
      
      // If both are valid numbers, compare numerically
      if (!isNaN(aId) && !isNaN(bId)) {
        return aId - bId;
      }
      
      // Otherwise, compare as strings
      return String(a.id).localeCompare(String(b.id));
    });
    
    const defaultOrder = sortedStatuses.map(s => s.id);
    
    // Clear localStorage for this project
    if (projectId && typeof window !== 'undefined') {
      const key = getStorageKey(projectId);
      if (key) {
        localStorage.removeItem(key);
        debug.storage('Reset column order: Cleared localStorage', { projectId, key, defaultOrder });
      }
    }
    
    // Set the default order
    setColumnOrder(defaultOrder);
    debug.storage('Reset column order to default (sorted by status ID)', { projectId, defaultOrder });
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
          // Sort missing statuses by ID (numeric if possible, otherwise string)
          const missingStatuses = availableStatuses
            .filter(s => !validOrder.includes(s.id))
            .sort((a, b) => {
              const aId = typeof a.id === 'number' ? a.id : Number(a.id);
              const bId = typeof b.id === 'number' ? b.id : Number(b.id);
              
              // If both are valid numbers, compare numerically
              if (!isNaN(aId) && !isNaN(bId)) {
                return aId - bId;
              }
              
              // Otherwise, compare as strings
              return String(a.id).localeCompare(String(b.id));
            });
          
          const finalOrder = [...validOrder, ...missingStatuses.map(s => s.id)];
          
          // Create order IDs from status IDs
          const { orderIds, mapping } = createOrderIdsFromStatusIds(finalOrder.map(id => String(id)));
          setColumnOrderIds(orderIds);
          setOrderIdToStatusIdMap(mapping);
          
          // Also set legacy columnOrder for backward compatibility
          setColumnOrder(finalOrder);
          setLastLoadedProjectId(activeProjectId);
          debug.storage('Loaded column order from localStorage', { projectId: activeProjectId, finalOrder, orderIds });
          // Reset loading flag after a brief delay to allow state to settle
          setTimeout(() => setIsLoadingFromStorage(false), 100);
        } else {
          // No saved order, use default (sorted by status ID)
          const sortedStatuses = [...availableStatuses].sort((a, b) => {
            const aId = typeof a.id === 'number' ? a.id : Number(a.id);
            const bId = typeof b.id === 'number' ? b.id : Number(b.id);
            
            // If both are valid numbers, compare numerically
            if (!isNaN(aId) && !isNaN(bId)) {
              return aId - bId;
            }
            
            // Otherwise, compare as strings
            return String(a.id).localeCompare(String(b.id));
          });
          const defaultOrder = sortedStatuses.map(s => String(s.id));
          
          // Create order IDs from status IDs
          const { orderIds, mapping } = createOrderIdsFromStatusIds(defaultOrder);
          setColumnOrderIds(orderIds);
          setOrderIdToStatusIdMap(mapping);
          
          // Also set legacy columnOrder for backward compatibility
          setColumnOrder(defaultOrder);
          setLastLoadedProjectId(activeProjectId);
          debug.storage('Using default column order (sorted by status ID)', { defaultOrder, orderIds });
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
      setColumnOrderIds([]);
      setOrderIdToStatusIdMap(new Map());
      setVisibleColumns(new Set());
      setLastLoadedProjectId(null);
    }
  }, [availableStatuses, activeProjectId, lastLoadedProjectId, loadColumnOrderFromStorage, createOrderIdsFromStatusIds]);

  // Reset column order to default (sorted by status ID) when flag is set or on first load
  useEffect(() => {
    if (availableStatuses && availableStatuses.length > 0 && activeProjectId) {
      // Check if reset flag is set in localStorage
      const resetFlag = typeof window !== 'undefined' ? localStorage.getItem('sprint-board-reset-column-order') : null;
      if (resetFlag === 'true') {
        // Reset the column order
        resetColumnOrderToDefault(activeProjectId, availableStatuses);
        // Clear the flag
        localStorage.removeItem('sprint-board-reset-column-order');
        debug.storage('Column order reset triggered by flag', { projectId: activeProjectId });
      } else {
        // Check if we need to do a one-time reset for this project (migration to ID-based sorting)
        const resetVersionKey = `sprint-board-column-order-reset-v2-${activeProjectId}`;
        const hasReset = typeof window !== 'undefined' ? localStorage.getItem(resetVersionKey) : null;
        if (!hasReset) {
          // First time loading with new ID-based sorting, reset the order
          resetColumnOrderToDefault(activeProjectId, availableStatuses);
          if (typeof window !== 'undefined') {
            localStorage.setItem(resetVersionKey, 'true');
          }
          debug.storage('Column order reset to ID-based sorting (one-time migration)', { projectId: activeProjectId });
        }
      }
    }
  }, [availableStatuses, activeProjectId, resetColumnOrderToDefault]);

  // Expose reset function to window for manual testing
  useEffect(() => {
    if (typeof window !== 'undefined') {
      (window as any).resetSprintBoardColumnOrder = () => {
        if (availableStatuses && availableStatuses.length > 0 && activeProjectId) {
          resetColumnOrderToDefault(activeProjectId, availableStatuses);
          console.log('Column order reset to default (sorted by status ID)');
        } else {
          console.warn('Cannot reset column order: no statuses or project ID');
        }
      };
      // Also expose a function to set the reset flag
      (window as any).setSprintBoardResetFlag = () => {
        localStorage.setItem('sprint-board-reset-column-order', 'true');
        console.log('Reset flag set. Refresh the page to reset column order.');
      };
    }
    return () => {
      if (typeof window !== 'undefined') {
        delete (window as any).resetSprintBoardColumnOrder;
        delete (window as any).setSprintBoardResetFlag;
      }
    };
  }, [availableStatuses, activeProjectId, resetColumnOrderToDefault]);

  // Save column order to localStorage whenever columnOrderIds changes (but not during initial load)
  // NEW: Convert order IDs to status IDs before saving
  useEffect(() => {
    debug.storage('useEffect for columnOrderIds change triggered', { 
      isLoadingFromStorage, 
      columnOrderIdsLength: columnOrderIds.length, 
      activeProjectId, 
      availableStatusesLength: availableStatuses?.length 
    });
    
    if (isLoadingFromStorage) {
      // Don't save during initial load from localStorage
      debug.storage('Skipping save (loading from storage)', { isLoadingFromStorage });
      return;
    }
    
    if (columnOrderIds.length > 0 && activeProjectId && availableStatuses && orderIdToStatusIdMap.size > 0) {
      // Convert order IDs to status IDs before saving
      const statusIdsToSave = getStatusIdsFromOrderIds(columnOrderIds, orderIdToStatusIdMap);
      
      // Validate that all status IDs exist in availableStatuses
      const statusIds = new Set(availableStatuses.map(s => String(s.id)));
      const orderHasValidStatuses = statusIdsToSave.length > 0 && statusIdsToSave.some(id => statusIds.has(id));
      
      debug.storage('Checking if should save', { 
        orderHasValidStatuses, 
        columnOrderIds,
        statusIdsToSave, 
        statusIds: Array.from(statusIds),
        allOrderIdsAreValid: statusIdsToSave.every(id => statusIds.has(id))
      });
      
      if (orderHasValidStatuses) {
        // Only save if all statuses in the order are valid (but don't require all statuses to be in the order)
        const allOrderIdsAreValid = statusIdsToSave.every(id => statusIds.has(id));
        if (allOrderIdsAreValid) {
          debug.storage('Calling saveColumnOrderToStorage from useEffect', { activeProjectId, statusIdsToSave, columnOrderIds });
          saveColumnOrderToStorage(activeProjectId, statusIdsToSave);
          debug.storage('Saved column order via useEffect (backup)', { activeProjectId, statusIdsToSave, columnOrderIds });
          
          // Also update legacy columnOrder for backward compatibility
          setColumnOrder(statusIdsToSave);
        } else {
          debug.storage('Not saving: some order IDs are invalid', { 
            columnOrderIds,
            statusIdsToSave, 
            statusIds: Array.from(statusIds),
            invalidIds: statusIdsToSave.filter(id => !statusIds.has(id))
          });
        }
      } else {
        debug.storage('Not saving: no valid statuses in order', { columnOrderIds, statusIdsToSave, statusIds: Array.from(statusIds) });
      }
    } else {
      debug.storage('Not saving: missing requirements', { 
        columnOrderIdsLength: columnOrderIds.length, 
        activeProjectId, 
        availableStatusesLength: availableStatuses?.length,
        mappingSize: orderIdToStatusIdMap.size
      });
    }
  }, [columnOrderIds, activeProjectId, availableStatuses, isLoadingFromStorage, saveColumnOrderToStorage, orderIdToStatusIdMap, getStatusIdsFromOrderIds]);

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
  // NEW: Use order IDs for ordering, but keep status IDs for task operations
  const orderedColumns = useMemo(() => {
    debug.column('Computing orderedColumns', { 
      columnsLength: columns.length, 
      visibleColumnsSize: visibleColumns.size, 
      columnOrderIdsLength: columnOrderIds.length,
      columnOrderIds,
      columnOrderLength: columnOrder.length,
      columnOrder,
      draggedColumnId,
      columns: columns.map(c => ({ id: c.id, title: c.title }))
    });
    
    // First filter by visibility
    let visibleCols = columns;
    if (visibleColumns.size > 0) {
      // Check if any of the visibleColumns IDs actually match current columns
      // Convert to strings for comparison (OpenProject uses numeric IDs, JIRA uses string IDs)
      const columnIds = new Set(columns.map(col => String(col.id)));
      const hasMatchingVisibleColumns = Array.from(visibleColumns).some(id => columnIds.has(String(id)));
      
      if (hasMatchingVisibleColumns) {
        // Filter by visibility only if we have matching IDs - convert to strings for comparison
        visibleCols = columns.filter(col => visibleColumns.has(String(col.id)));
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
    
    // Then apply order using order IDs
    if (columnOrderIds.length === 0) {
      debug.column('No column order IDs, returning visible columns', { visibleColsLength: visibleCols.length });
      // If no order IDs, return columns with order IDs set to status IDs (fallback)
      return visibleCols.map(col => ({
        ...col,
        orderId: String(col.id) // Fallback: use status ID as order ID
      }));
    }
    
    // Create a map from status ID to column for quick lookup
    const columnMap = new Map(visibleCols.map(col => [String(col.id), col]));
    
    // Map order IDs to columns via status IDs
    const ordered = columnOrderIds
      .map(orderId => {
        const statusId = getStatusIdFromOrderId(orderId, orderIdToStatusIdMap);
        if (!statusId) return null;
        const col = columnMap.get(statusId);
        if (!col) return null;
        return {
          ...col,
          orderId, // Include order ID for dragging
        };
      })
      .filter((col): col is typeof columns[0] & { orderId: string } => col !== null);
    
    // Add any visible columns that weren't in the order (new statuses)
    const orderedStatusIds = new Set(ordered.map(col => String(col.id)));
    const newColumns = visibleCols
      .filter(col => !orderedStatusIds.has(String(col.id)))
      .map(col => ({
        ...col,
        orderId: String(col.id) // Fallback: use status ID as order ID
      }));
    
    const result = [...ordered, ...newColumns];
    debug.column('Final orderedColumns', { 
      resultLength: result.length, 
      orderedLength: ordered.length, 
      newColumnsLength: newColumns.length,
      result: result.map(c => ({ id: c.id, orderId: (c as any).orderId, title: c.title })),
      columnOrderIds,
      columnOrder,
      draggedColumnId,
      containerScrollLeft: columnsContainerRef.current?.scrollLeft
    });
    return result;
  }, [columns, columnOrderIds, columnOrder, visibleColumns, draggedColumnId, orderIdToStatusIdMap, getStatusIdFromOrderId]);

  // Use tasks instead of filteredTasks to ensure we can always find the dragged task
  const activeTask = activeId ? tasks.find(t => String(t.id) === String(activeId)) : null;

  const activeColumnOverlay = useMemo(() => {
    if (!draggedColumnId) {
      return null;
    }

    const targetId = String(draggedColumnId);

    return (
      orderedColumns.find((column) => {
        const orderId = (column as any).orderId ? String((column as any).orderId) : null;
        const statusId = String(column.id);
        return orderId === targetId || statusId === targetId;
      }) || null
    );
  }, [draggedColumnId, orderedColumns]);

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
        collisionDetection={customCollisionDetection}
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
                      isDraggingColumn={draggedColumnId === (column as any).orderId || draggedColumnId === column.id}
                      isAnyColumnDragging={!!draggedColumnId}
                      onColumnDragStateChange={handleColumnDragStateChange}
                      orderId={(column as any).orderId} // NEW: Pass order ID for dragging
                      placeholderHeight={dragDimensions.taskHeight}
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

        <DragOverlay
          dropAnimation={{
            duration: 220,
            easing: 'cubic-bezier(0.2, 0, 0, 1)',
            dragSourceOpacity: 0.25,
          }}
        >
          {activeColumnOverlay ? (
            <ColumnDragPreview
              column={{ id: String(activeColumnOverlay.id), title: activeColumnOverlay.title }}
              tasks={(activeColumnOverlay as any).tasks || []}
              width={dragDimensions.columnWidth}
              height={dragDimensions.columnHeight}
              taskHeight={dragDimensions.taskHeight}
            />
          ) : activeTask ? (
            <TaskDragPreview
              task={activeTask}
              width={dragDimensions.taskWidth}
              height={dragDimensions.taskHeight}
            />
          ) : null}
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
