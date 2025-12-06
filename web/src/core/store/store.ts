// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { nanoid } from "nanoid";
import { toast } from "sonner";
import { create } from "zustand";
import { useShallow } from "zustand/react/shallow";

import { chatStream, generatePodcast } from "../api";
import type { Message, Resource } from "../messages";
import { mergeMessage } from "../messages";
import { parseJSON } from "../utils";

import { getChatStreamSettings } from "./settings-store";
import { 
  type ResearchBlockType,
  getBlockTypeForAgent,
} from "./research-store";

/**
 * Build conversation history from messages for context.
 * This extracts user and assistant messages in chronological order.
 */
function buildConversationHistory(
  messages: Map<string, Message>,
  messageIds: string[],
  maxMessages = 20
): Array<{ role: string; content: string }> {
  const history: Array<{ role: string; content: string }> = [];
  
  // Get recent messages (excluding the very last one which is the current user message)
  const recentIds = messageIds.slice(Math.max(0, messageIds.length - maxMessages - 1), -1);
  
  for (const id of recentIds) {
    const msg = messages.get(id);
    if (!msg) continue;
    
    // Only include user and assistant messages with actual content
    if (msg.role === "user" && msg.content?.trim()) {
      history.push({ role: "user", content: msg.content });
    } else if (msg.role === "assistant" && msg.content?.trim()) {
      // Include assistant responses (reporter, coordinator, etc.)
      // Truncate very long responses to save tokens
      const content = msg.content.length > 2000 
        ? msg.content.substring(0, 2000) + "... [truncated]"
        : msg.content;
      history.push({ role: "assistant", content });
    }
  }
  
  return history;
}

const THREAD_ID = nanoid();

// Block types for different agents
export type ResearchBlockType = "react" | "planner" | "pm" | "researcher" | "coder";

