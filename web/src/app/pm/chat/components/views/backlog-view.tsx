// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import type { DragEndEvent, DragOverEvent, DragStartEvent } from "@dnd-kit/core";
import { 
  DndContext, 
  DragOverlay, 
  PointerSensor, 
  closestCorners,
  useDroppable, 
  useSensor, 
  useSensors 
} from "@dnd-kit/core";
import { 
  SortableContext, 
  useSortable, 
  verticalListSortingStrategy,
  arrayMove 
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { ChevronDown, ChevronRight, Filter, GripVertical, Search, Plus, Calendar } from "lucide-react";
import { useMemo, useState, useEffect, useCallback } from "react";

import { Button } from "~/components/ui/button";
import { Card } from "~/components/ui/card";
import { Input } from "~/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { usePMLoading } from "../../../context/pm-loading-context";
import { useSprints } from "~/core/api/hooks/pm/use-sprints";
import type { Task } from "~/core/api/hooks/pm/use-tasks";
import { useTasks } from "~/core/api/hooks/pm/use-tasks";
import { useEpics, type Epic } from "~/core/api/hooks/pm/use-epics";
import { useStatuses } from "~/core/api/hooks/pm/use-statuses";
import { usePriorities } from "~/core/api/hooks/pm/use-priorities";
import { useProjectData } from "../../../hooks/use-project-data";
import { useTaskFiltering } from "../../../hooks/use-task-filtering";
import { debug } from "../../../utils/debug";

import { TaskDetailsModal } from "../task-details-modal";
import { CreateEpicDialog } from "../create-epic-dialog";

/* ============================================================================
 * TYPES
 * ========================================================================= */

type DragType = 'task' | 'sprint' | 'epic' | null;

interface DragState {
  type: DragType;
  id: string | null;
  sourceSprintId?: string | null;
  overTaskId?: string | null;
}

/* ============================================================================
 * TASK CARD COMPONENT
 * ========================================================================= */

function TaskCard({ 
  task, 
  onClick, 
  epic,
  isDragging 
}: { 
  task: Task; 
  onClick: () => void; 
  epic?: Epic;
  isDragging?: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
    id: `task-${task.id}`,
    data: { type: 'task', task }
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
      className="group flex items-start gap-2 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md hover:border-gray-300 dark:hover:border-gray-600 transition-all cursor-pointer"
    >
      <div
        {...listeners}
        className="mt-0.5 cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <GripVertical className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0" onClick={onClick}>
        <div className="flex items-start justify-between gap-2 mb-1">
          <div className="text-sm font-medium text-gray-900 dark:text-white line-clamp-2 flex-1">
            {task.title}
          </div>
          {task.priority && (
            <span className={`px-2 py-0.5 text-xs font-medium rounded shrink-0 ${
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
        <div className="flex items-center gap-2 flex-wrap">
          {epic && (
            <span className="px-2 py-0.5 text-xs font-medium rounded flex items-center gap-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200">
              {epic.color && <div className={`w-2 h-2 rounded-full ${epic.color}`}></div>}
              <span className="truncate max-w-[100px]">{epic.name}</span>
            </span>
          )}
          {task.assigned_to && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              @{task.assigned_to}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

/* ============================================================================
 * EPIC SIDEBAR
 * ========================================================================= */

function EpicSidebar({ 
  onEpicSelect, 
  selectedEpic,
  tasks,
  projectId,
  onEpicCreate
}: { 
  onEpicSelect: (epicId: string | null) => void;
  selectedEpic: string | null;
  tasks: Task[];
  projectId: string | null | undefined;
  onEpicCreate?: () => void;
}) {
  const { epics, loading: epicsLoading } = useEpics(projectId);

  const epicCounts = useMemo(() => {
    const counts = new Map<string, number>();
    tasks.forEach(task => {
      if (task.epic_id) {
        counts.set(task.epic_id, (counts.get(task.epic_id) || 0) + 1);
      }
    });
    return counts;
  }, [tasks]);

  const tasksWithoutEpic = useMemo(() => {
    return tasks.filter(t => !t.epic_id).length;
  }, [tasks]);

  return (
    <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col h-full">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">EPICS</h3>
        <CreateEpicDialog projectId={projectId} onEpicCreated={onEpicCreate} />
      </div>
      
      <div className="flex-1 overflow-y-auto p-2">
        <button
          onClick={() => onEpicSelect(null)}
          className={`w-full text-left p-2 rounded mb-1 transition-colors ${
            selectedEpic === null
              ? "bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300" 
              : "hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">All issues</span>
            <span className="text-xs text-gray-500 dark:text-gray-400">{tasks.length}</span>
          </div>
        </button>

        {epicsLoading ? (
          <div className="p-2 text-sm text-gray-500 dark:text-gray-400">
            Loading epics...
          </div>
        ) : epics.length > 0 ? (
          <div className="space-y-1">
            {epics.map((epic) => (
              <button
                key={epic.id}
                onClick={() => onEpicSelect(epic.id)}
                className={`w-full text-left p-2 rounded transition-colors ${
                  selectedEpic === epic.id
                    ? "bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300" 
                    : "hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  {epic.color && <div className={`w-3 h-3 rounded ${epic.color} shrink-0`}></div>}
                  <span className="text-sm font-medium truncate flex-1">{epic.name}</span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">{epicCounts.get(epic.id) || 0}</span>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <div className="p-2 text-sm text-gray-500 dark:text-gray-400">
            No epics found
          </div>
        )}

        {tasksWithoutEpic > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="p-2 text-sm text-gray-500 dark:text-gray-400">
              {tasksWithoutEpic} {tasksWithoutEpic === 1 ? 'issue' : 'issues'} without epic
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ============================================================================
 * SPRINT SECTION
 * ========================================================================= */

function SprintSection({ 
  sprint, 
  tasks, 
  onTaskClick, 
  epicsMap,
  isOver,
  draggedTaskId
}: { 
  sprint: { id: string; name: string; start_date?: string; end_date?: string; status: string }; 
  tasks: Task[]; 
  onTaskClick: (task: Task) => void; 
  epicsMap?: Map<string, Epic>;
  isOver?: boolean;
  draggedTaskId?: string | null;
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  
  const { setNodeRef } = useDroppable({ 
    id: `sprint-${sprint.id}`,
    data: { type: 'sprint', sprintId: sprint.id }
  });

  const isActive = sprint.status === "active";
  const isClosed = sprint.status === "closed";
  const isFuture = sprint.status === "future";

  const taskIds = useMemo(() => tasks.map(t => `task-${t.id}`), [tasks]);
  
  return (
    <div className="mb-4">
      <div 
        className={`p-3 rounded-t-lg border ${
          isActive 
            ? "bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800" 
            : isClosed
            ? "bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700"
            : isFuture
            ? "bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800"
            : "bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700"
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="shrink-0 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
            <h3 className="font-semibold text-gray-900 dark:text-white truncate">{sprint.name}</h3>
            {isActive && (
              <span className="px-2 py-0.5 text-xs font-medium rounded bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 shrink-0">
                Active
              </span>
            )}
            {isClosed && (
              <span className="px-2 py-0.5 text-xs font-medium rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 shrink-0">
                Closed
              </span>
            )}
            {isFuture && (
              <span className="px-2 py-0.5 text-xs font-medium rounded bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 shrink-0">
                Future
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 shrink-0">
            {sprint.start_date && sprint.end_date && (
              <div className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
                <Calendar className="w-3 h-3" />
                <span>{new Date(sprint.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                <span>-</span>
                <span>{new Date(sprint.end_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
              </div>
            )}
            <span className="px-2 py-1 bg-white dark:bg-gray-800 rounded text-xs font-medium text-gray-700 dark:text-gray-300">
              {tasks.length}
            </span>
          </div>
        </div>
      </div>
      
      {isExpanded && (
        <div 
          ref={setNodeRef}
          className={`p-3 rounded-b-lg border-x border-b transition-colors ${
            isOver 
              ? "border-blue-400 bg-blue-50/50 dark:bg-blue-950/50 border-2" 
              : "border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900"
          }`}
        >
          {tasks.length === 0 ? (
            <div className="text-center py-8 text-sm text-gray-500 dark:text-gray-400">
              {isOver ? (
                <div className="border-2 border-dashed border-blue-400 bg-blue-50 dark:bg-blue-900/40 rounded-lg p-4 text-blue-600 dark:text-blue-300 font-medium">
                  Drop task here
                </div>
              ) : (
                <>
                  <p className="mb-2">No tasks in this sprint</p>
                  <Button variant="outline" size="sm">
                    <Plus className="w-4 h-4 mr-1" />
                    Add task
                  </Button>
                </>
              )}
            </div>
          ) : (
            <SortableContext items={taskIds} strategy={verticalListSortingStrategy}>
              <div className="space-y-2">
                {tasks.map((task, index) => (
                  <TaskCard 
                    key={task.id}
                    task={task} 
                    onClick={() => onTaskClick(task)} 
                    epic={task.epic_id && epicsMap ? epicsMap.get(task.epic_id) : undefined}
                    isDragging={draggedTaskId === task.id}
                  />
                ))}
              </div>
            </SortableContext>
          )}
        </div>
      )}
    </div>
  );
}

/* ============================================================================
 * BACKLOG SECTION
 * ========================================================================= */

function BacklogSection({ 
  tasks, 
  onTaskClick, 
  epicsMap,
  isOver,
  draggedTaskId
}: { 
  tasks: Task[]; 
  onTaskClick: (task: Task) => void; 
  epicsMap?: Map<string, Epic>;
  isOver?: boolean;
  draggedTaskId?: string | null;
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  
  const { setNodeRef } = useDroppable({ 
    id: "backlog",
    data: { type: 'backlog' }
  });

  const taskIds = useMemo(() => tasks.map(t => `task-${t.id}`), [tasks]);
  
  return (
    <div className="mb-4">
      <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-t-lg border border-gray-300 dark:border-gray-600">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="shrink-0 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
            <h3 className="font-semibold text-gray-900 dark:text-white">Backlog</h3>
          </div>
          <span className="px-2 py-1 bg-white dark:bg-gray-700 rounded text-xs font-medium text-gray-700 dark:text-gray-300">
            {tasks.length}
          </span>
        </div>
      </div>
      
      {isExpanded && (
        <div 
          ref={setNodeRef}
          className={`p-3 rounded-b-lg border-x border-b transition-colors min-h-[200px] ${
            isOver 
              ? "border-blue-400 bg-blue-50/50 dark:bg-blue-950/50 border-2" 
              : "border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900"
          }`}
        >
          {tasks.length === 0 ? (
            <div className="text-center py-12 text-sm text-gray-500 dark:text-gray-400">
              {isOver ? (
                <div className="border-2 border-dashed border-blue-400 bg-blue-50 dark:bg-blue-900/40 rounded-lg p-6 text-blue-600 dark:text-blue-300 font-medium">
                  Drop here to remove from sprint
                </div>
              ) : (
                <p>No tasks in backlog</p>
              )}
            </div>
          ) : (
            <SortableContext items={taskIds} strategy={verticalListSortingStrategy}>
              <div className="space-y-2">
                {tasks.map((task) => (
                  <TaskCard 
                    key={task.id}
                    task={task} 
                    onClick={() => onTaskClick(task)} 
                    epic={task.epic_id && epicsMap ? epicsMap.get(task.epic_id) : undefined}
                    isDragging={draggedTaskId === task.id}
                  />
                ))}
              </div>
            </SortableContext>
          )}
        </div>
      )}
    </div>
  );
}

/* ============================================================================
 * MAIN BACKLOG VIEW
 * ========================================================================= */

export function BacklogView() {
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const [selectedEpic, setSelectedEpic] = useState<string | null>(null);
  const [dragState, setDragState] = useState<DragState>({ type: null, id: null });
  const [overSprintId, setOverSprintId] = useState<string | null>(null);
  const [overTaskId, setOverTaskId] = useState<string | null>(null);
  
  const { activeProjectId, activeProject, projectIdForData: projectIdForSprints } = useProjectData();
  const { state: loadingState, setTasksState } = usePMLoading();
  
  useEffect(() => {
    setSearchQuery("");
    setStatusFilter("all");
    setPriorityFilter("all");
    setSelectedEpic(null);
  }, [activeProject?.id, projectIdForSprints]);
  
  const shouldLoadTasks = loadingState.canLoadTasks && projectIdForSprints;
  const { tasks: allTasks, loading, error, refresh: refreshTasks } = useTasks(projectIdForSprints ?? undefined);
  
  useEffect(() => {
    if (shouldLoadTasks) {
      setTasksState({ loading, error, data: allTasks });
    } else if (!projectIdForSprints) {
      setTasksState({ loading: false, error: null, data: null });
    }
  }, [shouldLoadTasks, loading, error, allTasks, setTasksState, projectIdForSprints]);
  
  const { tasks } = useTaskFiltering({
    allTasks,
    projectId: projectIdForSprints,
    activeProject,
    loading,
  });
  
  const { sprints, loading: sprintsLoading } = useSprints(projectIdForSprints ?? "", undefined);
  const { epics } = useEpics(projectIdForSprints ?? undefined);
  const { statuses: availableStatusesFromBackend } = useStatuses(projectIdForSprints ?? undefined, "task");
  const { priorities: availablePrioritiesFromBackend } = usePriorities(projectIdForSprints ?? undefined);
  
  const epicsMap = useMemo(() => {
    const map = new Map<string, Epic>();
    epics.forEach(epic => map.set(epic.id, epic));
    return map;
  }, [epics]);
  
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    })
  );

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
    setIsModalOpen(true);
  };

  const handleUpdateTask = useCallback(async (taskId: string, updates: Partial<Task>) => {
    if (!projectIdForSprints) throw new Error("Project ID is required");
    
    const url = new URL(resolveServiceURL(`pm/tasks/${taskId}`));
    url.searchParams.set('project_id', projectIdForSprints);
    
    const response = await fetch(url.toString(), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Failed to update task: ${response.status}`);
    }
    
    const result = await response.json();
    if (selectedTask && selectedTask.id === taskId) {
      setSelectedTask({ ...selectedTask, ...result });
    }
    
    refreshTasks(false);
    return result;
  }, [projectIdForSprints, selectedTask, refreshTasks]);

  const handleAssignTaskToSprint = useCallback(async (taskId: string, sprintId: string) => {
    if (!projectIdForSprints) throw new Error('No project selected');
    
    const url = resolveServiceURL(`pm/projects/${projectIdForSprints}/tasks/${taskId}/assign-sprint`);
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sprint_id: sprintId }),
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Failed to assign task: ${response.status}`);
    }
    
    window.dispatchEvent(new CustomEvent("pm_refresh", { detail: { type: "pm_refresh" } }));
  }, [projectIdForSprints]);

  const handleMoveTaskToBacklog = useCallback(async (taskId: string) => {
    if (!projectIdForSprints) throw new Error('No project selected');
    
    const url = resolveServiceURL(`pm/projects/${projectIdForSprints}/tasks/${taskId}/move-to-backlog`);
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Failed to move to backlog: ${response.status}`);
    }
    
    window.dispatchEvent(new CustomEvent("pm_refresh", { detail: { type: "pm_refresh" } }));
  }, [projectIdForSprints]);

  // Filter tasks
  const filteredTasks = useMemo(() => {
    if (loading && (!tasks || tasks.length === 0)) return [];
    if (!tasks || tasks.length === 0) return [];
    
    let filtered = [...tasks];

    const trimmedQuery = (searchQuery || "").trim();
    if (trimmedQuery) {
      const query = trimmedQuery.toLowerCase();
      filtered = filtered.filter(t => {
        const title = (t.title || "").toLowerCase();
        const description = (t.description || "").toLowerCase();
        return title.includes(query) || description.includes(query);
      });
    }

    if (statusFilter && statusFilter !== "all") {
      const filterStatusLower = statusFilter.toLowerCase();
      filtered = filtered.filter(t => (t.status || "").toLowerCase() === filterStatusLower);
    }

    if (priorityFilter && priorityFilter !== "all") {
      const filterPriorityLower = priorityFilter.toLowerCase();
      filtered = filtered.filter(t => (t.priority || "").toLowerCase() === filterPriorityLower);
    }

    return filtered;
  }, [tasks, searchQuery, statusFilter, priorityFilter, loading]);
  
  const epicFilteredTasks = useMemo(() => {
    if (loading && (!filteredTasks || filteredTasks.length === 0)) return [];
    if (!filteredTasks || filteredTasks.length === 0) return [];
    if (!selectedEpic || selectedEpic === "all") return filteredTasks;
    return filteredTasks.filter(task => task.epic_id === selectedEpic);
  }, [filteredTasks, selectedEpic, loading]);

  const tasksInSprints = useMemo(() => {
    const grouped: Record<string, Task[]> = {};
    sprints.forEach(sprint => {
      grouped[sprint.id] = epicFilteredTasks.filter(task => 
        task.sprint_id === sprint.id || String(task.sprint_id) === String(sprint.id)
      );
    });
    return grouped;
  }, [sprints, epicFilteredTasks]);

  const backlogTasks = useMemo(() => {
    const sprintIds = new Set(sprints.map(s => s.id));
    return epicFilteredTasks.filter(task => {
      if (!task.sprint_id) return true;
      return !sprintIds.has(task.sprint_id) && !sprintIds.has(String(task.sprint_id));
    });
  }, [epicFilteredTasks, sprints]);

  const availableStatuses = useMemo(() => {
    if (availableStatusesFromBackend && availableStatusesFromBackend.length > 0) {
      return availableStatusesFromBackend.map(status => ({
        value: status.name.toLowerCase(),
        label: status.name
      }));
    }
    const statusMap = new Map<string, string>();
    tasks.forEach(task => {
      if (task.status) {
        const lower = task.status.toLowerCase();
        if (!statusMap.has(lower)) statusMap.set(lower, task.status);
      }
    });
    return Array.from(statusMap.entries()).map(([lower, original]) => ({ value: lower, label: original }));
  }, [availableStatusesFromBackend, tasks]);

  const availablePriorities = useMemo(() => {
    if (availablePrioritiesFromBackend && availablePrioritiesFromBackend.length > 0) {
      return availablePrioritiesFromBackend.map(priority => ({
        value: priority.name.toLowerCase(),
        label: priority.name
      }));
    }
    const priorityMap = new Map<string, string>();
    tasks.forEach(task => {
      if (task.priority) {
        const lower = task.priority.toLowerCase();
        if (!priorityMap.has(lower)) priorityMap.set(lower, task.priority);
      }
    });
    return Array.from(priorityMap.entries()).map(([lower, original]) => ({ value: lower, label: original }));
  }, [availablePrioritiesFromBackend, tasks]);

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    const activeId = String(active.id);
    
    if (activeId.startsWith('task-')) {
      const taskId = activeId.replace('task-', '');
      const task = tasks.find(t => String(t.id) === taskId);
      const sourceSprintId = task?.sprint_id ? String(task.sprint_id) : null;
      setDragState({ type: 'task', id: taskId, sourceSprintId });
    }
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { over } = event;
    if (!over) {
      setOverSprintId(null);
      setOverTaskId(null);
      return;
    }

    const overId = String(over.id);
    
    // Direct drop zone
    if (overId.startsWith('sprint-')) {
      setOverSprintId(overId.replace('sprint-', ''));
      setOverTaskId(null);
      return;
    }
    
    if (overId === 'backlog') {
      setOverSprintId('backlog');
      setOverTaskId(null);
      return;
    }
    
    // If hovering over a task, find which sprint it belongs to
    if (overId.startsWith('task-')) {
      const taskId = overId.replace('task-', '');
      const task = tasks.find(t => String(t.id) === taskId);
      
      if (task) {
        setOverTaskId(taskId);
        if (task.sprint_id) {
          setOverSprintId(String(task.sprint_id));
        } else {
          setOverSprintId('backlog');
        }
        return;
      }
    }
    
    setOverSprintId(null);
    setOverTaskId(null);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setDragState({ type: null, id: null });
    setOverSprintId(null);
    setOverTaskId(null);

    if (!over || dragState.type !== 'task' || !dragState.id) return;

    const overId = String(over.id);
    const taskId = dragState.id;
    const draggedTask = tasks.find(t => String(t.id) === taskId);
    if (!draggedTask) return;

    let targetSprintId: string | null = null;

    // Determine target sprint
    if (overId === "backlog") {
      targetSprintId = null; // Moving to backlog
    } else if (overId.startsWith("sprint-")) {
      targetSprintId = overId.replace("sprint-", "");
    } else if (overId.startsWith("task-")) {
      // Dropped on another task - find which sprint it belongs to
      const targetTaskId = overId.replace("task-", "");
      const targetTask = tasks.find(t => String(t.id) === targetTaskId);
      if (targetTask) {
        targetSprintId = targetTask.sprint_id ? String(targetTask.sprint_id) : null;
      }
    }

    // Handle move to backlog
    if (targetSprintId === null) {
      if (!draggedTask.sprint_id) return; // Already in backlog
      try {
        await handleMoveTaskToBacklog(taskId);
      } catch (error) {
        console.error("Failed to move task to backlog:", error);
      }
      return;
    }

    // Handle move to sprint
    if (String(draggedTask.sprint_id) === targetSprintId) return; // Already in this sprint

    try {
      await handleAssignTaskToSprint(taskId, targetSprintId);
    } catch (error) {
      console.error("Failed to assign task to sprint:", error);
    }
  };

  const draggedTask = useMemo(() => {
    if (dragState.type !== 'task' || !dragState.id) return null;
    return tasks.find(t => String(t.id) === dragState.id);
  }, [dragState, tasks]);

  const isLoading = loadingState.filterData.loading || (shouldLoadTasks && loading);
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">Loading backlog...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 px-4">
        <div className="text-red-500 font-semibold mb-2">Error Loading Tasks</div>
        <div className="text-red-400 text-sm text-center max-w-2xl">{error.message}</div>
      </div>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="flex h-full">
        {/* Left Sidebar - Epics */}
        <EpicSidebar 
          onEpicSelect={setSelectedEpic}
          selectedEpic={selectedEpic}
          tasks={tasks}
          projectId={projectIdForSprints}
          onEpicCreate={() => {
            window.dispatchEvent(new CustomEvent("pm_refresh", { detail: { type: "pm_refresh" } }));
          }}
        />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col overflow-hidden bg-gray-50 dark:bg-gray-900">
          {/* Top Header with Filters */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Backlog</h2>
            </div>

            {/* Filters */}
            <div className="flex flex-col md:flex-row gap-3">
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
              {(availableStatuses.length > 0 || availablePriorities.length > 0) && (
                <div className="flex gap-2">
                  {availableStatuses.length > 0 && (
                    <Select value={statusFilter} onValueChange={setStatusFilter}>
                      <SelectTrigger className="w-[140px]">
                        <Filter className="w-4 h-4 mr-2" />
                        <SelectValue placeholder="Status" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Status</SelectItem>
                        {availableStatuses.map(({ value, label }) => (
                          <SelectItem key={value} value={value}>{label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                  {availablePriorities.length > 0 && (
                    <Select value={priorityFilter} onValueChange={setPriorityFilter}>
                      <SelectTrigger className="w-[140px]">
                        <SelectValue placeholder="Priority" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Priority</SelectItem>
                        {availablePriorities.map(({ value, label }) => (
                          <SelectItem key={value} value={value}>{label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>
              )}
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
              <div className="max-w-5xl mx-auto">
                {/* Active sprints */}
                {sprints.filter(s => s.status === "active").length > 0 && (
                  <div className="mb-6">
                    <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3 px-1">
                      Active Sprints
                    </h2>
                    {sprints
                      .filter(s => s.status === "active")
                      .map((sprint) => (
                        <SprintSection
                          key={sprint.id}
                          sprint={sprint}
                          tasks={tasksInSprints[sprint.id] ?? []}
                          onTaskClick={handleTaskClick}
                          epicsMap={epicsMap}
                          isOver={overSprintId === sprint.id}
                          draggedTaskId={dragState.id}
                        />
                      ))}
                  </div>
                )}
                
                {/* Future sprints */}
                {sprints.filter(s => s.status === "future").length > 0 && (
                  <div className="mb-6">
                    <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3 px-1">
                      Future Sprints
                    </h2>
                    {sprints
                      .filter(s => s.status === "future")
                      .map((sprint) => (
                        <SprintSection
                          key={sprint.id}
                          sprint={sprint}
                          tasks={tasksInSprints[sprint.id] ?? []}
                          onTaskClick={handleTaskClick}
                          epicsMap={epicsMap}
                          isOver={overSprintId === sprint.id}
                          draggedTaskId={dragState.id}
                        />
                      ))}
                  </div>
                )}
                
                {/* Backlog */}
                <div className="mb-6">
                  <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3 px-1">
                    Backlog
                  </h2>
                  <BacklogSection
                    tasks={backlogTasks}
                    onTaskClick={handleTaskClick}
                    epicsMap={epicsMap}
                    isOver={overSprintId === 'backlog'}
                    draggedTaskId={dragState.id}
                  />
                </div>

                {/* Closed sprints */}
                {sprints.filter(s => s.status === "closed").length > 0 && (
                  <div className="mb-6">
                    <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3 px-1">
                      Closed Sprints
                    </h2>
                    {sprints
                      .filter(s => s.status === "closed")
                      .map((sprint) => (
                        <SprintSection
                          key={sprint.id}
                          sprint={sprint}
                          tasks={tasksInSprints[sprint.id] ?? []}
                          onTaskClick={handleTaskClick}
                          epicsMap={epicsMap}
                          isOver={overSprintId === sprint.id}
                          draggedTaskId={dragState.id}
                        />
                      ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <DragOverlay>
        {draggedTask ? (
          <div className="p-3 bg-white dark:bg-gray-800 rounded-lg border-2 border-blue-400 shadow-2xl opacity-95 max-w-md">
            <div className="font-medium text-sm text-gray-900 dark:text-white line-clamp-2">
              {draggedTask.title}
            </div>
            {draggedTask.priority && (
              <span className="inline-block mt-1 px-2 py-0.5 text-xs font-medium rounded bg-blue-100 text-blue-800">
                {draggedTask.priority}
              </span>
            )}
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
        projectId={projectIdForSprints}
      />
    </DndContext>
  );
}
