// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import type { DragEndEvent, DragStartEvent } from "@dnd-kit/core";
import { DndContext, DragOverlay, PointerSensor, closestCenter, useDroppable, useSensor, useSensors } from "@dnd-kit/core";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { ChevronDown, ChevronRight, Filter, GripVertical, Search, X } from "lucide-react";
import { useMemo, useState, useEffect } from "react";

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

// Task card component with drag handle
function TaskCard({ task, onClick, epic }: { task: Task; onClick: () => void; epic?: Epic }) {
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
        <div className="flex items-center gap-2">
          <div className="text-sm font-medium text-gray-900 dark:text-white truncate flex-1">
          {task.title}
          </div>
          {epic && (
            <span className="px-2 py-0.5 text-xs font-medium rounded shrink-0 flex items-center gap-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600">
              {epic.color && <div className={`w-2 h-2 rounded-full ${epic.color}`}></div>}
              <span className="truncate max-w-[120px]">{epic.name}</span>
            </span>
          )}
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

// Epic sidebar component
function EpicSidebar({ 
  onEpicSelect, 
  tasks,
  onTaskUpdate: _onTaskUpdate,
  projectId,
  onEpicCreate
}: { 
  onEpicSelect: (epicId: string | null) => void;
  tasks: Task[];
  onTaskUpdate: (taskId: string, updates: Partial<Task>) => Promise<void>;
  projectId: string | null | undefined;
  onEpicCreate?: () => void;
}) {
  const [selectedEpic, setSelectedEpic] = useState<string | null>("all");
  const [expandedEpics, setExpandedEpics] = useState<Set<string>>(new Set());
  
  // Fetch epics from backend
  const { epics, loading: epicsLoading } = useEpics(projectId);

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

  return (
    <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col h-full">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-gray-900 dark:text-white">EPICS</h3>
        </div>
        <CreateEpicDialog projectId={projectId} onEpicCreated={onEpicCreate} />
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

        {epicsLoading ? (
          <div className="p-2 text-sm text-gray-500 dark:text-gray-400">
            Loading epics...
          </div>
        ) : epics.length > 0 ? (
          epics.map((epic) => (
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
          ))
        ) : (
          <div className="p-2 text-sm text-gray-500 dark:text-gray-400">
            No epics found
          </div>
        )}

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
function SprintSection({ sprint, tasks, onTaskClick, epicsMap }: { sprint: { id: string; name: string; start_date?: string; end_date?: string; status: string }; tasks: Task[]; onTaskClick: (task: Task) => void; epicsMap?: Map<string, Epic> }) {
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
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-gray-900 dark:text-white">{sprint.name}</h3>
              {isActive && (
                <span className="px-1.5 py-0.5 text-xs font-medium rounded bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200">
                  Active
                </span>
              )}
              {isClosed && (
                <span className="px-1.5 py-0.5 text-xs font-medium rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                  Closed
                </span>
              )}
              {isFuture && (
                <span className="px-1.5 py-0.5 text-xs font-medium rounded bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200">
                  Future
                </span>
              )}
            </div>
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
              <TaskCard 
                key={task.id} 
                task={task} 
                onClick={() => onTaskClick(task)} 
                epic={task.epic_id && epicsMap ? epicsMap.get(task.epic_id) : undefined}
              />
            ))}
            {isOver && (
              <div className="border-2 border-dashed border-blue-400 bg-blue-50 dark:bg-blue-900/40 rounded-lg p-4 text-center text-sm text-blue-600 dark:text-blue-300 font-medium">
                Drop here
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Backlog section component
function BacklogSection({ tasks, onTaskClick, epicsMap }: { tasks: Task[]; onTaskClick: (task: Task) => void; epicsMap?: Map<string, Epic> }) {
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
              <TaskCard 
                key={task.id} 
                task={task} 
                onClick={() => onTaskClick(task)} 
                epic={task.epic_id && epicsMap ? epicsMap.get(task.epic_id) : undefined}
              />
            ))}
            {isOver && (
              <div className="border-2 border-dashed border-blue-400 bg-blue-50 dark:bg-blue-900/40 rounded-lg p-4 text-center text-sm text-blue-600 dark:text-blue-300 font-medium">
                Drop here to remove from sprint
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function BacklogView() {
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [selectedEpic, setSelectedEpic] = useState<string | null>(null);
  
  // Use the new useProjectData hook for cleaner project handling
  const { activeProjectId, activeProject, projectIdForData: projectIdForSprints, projects } = useProjectData();
  
  // Log when projectIdForSprints changes
  useEffect(() => {
    debug.project('projectIdForSprints changed', { projectIdForSprints, activeProjectId, activeProjectId: activeProject?.id });
  }, [projectIdForSprints, activeProjectId, activeProject?.id]);
  
  // Reset filters when project changes
  useEffect(() => {
    setSearchQuery("");
    setStatusFilter("all");
    setPriorityFilter("all");
    setSelectedEpic(null);
    // Also reset when projectIdForSprints changes to handle JIRA projects
  }, [activeProject?.id, projectIdForSprints]);
  
  // Get loading state from context
  const { state: loadingState, setTasksState } = usePMLoading();
  
  // Only load tasks when filter data is ready (Step 3: after all requirements loaded)
  // IMPORTANT: Use projectIdForSprints directly, not conditional on shouldLoadTasks
  // This prevents the projectId from flipping between valid and undefined, which causes
  // useTasks to restart the effect and mark previous fetches as stale
  // useTasks will handle the loading state internally
  const shouldLoadTasks = loadingState.canLoadTasks && projectIdForSprints;
  
  // Fetch tasks for the active project - use full project ID (with provider_id)
  // Always pass projectIdForSprints (even if shouldLoadTasks is false) to prevent
  // the projectId from changing from valid -> undefined -> valid, which causes race conditions
  // The useTasks hook will handle the case when projectId is null/undefined
  const { tasks: allTasks, loading, error, refresh: refreshTasks } = useTasks(projectIdForSprints ?? undefined);
  
  // Sync tasks state with loading context
  // Only sync when we actually have a project and should be loading
  useEffect(() => {
    debug.state('Syncing tasks state', { shouldLoadTasks, projectIdForSprints, allTasksLength: allTasks.length, loading });
    
    if (shouldLoadTasks) {
      setTasksState({
        loading,
        error,
        data: allTasks,
      });
      debug.state('Synced tasks state', { tasksCount: allTasks.length, loading });
    } else {
      // Don't clear the state immediately - keep it until we have a new project
      // This prevents flickering when switching projects
      if (!projectIdForSprints) {
        setTasksState({
          loading: false,
          error: null,
          data: null,
        });
        debug.state('Cleared tasks state (no project)');
      } else {
        // Project exists but canLoadTasks is false - keep current state
        debug.state('Keeping tasks state (waiting for canLoadTasks)');
      }
    }
  }, [shouldLoadTasks, loading, error, allTasks, setTasksState, projectIdForSprints]);
  
  // Use the new useTaskFiltering hook for cleaner task filtering logic
  const { tasks } = useTaskFiltering({
    allTasks,
    projectId: projectIdForSprints,
    activeProject,
    loading,
  });
  
  // Debug logging for task filtering
  useEffect(() => {
    debug.state('TASK STATE UPDATE', {
      allTasksLength: allTasks.length,
      filteredTasksLength: tasks.length,
      projectIdForSprints,
      activeProjectId: activeProject?.id,
      loading,
      shouldLoadTasks,
      allTasksIds: allTasks.length > 0 ? allTasks.slice(0, 5).map(t => t.id) : [],
      filteredTasksIds: tasks.length > 0 ? tasks.slice(0, 5).map(t => t.id) : [],
    });
    if (allTasks.length > 0 && tasks.length === 0) {
      debug.warn('WARNING: Tasks loaded but filtered out', { allTasksLength: allTasks.length, filteredTasksLength: tasks.length });
    }
  }, [allTasks.length, tasks.length, projectIdForSprints, activeProject?.id, loading, shouldLoadTasks]);
  
  // Fetch all sprints (active, closed, future) - no state filter to show all
  const { sprints, loading: sprintsLoading } = useSprints(projectIdForSprints ?? "", undefined);
  // Fetch epics for the active project
  const { epics } = useEpics(projectIdForSprints ?? undefined);
  // Fetch statuses and priorities from backend
  const { statuses: availableStatusesFromBackend } = useStatuses(projectIdForSprints ?? undefined, "task");
  const { priorities: availablePrioritiesFromBackend } = usePriorities(projectIdForSprints ?? undefined);
  
  // Create a map of epic_id -> epic for quick lookup
  const epicsMap = useMemo(() => {
    const map = new Map<string, Epic>();
    epics.forEach(epic => {
      map.set(epic.id, epic);
    });
    return map;
  }, [epics]);
  
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const handleTaskClick = (task: Task) => {
    // Always set the task before opening modal to ensure correct task is shown
    setSelectedTask(task);
    setIsModalOpen(true);
  };

  const handleUpdateTask = async (taskId: string, updates: Partial<Task>) => {
    try {
      if (!projectIdForSprints) {
        throw new Error("Project ID is required to update a task");
      }
      
      const url = new URL(resolveServiceURL(`pm/tasks/${taskId}`));
      url.searchParams.set('project_id', projectIdForSprints);
      
      console.log(`[handleUpdateTask] Updating task ${taskId}`);
      console.log(`[handleUpdateTask] URL: ${url.toString()}`);
      console.log(`[handleUpdateTask] Updates:`, updates);
      
      const response = await fetch(url.toString(), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      
      console.log(`[handleUpdateTask] Response status: ${response.status} ${response.statusText}`);
      
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
        console.error(`[handleUpdateTask] Response status: ${response.status}`);
        console.error(`[handleUpdateTask] Response text: ${errorText}`);
        console.error(`[handleUpdateTask] Full URL attempted: ${url}`);
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
      
      // Refresh the task list without clearing (to prevent flash) and update selectedTask
      refreshTasks(false);
    } catch (error) {
      console.error("[handleUpdateTask] Failed to update task:", error);
      if (error instanceof TypeError && error.message === "Failed to fetch") {
        console.error("[handleUpdateTask] Network error - check if server is running and CORS is configured");
      }
      throw error;
    }
  };

  const handleAssignTaskToEpic = async (taskId: string, epicId: string) => {
    if (!projectIdForSprints) {
      throw new Error('No project selected');
    }
    try {
      // Match exact pattern from use-tasks.ts - resolveServiceURL handles it correctly
      const url = resolveServiceURL(`pm/projects/${projectIdForSprints}/tasks/${taskId}/assign-epic`);
      
      console.log(`[handleAssignTaskToEpic] Assigning task ${taskId} to epic ${epicId} in project ${projectIdForSprints}`);
      console.log(`[handleAssignTaskToEpic] URL: ${url}`);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ epic_id: epicId }),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `Failed to assign task to epic: ${response.status} ${response.statusText}`;
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || errorMessage;
        } catch {
          if (errorText) {
            errorMessage = errorText;
          }
        }
        console.error(`[handleAssignTaskToEpic] Error: ${errorMessage}`);
        console.error(`[handleAssignTaskToEpic] Response status: ${response.status}`);
        console.error(`[handleAssignTaskToEpic] Response text: ${errorText}`);
        console.error(`[handleAssignTaskToEpic] Full URL attempted: ${url}`);
        throw new Error(errorMessage);
      }
      
      window.dispatchEvent(new CustomEvent("pm_refresh", { 
        detail: { type: "pm_refresh" } 
      }));
    } catch (error) {
      console.error("Failed to assign task to epic:", error);
      throw error;
    }
  };

  const handleRemoveTaskFromEpic = async (taskId: string) => {
    if (!projectIdForSprints) {
      throw new Error('No project selected');
    }
    try {
      // Match exact pattern from use-tasks.ts - resolveServiceURL handles it correctly
      const url = resolveServiceURL(`pm/projects/${projectIdForSprints}/tasks/${taskId}/remove-epic`);
      
      console.log(`[handleRemoveTaskFromEpic] Removing task ${taskId} from epic in project ${projectIdForSprints}`);
      console.log(`[handleRemoveTaskFromEpic] URL: ${url}`);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `Failed to remove task from epic: ${response.status} ${response.statusText}`;
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || errorMessage;
        } catch {
          if (errorText) {
            errorMessage = errorText;
          }
        }
        console.error(`[handleRemoveTaskFromEpic] Error: ${errorMessage}`);
        console.error(`[handleRemoveTaskFromEpic] Response status: ${response.status}`);
        console.error(`[handleRemoveTaskFromEpic] Response text: ${errorText}`);
        console.error(`[handleRemoveTaskFromEpic] Full URL attempted: ${url}`);
        throw new Error(errorMessage);
      }
      
      window.dispatchEvent(new CustomEvent("pm_refresh", { 
        detail: { type: "pm_refresh" } 
      }));
    } catch (error) {
      console.error("Failed to remove task from epic:", error);
      throw error;
    }
  };

  const handleAssignTaskToSprint = async (taskId: string, sprintId: string) => {
    if (!projectIdForSprints) {
      throw new Error('No project selected');
    }
    try {
      const url = resolveServiceURL(`pm/projects/${projectIdForSprints}/tasks/${taskId}/assign-sprint`);
      
      console.log(`[handleAssignTaskToSprint] Assigning task ${taskId} to sprint ${sprintId} in project ${projectIdForSprints}`);
      console.log(`[handleAssignTaskToSprint] URL: ${url}`);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sprint_id: sprintId }),
      });
      
      console.log(`[handleAssignTaskToSprint] Response status: ${response.status} ${response.statusText}`);
      
      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `Failed to assign task to sprint: ${response.status} ${response.statusText}`;
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || errorMessage;
        } catch {
          if (errorText) {
            errorMessage = errorText;
          }
        }
        console.error(`[handleAssignTaskToSprint] Error: ${errorMessage}`);
        console.error(`[handleAssignTaskToSprint] Response status: ${response.status}`);
        console.error(`[handleAssignTaskToSprint] Response text: ${errorText}`);
        console.error(`[handleAssignTaskToSprint] Full URL attempted: ${url}`);
        throw new Error(errorMessage);
      }
      
      const result = await response.json();
      console.log(`[handleAssignTaskToSprint] Success:`, result);
      
      window.dispatchEvent(new CustomEvent("pm_refresh", { 
        detail: { type: "pm_refresh" } 
      }));
    } catch (error) {
      console.error("Failed to assign task to sprint:", error);
      throw error;
    }
  };

  const handleMoveTaskToBacklog = async (taskId: string) => {
    if (!projectIdForSprints) {
      throw new Error('No project selected');
    }
    try {
      const url = resolveServiceURL(`pm/projects/${projectIdForSprints}/tasks/${taskId}/move-to-backlog`);
      
      console.log(`[handleMoveTaskToBacklog] Moving task ${taskId} to backlog in project ${projectIdForSprints}`);
      console.log(`[handleMoveTaskToBacklog] URL: ${url}`);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      
      console.log(`[handleMoveTaskToBacklog] Response status: ${response.status} ${response.statusText}`);
      
      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `Failed to move task to backlog: ${response.status} ${response.statusText}`;
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || errorMessage;
        } catch {
          if (errorText) {
            errorMessage = errorText;
          }
        }
        console.error(`[handleMoveTaskToBacklog] Error: ${errorMessage}`);
        console.error(`[handleMoveTaskToBacklog] Response status: ${response.status}`);
        console.error(`[handleMoveTaskToBacklog] Response text: ${errorText}`);
        console.error(`[handleMoveTaskToBacklog] Full URL attempted: ${url}`);
        throw new Error(errorMessage);
      }
      
      const result = await response.json();
      console.log(`[handleMoveTaskToBacklog] Success:`, result);
      
      window.dispatchEvent(new CustomEvent("pm_refresh", { 
        detail: { type: "pm_refresh" } 
      }));
    } catch (error) {
      console.error("Failed to move task to backlog:", error);
      throw error;
    }
  };

  // Filter tasks
  const filteredTasks = useMemo(() => {
    debug.filter('filteredTasks useMemo running', { searchQuery, tasksLength: tasks?.length, loading });
    
    // Return empty array only if we're loading AND have no tasks yet (to prevent flash of stale data)
    // If we have tasks, always filter them even if loading is true (for real-time filtering)
    if (loading && (!tasks || tasks.length === 0)) {
      debug.filter('Returning empty array (loading with no tasks)');
      return [];
    }
    
    // If we have no tasks at all, return empty
    if (!tasks || tasks.length === 0) {
      debug.filter('Returning empty array (no tasks)');
      return [];
    }
    
    let filtered = [...tasks]; // Create a copy to avoid mutating original

    // Search filter - search in title and description only
    const trimmedQuery = (searchQuery || "").trim();
    debug.filter('Filtering tasks', { searchQuery: trimmedQuery, totalTasks: tasks.length, loading });
    if (trimmedQuery) {
      const query = trimmedQuery.toLowerCase();
      const beforeCount = filtered.length;
      filtered = filtered.filter(t => {
        if (!t) return false;
        const title = (t.title || "").toLowerCase();
        const description = (t.description || "").toLowerCase();
        // Search in title and description only
        const matches = title.includes(query) || description.includes(query);
        return matches;
      });
      debug.filter('After search filter', { filteredCount: filtered.length, wasCount: beforeCount, query: trimmedQuery });
    } else {
      debug.filter('No search query, skipping search filter');
    }

    // Status filter - match by status name (case-insensitive)
    if (statusFilter && statusFilter !== "all") {
      const filterStatusLower = statusFilter.toLowerCase();
      const beforeCount = filtered.length;
      filtered = filtered.filter(t => {
        const taskStatus = (t.status || "").toLowerCase();
        return taskStatus === filterStatusLower;
      });
      debug.filter('After status filter', { filteredCount: filtered.length, wasCount: beforeCount });
    }

    // Priority filter - match by exact priority (case-insensitive)
    if (priorityFilter && priorityFilter !== "all") {
      const filterPriorityLower = priorityFilter.toLowerCase();
      const beforeCount = filtered.length;
      filtered = filtered.filter(t => {
        const taskPriority = (t.priority || "").toLowerCase();
        return taskPriority === filterPriorityLower;
      });
      debug.filter('After priority filter', { filteredCount: filtered.length, wasCount: beforeCount });
    }

    debug.filter('Final filtered tasks', { filteredCount: filtered.length, originalCount: tasks.length });
    return filtered;
  }, [tasks, searchQuery, statusFilter, priorityFilter, loading]);
  
  // Debug: Log when searchQuery changes
  useEffect(() => {
    debug.filter('searchQuery state changed', { searchQuery });
  }, [searchQuery]);

  // Use statuses and priorities from backend, with fallback to task data
  const availableStatuses = useMemo(() => {
    if (availableStatusesFromBackend && availableStatusesFromBackend.length > 0) {
      // Use backend statuses, store lowercase value for matching
      return availableStatusesFromBackend.map(status => ({
        value: status.name.toLowerCase(),
        label: status.name
      }));
    }
    // Fallback: extract from tasks if backend doesn't have statuses
    const statusMap = new Map<string, string>(); // lowercase -> original case
    tasks.forEach(task => {
      if (task.status) {
        const lower = task.status.toLowerCase();
        if (!statusMap.has(lower)) {
          statusMap.set(lower, task.status);
        }
      }
    });
    return Array.from(statusMap.entries()).map(([lower, original]) => ({ value: lower, label: original }));
  }, [availableStatusesFromBackend, tasks]);

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

  // Filter tasks by selected epic
  const epicFilteredTasks = useMemo(() => {
    debug.filter('Epic filtering', { filteredTasksLength: filteredTasks?.length, selectedEpic, loading });
    
    // Return empty array only if loading AND no tasks yet (to prevent flash)
    // But allow filtering if we have tasks, even if loading is true (for real-time filtering)
    if (loading && (!filteredTasks || filteredTasks.length === 0)) {
      debug.filter('Returning empty (loading with no filteredTasks)');
      return [];
    }
    if (!filteredTasks || filteredTasks.length === 0) {
      debug.filter('Returning empty (no filteredTasks)');
      return [];
    }
    
    if (!selectedEpic) {
      debug.filter('No epic filter, returning all filteredTasks', { count: filteredTasks.length });
      return filteredTasks;
    }
    if (selectedEpic === "all") {
      debug.filter('Epic filter is "all", returning all filteredTasks', { count: filteredTasks.length });
      return filteredTasks;
    }
    // Filter by epic_id
    const epicFiltered = filteredTasks.filter(task => task.epic_id === selectedEpic);
    debug.filter('Epic filtered', { filteredCount: epicFiltered.length, epicId: selectedEpic });
    return epicFiltered;
  }, [filteredTasks, selectedEpic, loading]);

  // Group tasks by sprint
  const tasksInSprints = useMemo(() => {
    const grouped: Record<string, Task[]> = {};
    
    // Debug: Log sprint IDs and task sprint_ids
    const sprintInfo = sprints.map(s => ({ id: s.id, name: s.name, id_type: typeof s.id }));
    const taskInfo = epicFilteredTasks.map(t => ({ id: t.id, title: t.title, sprint_id: t.sprint_id, sprint_id_type: typeof t.sprint_id }));
    debug.filter('Sprint IDs', { sprintInfo });
    debug.filter('Task sprint_ids', { taskInfo });
    
    sprints.forEach(sprint => {
      const matchingTasks = epicFilteredTasks.filter(task => {
        const matches = task.sprint_id === sprint.id || 
                       String(task.sprint_id) === String(sprint.id) ||
                       task.sprint_id?.toString() === sprint.id?.toString();
        if (matches && task.sprint_id !== sprint.id) {
          debug.filter('Type mismatch fixed', { taskSprintId: task.sprint_id, taskSprintIdType: typeof task.sprint_id, sprintId: sprint.id, sprintIdType: typeof sprint.id });
        }
        return matches;
      });
      grouped[sprint.id] = matchingTasks;
      if (matchingTasks.length > 0) {
        debug.filter(`Sprint "${sprint.name}" tasks`, { sprintId: sprint.id, count: matchingTasks.length, taskIds: matchingTasks.map(t => t.id) });
      } else {
        debug.filter(`Sprint "${sprint.name}" - No matching tasks`, { sprintId: sprint.id });
        // Show why tasks don't match
        const tasksWithSprintId = epicFilteredTasks.filter(t => t.sprint_id);
        if (tasksWithSprintId.length > 0) {
          debug.filter('Found tasks with sprint_id', { count: tasksWithSprintId.length, tasks: tasksWithSprintId.map(t => ({ id: t.id, sprint_id: t.sprint_id, sprint_id_type: typeof t.sprint_id })) });
        }
      }
    });
    
    const groupedInfo = Object.keys(grouped).map(key => ({ 
      sprintId: key, 
      count: grouped[key]?.length ?? 0,
      taskIds: grouped[key]?.map(t => t.id) ?? []
    }));
    debug.filter('Grouped tasks', { groupedInfo });
    return grouped;
  }, [sprints, epicFilteredTasks]);

  // Backlog tasks (tasks not in any sprint)
  const backlogTasks = useMemo(() => {
    const sprintIds = new Set(sprints.map(s => s.id));
    const backlog = epicFilteredTasks.filter(task => {
      const hasSprintId = task.sprint_id && (sprintIds.has(task.sprint_id) || 
                                             sprintIds.has(String(task.sprint_id)) ||
                                             Array.from(sprintIds).some(sid => String(sid) === String(task.sprint_id)));
      return !hasSprintId;
    });
    debug.filter('Backlog tasks', { backlogCount: backlog.length, totalTasks: epicFilteredTasks.length });
    const orphanedTasks = epicFilteredTasks.filter(t => t.sprint_id && !sprintIds.has(t.sprint_id) && !Array.from(sprintIds).some(sid => String(sid) === String(t.sprint_id))).map(t => ({ id: t.id, title: t.title, sprint_id: t.sprint_id }));
    if (orphanedTasks.length > 0) {
      debug.filter('Tasks with sprint_id but not in sprints', { orphanedTasks });
    }
    return backlog;
  }, [epicFilteredTasks, sprints]);

  // Handle drag end - assign task to sprint, epic, or remove from sprint
  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over) return;

    const taskId = active.id as string;
    const overId = over.id as string;
    const draggedTask = tasks.find(t => String(t.id) === String(taskId));

    if (!draggedTask) return;

    // Check if dropped on backlog (move to backlog)
    if (overId === "backlog") {
      // Skip if already in backlog (no sprint assigned)
      if (!draggedTask.sprint_id) {
        return;
      }
      try {
        await handleMoveTaskToBacklog(taskId);
      } catch (error) {
        console.error("Failed to move task to backlog:", error);
      }
      return;
    }

    // Check if dropped on an epic
    if (typeof overId === "string" && overId.startsWith("epic-")) {
      const epicId = overId.replace("epic-", "");
      
      // Handle "all" or "none" epic drops - remove from epic
      if (epicId === "all" || epicId === "none") {
        // Skip if already has no epic
        if (!draggedTask.epic_id) {
          return;
        }
        try {
          await handleRemoveTaskFromEpic(taskId);
        } catch (error) {
          console.error("Failed to remove task from epic:", error);
        }
      } else {
        // Skip if already in this epic
        if (String(draggedTask.epic_id) === String(epicId)) {
          return;
        }
        // Assign to epic using dedicated API endpoint
        try {
          await handleAssignTaskToEpic(taskId, epicId);
        } catch (error) {
          console.error("Failed to assign task to epic:", error);
        }
      }
      return;
    }

    // Check if dropped on a sprint
    if (typeof overId === "string" && overId.startsWith("sprint-")) {
      const sprintId = overId.replace("sprint-", "");
      
      // Skip if already in this sprint
      if (String(draggedTask.sprint_id) === String(sprintId)) {
        return;
      }

      try {
        await handleAssignTaskToSprint(taskId, sprintId);
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

  // Show loading state if filter data is not ready or tasks are loading
  const isLoading = loadingState.filterData.loading || (shouldLoadTasks && loading);
  useEffect(() => {
    debug.state('Loading check', {
      filterDataLoading: loadingState.filterData.loading,
      shouldLoadTasks,
      loading,
      isLoading,
      allTasksLength: allTasks.length,
      tasksLength: tasks.length,
    });
  }, [isLoading, loadingState.filterData.loading, shouldLoadTasks, loading, allTasks.length, tasks.length]);
  
  if (isLoading) {
    debug.render('Showing loading state', {
      filterDataLoading: loadingState.filterData.loading,
      shouldLoadTasks,
      loading,
    });
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
          projectId={projectIdForSprints}
          onEpicCreate={() => {
            window.dispatchEvent(new CustomEvent("pm_refresh", { 
              detail: { type: "pm_refresh" } 
            }));
          }}
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
                    onChange={(e) => {
                      const newValue = e.target.value;
                      console.log("[BacklogView] Input onChange triggered. Current searchQuery:", searchQuery, "New value:", newValue);
                      setSearchQuery(newValue);
                      // Force immediate re-render
                      console.log("[BacklogView] setSearchQuery called with:", newValue);
                    }}
                    onInput={(e) => {
                      // Additional logging for input events
                      const newValue = (e.target as HTMLInputElement).value;
                      console.log("[BacklogView] Input onInput event. Value:", newValue);
                    }}
                    className="pl-10"
                  />
                </div>
              </div>
              {availableStatuses.length > 0 || availablePriorities.length > 0 ? (
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
                          <SelectItem key={value} value={value}>
                            {label}
                          </SelectItem>
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
                          <SelectItem key={value} value={value}>
                            {label}
                          </SelectItem>
                        ))}
                   </SelectContent>
                 </Select>
                  )}
              </div>
              ) : null}
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
                {/* Sprints - stacked vertically, grouped by state */}
                {/* Active sprints first */}
                {sprints.filter(s => s.status === "active").length > 0 && (
                  <div className="mb-6">
                    <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 px-1">
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
                        />
                      ))}
                  </div>
                )}
                
                {/* Future sprints */}
                {sprints.filter(s => s.status === "future").length > 0 && (
                  <div className="mb-6">
                    <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 px-1">
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
                        />
                      ))}
                  </div>
                )}
                
                {/* Closed sprints */}
                {sprints.filter(s => s.status === "closed").length > 0 && (
                  <div className="mb-6">
                    <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 px-1">
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
                        />
                      ))}
                  </div>
                )}

                {/* Backlog - at the bottom */}
                <BacklogSection
                  tasks={backlogTasks}
                  onTaskClick={handleTaskClick}
                  epicsMap={epicsMap}
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
        projectId={projectIdForSprints}
      />
    </DndContext>
  );
}

