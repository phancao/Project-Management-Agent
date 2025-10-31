"use client";

import { useState, useEffect, useCallback, useRef } from 'react';

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
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Build WS URL from NEXT_PUBLIC_API_URL (which points to http(s)://host:port/api)
    const httpBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
    // Strip trailing /api
    const base = httpBase.replace(/\/?api\/?$/, '');
    const wsProtocol = base.startsWith('https') ? 'wss' : 'ws';
    const wsUrl = `${wsProtocol}://${base.replace(/^https?:\/\//, '')}/ws/chat/${encodeURIComponent(sessionId)}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    ws.onerror = (ev) => {
      console.error('WebSocket error:', ev);
      setError('Connection failed. Please try again.');
    };
      
    ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string);
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
      } catch (e) {
        console.error('Failed to parse message:', e);
      }
    };

    return () => {
      try { ws.close(); } catch {}
      wsRef.current = null;
    };
  }, [sessionId]);

  const sendMessage = useCallback(async (message: string) => {
    if (!wsRef.current || !isConnected) {
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
      // Send message as JSON text per FastAPI websocket
      wsRef.current.send(
        JSON.stringify({
        message,
        session_id: sessionId,
          user_id: 'current_user', // TODO: integrate auth
        timestamp: new Date().toISOString(),
        })
      );
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
