// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import type { Project } from "../types";

/**
 * Utility functions for working with projects
 */

/**
 * Extract project key from project ID
 * Example: "fc9e2adf-476e-4432-907a-4a5818f90bbc:TS" -> "TS"
 */
export function extractProjectKey(projectId: string): string {
  const parts = projectId.split(':');
  return parts.length > 1 ? parts[parts.length - 1] : projectId;
}

/**
 * Extract provider ID from project ID
 * Example: "fc9e2adf-476e-4432-907a-4a5818f90bbc:TS" -> "fc9e2adf-476e-4432-907a-4a5818f90bbc"
 */
export function extractProviderId(projectId: string): string | null {
  const parts = projectId.split(':');
  return parts.length > 1 ? parts[0] : null;
}

/**
 * Check if a project ID has a provider prefix (UUID:project_id format)
 */
export function hasProviderPrefix(projectId: string): boolean {
  const parts = projectId.split(':');
  if (parts.length < 2) return false;
  
  // Check if the first part is a valid UUID
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidRegex.test(parts[0]);
}

/**
 * Find a project in a list by ID, handling both prefixed and non-prefixed IDs
 */
export function findProjectById(projects: Project[], projectId: string): Project | undefined {
  if (!projectId) return undefined;
  
  // First try exact match
  const exactMatch = projects.find(p => p.id === projectId);
  if (exactMatch) return exactMatch;
  
  // Then try matching by project key (for provider-prefixed IDs)
  const projectKey = extractProjectKey(projectId);
  return projects.find(p => {
    const pKey = extractProjectKey(p.id);
    return pKey === projectKey || p.id === projectKey;
  });
}

/**
 * Normalize status name for comparison
 * Handles variations like "new", "no status", empty string, "none"
 */
export function normalizeStatusName(status: string | null | undefined): string {
  if (!status) return '';
  const normalized = status.toLowerCase().trim();
  
  // Treat these as equivalent to "no status"
  if (normalized === '' || normalized === 'new' || normalized === 'none' || normalized === 'no status') {
    return '';
  }
  
  return normalized;
}

/**
 * Check if two status names match (with normalization)
 */
export function statusNamesMatch(status1: string | null | undefined, status2: string | null | undefined): boolean {
  return normalizeStatusName(status1) === normalizeStatusName(status2);
}

