"use client";

import { useState, useEffect, useCallback } from 'react';

interface Project {
  id: string;
  name: string;
  description: string;
  status: 'planning' | 'in_progress' | 'completed' | 'on_hold' | 'cancelled';
  progress: number;
  startDate: string;
  endDate?: string;
  owner: string;
  teamMembers: string[];
  createdAt: string;
  updatedAt: string;
}

interface CreateProjectData {
  name: string;
  description: string;
  startDate?: string;
  endDate?: string;
  teamMembers?: string[];
}

interface UpdateProjectData {
  name?: string;
  description?: string;
  status?: string;
  progress?: number;
  endDate?: string;
  teamMembers?: string[];
}

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch projects from API
  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('/api/projects', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch projects');
      }

      const data = await response.json();
      setProjects(data.projects || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Error fetching projects:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Create new project
  const createProject = useCallback(async (projectData: CreateProjectData) => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('/api/projects', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(projectData),
      });

      if (!response.ok) {
        throw new Error('Failed to create project');
      }

      const newProject = await response.json();
      setProjects(prev => [...prev, newProject]);
      return newProject;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Error creating project:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Update existing project
  const updateProject = useCallback(async (projectId: string, updateData: UpdateProjectData) => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch(`/api/projects/${projectId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateData),
      });

      if (!response.ok) {
        throw new Error('Failed to update project');
      }

      const updatedProject = await response.json();
      setProjects(prev => 
        prev.map(project => 
          project.id === projectId ? { ...project, ...updatedProject } : project
        )
      );
      return updatedProject;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Error updating project:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Delete project
  const deleteProject = useCallback(async (projectId: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch(`/api/projects/${projectId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to delete project');
      }

      setProjects(prev => prev.filter(project => project.id !== projectId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Error deleting project:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Create project with research
  const createProjectWithResearch = useCallback(async (
    projectDescription: string,
    researchRequirements?: string[]
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('/api/agents/create-project-with-research', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_description: projectDescription,
          research_requirements: researchRequirements,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create project with research');
      }

      const result = await response.json();
      
      // Add the created project to the list
      if (result.result?.project) {
        setProjects(prev => [...prev, result.result.project]);
      }
      
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Error creating project with research:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Load projects on mount
  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  return {
    projects,
    loading,
    error,
    fetchProjects,
    createProject,
    updateProject,
    deleteProject,
    createProjectWithResearch,
  };
}
