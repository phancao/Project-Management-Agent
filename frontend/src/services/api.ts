/**
 * API client for Project Management Agent backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export interface Project {
  id: string;
  name: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at: string;
  domain?: string;
  priority?: string;
  timeline_weeks?: number;
  budget?: number;
}

export interface ProjectCreate {
  name: string;
  description?: string;
  domain?: string;
  priority?: string;
  timeline_weeks?: number;
  budget?: number;
}

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  estimated_hours?: number;
  due_date?: string;
  assigned_to?: string;
}

export interface TaskCreate {
  project_id: string;
  title: string;
  description?: string;
  priority?: string;
  estimated_hours?: number;
  due_date?: string;
  assigned_to?: string;
}

/**
 * Fetch helper with error handling
 */
async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    // Handle empty responses
    if (response.status === 204 || response.headers.get('content-length') === '0') {
      return {} as T;
    }

    return await response.json();
  } catch (error) {
    console.error(`API Error (${endpoint}):`, error);
    throw error;
  }
}

/**
 * Project API
 */
export const projectAPI = {
  /**
   * Get all projects
   */
  async list(): Promise<Project[]> {
    return fetchAPI<Project[]>('/projects');
  },

  /**
   * Get project by ID
   */
  async get(id: string): Promise<Project> {
    return fetchAPI<Project>(`/projects/${id}`);
  },

  /**
   * Create a new project
   */
  async create(data: ProjectCreate): Promise<Project> {
    return fetchAPI<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Update project
   */
  async update(id: string, data: Partial<ProjectCreate>): Promise<Project> {
    return fetchAPI<Project>(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete project
   */
  async delete(id: string): Promise<void> {
    await fetchAPI(`/projects/${id}`, {
      method: 'DELETE',
    });
  },

  /**
   * Get tasks for a project
   */
  async getTasks(projectId: string): Promise<Task[]> {
    return fetchAPI<Task[]>(`/projects/${projectId}/tasks`);
  },

  /**
   * Create a task in a project
   */
  async createTask(projectId: string, data: Omit<TaskCreate, 'project_id'>): Promise<Task> {
    return fetchAPI<Task>(`/projects/${projectId}/tasks`, {
      method: 'POST',
      body: JSON.stringify({
        ...data,
        project_id: projectId,
      }),
    });
  },
};

/**
 * Chat API
 */
export const chatAPI = {
  /**
   * Send a chat message
   */
  async sendMessage(
    message: string,
    sessionId: string,
    userId?: string
  ): Promise<any> {
    return fetchAPI('/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        session_id: sessionId,
        user_id: userId,
      }),
    });
  },

  /**
   * Get chat history
   */
  async getHistory(sessionId: string): Promise<any> {
    return fetchAPI(`/chat/history/${sessionId}`);
  },
};

/**
 * Health check
 */
export async function healthCheck(): Promise<{ status: string; timestamp: string }> {
  const baseUrl = API_BASE_URL.replace('/api', '');
  return fetchAPI(`${baseUrl}/health`);
}
