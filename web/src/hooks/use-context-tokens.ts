// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useMemo } from "react";
import { useSettingsStore } from "~/core/store/settings-store";
import { useStore } from "~/core/store/store";
import { countMessagesTokens, getModelTokenLimit } from "~/utils/token-counter";

/**
 * Hook to calculate current context token usage and limit.
 * Returns token count, limit, and percentage used.
 */
export function useContextTokens() {
  const messages = useStore((state) => state.messages);
  const messageIds = useStore((state) => state.messageIds);
  const modelName = useSettingsStore((state) => state.general.modelName);
  const modelProvider = useSettingsStore((state) => state.general.modelProvider);
  
  const { tokenCount, tokenLimit, percentage } = useMemo(() => {
    // Build conversation history from messages
    const conversationMessages = messageIds
      .map((id) => messages.get(id))
      .filter((msg): msg is NonNullable<typeof msg> => msg !== undefined)
      .map((msg) => ({
        role: msg.role || "user",
        content: msg.content || "",
        name: msg.agent,
        agent: msg.agent, // Include agent type for system prompt estimation
        toolCalls: msg.toolCalls, // Include tool calls for accurate token counting
      }));
    
    // Count tokens in conversation
    const count = countMessagesTokens(conversationMessages);
    
    // Get token limit for current model
    const limit = getModelTokenLimit(modelName);
    
    // Calculate percentage
    const pct = limit > 0 ? Math.min(100, (count / limit) * 100) : 0;
    
    return {
      tokenCount: count,
      tokenLimit: limit,
      percentage: pct,
    };
  }, [messages, messageIds, modelName, modelProvider]);
  
  return {
    tokenCount,
    tokenLimit,
    percentage,
    modelName: modelName || "default",
  };
}