export const useStore = create<{
  responding: boolean;
  threadId: string | undefined;
  messageIds: string[];
  messages: Map<string, Message>;
  researchIds: string[];
  researchPlanIds: Map<string, string>;
  researchReportIds: Map<string, string>;
  researchActivityIds: Map<string, string[]>;
  researchBlockTypes: Map<string, ResearchBlockType>; // Track block type for each research
  ongoingResearchId: string | null;
  openResearchId: string | null;

  appendMessage: (message: Message) => void;
  updateMessage: (message: Message) => void;
  updateMessages: (messages: Message[]) => void;
  openResearch: (researchId: string | null) => void;
  closeResearch: () => void;
  setOngoingResearch: (researchId: string | null) => void;
}>((set) => ({
  responding: false,
  threadId: THREAD_ID,
  messageIds: [],
  messages: new Map<string, Message>(),
  researchIds: [],
  researchPlanIds: new Map<string, string>(),
  researchReportIds: new Map<string, string>(),
  researchActivityIds: new Map<string, string[]>(),
  researchBlockTypes: new Map<string, ResearchBlockType>(),
  ongoingResearchId: null,
  openResearchId: null,

  appendMessage(message: Message) {
    set((state) => {
      // Prevent duplicate message IDs
      const isDuplicate = state.messageIds.includes(message.id);
      const newMessageIds = isDuplicate
        ? state.messageIds
        : [...state.messageIds, message.id];
      return {
        messageIds: newMessageIds,
        messages: new Map(state.messages).set(message.id, message),
      };
    });
  },
  updateMessage(message: Message) {
    // DEBUG: Log function entry for reporter messages
    if (message.agent === "reporter") {
      const state = useStore.getState();
      const existing = state.messages.get(message.id);
      const existingContentLen = existing?.content?.length ?? 0;
      const newContentLen = message.content?.length ?? 0;
      const existingLastChars = existing?.content?.slice(-50) ?? "";
      const newLastChars = message.content?.slice(-50) ?? "";
      console.log(`[DEBUG-UPDATE-ENTRY] 🚪 updateMessage ENTRY: messageId=${message.id}, existingContentLen=${existingContentLen}, newContentLen=${newContentLen}, isStreaming=${message.isStreaming}, finishReason=${message.finishReason}`);
      if (existingContentLen > 0) {
        console.log(`[DEBUG-UPDATE-ENTRY] 📝 Existing last 50 chars: "${existingLastChars}"`);
      }
      if (newContentLen > 0) {
        console.log(`[DEBUG-UPDATE-ENTRY] 📝 New last 50 chars: "${newLastChars}"`);
      }
      console.trace(`[DEBUG-UPDATE-ENTRY] Stack trace for updateMessage entry`);
    }
    
    set((state) => {
      const existing = state.messages.get(message.id);
      const existingContentLen = existing?.content?.length ?? 0;
      const newContentLen = message.content?.length ?? 0;
      const existingChunksLen = existing?.contentChunks?.length ?? 0;
      const newChunksLen = message.contentChunks?.length ?? 0;
      
      if (message.agent === "reporter") {
        const existingLastChars = existing?.content?.slice(-50) ?? "";
        const newLastChars = message.content?.slice(-50) ?? "";
        console.log(`[DEBUG-REPORTER-UPDATE] 🔄 updateMessage: messageId=${message.id}, existingLen=${existingContentLen}→${newContentLen}, existingChunks=${existingChunksLen}→${newChunksLen}, finishReason=${message.finishReason}, isStreaming=${message.isStreaming}`);
        if (existingContentLen > 0) {
          console.log(`[DEBUG-REPORTER-UPDATE] 📝 Existing last 50 chars: "${existingLastChars}"`);
        }
        if (newContentLen > 0) {
          console.log(`[DEBUG-REPORTER-UPDATE] 📝 New last 50 chars: "${newLastChars}"`);
        }
        console.trace(`[DEBUG-REPORTER-UPDATE] Stack trace for updateMessage call`);
      }
      
      if (existingContentLen > 0 && newContentLen === 0 && message.agent === "reporter") {
        console.error(`[DEBUG-REPORTER-UPDATE] ❌ REPORTER CONTENT LOSS! messageId=${message.id}, existingContentLen=${existingContentLen}, newContentLen=${newContentLen}, isStreaming=${message.isStreaming}, finishReason=${message.finishReason}`);
        console.trace("Stack trace for content loss");
        // Preserve existing content if new message has empty content
        message.content = existing.content;
        message.contentChunks = existing.contentChunks ?? [];
        console.log(`[DEBUG-REPORTER-UPDATE] ✅ Preserved existing content: contentLen=${message.content?.length ?? 0}, chunksLen=${message.contentChunks?.length ?? 0}`);
      }
      
      const updatedMessage = { ...message };
      const result = {
        messages: new Map(state.messages).set(message.id, updatedMessage),
      };
      
      // DEBUG: Log function exit for reporter messages
      if (message.agent === "reporter") {
        const finalContentLen = updatedMessage.content?.length ?? 0;
        const finalChunksLen = updatedMessage.contentChunks?.length ?? 0;
        const finalLastChars = updatedMessage.content?.slice(-50) ?? "";
        console.log(`[DEBUG-UPDATE-EXIT] 🚪 updateMessage EXIT: messageId=${message.id}, finalContentLen=${finalContentLen}, finalChunksLen=${finalChunksLen}`);
        if (finalContentLen > 0) {
          console.log(`[DEBUG-UPDATE-EXIT] 📝 Final last 50 chars: "${finalLastChars}"`);
        }
      }
      
      return result;
    });
  },
  updateMessages(messages: Message[]) {
    // DEBUG: Log function entry for reporter messages
    const reporterMessages = messages.filter(m => m.agent === "reporter");
    if (reporterMessages.length > 0) {
      console.log(`[DEBUG-BATCH-ENTRY] 🚪 updateMessages ENTRY: processing ${reporterMessages.length} reporter messages out of ${messages.length} total`);
      reporterMessages.forEach(m => {
        const state = useStore.getState();
        const existing = state.messages.get(m.id);
        const existingContentLen = existing?.content?.length ?? 0;
        const newContentLen = m.content?.length ?? 0;
        console.log(`[DEBUG-BATCH-ENTRY] 📋 Reporter message: messageId=${m.id}, existingLen=${existingContentLen}, newLen=${newContentLen}`);
      });
      console.trace(`[DEBUG-BATCH-ENTRY] Stack trace for updateMessages entry`);
    }
    
    set((state) => {
      const newMessages = new Map(state.messages);
      if (reporterMessages.length > 0) {
        console.log(`[DEBUG-REPORTER-BATCH] 📦 updateMessages: processing ${reporterMessages.length} reporter messages`);
      }
      
      messages.forEach((m) => {
        // Debug logging for reporter messages
        if (m.agent === "reporter") {
          const existing = state.messages.get(m.id);
          const existingContentLen = existing?.content?.length ?? 0;
          const newContentLen = m.content?.length ?? 0;
          const existingChunksLen = existing?.contentChunks?.length ?? 0;
          const newChunksLen = m.contentChunks?.length ?? 0;
          const existingLastChars = existing?.content?.slice(-50) ?? "";
          const newLastChars = m.content?.slice(-50) ?? "";
          
          console.log(`[DEBUG-REPORTER-BATCH] 🔄 messageId=${m.id}, existingLen=${existingContentLen}→${newContentLen}, existingChunks=${existingChunksLen}→${newChunksLen}, finishReason=${m.finishReason}`);
          if (existingContentLen > 0) {
            console.log(`[DEBUG-REPORTER-BATCH] 📝 Existing last 50 chars: "${existingLastChars}"`);
          }
          if (newContentLen > 0) {
            console.log(`[DEBUG-REPORTER-BATCH] 📝 New last 50 chars: "${newLastChars}"`);
          }
          
          if (existingContentLen > 0 && newContentLen === 0) {
            console.error(`[DEBUG-REPORTER-BATCH] ❌ REPORTER CONTENT LOSS in batch update! messageId=${m.id}, existingContentLen=${existingContentLen}, newContentLen=${newContentLen}`);
            console.trace("Stack trace for batch content loss");
            // Preserve existing content
            m.content = existing.content;
            m.contentChunks = existing.contentChunks ?? [];
            console.log(`[DEBUG-REPORTER-BATCH] ✅ Preserved existing content: contentLen=${m.content?.length ?? 0}, chunksLen=${m.contentChunks?.length ?? 0}`);
          }
        }
        newMessages.set(m.id, m);
      });
      
      // DEBUG: Log function exit for reporter messages
      if (reporterMessages.length > 0) {
        reporterMessages.forEach(m => {
          const finalMsg = newMessages.get(m.id);
          const finalContentLen = finalMsg?.content?.length ?? 0;
          const finalChunksLen = finalMsg?.contentChunks?.length ?? 0;
          const finalLastChars = finalMsg?.content?.slice(-50) ?? "";
          console.log(`[DEBUG-BATCH-EXIT] 🚪 updateMessages EXIT: messageId=${m.id}, finalContentLen=${finalContentLen}, finalChunksLen=${finalChunksLen}`);
          if (finalContentLen > 0) {
            console.log(`[DEBUG-BATCH-EXIT] 📝 Final last 50 chars: "${finalLastChars}"`);
          }
        });
      }
      
      return { messages: newMessages };
    });
  },
  openResearch(researchId: string | null) {
    set({ openResearchId: researchId });
  },
  closeResearch() {
    set({ openResearchId: null });
  },
  setOngoingResearch(researchId: string | null) {
    set({ ongoingResearchId: researchId });
  },
}));

