// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * Research Block Store
 * 
 * Unified management of research blocks with a single data structure.
 * Replaces the previous 5 separate Maps with one clean interface.
 */

import type { Message } from "../messages";

// Block types for different agents
export type ResearchBlockType = "react" | "planner" | "pm" | "researcher" | "coder";

// Unified research block interface
export interface ResearchBlock {
  id: string;
  type: ResearchBlockType;
  planMessageId?: string;
  reportMessageId?: string;
  activityIds: string[];
  status: "ongoing" | "completed";
  createdAt: number;
}

// Research store state
export interface ResearchState {
  researchBlocks: Map<string, ResearchBlock>;
  ongoingResearchId: string | null;
  openResearchId: string | null;
}

// Initial state
export const initialResearchState: ResearchState = {
  researchBlocks: new Map(),
  ongoingResearchId: null,
  openResearchId: null,
};

/**
 * Create a new research block.
 * Only called by planner agent or when no planner exists.
 */
export function createResearchBlock(
  state: ResearchState,
  researchId: string,
  blockType: ResearchBlockType,
  planMessageId?: string
): ResearchState {
  // Prevent creating block with undefined/null ID
  if (!researchId) {
    console.error("[research-store] Cannot create block with undefined ID");
    return state;
  }

  // Check if block already exists
  if (state.researchBlocks.has(researchId)) {
    return state;
  }

  const newBlock: ResearchBlock = {
    id: researchId,
    type: blockType,
    planMessageId,
    activityIds: planMessageId ? [planMessageId, researchId] : [researchId],
    status: "ongoing",
    createdAt: Date.now(),
  };

  const newBlocks = new Map(state.researchBlocks);
  newBlocks.set(researchId, newBlock);

  return {
    ...state,
    researchBlocks: newBlocks,
    ongoingResearchId: researchId,
    openResearchId: researchId,
  };
}

/**
 * Attach a message activity to an existing research block.
 */
export function attachActivityToResearch(
  state: ResearchState,
  researchId: string,
  messageId: string
): ResearchState {
  const block = state.researchBlocks.get(researchId);
  if (!block) {
    console.warn(`[research-store] Cannot attach to non-existent block: ${researchId}`);
    return state;
  }

  // Skip if already attached
  if (block.activityIds.includes(messageId)) {
    return state;
  }

  const newBlock: ResearchBlock = {
    ...block,
    activityIds: [...block.activityIds, messageId],
  };

  const newBlocks = new Map(state.researchBlocks);
  newBlocks.set(researchId, newBlock);

  return {
    ...state,
    researchBlocks: newBlocks,
  };
}

/**
 * Set the report message for a research block.
 */
export function setResearchReport(
  state: ResearchState,
  researchId: string,
  reportMessageId: string
): ResearchState {
  const block = state.researchBlocks.get(researchId);
  if (!block) {
    console.warn(`[research-store] Cannot set report for non-existent block: ${researchId}`);
    return state;
  }

  const newBlock: ResearchBlock = {
    ...block,
    reportMessageId,
  };

  const newBlocks = new Map(state.researchBlocks);
  newBlocks.set(researchId, newBlock);

  return {
    ...state,
    researchBlocks: newBlocks,
  };
}

/**
 * Complete a research block (mark as finished).
 */
export function completeResearch(
  state: ResearchState,
  researchId: string
): ResearchState {
  const block = state.researchBlocks.get(researchId);
  if (!block) {
    return state;
  }

  const newBlock: ResearchBlock = {
    ...block,
    status: "completed",
  };

  const newBlocks = new Map(state.researchBlocks);
  newBlocks.set(researchId, newBlock);

  // Clear ongoing if this was the ongoing block
  const newOngoingId = state.ongoingResearchId === researchId 
    ? null 
    : state.ongoingResearchId;

  return {
    ...state,
    researchBlocks: newBlocks,
    ongoingResearchId: newOngoingId,
  };
}

/**
 * Find the research block that contains a message.
 */
