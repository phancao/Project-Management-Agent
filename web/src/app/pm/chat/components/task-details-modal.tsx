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

interface TaskDetailsModalProps {
  task: Task | null;
  open: boolean;
  onClose: () => void;
  onUpdate?: (taskId: string, updates: Partial<Task>) => Promise<void>;
}

export function TaskDetailsModal({ task, open, onClose, onUpdate }: TaskDetailsModalProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTask, setEditedTask] = useState<Partial<Task> | null>(null);

  if (!task) return null;

  const handleEdit = () => {
    setEditedTask({ ...task });
    setIsEditing(true);
  };

  const handleSave = async () => {
    if (!editedTask || !onUpdate) return;
    
    try {
      await onUpdate(task.id, editedTask);
      setIsEditing(false);
      setEditedTask(null);
    } catch (error) {
      console.error("Failed to update task:", error);
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
                <Button size="sm" onClick={handleSave}>
                  <Save className="w-4 h-4 mr-2" />
                  Save
                </Button>
              </div>
            )}
          </DialogTitle>
        </DialogHeader>

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

          {/* Project */}
          {task.project_name && (
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Project</label>
              <div className="mt-1">
                <span className="inline-flex items-center px-3 py-1.5 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-lg text-sm font-medium">
                  {task.project_name}
                </span>
              </div>
            </div>
          )}

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
                  value={editedTask?.status ?? task.status}
                  onValueChange={(value) => setEditedTask({ ...editedTask, status: value })}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="todo">To Do</SelectItem>
                    <SelectItem value="in_progress">In Progress</SelectItem>
                    <SelectItem value="review">Review</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
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
                  value={editedTask?.priority ?? task.priority}
                  onValueChange={(value) => setEditedTask({ ...editedTask, priority: value })}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="lowest">Lowest</SelectItem>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="highest">Highest</SelectItem>
                    <SelectItem value="critical">Critical</SelectItem>
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

