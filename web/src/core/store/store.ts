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

export const useStore = create<{
  responding: boolean;
  threadId: string | undefined;
  messageIds: string[];
  messages: Map<string, Message>;
  researchIds: string[];
  researchPlanIds: Map<string, string>;
  researchReportIds: Map<string, string>;
  researchActivityIds: Map<string, string[]>;
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
  ongoingResearchId: null,
  openResearchId: null,

  appendMessage(message: Message) {
    set((state) => {
      // Prevent duplicate message IDs in the array to avoid React key warnings
      const newMessageIds = state.messageIds.includes(message.id)
        ? state.messageIds
        : [...state.messageIds, message.id];
      return {
        messageIds: newMessageIds,
        messages: new Map(state.messages).set(message.id, message),
      };
    });
  },
  updateMessage(message: Message) {
    set((state) => ({
      messages: new Map(state.messages).set(message.id, message),
    }));
  },
  updateMessages(messages: Message[]) {
    set((state) => {
      const newMessages = new Map(state.messages);
      messages.forEach((m) => newMessages.set(m.id, m));
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
        useStore.getState().updateMessages(Array.from(pendingUpdates.values()));
        pendingUpdates.clear();
      }
    }, 16); // ~60fps
  };

  try {
    for await (const event of stream) {
      const { type, data } = event;
      
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
          appendMessage(message);
        }
      }
      
      message ??= getMessage(messageId);
      if (message) {
        const previousIsStreaming = message.isStreaming;
        message = mergeMessage(message, event);
        
        // If finish_reason is present, apply update immediately to ensure UI updates quickly
        // This is especially important for reporter messages to show the final report
        if (event.data.finish_reason && previousIsStreaming) {
          // Immediately update using helper function to trigger UI re-render and run reporter logic
          updateMessage(message);
          // Remove from pending updates to avoid duplicate update
          pendingUpdates.delete(message.id);
        } else {
          // Collect pending messages for update, instead of updating immediately.
          pendingUpdates.set(message.id, message);
          scheduleUpdate();
        }
      }
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
  // Track research activities for all research-related agents including pm_agent
  if (
    message.agent === "coder" ||
    message.agent === "reporter" ||
    message.agent === "researcher" ||
    message.agent === "pm_agent"
  ) {
    const ongoingResearchId = getOngoingResearchId();
    
    if (!ongoingResearchId) {
      const id = message.id;
      appendResearch(id);
      openResearch(id);
    }
    appendResearchActivity(message);
  }
  useStore.getState().appendMessage(message);
}

function updateMessage(message: Message) {
  if (message.agent === "reporter" && !message.isStreaming) {
    // Find researchId - either from ongoingResearchId or by looking up which research has this reporter message
    let researchId = getOngoingResearchId();
    
    // If ongoingResearchId is null, find the research that has this reporter message as its report
    if (!researchId) {
      const state = useStore.getState();
      for (const [rId, reportId] of state.researchReportIds.entries()) {
        if (reportId === message.id) {
          researchId = rId;
          break;
        }
      }
      // If still not found, try finding by checking researchActivityIds
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
      
      if (!currentReportId || currentReportId !== message.id) {
        useStore.setState({
          researchReportIds: new Map(useStore.getState().researchReportIds).set(
            researchId,
            message.id,
          ),
        });
      }
      // Always auto-open the research when report finishes so user can see the results immediately
      // This ensures the report content is visible without requiring user to click "Open"
      useStore.getState().openResearch(researchId);
      // Clear ongoingResearchId to stop the loading indicator
      useStore.getState().setOngoingResearch(null);
    }
  }
  useStore.getState().updateMessage(message);
}

function getOngoingResearchId() {
  return useStore.getState().ongoingResearchId;
}

function appendResearch(researchId: string) {
  let planMessage: Message | undefined;
  const reversedMessageIds = [...useStore.getState().messageIds].reverse();
  for (const messageId of reversedMessageIds) {
    const message = getMessage(messageId);
    if (message?.agent === "planner") {
      planMessage = message;
      break;
    }
  }
  const messageIds = [researchId];
  messageIds.unshift(planMessage!.id);
  useStore.setState({
    ongoingResearchId: researchId,
    researchIds: [...useStore.getState().researchIds, researchId],
    researchPlanIds: new Map(useStore.getState().researchPlanIds).set(
      researchId,
      planMessage!.id,
    ),
    researchActivityIds: new Map(useStore.getState().researchActivityIds).set(
      researchId,
      messageIds,
    ),
  });
}

function appendResearchActivity(message: Message) {
  const researchId = getOngoingResearchId();
  
  if (researchId) {
    const researchActivityIds = useStore.getState().researchActivityIds;
    const current = researchActivityIds.get(researchId)!;
    if (!current.includes(message.id)) {
      useStore.setState({
        researchActivityIds: new Map(researchActivityIds).set(researchId, [
          ...current,
          message.id,
        ]),
      });
    }
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
