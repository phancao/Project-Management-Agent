"use client";

import React, { useState, useEffect } from 'react';
import { 
  ChartBarIcon, 
  ClockIcon, 
  CheckCircleIcon, 
  ExclamationTriangleIcon,
  UsersIcon,
  CalendarIcon
} from '@heroicons/react/24/outline';

interface Project {
  id: string;
  name: string;
  status: string;
  progress: number;
  startDate: string;
  endDate?: string;
  teamMembers: string[];
}

interface AnalyticsDashboardProps {
  projects: Project[];
}

export function AnalyticsDashboard({ projects }: AnalyticsDashboardProps) {
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | '1y'>('30d');
  const [stats, setStats] = useState({
    totalProjects: 0,
    completedProjects: 0,
    inProgressProjects: 0,
    overdueProjects: 0,
    totalTasks: 0,
    completedTasks: 0,
    teamMembers: 0,
    avgCompletionTime: 0
  });

  useEffect(() => {
    // Calculate stats from projects
    const totalProjects = projects.length;
    const completedProjects = projects.filter(p => p.status === 'completed').length;
    const inProgressProjects = projects.filter(p => p.status === 'in_progress').length;
    const overdueProjects = projects.filter(p => {
      if (!p.endDate) return false;
      return new Date(p.endDate) < new Date() && p.status !== 'completed';
    }).length;

    const totalTasks = projects.reduce((sum, p) => sum + (p.progress || 0), 0);
    const completedTasks = projects.reduce((sum, p) => sum + (p.progress || 0), 0);
    const teamMembers = new Set(projects.flatMap(p => p.teamMembers)).size;

    setStats({
      totalProjects,
      completedProjects,
      inProgressProjects,
      overdueProjects,
      totalTasks,
      completedTasks,
      teamMembers,
      avgCompletionTime: 0 // TODO: Calculate from actual data
    });
  }, [projects]);

  const StatCard = ({ 
    title, 
    value, 
    icon: Icon, 
    color, 
    change 
  }: {
    title: string;
    value: string | number;
    icon: React.ComponentType<{ className?: string }>;
    color: string;
    change?: string;
  }) => (
    <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
          {change && (
            <p className={`text-sm mt-1 ${change.startsWith('+') ? 'text-green-600' : 'text-red-600'}`}>
              {change}
            </p>
          )}
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="h-6 w-6 text-white" />
        </div>
      </div>
    </div>
  );

  const ProjectStatusChart = () => {
    const statusData = [
      { status: 'Completed', count: stats.completedProjects, color: 'bg-green-500' },
      { status: 'In Progress', count: stats.inProgressProjects, color: 'bg-blue-500' },
      { status: 'Overdue', count: stats.overdueProjects, color: 'bg-red-500' },
      { status: 'Planning', count: stats.totalProjects - stats.completedProjects - stats.inProgressProjects, color: 'bg-yellow-500' }
    ];

    const total = statusData.reduce((sum, item) => sum + item.count, 0);

    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Project Status Distribution</h3>
        <div className="space-y-4">
          {statusData.map((item) => (
            <div key={item.status} className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className={`w-4 h-4 rounded-full ${item.color}`}></div>
                <span className="text-sm font-medium text-gray-700">{item.status}</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-32 bg-gray-200 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full ${item.color}`}
                    style={{ width: `${total > 0 ? (item.count / total) * 100 : 0}%` }}
                  ></div>
                </div>
                <span className="text-sm font-medium text-gray-900 w-8 text-right">{item.count}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const RecentActivity = () => (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h3>
      <div className="space-y-4">
        {projects.slice(0, 5).map((project) => (
          <div key={project.id} className="flex items-center space-x-3 p-3 rounded-lg bg-gray-50">
            <div className="flex-shrink-0">
              <div className={`w-3 h-3 rounded-full ${
                project.status === 'completed' ? 'bg-green-500' :
                project.status === 'in_progress' ? 'bg-blue-500' :
                'bg-yellow-500'
              }`}></div>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{project.name}</p>
              <p className="text-sm text-gray-500">{project.status}</p>
            </div>
            <div className="flex-shrink-0">
              <span className="text-sm text-gray-500">{project.progress}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Analytics Dashboard</h1>
        <p className="text-gray-600">Track your project performance and team productivity</p>
        
        <div className="mt-4 flex space-x-2">
          {(['7d', '30d', '90d', '1y'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                timeRange === range
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              }`}
            >
              {range === '7d' ? '7 Days' : 
               range === '30d' ? '30 Days' :
               range === '90d' ? '90 Days' : '1 Year'}
            </button>
          ))}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Total Projects"
          value={stats.totalProjects}
          icon={ChartBarIcon}
          color="bg-blue-500"
          change="+12%"
        />
        <StatCard
          title="Completed"
          value={stats.completedProjects}
          icon={CheckCircleIcon}
          color="bg-green-500"
          change="+8%"
        />
        <StatCard
          title="In Progress"
          value={stats.inProgressProjects}
          icon={ClockIcon}
          color="bg-yellow-500"
          change="+5%"
        />
        <StatCard
          title="Overdue"
          value={stats.overdueProjects}
          icon={ExclamationTriangleIcon}
          color="bg-red-500"
          change="-2%"
        />
      </div>

      {/* Charts and Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ProjectStatusChart />
        <RecentActivity />
      </div>

      {/* Team Performance */}
      <div className="mt-8">
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Team Performance</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <UsersIcon className="h-8 w-8 text-blue-500 mx-auto mb-2" />
              <p className="text-2xl font-bold text-gray-900">{stats.teamMembers}</p>
              <p className="text-sm text-gray-600">Active Members</p>
            </div>
            <div className="text-center">
              <CalendarIcon className="h-8 w-8 text-green-500 mx-auto mb-2" />
              <p className="text-2xl font-bold text-gray-900">{stats.avgCompletionTime}</p>
              <p className="text-sm text-gray-600">Avg. Completion (days)</p>
            </div>
            <div className="text-center">
              <CheckCircleIcon className="h-8 w-8 text-purple-500 mx-auto mb-2" />
              <p className="text-2xl font-bold text-gray-900">
                {stats.totalTasks > 0 ? Math.round((stats.completedTasks / stats.totalTasks) * 100) : 0}%
              </p>
              <p className="text-sm text-gray-600">Task Completion Rate</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
