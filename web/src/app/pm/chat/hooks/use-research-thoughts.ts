// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * useResearchThoughts Hook
 * 
 * Extracts and collects thoughts from all messages in a research block.
 * Provides a clean interface for displaying agent reasoning in the UI.
 */

import { useMemo } from "react";
import { useStore } from "~/core/store";
import { parseJSON } from "~/core/utils";
import type { Message } from "~/core/messages";

export interface Thought {
  thought: string;
  before_tool: boolean;
  step_index: number;
  messageId?: string;
  agent?: string;
}

interface PlanStep {
  title?: string;
  description?: string;
  step_type?: string;
}

interface PlanData {
  title?: string;
  thought?: string;
  steps?: PlanStep[];
}

/**
 * Collect thoughts from a research block.
 * 
 * Extracts thoughts from:
 * 1. Plan message steps (descriptions)
 * 2. pm_agent/react_agent reactThoughts
 * 
 * @param researchId - The research block ID
 * @returns Array of thoughts sorted by step_index
 */
export function useResearchThoughts(researchId: string): Thought[] {
  const messages = useStore((state) => state.messages);
  const activityIds = useStore((state) => state.researchActivityIds.get(researchId)) ?? [];
  const planMessageId = useStore((state) => state.researchPlanIds.get(researchId));
  const messageIds = useStore((state) => state.messageIds);
  // FIX: Subscribe to thoughtsUpdateCounter to trigger recomputation when thoughts update progressively
  const thoughtsUpdateCounter = useStore((state) => state.thoughtsUpdateCounter);

  return useMemo(() => {
    const timestamp = new Date().toISOString();
    console.log(`[useResearchThoughts] 🔍 [${timestamp}] Collecting thoughts for researchId=${researchId}`, {
      planMessageId,
      activityIds: activityIds.length,
      totalMessages: messages.size,
    });

    const thoughts: Thought[] = [];
    const seenThoughts = new Set<string>();

    // Helper to check if content should be filtered out entirely
    // We filter TOOL_CALL and TOOL_RESULT because they're already shown in StepBox
    // But we KEEP DECISION content - that's the AI's reasoning!
    const shouldFilterThought = (content: string): boolean => {
      const trimmed = content.trim();
      // Filter out TOOL_CALL, TOOL_RESULT - these are duplicated in StepBox
      // We do NOT filter TOOL_CALL/TOOL_RESULT anymore because they are internal steps of the PM Agent
      // that are NOT exposed as separate messages, so they must be shown as thoughts.
      /*
      if (trimmed.startsWith('TOOL_CALL:') || trimmed.startsWith('🔧 TOOL_CALL:')) return true;
      if (trimmed.startsWith('TOOL_RESULT:') || trimmed.startsWith('📋 TOOL_RESULT:')) return true;
      */

      // Filter out empty or very short content
      if (trimmed.length < 5) return true;
      // Filter out content that's just JSON-like args
      if (trimmed.startsWith('({') || trimmed.startsWith('{}')) return true;
      return false;
    };

    // Helper to clean up thought content (remove prefixes for cleaner display)
    const cleanThoughtContent = (content: string): string => {
      let cleaned = content.trim();
      // Remove common prefixes for cleaner display
      const prefixes = [
        '✅ DECISION:', '🔄 DECISION:', 'DECISION:',
        '🧠 THINKING:', 'THINKING:',
        '💭 Thought:', 'Thought:',
        '🧠 Reasoning:', 'Reasoning:',
      ];
      for (const prefix of prefixes) {
        if (cleaned.startsWith(prefix)) {
          cleaned = cleaned.substring(prefix.length).trim();
          break;
        }
      }
      return cleaned;
    };

    // Helper to add a thought with deduplication
    const addThought = (thought: Thought) => {
      // Skip filtered content (TOOL_CALL, TOOL_RESULT)
      if (shouldFilterThought(thought.thought)) {
        console.log(`[useResearchThoughts] ⏭️ Filtering out: "${thought.thought.substring(0, 50)}..."`);
        return;
      }

      // Clean up the thought content
      const cleanedThought = cleanThoughtContent(thought.thought);

      if (seenThoughts.has(cleanedThought)) {
        console.log(`[useResearchThoughts] ⏭️ Skipping duplicate thought: "${cleanedThought.substring(0, 50)}..."`);
        return;
      }
      seenThoughts.add(cleanedThought);
      thoughts.push({
        ...thought,
        thought: cleanedThought,  // Use cleaned content
      });
      console.log(`[useResearchThoughts] ✅ Added thought: step_index=${thought.step_index}, agent=${thought.agent}, thought="${cleanedThought.substring(0, 50)}..."`);
    };

    // PRIORITY 1: Extract thoughts from plan steps IMMEDIATELY
    // These are available before any tool calls execute
    if (planMessageId) {
      const planMsg = messages.get(planMessageId);
      if (planMsg?.content) {
        try {
          const planData = parseJSON<PlanData>(planMsg.content, { title: "", thought: "", steps: [] });
          if (planData.steps && Array.isArray(planData.steps)) {
            planData.steps.forEach((step, stepIndex) => {
              if (step.description) {
                addThought({
                  thought: step.description,
                  before_tool: true,
                  step_index: stepIndex,
                  messageId: planMessageId,
                  agent: "planner",
                });
              }
            });
          }
        } catch {
          // Failed to parse plan, continue to other sources
        }
      }

      // Also check plan message's reactThoughts
      if (planMsg?.reactThoughts) {
        for (const t of planMsg.reactThoughts) {
          addThought({
            ...t,
            messageId: planMessageId,
            agent: planMsg.agent,
          });
        }
      }
    }

    // PRIORITY 2: Collect from activity messages
    for (const activityId of activityIds) {
      const msg = messages.get(activityId);
      if (!msg?.reactThoughts) continue;

      for (const t of msg.reactThoughts) {
        addThought({
          ...t,
          messageId: activityId,
          agent: msg.agent,
        });
      }
    }

    // PRIORITY 3: Check recent pm_agent/react_agent/planner messages not yet in activityIds
    const recentIds = messageIds.slice(-30);
    for (const msgId of recentIds) {
      if (activityIds.includes(msgId)) continue;
      if (planMessageId === msgId) continue;

      const msg = messages.get(msgId);
      if (!msg) continue;
      // Include planner agent for overall plan thoughts
      if (msg.agent !== "pm_agent" && msg.agent !== "react_agent" && msg.agent !== "planner") continue;
      if (!msg.reactThoughts || msg.reactThoughts.length === 0) continue;

      for (const t of msg.reactThoughts) {
        addThought({
          ...t,
          messageId: msgId,
          agent: msg.agent,
        });
      }
    }

    // Sort by step_index
    thoughts.sort((a, b) => a.step_index - b.step_index);

    const finalTimestamp = new Date().toISOString();
    console.log(`[useResearchThoughts] 📊 [${finalTimestamp}] Final thoughts count: ${thoughts.length}`, {
      thoughts: thoughts.map(t => ({ step_index: t.step_index, agent: t.agent, thought: t.thought.substring(0, 50) })),
    });

    return thoughts;
    // Include thoughtsUpdateCounter in dependencies to enable progressive thought updates
    // This counter increments every time a thoughts event is processed by the store
  }, [messages, activityIds, planMessageId, messageIds.length, researchId, thoughtsUpdateCounter]);
}

/**
 * Get the latest thought from a research block.
 * 
 * @param researchId - The research block ID
 * @returns The latest thought or undefined
 */
export function useLatestThought(researchId: string): Thought | undefined {
  const thoughts = useResearchThoughts(researchId);
  return thoughts.length > 0 ? thoughts[thoughts.length - 1] : undefined;
}

/**
 * Get the count of thoughts in a research block.
 * 
 * @param researchId - The research block ID
 * @returns Number of thoughts
 */
export function useThoughtCount(researchId: string): number {
  const thoughts = useResearchThoughts(researchId);
  return thoughts.length;
}