export function findResearchByMessageId(
  state: ResearchState,
  messageId: string
): ResearchBlock | undefined {
  for (const block of state.researchBlocks.values()) {
    if (block.activityIds.includes(messageId) || block.id === messageId) {
      return block;
    }
  }
  return undefined;
}

/**
 * Find the most recent research block of a given type.
 */
export function findRecentResearchByType(
  state: ResearchState,
  blockType: ResearchBlockType,
  maxAge = 60000 // 60 seconds default
): ResearchBlock | undefined {
  const now = Date.now();
  const blocks = Array.from(state.researchBlocks.values())
    .filter(b => b.type === blockType && (now - b.createdAt) < maxAge)
    .sort((a, b) => b.createdAt - a.createdAt);
  
  return blocks[0];
}

/**
 * Get the ongoing research block.
 */
export function getOngoingResearch(
  state: ResearchState
): ResearchBlock | undefined {
  if (!state.ongoingResearchId) return undefined;
  return state.researchBlocks.get(state.ongoingResearchId);
}

/**
 * Convert from old store format (5 Maps) to new unified format.
 * Useful for migration.
 */
export function migrateFromOldFormat(
  researchIds: string[],
  researchPlanIds: Map<string, string>,
  researchReportIds: Map<string, string>,
  researchActivityIds: Map<string, string[]>,
  researchBlockTypes: Map<string, ResearchBlockType>
): Map<string, ResearchBlock> {
  const blocks = new Map<string, ResearchBlock>();

  for (const id of researchIds) {
    const block: ResearchBlock = {
      id,
      type: researchBlockTypes.get(id) || "pm",
      planMessageId: researchPlanIds.get(id),
      reportMessageId: researchReportIds.get(id),
      activityIds: researchActivityIds.get(id) || [id],
      status: "completed", // Assume migrated blocks are completed
      createdAt: Date.now(),
    };
    blocks.set(id, block);
  }

  return blocks;
}

/**
 * Convert from new unified format to old format (for backward compatibility).
 */
export function convertToOldFormat(blocks: Map<string, ResearchBlock>): {
  researchIds: string[];
  researchPlanIds: Map<string, string>;
  researchReportIds: Map<string, string>;
  researchActivityIds: Map<string, string[]>;
  researchBlockTypes: Map<string, ResearchBlockType>;
} {
  const researchIds: string[] = [];
  const researchPlanIds = new Map<string, string>();
  const researchReportIds = new Map<string, string>();
  const researchActivityIds = new Map<string, string[]>();
  const researchBlockTypes = new Map<string, ResearchBlockType>();

  for (const [id, block] of blocks) {
    researchIds.push(id);
    if (block.planMessageId) {
      researchPlanIds.set(id, block.planMessageId);
    }
    if (block.reportMessageId) {
      researchReportIds.set(id, block.reportMessageId);
    }
    researchActivityIds.set(id, block.activityIds);
    researchBlockTypes.set(id, block.type);
  }

  return {
    researchIds,
    researchPlanIds,
    researchReportIds,
    researchActivityIds,
    researchBlockTypes,
  };
}

/**
 * Determine which agent should create a block vs attach to existing.
 */
export function shouldCreateNewBlock(
  state: ResearchState,
  agent: Message["agent"]
): boolean {
  // Only planner creates new blocks in normal flow
  if (agent === "planner") {
    return true;
  }

  // Other agents should attach to ongoing block
  if (state.ongoingResearchId) {
    return false;
  }

  // No ongoing block - check for recent planner block to reuse
  const recentPlannerBlock = findRecentResearchByType(state, "planner", 30000);
  if (recentPlannerBlock) {
    return false;
  }

  // Fallback: create new block only if truly no existing block
  return true;
}

/**
 * Get the block type for an agent.
 */
export function getBlockTypeForAgent(agent: Message["agent"]): ResearchBlockType {
  const agentToBlockType: Record<string, ResearchBlockType> = {
    planner: "planner",
    react_agent: "react",
    pm_agent: "pm",
    researcher: "researcher",
    coder: "coder",
  };
  return agentToBlockType[agent || ""] || "pm";
}

