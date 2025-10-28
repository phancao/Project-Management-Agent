"use client";

import React, { useState, useEffect } from 'react';
import { ProjectDashboard } from '@/components/ProjectDashboard';
import { ConversationPanel } from '@/components/ConversationPanel';
import { Header } from '@/components/Header';
import { Sidebar } from '@/components/Sidebar';
import { AnalyticsDashboard } from '@/components/AnalyticsDashboard';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useConversation } from '@/hooks/useConversation';
import { useProjects } from '@/hooks/useProjects';
import { useNotifications } from '@/hooks/useNotifications';

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<'chat' | 'projects' | 'analytics' | 'tasks' | 'team'>('chat');
  const [sessionId] = useState(() => `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
  
  const { messages, sendMessage, isConnected } = useWebSocket(sessionId);
  const { conversationState, intent, missingFields } = useConversation(messages);
  const { projects, createProject, updateProject, deleteProject } = useProjects();
  const { notifications, markAsRead } = useNotifications();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <Header notifications={notifications} onMarkAsRead={markAsRead} />
      
      <div className="flex h-screen">
        <Sidebar 
          activeTab={activeTab} 
          onTabChange={setActiveTab}
          isConnected={isConnected}
          notificationCount={notifications.filter(n => !n.read).length}
        />
        
        <main className="flex-1 overflow-y-auto">
          <div className="p-6">
            {activeTab === 'chat' && (
              <div className="max-w-6xl mx-auto">
                <div className="mb-6">
                  <h1 className="text-3xl font-bold text-gray-900 mb-2">AI Project Assistant</h1>
                  <p className="text-gray-600">Get help with project planning, task management, and team coordination</p>
                </div>
                <ConversationPanel
                  messages={messages}
                  onSendMessage={sendMessage}
                  conversationState={conversationState}
                  intent={intent}
                  missingFields={missingFields}
                  sessionId={sessionId}
                />
              </div>
            )}
            
            {activeTab === 'projects' && (
              <ProjectDashboard 
                projects={projects}
                onCreateProject={createProject}
                onUpdateProject={updateProject}
                onDeleteProject={deleteProject}
              />
            )}
            
            {activeTab === 'tasks' && (
              <div className="max-w-6xl mx-auto">
                <div className="mb-6">
                  <h1 className="text-3xl font-bold text-gray-900 mb-2">Task Management</h1>
                  <p className="text-gray-600">Manage your tasks and track progress</p>
                </div>
                <div className="bg-white rounded-xl shadow-lg p-6">
                  <p className="text-gray-600">Task management interface coming soon...</p>
                </div>
              </div>
            )}
            
            {activeTab === 'team' && (
              <div className="max-w-6xl mx-auto">
                <div className="mb-6">
                  <h1 className="text-3xl font-bold text-gray-900 mb-2">Team Management</h1>
                  <p className="text-gray-600">Coordinate with your team members</p>
                </div>
                <div className="bg-white rounded-xl shadow-lg p-6">
                  <p className="text-gray-600">Team management interface coming soon...</p>
                </div>
              </div>
            )}
            
            {activeTab === 'analytics' && (
              <AnalyticsDashboard projects={projects} />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
