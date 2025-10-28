"use client";

import React from 'react';
import { MessageCircle, FolderOpen, BarChart3, Wifi, WifiOff } from 'lucide-react';

interface SidebarProps {
  activeTab: 'chat' | 'projects' | 'analytics';
  onTabChange: (tab: 'chat' | 'projects' | 'analytics') => void;
  isConnected: boolean;
}

export function Sidebar({ activeTab, onTabChange, isConnected }: SidebarProps) {
  const tabs = [
    {
      id: 'chat' as const,
      name: 'Chat',
      icon: MessageCircle,
      description: 'Talk to the AI agent'
    },
    {
      id: 'projects' as const,
      name: 'Projects',
      icon: FolderOpen,
      description: 'Manage your projects'
    },
    {
      id: 'analytics' as const,
      name: 'Analytics',
      icon: BarChart3,
      description: 'View project analytics'
    }
  ];

  return (
    <aside className="w-64 bg-white shadow-sm border-r border-gray-200">
      <div className="p-4">
        <div className="flex items-center space-x-2 mb-6">
          {isConnected ? (
            <Wifi className="w-5 h-5 text-green-500" />
          ) : (
            <WifiOff className="w-5 h-5 text-red-500" />
          )}
          <span className={`text-sm font-medium ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>

        <nav className="space-y-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-left transition-colors ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <Icon className="w-5 h-5" />
                <div>
                  <div className="font-medium">{tab.name}</div>
                  <div className="text-xs text-gray-500">{tab.description}</div>
                </div>
              </button>
            );
          })}
        </nav>

        <div className="mt-8 p-3 bg-gray-50 rounded-lg">
          <h3 className="text-sm font-medium text-gray-900 mb-2">Quick Actions</h3>
          <div className="space-y-1">
            <button className="w-full text-left text-xs text-blue-600 hover:text-blue-800">
              + New Project
            </button>
            <button className="w-full text-left text-xs text-blue-600 hover:text-blue-800">
              + Research Topic
            </button>
            <button className="w-full text-left text-xs text-blue-600 hover:text-blue-800">
              View Templates
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
}
