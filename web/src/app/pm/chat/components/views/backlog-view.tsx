// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useState, useMemo } from "react";
import { Card } from "~/components/ui/card";
import { Input } from "~/components/ui/input";
import { useMyTasks } from "~/core/api/hooks/pm/use-tasks";
import { TaskDetailsModal } from "../task-details-modal";
import type { Task } from "~/core/api/hooks/pm/use-tasks";
import { Search, Filter } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";

export function BacklogView() {
  const { tasks, loading, error } = useMyTasks();
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const [projectFilter, setProjectFilter] = useState<string>("all");

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
    setIsModalOpen(true);
  };

  const handleUpdateTask = async (taskId: string, updates: Partial<Task>) => {
    try {
      const response = await fetch(`http://localhost:8000/api/pm/tasks/${taskId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (!response.ok) throw new Error('Failed to update task');
      
      window.dispatchEvent(new CustomEvent("pm_refresh", { 
        detail: { type: "pm_refresh" } 
      }));
    } catch (error) {
      console.error("Failed to update task:", error);
      throw error;
    }
  };

  // Filter tasks
  const filteredTasks = useMemo(() => {
    let filtered = tasks;

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(t => 
        t.title.toLowerCase().includes(query) ||
        (t.description && t.description.toLowerCase().includes(query)) ||
        (t.project_name && t.project_name.toLowerCase().includes(query))
      );
    }

    // Status filter
    if (statusFilter !== "all") {
      filtered = filtered.filter(t => {
        const status = t.status?.toLowerCase() || "";
        if (statusFilter === "todo") {
          return !status || status === "none" || status.includes("todo") || status.includes("new");
        }
        if (statusFilter === "in-progress") {
          return status.includes("progress") || status.includes("in_progress");
        }
        if (statusFilter === "done") {
          return status.includes("done") || status.includes("completed") || status.includes("closed");
        }
        return status === statusFilter;
      });
    }

    // Priority filter
    if (priorityFilter !== "all") {
      filtered = filtered.filter(t => {
        const priority = t.priority?.toLowerCase() || "";
        if (priorityFilter === "high") {
          return priority === "high" || priority === "highest" || priority === "critical";
        }
        if (priorityFilter === "low") {
          return priority === "low" || priority === "lowest";
        }
        return priority === priorityFilter;
      });
    }

    // Project filter
    if (projectFilter !== "all") {
      filtered = filtered.filter(t => t.project_name === projectFilter);
    }

    return filtered;
  }, [tasks, searchQuery, statusFilter, priorityFilter, projectFilter]);

  const highPriority = filteredTasks.filter(t => t.priority === "high" || t.priority === "highest" || t.priority === "critical");
  const mediumPriority = filteredTasks.filter(t => t.priority === "medium");
  const lowPriority = filteredTasks.filter(t => t.priority === "low" || t.priority === "lowest");
  const noPriority = filteredTasks.filter(t => !t.priority || t.priority === "None");

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">Loading backlog...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-red-500">Error loading tasks: {error.message}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Backlog</h2>
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
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[140px]">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="todo">To Do</SelectItem>
                <SelectItem value="in-progress">In Progress</SelectItem>
                <SelectItem value="done">Done</SelectItem>
              </SelectContent>
            </Select>
            <Select value={priorityFilter} onValueChange={setPriorityFilter}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Priority" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Priority</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="low">Low</SelectItem>
              </SelectContent>
            </Select>
            <Select value={projectFilter} onValueChange={setProjectFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Project" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Projects</SelectItem>
                {[...new Set(tasks.map(t => t.project_name).filter(Boolean))].map(projectName => (
                  <SelectItem key={projectName} value={projectName}>{projectName}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      <Card className="p-6">
        <div className="space-y-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Priority Legend: 🔴 High | 🟡 Medium | 🔵 Low
          </div>
          
          {highPriority.length > 0 && (
            <div className="space-y-2">
              <div className="font-semibold text-gray-900 dark:text-white">
                🔴 HIGH PRIORITY ({highPriority.length} tasks)
              </div>
              {highPriority.map((task) => (
                <div 
                  key={task.id} 
                  onClick={() => handleTaskClick(task)}
                  className="flex items-center gap-3 p-3 bg-red-50 dark:bg-red-950 rounded-lg border border-red-200 dark:border-red-800 hover:shadow-md transition-shadow cursor-pointer"
                >
                  <input type="checkbox" className="w-4 h-4" onClick={(e) => e.stopPropagation()} />
                  <div className="flex-1">
                    <div className="font-medium text-gray-900 dark:text-white">{task.title}</div>
                    {task.assigned_to && (
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        👤 {task.assigned_to} {task.estimated_hours && `| ⏱️ ${task.estimated_hours}h`}
                      </div>
                    )}
                  </div>
                  <span className="px-2 py-1 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 rounded text-xs">
                    High
                  </span>
                </div>
              ))}
            </div>
          )}

          {mediumPriority.length > 0 && (
            <div className="space-y-2 pt-4">
              <div className="font-semibold text-gray-900 dark:text-white">
                🟡 MEDIUM PRIORITY ({mediumPriority.length} tasks)
              </div>
              {mediumPriority.map((task) => (
                <div 
                  key={task.id} 
                  onClick={() => handleTaskClick(task)}
                  className="flex items-center gap-3 p-3 bg-orange-50 dark:bg-orange-950 rounded-lg border border-orange-200 dark:border-orange-800 hover:shadow-md transition-shadow cursor-pointer"
                >
                  <input type="checkbox" className="w-4 h-4" onClick={(e) => e.stopPropagation()} />
                  <div className="flex-1">
                    <div className="font-medium text-gray-900 dark:text-white">{task.title}</div>
                    {task.assigned_to && (
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        👤 {task.assigned_to} {task.estimated_hours && `| ⏱️ ${task.estimated_hours}h`}
                      </div>
                    )}
                  </div>
                  <span className="px-2 py-1 bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200 rounded text-xs">
                    Medium
                  </span>
                </div>
              ))}
            </div>
          )}

          {lowPriority.length > 0 && (
            <div className="space-y-2 pt-4">
              <div className="font-semibold text-gray-900 dark:text-white">
                🔵 LOW PRIORITY ({lowPriority.length} tasks)
              </div>
              {lowPriority.map((task) => (
                <div 
                  key={task.id} 
                  onClick={() => handleTaskClick(task)}
                  className="flex items-center gap-3 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800 hover:shadow-md transition-shadow cursor-pointer"
                >
                  <input type="checkbox" className="w-4 h-4" onClick={(e) => e.stopPropagation()} />
                  <div className="flex-1">
                    <div className="font-medium text-gray-900 dark:text-white">{task.title}</div>
                    {task.assigned_to && (
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        👤 {task.assigned_to} {task.estimated_hours && `| ⏱️ ${task.estimated_hours}h`}
                      </div>
                    )}
                  </div>
                  <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded text-xs">
                    Low
                  </span>
                </div>
              ))}
            </div>
          )}

          {noPriority.length > 0 && (
            <div className="space-y-2 pt-4">
              <div className="font-semibold text-gray-900 dark:text-white">
                📋 NO PRIORITY ({noPriority.length} tasks)
              </div>
              {noPriority.map((task) => (
                <div 
                  key={task.id} 
                  onClick={() => handleTaskClick(task)}
                  className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-950 rounded-lg border border-gray-200 dark:border-gray-800 hover:shadow-md transition-shadow cursor-pointer"
                >
                  <input type="checkbox" className="w-4 h-4" onClick={(e) => e.stopPropagation()} />
                  <div className="flex-1">
                    <div className="font-medium text-gray-900 dark:text-white">{task.title}</div>
                    {task.estimated_hours && (
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        ⏱️ {task.estimated_hours}h
                      </div>
                    )}
                  </div>
                  <span className="px-2 py-1 bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-gray-200 rounded text-xs">
                    {task.status}
                  </span>
                </div>
              ))}
            </div>
          )}

          {filteredTasks.length === 0 && (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              {tasks.length === 0 ? "No tasks in backlog" : "No tasks match your filters"}
            </div>
          )}
        </div>
      </Card>

      <TaskDetailsModal
        task={selectedTask}
        open={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedTask(null);
        }}
        onUpdate={handleUpdateTask}
      />
    </div>
  );
}