export async function sendMessage(
  content?: string,
  {
    interruptFeedback,
    resources,
  }: {
    interruptFeedback?: string;
    resources?: Array<Resource>;
  } = {},
  options: { abortSignal?: AbortSignal } = {},
) {
  if (content != null) {
    appendMessage({
      id: nanoid(),
      threadId: THREAD_ID,
      role: "user",
      content: content,
      contentChunks: [content],
      resources,
    });
  }

  const settings = getChatStreamSettings();
  
  // Build conversation history from existing messages for context continuity
  const state = useStore.getState();
  const conversationHistory = buildConversationHistory(
    state.messages,
    state.messageIds,
    20 // Max 20 previous messages for context
  );
  
  const stream = chatStream(
    content ?? "[REPLAY]",
    {
      thread_id: THREAD_ID,
      interrupt_feedback: interruptFeedback,
      resources,
      auto_accepted_plan: settings.autoAcceptedPlan,
      enable_clarification: settings.enableClarification ?? false,
      max_clarification_rounds: settings.maxClarificationRounds ?? 3,
      enable_deep_thinking: settings.enableDeepThinking ?? false,
      enable_background_investigation:
        settings.enableBackgroundInvestigation ?? true,
      max_plan_iterations: settings.maxPlanIterations,
      max_step_num: settings.maxStepNum,
      max_search_results: settings.maxSearchResults,
      report_style: settings.reportStyle,
      mcp_settings: settings.mcpSettings,
      conversation_history: conversationHistory,
      model_provider: settings.modelProvider,
      model_name: settings.modelName,
      search_provider: settings.searchProvider,
    },
    options,
  );

  setResponding(true);
  let messageId: string | undefined;
  const pendingUpdates = new Map<string, Message>();
  let updateTimer: NodeJS.Timeout | undefined;

  const scheduleUpdate = () => {
    if (updateTimer) clearTimeout(updateTimer);
    updateTimer = setTimeout(() => {
      // Batch update message status
      if (pendingUpdates.size > 0) {
        const reporterUpdates = Array.from(pendingUpdates.values()).filter(m => m.agent === "reporter");
        if (reporterUpdates.length > 0) {
          console.log(`[DEBUG-SCHEDULE-ENTRY] 🚪 scheduleUpdate ENTRY: processing ${reporterUpdates.length} reporter messages out of ${pendingUpdates.size} total`);
          reporterUpdates.forEach(m => {
            const contentLen = m.content?.length ?? 0;
            const chunksLen = m.contentChunks?.length ?? 0;
            const lastChars = m.content?.slice(-50) ?? "";
            console.log(`[DEBUG-REPORTER-SCHEDULE] 📋 messageId=${m.id}, contentLen=${contentLen}, chunksLen=${chunksLen}, finishReason=${m.finishReason}`);
            if (contentLen > 0) {
              console.log(`[DEBUG-REPORTER-SCHEDULE] 📝 Last 50 chars: "${lastChars}"`);
            }
          });
          console.trace(`[DEBUG-SCHEDULE-ENTRY] Stack trace for scheduleUpdate entry`);
        }
        const messagesToUpdate = Array.from(pendingUpdates.values());
        useStore.getState().updateMessages(messagesToUpdate);
        
        // DEBUG: Log after updateMessages call
        if (reporterUpdates.length > 0) {
          console.log(`[DEBUG-SCHEDULE-EXIT] 🚪 scheduleUpdate EXIT: updated ${reporterUpdates.length} reporter messages`);
          reporterUpdates.forEach(m => {
            const state = useStore.getState();
            const updatedMsg = state.messages.get(m.id);
            const finalContentLen = updatedMsg?.content?.length ?? 0;
            const finalChunksLen = updatedMsg?.contentChunks?.length ?? 0;
            const finalLastChars = updatedMsg?.content?.slice(-50) ?? "";
            console.log(`[DEBUG-SCHEDULE-EXIT] 📋 messageId=${m.id}, finalContentLen=${finalContentLen}, finalChunksLen=${finalChunksLen}`);
            if (finalContentLen > 0) {
              console.log(`[DEBUG-SCHEDULE-EXIT] 📝 Final last 50 chars: "${finalLastChars}"`);
            }
          });
        }
        
        pendingUpdates.clear();
      }
    }, 16); // ~60fps
  };

  try {
    for await (const event of stream) {
      const { type, data } = event;
      
      // DEBUG: Log all events to see what's being received
      if (data.agent === "reporter" || type === "message_chunk" && data.agent === "reporter") {
        console.log(`[DEBUG-REPORTER-EVENT] 📨 Event received: type=${type}, agent=${data.agent}, id=${data.id}, hasContent=${!!data.content}, contentLen=${data.content?.length ?? 0}, finishReason=${data.finish_reason}`);
      }
      
      // Handle PM refresh events to update PM views
      // Type assertion needed because ChatEvent type doesn't include pm_refresh
      if ((type as string) === "pm_refresh") {
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("pm_refresh", { 
            detail: { type: "pm_refresh", data } 
          }));
        }
        continue;
      }
      
      let message: Message | undefined;
      
      // Handle tool_call_result specially: use the message that contains the tool call
      if (type === "tool_call_result") {
        console.log(`[Store] tool_call_result event received: tool_call_id=${data.tool_call_id}`);
        message = findMessageByToolCallId(data.tool_call_id);
        if (message) {
          // Use the found message's ID, not data.id
          messageId = message.id;
          console.log(`[Store] Found message for tool_call_result: id=${message.id}, agent=${message.agent}`);
        } else {
          // Shouldn't happen, but handle gracefully
          console.warn(`[Store] Could not find message for tool_call_id=${data.tool_call_id}, skipping`);
          continue; // Skip this event
        }
      } else {
        // For other event types, use data.id
        messageId = data.id;
        
        // Generate ID if missing (backend should provide it, but handle gracefully)
        if (!messageId) {
          messageId = `run--${nanoid(32)}`;
        }
        
        if (!existsMessage(messageId)) {
          message = {
            id: messageId,
            threadId: data.thread_id,
            agent: data.agent,
            role: data.role,
            content: "",
            contentChunks: [],
            reasoningContent: "",
            reasoningContentChunks: [],
            isStreaming: true,
            interruptFeedback,
          };
          // DEBUG: Log when reporter message is created
          if (data.agent === "reporter") {
            console.log(`[DEBUG-REPORTER-CREATE] 🆕 Reporter message created: messageId=${messageId}, agent=${data.agent}, role=${data.role}`);
          }
          appendMessage(message);
        }
      }
      
      message ??= getMessage(messageId);
      if (message) {
        const previousIsStreaming = message.isStreaming;
        const contentBeforeMerge = message.content?.length ?? 0;
        const chunksBeforeMerge = message.contentChunks?.length ?? 0;
        const lastCharsBefore = message.content?.slice(-50) ?? "";
        
        // DEBUG: Log when reporter content starts streaming
        if (message.agent === "reporter" && type === "message_chunk" && data.content) {
          console.log(`[DEBUG-REPORTER-STREAM] 📥 Reporter chunk received: messageId=${message.id}, chunkLen=${data.content.length}, contentBefore=${contentBeforeMerge}, chunkText="${data.content.substring(0, 50)}..."`);
        }
        
        message = mergeMessage(message, event);
        const contentAfterMerge = message.content?.length ?? 0;
        const chunksAfterMerge = message.contentChunks?.length ?? 0;
        const lastCharsAfter = message.content?.slice(-50) ?? "";
        
        // Comprehensive debug logging for reporter messages
        if (message.agent === "reporter") {
          console.log(`[DEBUG-REPORTER-MERGE] 🔄 mergeMessage: messageId=${message.id}, eventType=${type}, contentBefore=${contentBeforeMerge}→${contentAfterMerge}, chunksBefore=${chunksBeforeMerge}→${chunksAfterMerge}, hasFinishReason=${!!event.data.finish_reason}`);
          if (contentBeforeMerge > 0) {
            console.log(`[DEBUG-REPORTER-MERGE] 📝 Last 50 chars before: "${lastCharsBefore}"`);
          }
          if (contentAfterMerge > 0) {
            console.log(`[DEBUG-REPORTER-MERGE] 📝 Last 50 chars after: "${lastCharsAfter}"`);
          }
          if (contentBeforeMerge > 0 && contentAfterMerge === 0) {
            console.error(`[DEBUG-REPORTER-MERGE] ❌ Content lost during merge! messageId=${message.id}, eventType=${type}`);
            console.trace("Stack trace for content loss in merge");
          }
          if (contentBeforeMerge > contentAfterMerge && contentAfterMerge > 0) {
            console.warn(`[DEBUG-REPORTER-MERGE] ⚠️ Content reduced during merge! messageId=${message.id}, before=${contentBeforeMerge}, after=${contentAfterMerge}, eventType=${type}`);
          }
        }
        
        // If finish_reason is present, apply update immediately to ensure UI updates quickly
        // This is especially important for reporter messages to show the final report
        if (event.data.finish_reason && previousIsStreaming) {
          // Immediately update using helper function to trigger UI re-render and run reporter logic
          if (message.agent === "reporter") {
            const finalContent = message.content ?? "";
            const finalChunks = message.contentChunks?.length ?? 0;
            console.log(`[DEBUG-REPORTER-FINISH] ✅ finish_reason received: messageId=${message.id}, contentLen=${finalContent.length}, chunksLen=${finalChunks}, lastChars="${finalContent.slice(-50)}"`);
          }
          updateMessage(message);
          // Remove from pending updates to avoid duplicate update
          pendingUpdates.delete(message.id);
        } else {
          // Collect pending messages for update, instead of updating immediately.
          if (message.agent === "reporter") {
            console.log(`[DEBUG-REPORTER-PENDING] 📋 Adding to pendingUpdates: messageId=${message.id}, contentLen=${message.content?.length ?? 0}`);
          }
          pendingUpdates.set(message.id, message);
          scheduleUpdate();
        }
      }
    }
    
    // Stream completed successfully - ensure all messages are marked as not streaming
    // Process any remaining pending updates
    if (updateTimer) clearTimeout(updateTimer);
    if (pendingUpdates.size > 0) {
      // Mark all pending messages as not streaming
      for (const [id, msg] of pendingUpdates.entries()) {
        if (msg.isStreaming) {
          msg.isStreaming = false;
        }
      }
      useStore.getState().updateMessages(Array.from(pendingUpdates.values()));
      pendingUpdates.clear();
    }
    
    // Ensure all messages with finish_reason are marked as not streaming
    // CRITICAL: Process reporter messages LAST so they can find the researchId from ongoingResearchId
    const state = useStore.getState();
    const finishedMessages: Message[] = [];
    const reporterMessages: Message[] = [];
    
    console.log(`[Store] Cleanup loop starting: checking ${state.messages.size} messages`);
    
    // Collect all finished messages, separating reporter messages
    // NOTE: After immediate update, isStreaming is already false, so we check finishReason only
    for (const [id, msg] of state.messages.entries()) {
      if (msg.agent === "reporter") {
        const contentLen = msg.content?.length ?? 0;
        console.log(`[Store] Cleanup loop checking reporter: messageId=${id}, isStreaming=${msg.isStreaming}, finishReason=${msg.finishReason}, contentLen=${contentLen}`);
      }
      // Check if message has finishReason (regardless of isStreaming, since it might have been set to false already)
      if (msg.finishReason) {
        if (msg.isStreaming) {
          msg.isStreaming = false;
        }
        if (msg.agent === "reporter") {
          const contentLen = msg.content?.length ?? 0;
          console.log(`[Store] Cleanup loop found reporter message: messageId=${id}, contentLen=${contentLen}, finishReason=${msg.finishReason}`);
          if (contentLen === 0) {
            console.error(`[Store] ❌ Cleanup loop: Reporter message has empty content! messageId=${id}`);
          }
          reporterMessages.push(msg);
        } else {
          finishedMessages.push(msg);
        }
      }
    }
    
    console.log(`[Store] Cleanup loop: found ${reporterMessages.length} reporter messages, ${finishedMessages.length} other finished messages`);
    
    // Process non-reporter messages first
    for (const msg of finishedMessages) {
      useStore.getState().updateMessage(msg);
    }
    
    // Process reporter messages LAST - this ensures ongoingResearchId is still available
    // updateMessage will clear ongoingResearchId when reporter finishes
    if (reporterMessages.length > 0) {
      console.log(`[DEBUG-REPORTER-CLEANUP] 🧹 Cleanup loop: processing ${reporterMessages.length} reporter messages`);
    }
    for (const msg of reporterMessages) {
      const contentLenBefore = msg.content?.length ?? 0;
      const chunksLenBefore = msg.contentChunks?.length ?? 0;
      const lastCharsBefore = msg.content?.slice(-50) ?? "";
      console.log(`[DEBUG-REPORTER-CLEANUP] 🔄 Cleanup loop updating reporter: messageId=${msg.id}, contentLen=${contentLenBefore}, chunksLen=${chunksLenBefore}, finishReason=${msg.finishReason}`);
      if (contentLenBefore > 0) {
        console.log(`[DEBUG-REPORTER-CLEANUP] 📝 Last 50 chars before cleanup: "${lastCharsBefore}"`);
      }
      console.trace(`[DEBUG-REPORTER-CLEANUP] Stack trace for cleanup updateMessage call`);
      useStore.getState().updateMessage(msg);
    }
  } catch (error) {
    // Extract error message
    const errorMessage = error instanceof Error ? error.message : "An error occurred while generating the response. Please try again.";
    
    // Check if it's a provider configuration error
    const isAIProviderError = errorMessage.toLowerCase().includes("no ai providers configured") || 
                              errorMessage.toLowerCase().includes("ai provider");
    const isPMProviderError = errorMessage.toLowerCase().includes("no pm providers configured") || 
                              (errorMessage.toLowerCase().includes("pm provider") && 
                               !errorMessage.toLowerCase().includes("ai provider"));
    
    if (isAIProviderError) {
      // Don't log AI provider errors to console - we show a user-friendly toast instead
      // Show error toast with action button to open Provider Management
      toast.error("AI Provider Required", {
        description: errorMessage,
        duration: 10000,
        action: {
          label: "Configure",
          onClick: () => {
            // Trigger the Provider Management dialog and open AI Providers tab
            if (typeof window !== "undefined") {
              window.dispatchEvent(new CustomEvent("pm_show_providers", { 
                detail: { tab: "ai" } 
              }));
            }
          },
        },
      });
    } else if (isPMProviderError) {
      // Don't log PM provider errors to console - we show a user-friendly toast instead
      // Show error toast with action button to open Provider Management
      toast.error("PM Provider Required", {
        description: errorMessage,
        duration: 10000,
        action: {
          label: "Configure",
          onClick: () => {
            // Trigger the Provider Management dialog and open PM Providers tab
            if (typeof window !== "undefined") {
              window.dispatchEvent(new CustomEvent("pm_show_providers", { 
                detail: { tab: "pm" } 
              }));
            }
          },
        },
      });
    } else {
      // Log other errors to console for debugging
      console.error("[Store] Error in sendMessage:", error);
      // Show regular error toast
      toast.error(errorMessage);
    }
    
    // Update message status.
    // TODO: const isAborted = (error as Error).name === "AbortError";
    if (messageId != null) {
      const message = getMessage(messageId);
      if (message?.isStreaming) {
        message.isStreaming = false;
        useStore.getState().updateMessage(message);
      }
    }
    useStore.getState().setOngoingResearch(null);
  } finally {
    setResponding(false);
    // Ensure all pending updates are processed.
    if (updateTimer) clearTimeout(updateTimer);
    if (pendingUpdates.size > 0) {
      useStore.getState().updateMessages(Array.from(pendingUpdates.values()));
    }

  }
}

