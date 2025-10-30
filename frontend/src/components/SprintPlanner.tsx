"use client";

import React, { useState, useEffect } from 'react';
import { Calendar, Users, Clock, CheckCircle, Target, TrendingUp, AlertCircle } from 'lucide-react';
import { projectAPI, Project, Task } from '@/services/api';

interface SprintTask {
  task_id: string;
  title: string;
  estimated_hours: number;
  priority: string;
  assigned_to?: string;
}

interface SprintData {
  sprint_name: string;
  start_date: string;
  end_date: string;
  duration_weeks: number;
  duration_days: number;
  total_capacity_hours: number;
  planned_hours: number;
  utilization: number;
  team_members: string[];
  tasks_assigned: number;
  tasks: SprintTask[];
}

interface SprintPlannerProps {
  projectId?: string;
  onClose?: () => void;
}

export function SprintPlanner({ projectId, onClose }: SprintPlannerProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>(projectId || '');
  const [sprintName, setSprintName] = useState('Sprint 1');
  const [durationWeeks, setDurationWeeks] = useState(2);
  const [capacityHours, setCapacityHours] = useState(6);
  const [isCreating, setIsCreating] = useState(false);
  const [sprintResult, setSprintResult] = useState<SprintData | null>(null);

  // Fetch projects
  useEffect(() => {
    async function fetchProjects() {
      try {
        const data = await projectAPI.list();
        setProjects(data);
        if (data.length > 0 && !projectId) {
          setSelectedProject(data[0].id);
        }
      } catch (err) {
        console.error('Error fetching projects:', err);
      }
    }
    fetchProjects();
  }, [projectId]);

  const handleCreateSprint = async () => {
    if (!selectedProject) {
      alert('Please select a project');
      return;
    }

    setIsCreating(true);
    try {
      // For now, we'll simulate sprint creation
      // In production, this would call the backend API
      // For demo purposes, we'll create mock sprint data
      
      const tasks = await projectAPI.getTasks(selectedProject);
      const filteredTasks = tasks.filter(t => t.status === 'todo');
      const totalEstimated = filteredTasks.reduce((sum, t) => sum + (t.estimated_hours || 0), 0);
      const capacityPerDay = capacityHours;
      const workDays = durationWeeks * 5;
      const totalCapacity = capacityPerDay * workDays; // Assuming 1 team member for now
      
      // Select tasks that fit capacity
      const selectedTasks: SprintTask[] = [];
      let hoursUsed = 0;
      
      for (const task of filteredTasks) {
        if (hoursUsed + (task.estimated_hours || 0) <= totalCapacity && task.estimated_hours) {
          selectedTasks.push({
            task_id: task.id,
            title: task.title,
            estimated_hours: task.estimated_hours,
            priority: task.priority,
          });
          hoursUsed += task.estimated_hours;
        }
      }

      const startDate = new Date();
      const endDate = new Date();
      endDate.setDate(endDate.getDate() + (durationWeeks * 7));

      setSprintResult({
        sprint_name: sprintName,
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString(),
        duration_weeks: durationWeeks,
        duration_days: durationWeeks * 7,
        total_capacity_hours: totalCapacity,
        planned_hours: hoursUsed,
        utilization: (hoursUsed / totalCapacity) * 100,
        team_members: ['Developer 1'], // TODO: Fetch from project
        tasks_assigned: selectedTasks.length,
        tasks: selectedTasks,
      });
    } catch (err) {
      console.error('Error creating sprint:', err);
      alert('Failed to create sprint');
    } finally {
      setIsCreating(false);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'bg-red-100 text-red-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Sprint Planning</h2>
            <p className="text-sm text-gray-600 mt-1">Plan your sprint tasks and capacity</p>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Close
            </button>
          )}
        </div>
      </div>

      <div className="p-6">
        {!sprintResult ? (
          <>
            {/* Sprint Configuration */}
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Project
                </label>
                <select
                  value={selectedProject}
                  onChange={(e) => setSelectedProject(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={isCreating}
                >
                  <option value="">Select a project...</option>
                  {projects.map(project => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Sprint Name
                </label>
                <input
                  type="text"
                  value={sprintName}
                  onChange={(e) => setSprintName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Sprint 1"
                  disabled={isCreating}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Duration (Weeks)
                  </label>
                  <input
                    type="number"
                    value={durationWeeks}
                    onChange={(e) => setDurationWeeks(Number(e.target.value))}
                    min="1"
                    max="12"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={isCreating}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Capacity (Hours/Day)
                  </label>
                  <input
                    type="number"
                    value={capacityHours}
                    onChange={(e) => setCapacityHours(Number(e.target.value))}
                    min="1"
                    max="12"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={isCreating}
                  />
                </div>
              </div>

              <button
                onClick={handleCreateSprint}
                disabled={!selectedProject || isCreating}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
              >
                {isCreating ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Creating Sprint...</span>
                  </>
                ) : (
                  <>
                    <Target className="w-4 h-4" />
                    <span>Create Sprint Plan</span>
                  </>
                )}
              </button>
            </div>
          </>
        ) : (
          <>
            {/* Sprint Results */}
            <div className="space-y-6">
              {/* Summary */}
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-6 border border-blue-200">
                <h3 className="text-xl font-bold text-gray-900 mb-4">{sprintResult.sprint_name}</h3>
                
                <div className="grid grid-cols-4 gap-4">
                  <div className="bg-white rounded-lg p-4 border border-gray-200">
                    <div className="flex items-center space-x-2 mb-2">
                      <Calendar className="w-5 h-5 text-blue-600" />
                      <span className="text-sm font-medium text-gray-700">Duration</span>
                    </div>
                    <div className="text-2xl font-bold text-gray-900">{sprintResult.duration_weeks} weeks</div>
                    <div className="text-xs text-gray-600 mt-1">{sprintResult.duration_days} days</div>
                  </div>

                  <div className="bg-white rounded-lg p-4 border border-gray-200">
                    <div className="flex items-center space-x-2 mb-2">
                      <Clock className="w-5 h-5 text-green-600" />
                      <span className="text-sm font-medium text-gray-700">Capacity</span>
                    </div>
                    <div className="text-2xl font-bold text-gray-900">{sprintResult.total_capacity_hours}h</div>
                    <div className="text-xs text-gray-600 mt-1">Total available</div>
                  </div>

                  <div className="bg-white rounded-lg p-4 border border-gray-200">
                    <div className="flex items-center space-x-2 mb-2">
                      <CheckCircle className="w-5 h-5 text-purple-600" />
                      <span className="text-sm font-medium text-gray-700">Planned</span>
                    </div>
                    <div className="text-2xl font-bold text-gray-900">{sprintResult.planned_hours}h</div>
                    <div className="text-xs text-gray-600 mt-1">{sprintResult.tasks_assigned} tasks</div>
                  </div>

                  <div className="bg-white rounded-lg p-4 border border-gray-200">
                    <div className="flex items-center space-x-2 mb-2">
                      <TrendingUp className="w-5 h-5 text-orange-600" />
                      <span className="text-sm font-medium text-gray-700">Utilization</span>
                    </div>
                    <div className="text-2xl font-bold text-gray-900">{sprintResult.utilization.toFixed(1)}%</div>
                    <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                      <div
                        className="bg-orange-600 h-2 rounded-full transition-all"
                        style={{ width: `${Math.min(sprintResult.utilization, 100)}%` }}
                      ></div>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-blue-200">
                  <div className="flex items-center space-x-2">
                    <Users className="w-4 h-4 text-gray-600" />
                    <span className="text-sm text-gray-700">
                      Team: {sprintResult.team_members.join(', ') || 'Not assigned'}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2 mt-2">
                    <Calendar className="w-4 h-4 text-gray-600" />
                    <span className="text-sm text-gray-700">
                      {new Date(sprintResult.start_date).toLocaleDateString()} - {new Date(sprintResult.end_date).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>

              {/* Tasks */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Assigned Tasks</h3>
                <div className="space-y-2">
                  {sprintResult.tasks.map((task) => (
                    <div
                      key={task.task_id}
                      className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200 hover:bg-gray-100 transition-colors"
                    >
                      <div className="flex-1">
                        <div className="flex items-center space-x-3">
                          <CheckCircle className="w-5 h-5 text-gray-400" />
                          <span className="font-medium text-gray-900">{task.title}</span>
                          <span className={`text-xs px-2 py-1 rounded-full ${getPriorityColor(task.priority)}`}>
                            {task.priority}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="flex items-center space-x-1 text-sm text-gray-600">
                          <Clock className="w-4 h-4" />
                          <span>{task.estimated_hours}h</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Actions */}
              <div className="flex space-x-3">
                <button
                  onClick={() => setSprintResult(null)}
                  className="flex-1 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-700"
                >
                  Plan Another Sprint
                </button>
                <button
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Save Sprint Plan
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
