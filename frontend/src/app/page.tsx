"use client";

import React, { useState, useEffect } from 'react';
import { ProjectDashboard } from '@/components/ProjectDashboard';
import { ConversationPanel } from '@/components/ConversationPanel';
import { WBSVisualizer } from '@/components/WBSVisualizer';
import { SprintPlanner } from '@/components/SprintPlanner';
import { ReportsDashboard } from '@/components/ReportsDashboard';
import { Header } from '@/components/Header';
import { Sidebar } from '@/components/Sidebar';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useConversation } from '@/hooks/useConversation';

type TabType = 'chat' | 'projects' | 'analytics' | 'wbs' | 'sprint' | 'reports';

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<TabType>('chat');
  const [sessionId] = useState(() => `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
  
  const { messages, sendMessage, isConnected } = useWebSocket(sessionId);
  const { conversationState, intent, missingFields } = useConversation(messages);

  // Store last generated WBS data from chat
  const [wbsData, setWbsData] = useState<any>(null);

  // Extract WBS data from chat messages
  useEffect(() => {
    const lastMessage = messages[messages.length - 1];
    if (lastMessage && lastMessage.data && lastMessage.data.wbs) {
      setWbsData(lastMessage.data.wbs);
    }
  }, [messages]);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <div className="flex">
        <Sidebar 
          activeTab={activeTab} 
          onTabChange={setActiveTab}
          isConnected={isConnected}
        />
        
        <main className="flex-1 p-6">
          {activeTab === 'chat' && (
            <div className="max-w-4xl mx-auto">
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
            <ProjectDashboard />
          )}
          
          {activeTab === 'wbs' && (
            <WBSVisualizer wbsData={wbsData} onClose={() => setActiveTab('chat')} />
          )}
          
          {activeTab === 'sprint' && (
            <SprintPlanner onClose={() => setActiveTab('projects')} />
          )}
          
          {activeTab === 'reports' && (
            <ReportsDashboard onClose={() => setActiveTab('projects')} />
          )}
          
          {activeTab === 'analytics' && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-2xl font-bold mb-4">Analytics</h2>
              <p className="text-gray-600">Analytics dashboard coming soon...</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
