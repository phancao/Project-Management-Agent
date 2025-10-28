"use client";

import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, CheckCircle, AlertCircle } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  type?: string;
  state?: string;
  intent?: string;
  missing_fields?: string[];
  data?: any;
}

interface ConversationPanelProps {
  messages: Message[];
  onSendMessage: (message: string) => void;
  conversationState: string;
  intent: string;
  missingFields: string[];
  sessionId: string;
}

export function ConversationPanel({
  messages,
  onSendMessage,
  conversationState,
  intent,
  missingFields,
  sessionId
}: ConversationPanelProps) {
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    const message = inputMessage.trim();
    setInputMessage('');
    setIsLoading(true);

    try {
      await onSendMessage(message);
    } finally {
      setIsLoading(false);
    }
  };

  const getStateIcon = (state: string) => {
    switch (state) {
      case 'intent_detection':
        return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />;
      case 'context_gathering':
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
      case 'research_phase':
        return <Loader2 className="w-4 h-4 animate-spin text-purple-500" />;
      case 'planning_phase':
        return <Loader2 className="w-4 h-4 animate-spin text-green-500" />;
      case 'execution_phase':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      default:
        return <Bot className="w-4 h-4 text-gray-500" />;
    }
  };

  const getStateColor = (state: string) => {
    switch (state) {
      case 'intent_detection':
        return 'bg-blue-100 text-blue-800';
      case 'context_gathering':
        return 'bg-yellow-100 text-yellow-800';
      case 'research_phase':
        return 'bg-purple-100 text-purple-800';
      case 'planning_phase':
        return 'bg-green-100 text-green-800';
      case 'execution_phase':
        return 'bg-green-100 text-green-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-200px)] bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Bot className="w-6 h-6 text-blue-600" />
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Project Management Agent</h2>
              <p className="text-sm text-gray-500">Session: {sessionId.slice(-8)}</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {getStateIcon(conversationState)}
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStateColor(conversationState)}`}>
              {conversationState.replace('_', ' ').toUpperCase()}
            </span>
          </div>
        </div>
        
        {intent && intent !== 'unknown' && (
          <div className="mt-2">
            <span className="text-xs text-gray-500">Intent: </span>
            <span className="text-xs font-medium text-blue-600">
              {intent.replace('_', ' ').toUpperCase()}
            </span>
          </div>
        )}
        
        {missingFields.length > 0 && (
          <div className="mt-2">
            <span className="text-xs text-gray-500">Missing: </span>
            <span className="text-xs text-yellow-600">
              {missingFields.join(', ')}
            </span>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 mt-8">
            <Bot className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p className="text-lg font-medium">Welcome to Project Management Agent!</p>
            <p className="text-sm">I can help you create projects, plan tasks, and manage your team.</p>
            <div className="mt-4 space-y-2">
              <p className="text-xs text-gray-400">Try saying:</p>
              <div className="space-y-1">
                <button
                  onClick={() => setInputMessage("Create a new software project")}
                  className="block mx-auto px-3 py-1 bg-blue-50 text-blue-600 rounded-full text-xs hover:bg-blue-100"
                >
                  "Create a new software project"
                </button>
                <button
                  onClick={() => setInputMessage("Plan tasks for my project")}
                  className="block mx-auto px-3 py-1 bg-green-50 text-green-600 rounded-full text-xs hover:bg-green-100"
                >
                  "Plan tasks for my project"
                </button>
                <button
                  onClick={() => setInputMessage("Research AI project management")}
                  className="block mx-auto px-3 py-1 bg-purple-50 text-purple-600 rounded-full text-xs hover:bg-purple-100"
                >
                  "Research AI project management"
                </button>
              </div>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                <div className="flex items-start space-x-2">
                  {message.role === 'assistant' && (
                    <Bot className="w-4 h-4 mt-1 flex-shrink-0" />
                  )}
                  {message.role === 'user' && (
                    <User className="w-4 h-4 mt-1 flex-shrink-0" />
                  )}
                  <div className="flex-1">
                    <p className="text-sm">{message.content}</p>
                    {message.type && message.type !== 'message' && (
                      <div className="mt-2 text-xs opacity-75">
                        Type: {message.type}
                      </div>
                    )}
                    <div className="mt-1 text-xs opacity-75">
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-4 py-2 flex items-center space-x-2">
              <Bot className="w-4 h-4" />
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm text-gray-600">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSendMessage} className="p-4 border-t border-gray-200">
        <div className="flex space-x-2">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!inputMessage.trim() || isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            <Send className="w-4 h-4" />
            <span>Send</span>
          </button>
        </div>
      </form>
    </div>
  );
}
