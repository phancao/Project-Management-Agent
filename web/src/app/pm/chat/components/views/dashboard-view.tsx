// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useState, useMemo } from "react";
import { Card } from "~/components/ui/card";
import { useProjects } from "~/core/api/hooks/pm/use-projects";
import { useMyTasks, useAllTasks } from "~/core/api/hooks/pm/use-tasks";
import { TaskDetailsModal } from "../task-details-modal";
import type { Task } from "~/core/api/hooks/pm/use-tasks";
import { useRouter, useSearchParams } from "next/navigation";

export function DashboardView() {
  const { projects, loading: projectsLoading } = useProjects();
  const { tasks: myTasks, loading: myTasksLoading } = useMyTasks();
  const { tasks: allTasks, loading: allTasksLoading } = useAllTasks();
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeProjectId = searchParams.get('project');
  
  // Filter tasks if viewing a specific project
  const filteredMyTasks = useMemo(() => {
    if (!activeProjectId) return myTasks;
    return myTasks.filter(t => t.project_name && projects.find(p => p.id === activeProjectId && p.name === t.project_name));
  }, [myTasks, activeProjectId, projects]);
  
  const filteredAllTasks = useMemo(() => {
    if (!activeProjectId) return allTasks;
    const activeProject = projects.find(p => p.id === activeProjectId);
    return activeProject ? allTasks.filter(t => t.project_name === activeProject.name) : [];
  }, [allTasks, activeProjectId, projects]);
  
  const activeProject = useMemo(() => {
    return activeProjectId ? projects.find(p => p.id === activeProjectId) : null;
  }, [projects, activeProjectId]);

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
    setIsModalOpen(true);
  };

  const handleProjectClick = (projectId: string) => {
    router.push(`/pm/chat?project=${projectId}`);
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

  const activeProjects = projects.filter(p => p.status === "active" || p.status === "in_progress");
  const openTasks = filteredAllTasks.filter(t => t.status !== "completed" && t.status !== "done");
  const tasksLoading = allTasksLoading || myTasksLoading;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">Dashboard</h2>
          {activeProject && (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-700">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {activeProject.name}
              </span>
              <button
                onClick={() => router.push('/pm/chat')}
                className="ml-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                aria-label="Remove filter"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
          <div className="text-sm text-blue-600 dark:text-blue-400 font-medium">Total Projects</div>
          <div className="text-3xl font-bold text-blue-900 dark:text-blue-100 mt-2">
            {projectsLoading ? "..." : projects.length}
          </div>
        </Card>
        <Card className="p-4 bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800">
          <div className="text-sm text-purple-600 dark:text-purple-400 font-medium">Active Projects</div>
          <div className="text-3xl font-bold text-purple-900 dark:text-purple-100 mt-2">
            {projectsLoading ? "..." : activeProjects.length}
          </div>
        </Card>
        <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
          <div className="text-sm text-green-600 dark:text-green-400 font-medium">Open Tasks</div>
          <div className="text-3xl font-bold text-green-900 dark:text-green-100 mt-2">
            {tasksLoading ? "..." : openTasks.length}
          </div>
        </Card>
        <Card className="p-4 bg-orange-50 dark:bg-orange-950 border-orange-200 dark:border-orange-800">
          <div className="text-sm text-orange-600 dark:text-orange-400 font-medium">My Tasks</div>
          <div className="text-3xl font-bold text-orange-900 dark:text-orange-100 mt-2">
            {tasksLoading ? "..." : filteredMyTasks.length}
          </div>
        </Card>
      </div>

      {/* My Work Section */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">My Work</h3>
        {tasksLoading ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">Loading tasks...</div>
        ) : filteredMyTasks.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            {activeProject ? "No tasks in this project" : "No tasks assigned"}
          </div>
        ) : (
          <div className="space-y-3">
            {filteredMyTasks.slice(0, 10).map((task) => (
              <div 
                key={task.id} 
                onClick={() => handleTaskClick(task)}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg hover:shadow-md transition-shadow cursor-pointer"
              >
                <div className="flex-1">
                  <div className="font-medium text-gray-900 dark:text-white">{task.title}</div>
                  {task.project_name && (
                    <div className="text-sm text-gray-500 dark:text-gray-400">{task.project_name}</div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded text-xs font-medium">
                    {task.status}
                  </span>
                  {task.priority && (
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      task.priority === "high" ? "bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200" :
                      task.priority === "medium" ? "bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200" :
                      "bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200"
                    }`}>
                      {task.priority}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Projects List */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Projects</h3>
        {projectsLoading ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">Loading projects...</div>
        ) : projects.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">No projects yet</div>
        ) : (
          <div className="space-y-2">
            {projects.map((project) => (
              <div 
                key={project.id} 
                onClick={() => handleProjectClick(project.id)}
                className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg hover:shadow-md transition-shadow cursor-pointer"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">{project.name}</div>
                    {project.description && (
                      <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">{project.description}</div>
                    )}
                  </div>
                  <span className="px-2 py-1 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded text-xs font-medium">
                    {project.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
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