function setResponding(value: boolean) {
  useStore.setState({ responding: value });
}

function existsMessage(id: string) {
  return useStore.getState().messageIds.includes(id);
}

function getMessage(id: string) {
  return useStore.getState().messages.get(id);
}

function findMessageByToolCallId(toolCallId: string) {
  const allMessages = Array.from(useStore.getState().messages.values());
  
  return allMessages
    .reverse()
    .find((message) => {
      if (message.toolCalls) {
        return message.toolCalls.some((toolCall) => toolCall.id === toolCallId);
      }
      return false;
    });
}

function appendMessage(message: Message) {
  // Planner creates the research block first, then agents reuse it
  if (message.agent === "planner") {
    // Prevent creating research block with undefined message.id
    if (!message.id) {
      useStore.getState().appendMessage(message);
      return;
    }
    
    const state = useStore.getState();
    
    // Check if this planner message already has a block
    if (state.researchIds.includes(message.id)) {
      appendResearchActivity(message);
      useStore.getState().appendMessage(message);
      return;
    }
    
    // Planner creates the research block
    appendResearch(message.id, "planner");
    openResearch(message.id);
    useStore.getState().setOngoingResearch(message.id);
    appendResearchActivity(message);
    useStore.getState().appendMessage(message);
    return;
  }
  
  // Track research activities for execution agents (they reuse planner's block)
  if (
    message.agent === "coder" ||
    message.agent === "reporter" ||
    message.agent === "researcher" ||
    message.agent === "pm_agent" ||
    message.agent === "react_agent"
  ) {
    const state = useStore.getState();
    const blockType = getBlockTypeForAgent(message.agent);
    
    // Check if this message already belongs to a research block
    let existingBlockForThisMessage: string | null = null;
    
    if (state.researchIds.includes(message.id)) {
      existingBlockForThisMessage = message.id;
    } else {
      for (const [researchId, activityIds] of state.researchActivityIds.entries()) {
        if (activityIds.includes(message.id)) {
          existingBlockForThisMessage = researchId;
          break;
        }
      }
    }
    
    // If message already belongs to a block, reuse it
    if (existingBlockForThisMessage) {
      if (state.ongoingResearchId !== existingBlockForThisMessage) {
        useStore.getState().setOngoingResearch(existingBlockForThisMessage);
      }
      appendResearchActivity(message);
      useStore.getState().appendMessage(message);
      return;
    }
    
    // Reuse ongoing research block if it exists
    let blockToUse: string | null = null;
    
    if (state.ongoingResearchId) {
      blockToUse = state.ongoingResearchId;
    } else {
      // Find most recent planner block
      const reversedIds = [...state.researchIds].reverse();
      for (const researchId of reversedIds.slice(0, 5)) {
        const existingType = state.researchBlockTypes.get(researchId);
        if (existingType === "planner") {
          blockToUse = researchId;
          break;
        }
      }
      
      // Fallback: Find most recent block of same type
      if (!blockToUse) {
        for (const researchId of reversedIds.slice(0, 5)) {
          const existingType = state.researchBlockTypes.get(researchId);
          if (existingType === blockType) {
            blockToUse = researchId;
            break;
          }
        }
      }
    }
    
    if (blockToUse) {
      if (state.ongoingResearchId !== blockToUse) {
        useStore.getState().setOngoingResearch(blockToUse);
      }
      appendResearchActivity(message);
    } else {
      // Create new block only if truly no existing block
      appendResearch(message.id, blockType);
      openResearch(message.id);
      useStore.getState().setOngoingResearch(message.id);
      appendResearchActivity(message);
    }
  }
  useStore.getState().appendMessage(message);
}

