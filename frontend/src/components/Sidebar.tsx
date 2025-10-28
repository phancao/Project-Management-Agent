"use client";

import React from 'react';
import { 
  MessageCircle, 
  FolderOpen, 
  BarChart3, 
  CheckSquare, 
  Users, 
  Wifi, 
  WifiOff,
  Plus,
  Search,
  FileText,
  Calendar,
  Settings
} from 'lucide-react';

interface SidebarProps {
  activeTab: 'chat' | 'projects' | 'analytics' | 'tasks' | 'team';
  onTabChange: (tab: 'chat' | 'projects' | 'analytics' | 'tasks' | 'team') => void;
  isConnected: boolean;
  notificationCount?: number;
}

export function Sidebar({ activeTab, onTabChange, isConnected, notificationCount = 0 }: SidebarProps) {
  const tabs = [
    {
      id: 'chat' as const,
      name: 'AI Assistant',
      icon: MessageCircle,
      description: 'Chat with AI agents',
      badge: notificationCount > 0 ? notificationCount : undefined
    },
    {
      id: 'projects' as const,
      name: 'Projects',
      icon: FolderOpen,
      description: 'Manage your projects'
    },
    {
      id: 'tasks' as const,
      name: 'Tasks',
      icon: CheckSquare,
      description: 'Track tasks & progress'
    },
    {
      id: 'team' as const,
      name: 'Team',
      icon: Users,
      description: 'Team collaboration'
    },
    {
      id: 'analytics' as const,
      name: 'Analytics',
      icon: BarChart3,
      description: 'Project insights'
    }
  ];

  const quickActions = [
    {
      name: 'New Project',
      icon: Plus,
      action: () => onTabChange('projects')
    },
    {
      name: 'Research Topic',
      icon: Search,
      action: () => onTabChange('chat')
    },
    {
      name: 'View Templates',
      icon: FileText,
      action: () => console.log('View templates')
    },
    {
      name: 'Schedule Meeting',
      icon: Calendar,
      action: () => console.log('Schedule meeting')
    }
  ];

  return (
    <aside className="w-72 bg-white shadow-sm border-r border-gray-200 flex flex-col h-full">
      <div className="p-4 flex-1">
        {/* Connection Status */}
        <div className="flex items-center space-x-2 mb-6 p-3 bg-gray-50 rounded-lg">
          {isConnected ? (
            <Wifi className="w-5 h-5 text-green-500" />
          ) : (
            <WifiOff className="w-5 h-5 text-red-500" />
          )}
          <span className={`text-sm font-medium ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>

        {/* Navigation */}
        <nav className="space-y-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`w-full flex items-center justify-between px-3 py-3 rounded-lg text-left transition-all duration-200 group ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 border border-blue-200 shadow-sm'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className={`w-5 h-5 ${isActive ? 'text-blue-600' : 'text-gray-400 group-hover:text-gray-600'}`} />
                  <div>
                    <div className="font-medium text-sm">{tab.name}</div>
                    <div className="text-xs text-gray-500">{tab.description}</div>
                  </div>
                </div>
                {tab.badge && (
                  <span className="bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                    {tab.badge > 9 ? '9+' : tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Quick Actions */}
        <div className="mt-8">
          <h3 className="text-sm font-semibold text-gray-900 mb-3 px-1">Quick Actions</h3>
          <div className="space-y-1">
            {quickActions.map((action, index) => {
              const Icon = action.icon;
              return (
                <button
                  key={index}
                  onClick={action.action}
                  className="w-full flex items-center space-x-3 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-900 rounded-lg transition-colors"
                >
                  <Icon className="w-4 h-4" />
                  <span>{action.name}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Recent Projects */}
        <div className="mt-8">
          <h3 className="text-sm font-semibold text-gray-900 mb-3 px-1">Recent Projects</h3>
          <div className="space-y-1">
            <div className="px-3 py-2 text-sm text-gray-500 bg-gray-50 rounded-lg">
              <div className="font-medium">E-commerce Platform</div>
              <div className="text-xs">Updated 2 hours ago</div>
            </div>
            <div className="px-3 py-2 text-sm text-gray-500 bg-gray-50 rounded-lg">
              <div className="font-medium">Mobile App</div>
              <div className="text-xs">Updated 1 day ago</div>
            </div>
            <div className="px-3 py-2 text-sm text-gray-500 bg-gray-50 rounded-lg">
              <div className="font-medium">Data Analytics</div>
              <div className="text-xs">Updated 3 days ago</div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Section */}
      <div className="p-4 border-t border-gray-200">
        <div className="flex items-center space-x-3 p-2 hover:bg-gray-50 rounded-lg cursor-pointer">
          <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
            <span className="text-white text-sm font-medium">JD</span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-gray-900">John Doe</div>
            <div className="text-xs text-gray-500">Project Manager</div>
          </div>
          <Settings className="w-4 h-4 text-gray-400" />
        </div>
      </div>
    </aside>
  );
}
