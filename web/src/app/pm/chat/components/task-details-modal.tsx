// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Edit2, Save, ExternalLink } from "lucide-react";
import { useState, useEffect, useMemo } from "react";

import { Button } from "~/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "~/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Textarea } from "~/components/ui/textarea";
import { useEpics } from "~/core/api/hooks/pm/use-epics";
import { usePriorities } from "~/core/api/hooks/pm/use-priorities";
import { useStatuses } from "~/core/api/hooks/pm/use-statuses";
import type { Task } from "~/core/api/hooks/pm/use-tasks";
import { useUsers } from "~/core/api/hooks/pm/use-users";
import { useProviders } from "~/core/api/hooks/pm/use-providers";
import type { ProviderConfig } from "~/core/api/pm/providers";

interface TaskDetailsModalProps {
  task: Task | null;
  open: boolean;
  onClose: () => void;
  onUpdate?: (taskId: string, updates: Partial<Task>) => Promise<void>;
  projectId?: string | null;
}

export function TaskDetailsModal({ task, open, onClose, onUpdate, projectId }: TaskDetailsModalProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTask, setEditedTask] = useState<Partial<Task> | null>(null);
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null); // Store the task ID being edited
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const { providers } = useProviders();
  
  // Fetch statuses, priorities, epics, and users for the project (hooks must be called before early return)
  const { statuses } = useStatuses(projectId ?? undefined, "task");
  const { priorities, loading: prioritiesLoading, error: prioritiesError } = usePriorities(projectId ?? undefined);
  const { epics } = useEpics(projectId ?? undefined);
  const { users, loading: usersLoading } = useUsers(projectId ?? undefined);
  
  // Log errors only
  useEffect(() => {
    if (prioritiesError) {
      console.error("[TaskDetailsModal] Error loading priorities:", prioritiesError);
    }
  }, [prioritiesError]);

  // Reset state when modal closes or task changes significantly
  useEffect(() => {
    if (!open) {
      // Reset everything when modal closes
      setIsEditing(false);
      setEditedTask(null);
      setEditingTaskId(null);
      setError(null);
      return;
    }
    
    // If task ID changes while we're editing, cancel editing to prevent data corruption
    if (isEditing && task && editingTaskId && task.id !== editingTaskId) {
      console.warn(`[TaskDetailsModal] Task ID changed from ${editingTaskId} to ${task.id} while editing. Canceling edit to prevent data corruption.`);
      setIsEditing(false);
      setEditedTask(null);
      setEditingTaskId(null);
      setError(null);
      return;
    }
    
    // Sync editedTask when task prop changes (if not editing)
    if (!isEditing && task) {
      setEditedTask(null);
      setEditingTaskId(null);
      setError(null);
    }
  }, [task, isEditing, open, editingTaskId]);

  // Get external URL for the task (must be before early return to follow Rules of Hooks)
  const externalUrl = useMemo(() => {
    if (!task || !projectId) return null;
    
    // Skip mock projects
    if (projectId.startsWith("mock:")) {
      return null;
    }

    // Parse project ID to get provider ID
    const parts = projectId.split(":");
    if (parts.length < 2) return null;
    
    const providerId = parts[0];
    const provider = providers.find(p => p.id === providerId);
    
    if (!provider?.base_url) return null;

    // Extract task ID (might be in format "provider_id:task_id" or just "task_id")
    let taskId = task.id;
    if (task.id.includes(":")) {
      const taskParts = task.id.split(":");
      taskId = taskParts.length > 1 ? taskParts[1] : taskParts[0];
    }

    // Construct URL based on provider type
    const baseUrl = provider.base_url.replace(/\/$/, '');
    switch (provider.provider_type) {
      case "jira":
        // JIRA uses task key format like "PROJ-123"
        return `${baseUrl}/browse/${taskId}`;
      case "openproject":
      case "openproject_v13":
        // OpenProject uses work package ID
        return `${baseUrl}/work_packages/${taskId}`;
      case "clickup":
        // ClickUp uses task ID in URL
        return `${baseUrl.replace('/api/v2', '')}/t/${taskId}`;
      default:
        return null;
    }
  }, [task, projectId, providers]);

  // Helper function to find matching status/priority name (case-insensitive)
  // IMPORTANT: Check longer names first to avoid "high" matching "highest"
  const findMatchingName = (value: string | undefined, options: Array<{ id: string; name: string }>): string | undefined => {
    if (!value) return undefined;
    
    // Sort options by name length (longest first) to prefer longer matches
    // This prevents "high" from matching when looking for "highest"
    const sortedOptions = [...options].sort((a, b) => b.name.length - a.name.length);
    
    // First try exact match
    const exactMatch = sortedOptions.find(opt => opt.name === value);
    if (exactMatch) return exactMatch.name;
    
    // Then try case-insensitive match
    const caseInsensitiveMatch = sortedOptions.find(opt => opt.name.toLowerCase() === value.toLowerCase());
    if (caseInsensitiveMatch) return caseInsensitiveMatch.name;
    
    // Finally try partial match (but only if the option name is at least as long as the value)
    // This prevents "high" from matching when looking for "highest"
    const partialMatch = sortedOptions.find(opt => {
      const optLower = opt.name.toLowerCase();
      const valueLower = value.toLowerCase();
      // Only match if the option name is at least as long as the value (prevents "high" matching "highest")
      if (optLower.length >= valueLower.length) {
        return optLower.includes(valueLower);
      }
      // Or if the value is longer, check if option name is contained in value
      return valueLower.includes(optLower);
    });
    if (partialMatch) return partialMatch.name;
    
    // If no match found, return the original value (will show as-is but may not be selectable)
    return value;
  };


  // Early return if task is null
  if (!task) return null;

  // Get the matching status and priority names for the Select values (task is guaranteed to be non-null here)
  // Ensure values are always strings (never empty string or undefined) to avoid controlled/uncontrolled warnings
  const currentStatusValue = findMatchingName(editedTask?.status ?? task?.status, statuses) ?? editedTask?.status ?? task?.status ?? "__no_status__";
  const currentPriorityValue = findMatchingName(editedTask?.priority ?? task?.priority, priorities) ?? editedTask?.priority ?? task?.priority ?? "__no_priority__";
  
  // Find the epic for this task (handle both string and number ID comparisons)
  const currentEpic = task.epic_id 
    ? epics.find(epic => {
        // Compare as strings to handle type mismatches
        const epicIdStr = String(epic.id);
        const taskEpicIdStr = String(task.epic_id);
        return epicIdStr === taskEpicIdStr;
      })
    : null;

  const handleEdit = () => {
    if (!task) return;
    // Store the task ID when editing starts to prevent updating wrong task
    setEditingTaskId(task.id);
    setEditedTask({ ...task });
    setIsEditing(true);
  };

  const handleSave = async () => {
    if (!editedTask || !onUpdate || !task) return;
    
    // Use the stored task ID instead of the current task.id to prevent updating wrong task
    const taskIdToUpdate = editingTaskId || task.id;
    
    // Verify we're still editing the same task
    if (taskIdToUpdate !== task.id) {
      const errorMessage = "Task changed while editing. Please close and reopen the modal to edit the current task.";
      setError(errorMessage);
      console.error(`[TaskDetailsModal] Task ID mismatch: editing ${taskIdToUpdate} but current task is ${task.id}`);
      setIsEditing(false);
      setEditedTask(null);
      setEditingTaskId(null);
      return;
    }
    
    setError(null);
    setIsSaving(true);
    
    try {
      // Only send fields that can be updated (exclude read-only fields like id, project_name, etc.)
      const updates: Partial<Task> = {};
      if (editedTask.title !== undefined && editedTask.title !== task.title) {
        updates.title = editedTask.title;
      }
      if (editedTask.description !== undefined && editedTask.description !== task.description) {
        updates.description = editedTask.description;
      }
      if (editedTask.status !== undefined && editedTask.status !== task.status) {
        updates.status = editedTask.status;
      }
      if (editedTask.priority !== undefined && editedTask.priority !== task.priority) {
        updates.priority = editedTask.priority;
      }
      if (editedTask.assignee_id !== undefined && editedTask.assignee_id !== task.assignee_id) {
        // Convert empty string to null for unassignment
        updates.assignee_id = editedTask.assignee_id || null;
      }
      
      // Only call update if there are actual changes
      if (Object.keys(updates).length > 0) {
        // Use the stored task ID to ensure we update the correct task
        await onUpdate(taskIdToUpdate, updates);
        // Update the local task state with the changes
        setEditedTask(null);
        setEditingTaskId(null);
        setIsEditing(false);
        // The parent component should update the task, but we'll also update locally
        // to reflect changes immediately in the modal
      } else {
        // No changes, just close editing mode
        setIsEditing(false);
        setEditedTask(null);
        setEditingTaskId(null);
      }
    } catch (error) {
      console.error("Failed to update task:", error);
      const errorMessage = error instanceof Error ? error.message : "Failed to update task. Please check your connection and try again.";
      setError(errorMessage);
      // Don't close the modal on error so user can retry
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditedTask(null);
    setEditingTaskId(null);
  };



  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between">
            <span>Task Details</span>
            {!isEditing ? (
              <Button variant="ghost" size="sm" onClick={handleEdit}>
                <Edit2 className="w-4 h-4 mr-2" />
                Edit
              </Button>
            ) : (
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={handleCancel}>
                  Cancel
                </Button>
                <Button size="sm" onClick={handleSave} disabled={isSaving}>
                  <Save className="w-4 h-4 mr-2" />
                  {isSaving ? "Saving..." : "Save"}
                </Button>
              </div>
            )}
          </DialogTitle>
        </DialogHeader>

        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-3 mb-4">
            <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        <div className="space-y-4 mt-4">
          {/* Title */}
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Title</label>
            {isEditing ? (
              <input
                type="text"
                value={editedTask?.title ?? ""}
                onChange={(e) => setEditedTask({ ...editedTask, title: e.target.value })}
                className="mt-1 w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            ) : (
              <div className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">{task.title}</div>
            )}
          </div>

          {/* Project and Epic */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Project</label>
              <div className="mt-1">
                {task.project_name ? (
                  <span className="inline-flex items-center px-3 py-1.5 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-lg text-sm font-medium">
                    {task.project_name}
                  </span>
                ) : (
                  <span className="text-sm text-gray-500 dark:text-gray-400">Not set</span>
                )}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Epic</label>
              <div className="mt-1">
                {currentEpic ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg text-sm font-medium border border-gray-200 dark:border-gray-600">
                    {currentEpic.color && (
                      <div 
                        className={`w-2 h-2 rounded-full shrink-0 ${currentEpic.color}`}
                      >
                      </div>
                    )}
                    {currentEpic.name}
                  </span>
                ) : (
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {task.epic_id ? `Epic ID: ${task.epic_id} (not found)` : "Not set"}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Description</label>
            {isEditing ? (
              <Textarea
                value={editedTask?.description ?? ""}
                onChange={(e) => setEditedTask({ ...editedTask, description: e.target.value })}
                className="mt-1 min-h-[100px]"
              />
            ) : (
              <div className="mt-1 text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                {task.description ?? "No description"}
              </div>
            )}
          </div>

          {/* Status and Priority */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Status</label>
              {isEditing ? (
                <Select
                  value={currentStatusValue === "__no_status__" && statuses.length > 0 ? statuses[0].name : currentStatusValue}
                  onValueChange={(value) => setEditedTask({ ...editedTask, status: value === "__no_status__" ? undefined : value })}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {statuses.length > 0 ? (
                      <>
                        {statuses.map((status) => (
                          <SelectItem key={status.id} value={status.name}>
                            {status.name}
                          </SelectItem>
                        ))}
                        {/* Add current value if it's not in the list and not a placeholder */}
                        {currentStatusValue && currentStatusValue !== "__no_status__" && !statuses.find(s => s.name === currentStatusValue) && (
                          <SelectItem value={currentStatusValue}>
                            {currentStatusValue}
                          </SelectItem>
                        )}
                      </>
                    ) : (
                      // Fallback to default values if no statuses loaded
                      <>
                        <SelectItem value="todo">To Do</SelectItem>
                        <SelectItem value="in_progress">In Progress</SelectItem>
                        <SelectItem value="review">Review</SelectItem>
                        <SelectItem value="completed">Completed</SelectItem>
                        {/* Add current value if it's not in the defaults and not a placeholder */}
                        {currentStatusValue && currentStatusValue !== "__no_status__" && !["todo", "in_progress", "review", "completed"].includes(currentStatusValue) && (
                          <SelectItem value={currentStatusValue}>
                            {currentStatusValue}
                          </SelectItem>
                        )}
                      </>
                    )}
                  </SelectContent>
                </Select>
              ) : (
                <div className="mt-1">
                  <span className={`px-2 py-1 rounded text-sm ${
                    task.status === "completed" ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200" :
                    task.status === "in_progress" ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200" :
                    "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200"
                  }`}>
                    {task.status}
                  </span>
                </div>
              )}
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Priority</label>
              {isEditing ? (
                <Select
                  value={currentPriorityValue === "__no_priority__" && priorities.length > 0 ? priorities[0].name : currentPriorityValue}
                  onValueChange={(value) => {
                    setEditedTask({ ...editedTask, priority: value === "__no_priority__" ? undefined : value });
                  }}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {priorities.length > 0 ? (
                      <>
                        {priorities.map((priority) => (
                          <SelectItem key={priority.id} value={priority.name}>
                            {priority.name}
                          </SelectItem>
                        ))}
                        {/* Add current value if it's not in the list */}
                        {currentPriorityValue && currentPriorityValue !== "__no_priority__" && !priorities.find(p => p.name === currentPriorityValue) && (
                          <SelectItem value={currentPriorityValue}>
                            {currentPriorityValue}
                          </SelectItem>
                        )}
                      </>
                    ) : prioritiesLoading ? (
                      // Show loading state
                      <SelectItem value="__loading__" disabled>Loading priorities...</SelectItem>
                    ) : (
                      // Fallback: Show current value if available, or generic message
                      <>
                        {currentPriorityValue ? (
                          <SelectItem value={currentPriorityValue}>
                            {currentPriorityValue}
                          </SelectItem>
                        ) : (
                          <SelectItem value="__no_priorities__" disabled>No priorities available</SelectItem>
                        )}
                      </>
                    )}
                  </SelectContent>
                </Select>
              ) : (
                <div className="mt-1">
                  <span className={`px-2 py-1 rounded text-sm ${
                    task.priority === "high" || task.priority === "highest" || task.priority === "critical"
                      ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                      : task.priority === "medium"
                      ? "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200"
                      : "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                  }`}>
                    {task.priority || "None"}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Assignee */}
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Assigned To</label>
            {isEditing ? (
              <Select
                value={(editedTask?.assignee_id ?? task?.assignee_id) || "__unassigned__"}
                onValueChange={(value) => {
                  setEditedTask({ 
                    ...editedTask, 
                    assignee_id: value === "__unassigned__" ? undefined : value 
                  });
                }}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Unassigned" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__unassigned__">Unassigned</SelectItem>
                  {usersLoading ? (
                    <SelectItem value="__loading__" disabled>Loading users...</SelectItem>
                  ) : users.length > 0 ? (
                    users.map((user) => (
                      <SelectItem key={user.id} value={user.id}>
                        {user.name} {user.email ? `(${user.email})` : ""}
                      </SelectItem>
                    ))
                  ) : (
                    <SelectItem value="__no_users__" disabled>No users available</SelectItem>
                  )}
                </SelectContent>
              </Select>
            ) : (
              <div className="mt-1 text-gray-700 dark:text-gray-300">
                {task.assigned_to ? (
                  <span className="px-2 py-1 rounded text-sm bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                    {task.assigned_to}
                  </span>
                ) : (
                  <span className="text-sm text-gray-500 dark:text-gray-400">Unassigned</span>
                )}
              </div>
            )}
          </div>

          {/* Dates */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Start Date</label>
              <div className="mt-1 text-gray-700 dark:text-gray-300">
                {task.start_date ? new Date(task.start_date).toLocaleDateString() : "Not set"}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Due Date</label>
              <div className="mt-1 text-gray-700 dark:text-gray-300">
                {task.due_date ? new Date(task.due_date).toLocaleDateString() : "Not set"}
              </div>
            </div>
          </div>

          {/* Other Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Estimated Hours</label>
              <div className="mt-1 text-gray-700 dark:text-gray-300">
                {task.estimated_hours ? `${task.estimated_hours}h` : "Not set"}
              </div>
            </div>
          </div>

          {/* External Link */}
          {externalUrl && (
            <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  window.open(externalUrl, '_blank', 'noopener,noreferrer');
                }}
                className="inline-flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors cursor-pointer"
              >
                <ExternalLink className="w-4 h-4" />
                <span>View in {(() => {
                  const parts = projectId?.split(":");
                  if (parts && parts.length >= 2) {
                    const providerId = parts[0];
                    const provider = providers.find(p => p.id === providerId);
                    if (provider) {
                      const type = provider.provider_type;
                      if (type === "openproject_v13") return "OpenProject v13";
                      if (type === "openproject") return "OpenProject";
                      return type.toUpperCase();
                    }
                  }
                  return "External Tool";
                })()}</span>
              </button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