function updateMessage(message: Message) {
  // DEBUG: Log function entry for reporter messages
  if (message.agent === "reporter") {
    const contentLen = message.content?.length ?? 0;
    const chunksLen = message.contentChunks?.length ?? 0;
    const lastChars = message.content?.slice(-50) ?? "";
    console.log(`[DEBUG-HELPER-ENTRY] 🚪 updateMessage helper ENTRY: messageId=${message.id}, contentLen=${contentLen}, chunksLen=${chunksLen}, isStreaming=${message.isStreaming}, finishReason=${message.finishReason}`);
    if (contentLen > 0) {
      console.log(`[DEBUG-HELPER-ENTRY] 📝 Last 50 chars: "${lastChars}"`);
    }
    console.trace(`[DEBUG-HELPER-ENTRY] Stack trace for helper updateMessage entry`);
  }
  
  if (message.agent === "reporter" && !message.isStreaming) {
    const contentLen = message.content?.length ?? 0;
    const chunksLen = message.contentChunks?.length ?? 0;
    const lastChars = message.content?.slice(-50) ?? "";
    console.log(`[DEBUG-REPORTER-HELPER] 🔧 updateMessage helper: messageId=${message.id}, contentLen=${contentLen}, chunksLen=${chunksLen}, isStreaming=${message.isStreaming}, finishReason=${message.finishReason}`);
    if (contentLen > 0) {
      console.log(`[DEBUG-REPORTER-HELPER] 📝 Last 50 chars: "${lastChars}"`);
    }
    console.trace(`[DEBUG-REPORTER-HELPER] Stack trace for helper updateMessage call`);
    
    let researchId = getOngoingResearchId();
    
    // Find the research that has this reporter message
    if (!researchId) {
      const state = useStore.getState();
      
      for (const [rId, reportId] of state.researchReportIds.entries()) {
        if (reportId === message.id) {
          researchId = rId;
          break;
        }
      }
      if (!researchId) {
        for (const [rId, activityIds] of state.researchActivityIds.entries()) {
          if (activityIds.includes(message.id)) {
            researchId = rId;
            break;
          }
        }
      }
    }
    
    if (researchId) {
      const currentReportId = useStore.getState().researchReportIds.get(researchId);
      console.log(`[Store.updateMessage helper] Setting researchReportIds: researchId=${researchId}, currentReportId=${currentReportId}, newReportId=${message.id}, contentLen=${contentLen}`);
      
      if (!currentReportId || currentReportId !== message.id) {
        // WARNING: If we're setting a report with empty content, log it
        if (contentLen === 0 && currentReportId) {
          const currentMsg = useStore.getState().messages.get(currentReportId);
          const currentContentLen = currentMsg?.content?.length ?? 0;
          console.error(`[Store.updateMessage helper] ❌ OVERWRITING reportId! researchId=${researchId}, oldReportId=${currentReportId} (contentLen=${currentContentLen}), newReportId=${message.id} (contentLen=0)`);
        }
        useStore.setState({
          researchReportIds: new Map(useStore.getState().researchReportIds).set(
            researchId,
            message.id,
          ),
        });
      }
      
      // Auto-open the research when report finishes
      useStore.getState().openResearch(researchId);
    } else {
      // Fallback: Try to find researchId by checking activityIds
      const state = useStore.getState();
      for (const [rId, activityIds] of state.researchActivityIds.entries()) {
        if (activityIds.includes(message.id)) {
          useStore.setState({
            researchReportIds: new Map(state.researchReportIds).set(rId, message.id),
          });
          useStore.getState().openResearch(rId);
          break;
        }
      }
    }
  }
  
  // DEBUG: Log before calling store's updateMessage
  if (message.agent === "reporter") {
    const contentLen = message.content?.length ?? 0;
    const chunksLen = message.contentChunks?.length ?? 0;
    const lastChars = message.content?.slice(-50) ?? "";
    console.log(`[DEBUG-HELPER-BEFORE-UPDATE] 🔧 About to call store.updateMessage: messageId=${message.id}, contentLen=${contentLen}, chunksLen=${chunksLen}`);
    if (contentLen > 0) {
      console.log(`[DEBUG-HELPER-BEFORE-UPDATE] 📝 Last 50 chars: "${lastChars}"`);
    }
  }
  
  useStore.getState().updateMessage(message);
  
  // DEBUG: Log after calling store's updateMessage
  if (message.agent === "reporter") {
    const state = useStore.getState();
    const updatedMsg = state.messages.get(message.id);
    const finalContentLen = updatedMsg?.content?.length ?? 0;
    const finalChunksLen = updatedMsg?.contentChunks?.length ?? 0;
    const finalLastChars = updatedMsg?.content?.slice(-50) ?? "";
    console.log(`[DEBUG-HELPER-AFTER-UPDATE] 🔧 After store.updateMessage: messageId=${message.id}, finalContentLen=${finalContentLen}, finalChunksLen=${finalChunksLen}`);
    if (finalContentLen > 0) {
      console.log(`[DEBUG-HELPER-AFTER-UPDATE] 📝 Final last 50 chars: "${finalLastChars}"`);
    }
    console.log(`[DEBUG-HELPER-EXIT] 🚪 updateMessage helper EXIT: messageId=${message.id}`);
  }
}

