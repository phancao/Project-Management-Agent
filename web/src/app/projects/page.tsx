"use client";

import Link from 'next/link';
import { useEffect, useState } from 'react';

interface Task {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  estimated_hours?: number;
  assigned_to?: string;
  due_date?: string;
}

interface Sprint {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  duration_weeks: number;
  duration_days: number;
  capacity_hours: number;
  planned_hours: number;
  utilization: number;
  status: string;
}

interface Project {
  id: string;
  name: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [tasks, setTasks] = useState<Record<string, Task[]>>({});
  const [sprints, setSprints] = useState<Record<string, Sprint[]>>({});
  const [sprintTasks, setSprintTasks] = useState<Record<string, Task[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedProject, setExpandedProject] = useState<string | null>(null);
  const [expandedSprint, setExpandedSprint] = useState<string | null>(null);
  
  const getPriorityColor = (priority: string) => {
    switch (priority?.toLowerCase()) {
      case 'high':
        return 'bg-red-50 border-red-300 text-red-800';
      case 'medium':
        return 'bg-orange-50 border-orange-300 text-orange-800';
      case 'low':
        return 'bg-blue-50 border-blue-300 text-blue-800';
      default:
        return 'bg-gray-50 border-gray-300 text-gray-800';
    }
  };
  
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 border-green-300 text-green-800';
      case 'in_progress':
        return 'bg-blue-100 border-blue-300 text-blue-800';
      case 'planned':
        return 'bg-yellow-100 border-yellow-300 text-yellow-800';
      default:
        return 'bg-gray-100 border-gray-300 text-gray-800';
    }
  };

  useEffect(() => {
    void fetchProjects();
  }, []);

  useEffect(() => {
    if (expandedProject && !tasks[expandedProject]) {
      void fetchTasks(expandedProject);
    }
    if (expandedProject && !sprints[expandedProject]) {
      void fetchSprints(expandedProject);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expandedProject]);

  useEffect(() => {
    if (expandedSprint && !sprintTasks[expandedSprint]) {
      void fetchSprintTasks(expandedSprint);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expandedSprint]);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/api/projects', {
        headers: {
          'Authorization': 'Bearer mock_token',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch projects');
      }

      const data = await response.json();
      setProjects(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const fetchTasks = async (projectId: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/projects/${projectId}/tasks`, {
        headers: {
          'Authorization': 'Bearer mock_token',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setTasks(prev => ({ ...prev, [projectId]: data }));
      }
    } catch (err) {
      console.error('Failed to fetch tasks:', err);
    }
  };

  const fetchSprints = async (projectId: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/projects/${projectId}/sprints`, {
        headers: {
          'Authorization': 'Bearer mock_token',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setSprints(prev => ({ ...prev, [projectId]: data }));
      }
    } catch (err) {
      console.error('Failed to fetch sprints:', err);
    }
  };

  const fetchSprintTasks = async (sprintId: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/sprints/${sprintId}/tasks`, {
        headers: {
          'Authorization': 'Bearer mock_token',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setSprintTasks(prev => ({ ...prev, [sprintId]: data }));
      }
    } catch (err) {
      console.error('Failed to fetch sprint tasks:', err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
            <div className="text-gray-700 text-lg font-medium">Loading projects...</div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 via-white to-pink-50 flex items-center justify-center">
        <div className="bg-white rounded-xl shadow-lg p-8 max-w-md mx-4">
          <div className="text-red-600 text-6xl mb-4 text-center">⚠️</div>
          <div className="text-red-800 text-xl font-semibold mb-2">Error Loading Projects</div>
          <div className="text-gray-600">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                🦌 DeerFlow Projects
              </h1>
              <p className="text-gray-600 mt-1">Manage your AI-powered project development</p>
            </div>
            <div className="flex gap-3">
              <Link 
                href="/" 
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors font-medium"
              >
                Home
              </Link>
              <Link 
                href="/chat" 
                className="px-6 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 shadow-md hover:shadow-lg transition-all font-semibold"
              >
                💬 Start Chat
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {projects.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-xl p-12 text-center border-2 border-dashed border-gray-300">
            <div className="text-6xl mb-4">🎯</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">No Projects Yet</h2>
            <p className="text-gray-600 mb-6">Create your first project by chatting with the AI assistant!</p>
            <Link 
              href="/chat"
              className="inline-block px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 shadow-md hover:shadow-lg transition-all font-semibold"
            >
              🚀 Get Started
            </Link>
          </div>
        ) : (
          <>
            <div className="mb-8">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-900">
                  Projects Overview
                </h2>
                <span className="px-4 py-2 bg-white rounded-lg shadow-sm border border-gray-200 text-gray-700 font-medium">
                  {projects.length} {projects.length === 1 ? 'Project' : 'Projects'}
                </span>
              </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {projects.map((project) => (
                <div
                  key={project.id}
                  className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden hover:shadow-xl transition-all duration-300"
                >
                  {/* Project Header */}
                  <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-6">
                    <div className="flex items-start justify-between mb-3">
                      <h3 className="text-xl font-bold text-white line-clamp-2">{project.name}</h3>
                      <span className={`px-3 py-1 text-xs font-semibold rounded-full border ${getStatusColor(project.status)} flex-shrink-0 ml-2`}>
                        {project.status.replace('_', ' ')}
                      </span>
                    </div>
                    
                    {project.description && (
                      <p className="text-blue-50 text-sm line-clamp-2">
                        {project.description}
                      </p>
                    )}
                  </div>

                  {/* Project Actions */}
                  <div className="p-6 space-y-4">
                    <button
                      onClick={() => setExpandedProject(expandedProject === project.id ? null : project.id)}
                      className="w-full px-4 py-3 bg-gradient-to-r from-gray-100 to-gray-200 hover:from-gray-200 hover:to-gray-300 rounded-lg text-sm font-semibold text-gray-800 transition-all border border-gray-300"
                    >
                      {expandedProject === project.id ? '▼ Hide Details' : '▶ Show Details'}
                    </button>

                    {expandedProject === project.id && (
                      <div className="space-y-6 animate-in fade-in slide-in-from-top-2 duration-300">
                        {/* Stats Summary */}
                        <div className="grid grid-cols-2 gap-3">
                          <div className="bg-blue-50 rounded-lg p-3 text-center border border-blue-200">
                            <div className="text-2xl font-bold text-blue-700">
                              {sprints[project.id]?.length ?? 0}
                            </div>
                            <div className="text-xs text-blue-600 font-medium mt-1">Sprints</div>
                          </div>
                          <div className="bg-purple-50 rounded-lg p-3 text-center border border-purple-200">
                            <div className="text-2xl font-bold text-purple-700">
                              {tasks[project.id]?.length ?? 0}
                            </div>
                            <div className="text-xs text-purple-600 font-medium mt-1">Tasks</div>
                          </div>
                        </div>

                        {/* Sprints Section */}
                        <div>
                          <h4 className="text-base font-bold text-gray-900 mb-3 flex items-center gap-2">
                            🏃 Sprint Plans
                            <span className="text-sm font-normal text-gray-500">
                              ({sprints[project.id]?.length ?? 0})
                            </span>
                          </h4>
                          {sprints[project.id] ? (
                            sprints[project.id]!.length > 0 ? (
                              <div className="space-y-2">
                                {sprints[project.id]!.map((sprint) => (
                                  <div key={sprint.id} className="border-2 border-blue-200 rounded-xl overflow-hidden bg-white hover:border-blue-400 transition-colors">
                                    <button
                                      onClick={() => setExpandedSprint(expandedSprint === sprint.id ? null : sprint.id)}
                                      className="w-full px-4 py-3 bg-gradient-to-r from-blue-50 to-purple-50 hover:from-blue-100 hover:to-purple-100 flex items-center justify-between transition-colors"
                                    >
                                      <div className="flex items-center gap-3">
                                        <span className="font-bold text-blue-900">{sprint.name}</span>
                                        <span className={`px-2 py-1 text-xs font-semibold rounded-lg border ${getStatusColor(sprint.status)}`}>
                                          {sprint.status}
                                        </span>
                                      </div>
                                      <span className="text-blue-600 font-bold">
                                        {expandedSprint === sprint.id ? '▲' : '▼'}
                                      </span>
                                    </button>
                                    {expandedSprint === sprint.id && (
                                      <div className="p-4 bg-white border-t-2 border-blue-200 space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
                                        <div className="grid grid-cols-2 gap-2 text-xs">
                                          <div className="bg-gray-50 rounded-lg p-2 border border-gray-200">
                                            <div className="font-semibold text-gray-700">Duration</div>
                                            <div className="text-gray-900 font-bold">{sprint.duration_weeks} weeks</div>
                                          </div>
                                          <div className="bg-gray-50 rounded-lg p-2 border border-gray-200">
                                            <div className="font-semibold text-gray-700">Capacity</div>
                                            <div className="text-gray-900 font-bold">{sprint.capacity_hours?.toFixed(0)}h</div>
                                          </div>
                                          <div className="bg-gray-50 rounded-lg p-2 border border-gray-200">
                                            <div className="font-semibold text-gray-700">Planned</div>
                                            <div className="text-gray-900 font-bold">{sprint.planned_hours?.toFixed(0)}h</div>
                                          </div>
                                          <div className="bg-gray-50 rounded-lg p-2 border border-gray-200">
                                            <div className="font-semibold text-gray-700">Utilization</div>
                                            <div className="text-gray-900 font-bold">{sprint.utilization?.toFixed(0)}%</div>
                                          </div>
                                        </div>
                                        <div>
                                          <div className="text-xs font-bold text-gray-800 mb-2 flex items-center gap-2">
                                            📋 Sprint Tasks
                                            <span className="font-normal text-gray-500">
                                              ({sprintTasks[sprint.id]?.length ?? 0})
                                            </span>
                                          </div>
                                          {sprintTasks[sprint.id] ? (
                                            sprintTasks[sprint.id]!.length > 0 ? (
                                              <div className="space-y-2">
                                                {sprintTasks[sprint.id]!.map((task) => (
                                                  <div key={task.id} className="flex items-center justify-between p-3 bg-gradient-to-r from-gray-50 to-blue-50 rounded-lg border border-gray-200 hover:border-blue-300 transition-colors">
                                                    <div className="flex-1 min-w-0">
                                                      <div className="font-medium text-sm text-gray-900 truncate">{task.title}</div>
                                                      {task.assigned_to && (
                                                        <div className="text-xs text-gray-600 mt-1">
                                                          👤 {task.assigned_to}
                                                        </div>
                                                      )}
                                                    </div>
                                                    <div className="flex items-center gap-2 flex-shrink-0 ml-3">
                                                      {task.priority && (
                                                        <span className={`px-2 py-0.5 text-xs font-semibold rounded border ${getPriorityColor(task.priority)}`}>
                                                          {task.priority}
                                                        </span>
                                                      )}
                                                      {task.estimated_hours && (
                                                        <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs font-semibold rounded border border-blue-300">
                                                          ⏱️ {task.estimated_hours}h
                                                        </span>
                                                      )}
                                                    </div>
                                                  </div>
                                                ))}
                                              </div>
                                            ) : (
                                              <div className="text-sm text-gray-500 text-center py-4 bg-gray-50 rounded-lg border border-gray-200">
                                                No tasks assigned yet
                                              </div>
                                            )
                                          ) : (
                                            <div className="text-sm text-gray-500 text-center py-4 bg-gray-50 rounded-lg border border-gray-200">
                                              Loading...
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <div className="text-center py-6 bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl border-2 border-dashed border-blue-300">
                                <div className="text-3xl mb-2">📅</div>
                                <p className="text-sm font-medium text-gray-700">
                                  No sprints planned yet
                                </p>
                                <Link 
                                  href={`/chat?project=${project.id}`}
                                  className="text-xs text-blue-600 hover:underline mt-1 inline-block"
                                >
                                  Plan a sprint →
                                </Link>
                              </div>
                            )
                          ) : (
                            <div className="text-center py-4 bg-gray-50 rounded-lg border border-gray-200">
                              <div className="inline-block animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                            </div>
                          )}
                        </div>

                        {/* All Tasks Section */}
                        <div>
                          <h4 className="text-base font-bold text-gray-900 mb-3 flex items-center gap-2">
                            📋 All Project Tasks
                            <span className="text-sm font-normal text-gray-500">
                              ({tasks[project.id]?.length ?? 0})
                            </span>
                          </h4>
                          {tasks[project.id] ? (
                            tasks[project.id]!.length > 0 ? (
                              <div className="space-y-2 max-h-96 overflow-y-auto pr-2">
                                {tasks[project.id]!.map((task) => (
                                  <div key={task.id} className="p-3 bg-gradient-to-r from-gray-50 to-white rounded-lg border border-gray-200 hover:border-purple-300 hover:shadow-md transition-all">
                                    <div className="flex items-start justify-between gap-3">
                                      <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-2">
                                          <h5 className="font-semibold text-sm text-gray-900 truncate">{task.title}</h5>
                                          <span className={`px-2 py-0.5 text-xs font-semibold rounded border flex-shrink-0 ${getStatusColor(task.status)}`}>
                                            {task.status}
                                          </span>
                                        </div>
                                        {task.description && (
                                          <p className="text-xs text-gray-600 mb-2 line-clamp-2">{task.description}</p>
                                        )}
                                        <div className="flex items-center gap-2 flex-wrap">
                                          {task.priority && (
                                            <span className={`px-2 py-0.5 text-xs font-semibold rounded border ${getPriorityColor(task.priority)}`}>
                                              {task.priority}
                                            </span>
                                          )}
                                          {task.estimated_hours && (
                                            <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs font-semibold rounded border border-blue-300">
                                              ⏱️ {task.estimated_hours}h
                                            </span>
                                          )}
                                          {task.assigned_to && (
                                            <span className="px-2 py-0.5 bg-purple-100 text-purple-800 text-xs font-semibold rounded border border-purple-300">
                                              👤 {task.assigned_to}
                                            </span>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <div className="text-center py-6 bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl border-2 border-dashed border-purple-300">
                                <div className="text-3xl mb-2">📝</div>
                                <p className="text-sm font-medium text-gray-700">
                                  No tasks created yet
                                </p>
                                <Link 
                                  href={`/chat?project=${project.id}`}
                                  className="text-xs text-purple-600 hover:underline mt-1 inline-block"
                                >
                                  Create tasks →
                                </Link>
                              </div>
                            )
                          ) : (
                            <div className="text-center py-4 bg-gray-50 rounded-lg border border-gray-200">
                              <div className="inline-block animate-spin rounded-full h-5 w-5 border-b-2 border-purple-600"></div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {/* Footer */}
                  <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
                    <span className="text-xs text-gray-600">
                      Created {new Date(project.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </span>
                    <Link 
                      href={`/chat?project=${project.id}`}
                      className="text-sm font-semibold text-blue-600 hover:text-blue-700 transition-colors flex items-center gap-1"
                    >
                      Open Chat
                      <span className="text-blue-600">→</span>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
