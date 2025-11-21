// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import type { ProviderConfig } from "~/core/api/pm/providers";

export const PROVIDER_TYPES = [
  { type: "openproject", display_name: "OpenProject v16" },
  { type: "openproject_v13", display_name: "OpenProject v13" },
  { type: "jira", display_name: "JIRA" },
  { type: "clickup", display_name: "ClickUp" },
] as const;

export interface ProviderBadgeConfig {
  label: string;
  color: string;
}

const PROVIDER_BADGE_CONFIG: Record<string, ProviderBadgeConfig> = {
  jira: {
    label: "JIRA",
    color: "bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200",
  },
  openproject: {
    label: "OP",
    color: "bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200",
  },
  openproject_v13: {
    label: "OP13",
    color: "bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200",
  },
  clickup: {
    label: "CU",
    color: "bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200",
  },
  mock: {
    label: "DEMO",
    color: "bg-amber-100 dark:bg-amber-900 text-amber-800 dark:text-amber-200",
  },
} as const;

const PROVIDER_ICONS: Record<string, string> = {
  openproject: "🔧",
  openproject_v13: "🔧",
  jira: "🎯",
  clickup: "📋",
} as const;

/**
 * Extract provider ID from project ID
 * Project IDs are in format: "providerId:projectId"
 */
export function extractProviderId(projectId: string | undefined): string | null {
  if (!projectId) return null;
  if (projectId.startsWith("mock:")) return "mock";
  const parts = projectId.split(":");
  return parts.length >= 2 ? parts[0] : null;
}

/**
 * Get provider type from project ID using provider mappings
 */
export function getProviderTypeFromProjectId(
  projectId: string | undefined,
  typeMap: Map<string, string>,
): string | null {
  const providerId = extractProviderId(projectId);
  if (!providerId) return null;
  if (providerId === "mock") return "mock";
  return typeMap.get(providerId) || null;
}

/**
 * Get provider badge configuration
 */
export function getProviderBadgeConfig(providerType: string | null): ProviderBadgeConfig {
  if (!providerType) {
    return {
      label: "??",
      color: "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200",
    };
  }
  return (
    PROVIDER_BADGE_CONFIG[providerType] || {
      label: providerType.toUpperCase().slice(0, 2),
      color: "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200",
    }
  );
}

/**
 * Get provider icon emoji
 */
export function getProviderIcon(providerType: string): string {
  return PROVIDER_ICONS[providerType] || "📦";
}

/**
 * Render provider badge component (returns className string for badge)
 */
export function getProviderBadgeClassName(providerType: string | null): string {
  const config = getProviderBadgeConfig(providerType);
  return `px-1.5 py-0.5 text-xs font-medium rounded ${config.color}`;
}

/**
 * Filter and normalize providers from API response
 */
export function normalizeProviders(
  providers: ProviderConfig[],
): Array<{ id: string; provider_type: string; base_url?: string }> {
  return providers
    .filter((p) => p.id && p.provider_type)
    .map((p) => ({
      id: p.id!,
      provider_type: p.provider_type,
      base_url: p.base_url,
    }));
}