function getOngoingResearchId() {
  return useStore.getState().ongoingResearchId;
}

function appendResearch(researchId: string, blockType: ResearchBlockType) {
  // Prevent creating research block with undefined/null researchId
  if (!researchId) {
    return;
  }
  
  // Check if this research already exists
  const state = useStore.getState();
  if (state.researchIds.includes(researchId)) {
    return;
  }
  
  let planMessage: Message | undefined;
  const reversedMessageIds = [...state.messageIds].reverse();
  for (const messageId of reversedMessageIds) {
    const message = getMessage(messageId);
    if (message?.agent === "planner") {
      planMessage = message;
      break;
    }
  }
  
  const messageIds = [researchId];
  const newResearchIds = [...useStore.getState().researchIds, researchId];
  
  // Add planner message if it exists (may not exist for ReAct fast path)
  if (planMessage?.id) {
    messageIds.unshift(planMessage.id);
    useStore.setState({
      ongoingResearchId: researchId,
      researchIds: newResearchIds,
      researchPlanIds: new Map(useStore.getState().researchPlanIds).set(
        researchId,
        planMessage.id,
      ),
      researchActivityIds: new Map(useStore.getState().researchActivityIds).set(
        researchId,
        messageIds,
      ),
      researchBlockTypes: new Map(useStore.getState().researchBlockTypes).set(
        researchId,
        blockType,
      ),
    });
  } else {
    // Fast path (ReAct) - no planner message
    useStore.setState({
      ongoingResearchId: researchId,
      researchIds: newResearchIds,
      researchActivityIds: new Map(useStore.getState().researchActivityIds).set(
        researchId,
        messageIds,
      ),
      researchBlockTypes: new Map(useStore.getState().researchBlockTypes).set(
        researchId,
        blockType,
      ),
    });
  }
}

