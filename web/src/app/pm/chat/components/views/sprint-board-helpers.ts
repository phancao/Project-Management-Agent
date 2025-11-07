// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import type { DragStartEvent, DragOverEvent, DragEndEvent } from "@dnd-kit/core";
import type { Task } from "~/core/api/hooks/pm/use-tasks";

/**
 * Column Order ID System
 * Separates visual ordering (order IDs) from status IDs for stable dragging
 */

export function getOrderId(index: number): string {
  return `order-${index}`;
}

export function createOrderIdsFromStatusIds(statusIds: string[]): { orderIds: string[]; mapping: Map<string, string> } {
  const orderIds: string[] = [];
  const mapping = new Map<string, string>();
  
  statusIds.forEach((statusId, index) => {
    const orderId = getOrderId(index);
    orderIds.push(orderId);
    mapping.set(orderId, String(statusId));
  });
  
  return { orderIds, mapping };
}

export function getStatusIdsFromOrderIds(orderIds: string[], mapping: Map<string, string>): string[] {
  return orderIds.map(orderId => mapping.get(orderId) || '').filter(Boolean);
}

export function getStatusIdFromOrderId(orderId: string, mapping: Map<string, string>): string | null {
  return mapping.get(orderId) || null;
}

export function getOrderIdFromStatusId(statusId: string, mapping: Map<string, string>): string | null {
  for (const [orderId, mappedStatusId] of mapping.entries()) {
    if (String(mappedStatusId) === String(statusId)) {
      return orderId;
    }
  }
  return null;
}

/**
 * Drag Detection Helpers
 */

export type DragType = 'column' | 'task' | 'unknown';

export interface DragInfo {
  type: DragType;
  id: string;
  orderId?: string;
  statusId?: string;
}

export function detectDragType(
  event: DragStartEvent | DragOverEvent | DragEndEvent,
  columnOrderIds: string[],
  taskIds: Set<string>
): DragInfo {
  const activeId = String(event.active.id);
  const activeData = event.active.data.current;
  
  // Priority 1: Check data.type (most reliable)
  if (activeData?.type === 'column') {
    const orderId = activeData.orderId || activeId;
    const statusId = activeData.statusId || null;
    return {
      type: 'column',
      id: activeId,
      orderId: columnOrderIds.includes(orderId) ? orderId : undefined,
      statusId: statusId || undefined,
    };
  }
  
  // Priority 2: Check if it's an order ID
  if (activeId.startsWith('order-') && columnOrderIds.includes(activeId)) {
    return {
      type: 'column',
      id: activeId,
      orderId: activeId,
    };
  }
  
  // Priority 3: Check if it's a task ID
  if (taskIds.has(activeId)) {
    return {
      type: 'task',
      id: activeId,
    };
  }
  
  return {
    type: 'unknown',
    id: activeId,
  };
}

/**
 * Extract target column from drag over event
 */
export function extractTargetColumn(
  overId: string,
  overData: any,
  columnOrderIds: string[],
  orderIdToStatusIdMap: Map<string, string>,
  availableStatuses: Array<{ id: string | number }>,
  tasks: Task[]
): { orderId: string | null; statusId: string | null } {
  let orderId: string | null = null;
  
  // Check if it's a drop zone
  if (overId.endsWith('-top-drop') || overId.endsWith('-bottom-drop')) {
    orderId = overId.replace(/-top-drop$/, '').replace(/-bottom-drop$/, '');
  }
  // Handle main column dropzone (empty column area)
  else if (overId.endsWith('-dropzone')) {
    orderId = overId.replace(/-dropzone$/, '');
  }
  // Check if it's a direct order ID
  else if (overId.startsWith('order-') && columnOrderIds.includes(overId)) {
    orderId = overId;
  }
  // Check overData
  else if (overData?.type === 'column') {
    if (overData.orderId && columnOrderIds.includes(overData.orderId)) {
      orderId = overData.orderId;
    } else if (overData.statusId) {
      orderId = getOrderIdFromStatusId(String(overData.statusId), orderIdToStatusIdMap);
    } else if (overData.column && columnOrderIds.includes(overData.column)) {
      orderId = overData.column;
    }
  }
  // Check if dropped on a task
  else {
    const droppedTask = tasks.find(t => String(t.id) === overId);
    if (droppedTask && droppedTask.status) {
      const taskStatus = availableStatuses.find(s => {
        const taskStatusLower = (droppedTask.status || "").toLowerCase();
        const statusNameLower = s.name.toLowerCase();
        return taskStatusLower === statusNameLower || 
               taskStatusLower.includes(statusNameLower) || 
               statusNameLower.includes(taskStatusLower);
      });
      if (taskStatus) {
        orderId = getOrderIdFromStatusId(String(taskStatus.id), orderIdToStatusIdMap);
      }
    }
  }
  
  const statusId = orderId ? getStatusIdFromOrderId(orderId, orderIdToStatusIdMap) : null;
  let derivedStatusId = statusId;

  if (!derivedStatusId && overData?.statusId) {
    derivedStatusId = String(overData.statusId);
  }

  if (!derivedStatusId && orderId && !orderId.startsWith('order-')) {
    derivedStatusId = orderId;
  }

  return { orderId, statusId: derivedStatusId };
}

