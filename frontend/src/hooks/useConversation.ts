"use client";

import { useState, useEffect } from 'react';

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

interface UseConversationReturn {
  conversationState: string;
  intent: string;
  missingFields: string[];
  isGatheringContext: boolean;
  isResearching: boolean;
  isPlanning: boolean;
  isExecuting: boolean;
  isCompleted: boolean;
}

export function useConversation(messages: Message[]): UseConversationReturn {
  const [conversationState, setConversationState] = useState('intent_detection');
  const [intent, setIntent] = useState('unknown');
  const [missingFields, setMissingFields] = useState<string[]>([]);

  useEffect(() => {
    // Get the latest assistant message to extract state information
    const latestAssistantMessage = messages
      .filter(msg => msg.role === 'assistant')
      .pop();

    if (latestAssistantMessage) {
      if (latestAssistantMessage.state) {
        setConversationState(latestAssistantMessage.state);
      }
      if (latestAssistantMessage.intent) {
        setIntent(latestAssistantMessage.intent);
      }
      if (latestAssistantMessage.missing_fields) {
        setMissingFields(latestAssistantMessage.missing_fields);
      }
    }
  }, [messages]);

  const isGatheringContext = conversationState === 'context_gathering';
  const isResearching = conversationState === 'research_phase';
  const isPlanning = conversationState === 'planning_phase';
  const isExecuting = conversationState === 'execution_phase';
  const isCompleted = conversationState === 'completed';

  return {
    conversationState,
    intent,
    missingFields,
    isGatheringContext,
    isResearching,
    isPlanning,
    isExecuting,
    isCompleted,
  };
}