function appendResearchActivity(message: Message) {
  const researchId = getOngoingResearchId();
  
  if (researchId) {
    const researchActivityIds = useStore.getState().researchActivityIds;
    const current = researchActivityIds.get(researchId);
    
    // Initialize or add to activity ids
    if (!current) {
      useStore.setState({
        researchActivityIds: new Map(researchActivityIds).set(researchId, [message.id]),
      });
    } else if (!current.includes(message.id)) {
      useStore.setState({
        researchActivityIds: new Map(researchActivityIds).set(researchId, [
          ...current,
          message.id,
        ]),
      });
    }
    
    // Set reportId for reporter messages
    if (message.agent === "reporter") {
      useStore.setState({
        researchReportIds: new Map(useStore.getState().researchReportIds).set(
          researchId,
          message.id,
        ),
      });
    }
  }
}

export function openResearch(researchId: string | null) {
  useStore.getState().openResearch(researchId);
}

export function closeResearch() {
  useStore.getState().closeResearch();
}

export async function listenToPodcast(researchId: string) {
  const planMessageId = useStore.getState().researchPlanIds.get(researchId);
  const reportMessageId = useStore.getState().researchReportIds.get(researchId);
  if (planMessageId && reportMessageId) {
    const planMessage = getMessage(planMessageId)!;
    const title = parseJSON(planMessage.content, { title: "Untitled" }).title;
    const reportMessage = getMessage(reportMessageId);
    if (reportMessage?.content) {
      appendMessage({
        id: nanoid(),
        threadId: THREAD_ID,
        role: "user",
        content: "Please generate a podcast for the above research.",
        contentChunks: [],
      });
      const podCastMessageId = nanoid();
      const podcastObject = { title, researchId };
      const podcastMessage: Message = {
        id: podCastMessageId,
        threadId: THREAD_ID,
        role: "assistant",
        agent: "podcast",
        content: JSON.stringify(podcastObject),
        contentChunks: [],
        reasoningContent: "",
        reasoningContentChunks: [],
        isStreaming: true,
      };
      appendMessage(podcastMessage);
      // Generating podcast...
      let audioUrl: string | undefined;
      try {
        audioUrl = await generatePodcast(reportMessage.content);
      } catch (e) {
        console.error(e);
        useStore.setState((state) => ({
          messages: new Map(useStore.getState().messages).set(
            podCastMessageId,
            {
              ...state.messages.get(podCastMessageId)!,
              content: JSON.stringify({
                ...podcastObject,
                error: e instanceof Error ? e.message : "Unknown error",
              }),
              isStreaming: false,
            },
          ),
        }));
        toast("An error occurred while generating podcast. Please try again.");
        return;
      }
      useStore.setState((state) => ({
        messages: new Map(useStore.getState().messages).set(podCastMessageId, {
          ...state.messages.get(podCastMessageId)!,
          content: JSON.stringify({ ...podcastObject, audioUrl }),
          isStreaming: false,
        }),
      }));
    }
  }
}

