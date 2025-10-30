"use client";

import { useEffect, useState } from 'react';

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchProjects();
  }, []);

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
                
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>Created: {new Date(project.created_at).toLocaleDateString()}</span>
                  <a 
                    href={`/chat?project=${project.id}`}
                    className="text-blue-600 hover:text-blue-700"
                  >
                    View →
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