/**
 * Status normalization helpers
 */
export function normalizeStatus(status: string | null | undefined): string {
  if (!status) return '';
  const normalized = status.toLowerCase().trim();
  if (normalized === '' || normalized === 'new' || normalized === 'no status' || normalized === 'none') {
    return '';
  }
  return normalized;
}

export function findMatchingStatusId(
  statusName: string | null | undefined,
  availableStatuses: Array<{ id: string | number; name: string }>
): string | null {
  if (!statusName || !availableStatuses) return null;
  const normalized = normalizeStatus(statusName);
  
  // Try exact match
  let matching = availableStatuses.find(s => {
    const sNormalized = normalizeStatus(s.name);
    return sNormalized === normalized;
  });
  
  // Try partial match
  if (!matching) {
    matching = availableStatuses.find(s => {
      const sNormalized = normalizeStatus(s.name);
      return sNormalized.includes(normalized) || normalized.includes(sNormalized);
    });
  }
  
  return matching ? String(matching.id) : null;
}

/**
 * Error message formatting
 */
export function formatTaskUpdateError(error: unknown): { message: string; description: string } {
  const errorMessage = error instanceof Error ? error.message : String(error);
  
  if (errorMessage.includes('no valid transition exists') || errorMessage.includes('no valid transition')) {
    return {
      message: 'Status transition not allowed',
      description: 'You do not have permission to change the task status from the current status to the target status based on your role. Please contact your administrator or try a different status transition.',
    };
  }
  
  if (errorMessage.includes('Status is invalid')) {
    return {
      message: 'Status change not allowed',
      description: 'This status change is not allowed. The status transition may be restricted by your role permissions or workflow rules.',
    };
  }
  
  if (errorMessage.includes('workflow') || errorMessage.includes('transition')) {
    return {
      message: 'Workflow restriction',
      description: 'This status transition is not allowed by the workflow rules. Please try a different status or contact your administrator.',
    };
  }
  
  if (errorMessage.includes('422') || errorMessage.includes('Unprocessable')) {
    return {
      message: 'Validation error',
      description: 'The status change could not be processed. This may be due to workflow restrictions or invalid data.',
    };
  }
  
  if (errorMessage.includes('404') || errorMessage.includes('Not Found')) {
    return {
      message: 'Task not found',
      description: 'The task could not be found. It may have been deleted or you may not have permission to access it.',
    };
  }
  
  if (errorMessage.includes('403') || errorMessage.includes('Forbidden')) {
    return {
      message: 'Permission denied',
      description: 'You do not have permission to update this task.',
    };
  }
  
  if (errorMessage.includes('401') || errorMessage.includes('Unauthorized')) {
    return {
      message: 'Authentication required',
      description: 'Your session may have expired. Please refresh the page and try again.',
    };
  }
  
  return {
    message: 'Failed to update task status',
    description: errorMessage || 'An unknown error occurred while updating the task status.',
  };
}

