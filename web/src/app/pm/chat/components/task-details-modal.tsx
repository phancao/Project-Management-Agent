// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Edit2, Save } from "lucide-react";
import { useState } from "react";

import { Button } from "~/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "~/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Textarea } from "~/components/ui/textarea";
import type { Task } from "~/core/api/hooks/pm/use-tasks";
import { useStatuses } from "~/core/api/hooks/pm/use-statuses";
import { usePriorities } from "~/core/api/hooks/pm/use-priorities";
import { useEpics } from "~/core/api/hooks/pm/use-epics";

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
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  
  // Fetch statuses, priorities, and epics for the project (hooks must be called before early return)
  const { statuses } = useStatuses(projectId ?? undefined, "task");
  const { priorities } = usePriorities(projectId ?? undefined);
  const { epics } = useEpics(projectId ?? undefined);

  // Early return if task is null
  if (!task) return null;

  // Helper function to find matching status/priority name (case-insensitive)
  const findMatchingName = (value: string | undefined, options: Array<{ id: string; name: string }>): string | undefined => {
    if (!value) return undefined;
    
    // First try exact match
    const exactMatch = options.find(opt => opt.name === value);
    if (exactMatch) return exactMatch.name;
    
    // Then try case-insensitive match
    const caseInsensitiveMatch = options.find(opt => opt.name.toLowerCase() === value.toLowerCase());
    if (caseInsensitiveMatch) return caseInsensitiveMatch.name;
    
    // Finally try partial match
    const partialMatch = options.find(opt => 
      opt.name.toLowerCase().includes(value.toLowerCase()) || 
      value.toLowerCase().includes(opt.name.toLowerCase())
    );
    if (partialMatch) return partialMatch.name;
    
    // If no match found, return the original value (will show as-is but may not be selectable)
    return value;
  };

  // Get the matching status and priority names for the Select values (task is guaranteed to be non-null here)
  const currentStatusValue = findMatchingName(editedTask?.status ?? task?.status, statuses) ?? editedTask?.status ?? task?.status ?? "";
  const currentPriorityValue = findMatchingName(editedTask?.priority ?? task?.priority, priorities) ?? editedTask?.priority ?? task?.priority ?? "";
  
  // Find the epic for this task (handle both string and number ID comparisons)
  const currentEpic = task.epic_id 
    ? epics.find(epic => {
        // Compare as strings to handle type mismatches
        const epicIdStr = String(epic.id);
        const taskEpicIdStr = String(task.epic_id);
        return epicIdStr === taskEpicIdStr;
      })
    : null;
  
  // Debug logging
  if (task.epic_id) {
    console.log('[TaskDetailsModal] Task epic_id:', task.epic_id);
    console.log('[TaskDetailsModal] Available epics:', epics.map(e => ({ id: e.id, name: e.name })));
    console.log('[TaskDetailsModal] Found epic:', currentEpic);
  }

  const handleEdit = () => {
    setEditedTask({ ...task });
    setIsEditing(true);
  };

  const handleSave = async () => {
    if (!editedTask || !onUpdate) return;
    
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
      
      // Only call update if there are actual changes
      if (Object.keys(updates).length > 0) {
        await onUpdate(task.id, updates);
        setIsEditing(false);
        setEditedTask(null);
      } else {
        // No changes, just close editing mode
        setIsEditing(false);
        setEditedTask(null);
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
                  value={currentStatusValue}
                  onValueChange={(value) => setEditedTask({ ...editedTask, status: value })}
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
                        {/* Add current value if it's not in the list */}
                        {currentStatusValue && !statuses.find(s => s.name === currentStatusValue) && (
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
                        {/* Add current value if it's not in the defaults */}
                        {currentStatusValue && !["todo", "in_progress", "review", "completed"].includes(currentStatusValue) && (
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
                  value={currentPriorityValue}
                  onValueChange={(value) => setEditedTask({ ...editedTask, priority: value })}
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
                        {currentPriorityValue && !priorities.find(p => p.name === currentPriorityValue) && (
                          <SelectItem value={currentPriorityValue}>
                            {currentPriorityValue}
                          </SelectItem>
                        )}
                      </>
                    ) : (
                      // Fallback to default values if no priorities loaded
                      <>
                        <SelectItem value="lowest">Lowest</SelectItem>
                        <SelectItem value="low">Low</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                        <SelectItem value="highest">Highest</SelectItem>
                        <SelectItem value="critical">Critical</SelectItem>
                        {/* Add current value if it's not in the defaults */}
                        {currentPriorityValue && !["lowest", "low", "medium", "high", "highest", "critical"].includes(currentPriorityValue) && (
                          <SelectItem value={currentPriorityValue}>
                            {currentPriorityValue}
                          </SelectItem>
                        )}
                      </>
                    )}
                  </SelectContent>
                </Select>
              ) : (
                <div className="mt-1">
                  <span className={`px-2 py-1 rounded text-sm ${
                    task.priority === "high" || task.priority === "critical" ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" :
                    task.priority === "medium" ? "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200" :
                    "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                  }`}>
                    {task.priority || "None"}
                  </span>
                </div>
              )}
            </div>
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
        </div>
      </DialogContent>
    </Dialog>
  );
}

