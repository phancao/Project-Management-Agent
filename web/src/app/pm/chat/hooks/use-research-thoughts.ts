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
  
  return useMemo(() => {
    const timestamp = new Date().toISOString();
    console.log(`[useResearchThoughts] 🔍 [${timestamp}] Collecting thoughts for researchId=${researchId}`, {
      planMessageId,
      activityIds: activityIds.length,
      totalMessages: messages.size,
    });
    
    const thoughts: Thought[] = [];
    const seenThoughts = new Set<string>();
    
    // Helper to add a thought with deduplication
    const addThought = (thought: Thought) => {
      if (seenThoughts.has(thought.thought)) {
        console.log(`[useResearchThoughts] ⏭️ Skipping duplicate thought: "${thought.thought.substring(0, 50)}..."`);
        return;
      }
      seenThoughts.add(thought.thought);
      thoughts.push(thought);
      console.log(`[useResearchThoughts] ✅ Added thought: step_index=${thought.step_index}, agent=${thought.agent}, thought="${thought.thought.substring(0, 50)}..."`);
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
  }, [messages, activityIds, planMessageId, messageIds.length, researchId]);
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

