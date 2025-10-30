"use client";

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedProject, setExpandedProject] = useState<string | null>(null);

  useEffect(() => {
    fetchProjects();
  }, []);

  useEffect(() => {
    // Fetch tasks for expanded project
    if (expandedProject && !tasks[expandedProject]) {
      fetchTasks(expandedProject);
    }
  }, [expandedProject]);

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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Loading projects...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-red-600">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">🦌 DeerFlow - Projects</h1>
            <div className="flex gap-4">
              <a 
                href="/" 
                className="px-4 py-2 text-gray-600 hover:text-gray-900"
              >
                Home
              </a>
              <a 
                href="/chat" 
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Chat
              </a>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-gray-800">
            Your Projects ({projects.length})
          </h2>
        </div>

        {projects.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <p className="text-gray-600">No projects found. Create one by chatting with the AI!</p>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <div
                key={project.id}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">{project.name}</h3>
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    project.status === 'planning' 
                      ? 'bg-yellow-100 text-yellow-800'
                      : project.status === 'in_progress'
                      ? 'bg-blue-100 text-blue-800'
                      : project.status === 'completed'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    {project.status}
                  </span>
                </div>
                
                <p className="text-gray-600 text-sm mb-4">
                  {project.description || 'No description'}
                </p>
                
                <button
                  onClick={() => setExpandedProject(expandedProject === project.id ? null : project.id)}
                  className="w-full mb-4 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-md text-sm font-medium text-gray-700 transition-colors"
                >
                  {expandedProject === project.id ? 'Hide' : 'Show'} Tasks ({tasks[project.id]?.length || 0})
                </button>

                {expandedProject === project.id && (
                  <div className="border-t pt-4">
                    {tasks[project.id] ? (
                      tasks[project.id].length > 0 ? (
                        <div className="space-y-2">
                          {tasks[project.id].map((task) => (
                            <div key={task.id} className="flex items-start justify-between p-3 bg-gray-50 rounded-md">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <h4 className="font-medium text-sm text-gray-900">{task.title}</h4>
                                  <span className={`px-2 py-0.5 text-xs rounded ${
                                    task.status === 'completed' 
                                      ? 'bg-green-100 text-green-800'
                                      : task.status === 'in_progress'
                                      ? 'bg-blue-100 text-blue-800'
                                      : 'bg-yellow-100 text-yellow-800'
                                  }`}>
                                    {task.status}
                                  </span>
                                </div>
                                {task.description && (
                                  <p className="text-xs text-gray-600">{task.description}</p>
                                )}
                                <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                                  {task.priority && (
                                    <span className={`px-2 py-0.5 rounded ${
                                      task.priority === 'high' 
                                        ? 'bg-red-100 text-red-700'
                                        : task.priority === 'medium'
                                        ? 'bg-orange-100 text-orange-700'
                                        : 'bg-gray-100 text-gray-700'
                                    }`}>
                                      {task.priority}
                                    </span>
                                  )}
                                  {task.estimated_hours && (
                                    <span>⏱️ {task.estimated_hours}h</span>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500 text-center py-4">
                          No tasks yet. Create tasks by chatting with the AI!
                        </p>
                      )
                    ) : (
                      <div className="text-sm text-gray-500 text-center py-4">Loading tasks...</div>
                    )}
                  </div>
                )}
                
                <div className="flex items-center justify-between text-xs text-gray-500 mt-4 pt-4 border-t">
                  <span>Created: {new Date(project.created_at).toLocaleDateString()}</span>
                  <a 
                    href={`/chat?project=${project.id}`}
                    className="text-blue-600 hover:text-blue-700"
                  >
                    Chat →
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

