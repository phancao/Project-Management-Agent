"use client";

import React, { useState, useEffect } from 'react';
import { ChatKit } from '@openai/chatkit-react';
import { ProjectDashboard } from '@/components/ProjectDashboard';
import { ConversationPanel } from '@/components/ConversationPanel';
import { Header } from '@/components/Header';
import { Sidebar } from '@/components/Sidebar';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useConversation } from '@/hooks/useConversation';

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<'chat' | 'projects' | 'analytics'>('chat');
  const [sessionId] = useState(() => `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
  
  const { messages, sendMessage, isConnected } = useWebSocket(sessionId);
  const { conversationState, intent, missingFields } = useConversation(messages);

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
