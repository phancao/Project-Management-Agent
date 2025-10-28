"use client";

import { useState, useEffect, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';

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

interface UseWebSocketReturn {
  messages: Message[];
  sendMessage: (message: string) => Promise<void>;
  isConnected: boolean;
  error: string | null;
}

export function useWebSocket(sessionId: string): UseWebSocketReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    // Initialize WebSocket connection
    const socket = io(process.env.NEXT_PUBLIC_API_URL || 'ws://localhost:8000', {
      path: '/ws/chat',
      transports: ['websocket'],
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      setError(null);
    });

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    });

    socket.on('connect_error', (err) => {
      console.error('WebSocket connection error:', err);
      setError('Connection failed. Please try again.');
    });

    socket.on('message', (data: any) => {
      console.log('Received message:', data);
      
      const newMessage: Message = {
        id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        role: 'assistant',
        content: data.message || 'No message content',
        timestamp: new Date().toISOString(),
        type: data.type,
        state: data.state,
        intent: data.intent,
        missing_fields: data.missing_fields,
        data: data.data,
      };

      setMessages(prev => [...prev, newMessage]);
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [sessionId]);

  const sendMessage = useCallback(async (message: string) => {
    if (!socketRef.current || !isConnected) {
      setError('Not connected to server');
      return;
    }

    // Add user message to local state immediately
    const userMessage: Message = {
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);

    try {
      // Send message to server
      socketRef.current.emit('message', {
        message,
        session_id: sessionId,
        user_id: 'current_user', // TODO: Get from auth context
        timestamp: new Date().toISOString(),
      });
    } catch (err) {
      console.error('Error sending message:', err);
      setError('Failed to send message');
    }
  }, [sessionId, isConnected]);

  return {
    messages,
    sendMessage,
    isConnected,
    error,
  };
}
