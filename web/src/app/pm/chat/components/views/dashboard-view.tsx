// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Card } from "~/components/ui/card";
import { useProjects } from "~/core/api/hooks/pm/use-projects";
import { useMyTasks, useAllTasks } from "~/core/api/hooks/pm/use-tasks";

export function DashboardView() {
  const { projects, loading: projectsLoading } = useProjects();
  const { tasks: myTasks, loading: myTasksLoading } = useMyTasks();
  const { tasks: allTasks, loading: allTasksLoading } = useAllTasks();

  const activeProjects = projects.filter(p => p.status === "active" || p.status === "in_progress");
  const openTasks = allTasks.filter(t => t.status !== "completed" && t.status !== "done");
  const tasksLoading = allTasksLoading || myTasksLoading;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h2>
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
            {tasksLoading ? "..." : myTasks.length}
          </div>
        </Card>
      </div>

      {/* My Work Section */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">My Work</h3>
        {tasksLoading ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">Loading tasks...</div>
        ) : myTasks.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">No tasks assigned</div>
        ) : (
          <div className="space-y-3">
            {myTasks.slice(0, 10).map((task) => (
              <div key={task.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
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
              <div key={project.id} className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
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
    </div>
  );
}