export function useResearchMessage(researchId: string) {
  return useStore(
    useShallow((state) => {
      const messageId = state.researchPlanIds.get(researchId);
      return messageId ? state.messages.get(messageId) : undefined;
    }),
  );
}

export function useMessage(messageId: string | null | undefined) {
  return useStore(
    useShallow((state) =>
      messageId ? state.messages.get(messageId) : undefined,
    ),
  );
}

export function useMessageIds() {
  return useStore(useShallow((state) => state.messageIds));
}

export function useRenderableMessageIds() {
  return useStore(
    useShallow((state) => {
      // Filter to only messages that will actually render in MessageListView
      // This prevents duplicate keys and React warnings when messages change state
      const seen = new Set<string>();
      return state.messageIds.filter((messageId) => {
        // Skip null/undefined/empty messageIds
        if (!messageId) {
          return false;
        }
        // Skip duplicates to ensure unique keys
        if (seen.has(messageId)) {
          return false;
        }
        seen.add(messageId);
        
        const message = state.messages.get(messageId);
        if (!message) return false;
        
        // Only include messages that match MessageListItem rendering conditions
        // These are the same conditions checked in MessageListItem component
        // Note: reporter is NOT included - report is shown inside AnalysisBlock
        return (
          message.role === "user" ||
          message.agent === "coordinator" ||
          message.agent === "planner" ||
          message.agent === "podcast" ||
          state.researchIds.includes(messageId) // startOfResearch condition
        );
      });
    }),
  );
}

export function useLastInterruptMessage() {
  return useStore(
    useShallow((state) => {
      if (state.messageIds.length >= 2) {
        const lastMessage = state.messages.get(
          state.messageIds[state.messageIds.length - 1]!,
        );
        return lastMessage?.finishReason === "interrupt" ? lastMessage : null;
      }
      return null;
    }),
  );
}

export function useLastFeedbackMessageId() {
  const waitingForFeedbackMessageId = useStore(
    useShallow((state) => {
      if (state.messageIds.length >= 2) {
        const lastMessage = state.messages.get(
          state.messageIds[state.messageIds.length - 1]!,
        );
        if (lastMessage?.finishReason === "interrupt") {
          return state.messageIds[state.messageIds.length - 2];
        }
      }
      return null;
    }),
  );
  return waitingForFeedbackMessageId;
}

export function useToolCalls() {
  return useStore(
    useShallow((state) => {
      return state.messageIds
        ?.map((id) => getMessage(id)?.toolCalls)
        .filter((toolCalls) => toolCalls != null)
        .flat();
    }),
  );
}
