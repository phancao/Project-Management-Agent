// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useMemo } from "react";
import { usePMLoading } from "~/app/pm/context/pm-loading-context";
import type { ProviderConfig as PMProviderConfig } from "~/app/pm/types";

export interface ProviderMappings {
  typeMap: Map<string, string>;
  urlMap: Map<string, string>;
  isActiveMap: Map<string, boolean>; // Track active status of providers
  providers: Array<{ id: string; provider_type: string; base_url?: string; is_active: boolean }>;
}

/**
 * Hook to access providers from PM loading context
 * Returns providers and pre-computed mappings for efficient lookups
 */
export function useProviders(): {
  providers: PMProviderConfig[];
  loading: boolean;
  error: Error | null;
  mappings: ProviderMappings;
} {
  const { state } = usePMLoading();

  const mappings = useMemo<ProviderMappings>(() => {
    const providers = state.providers.data || [];
    const typeMap = new Map<string, string>();
    const urlMap = new Map<string, string>();
    const isActiveMap = new Map<string, boolean>();
    const providerList: Array<{ id: string; provider_type: string; base_url?: string; is_active: boolean }> = [];

    providers.forEach((p) => {
      if (p.id && p.provider_type) {
        typeMap.set(p.id, p.provider_type);
        isActiveMap.set(p.id, p.is_active !== false); // Default to true if not specified
        if (p.base_url) {
          urlMap.set(p.id, p.base_url);
        }

        // Also map by backend_provider_id if present (used by OpenProject v13)
        // Project IDs use this format: "<backend_provider_id>:<project_id>"
        const backendProviderId = p.additional_config?.backend_provider_id;
        if (backendProviderId && typeof backendProviderId === 'string') {
          typeMap.set(backendProviderId, p.provider_type);
          isActiveMap.set(backendProviderId, p.is_active !== false);
          if (p.base_url) {
            urlMap.set(backendProviderId, p.base_url);
          }
        }

        providerList.push({
          id: p.id,
          provider_type: p.provider_type,
          base_url: p.base_url,
          is_active: p.is_active !== false,
        });
      }
    });

    return { typeMap, urlMap, isActiveMap, providers: providerList };
  }, [state.providers.data]);

  return {
    providers: state.providers.data || [],
    loading: state.providers.loading,
    error: state.providers.error,
    mappings,
  };
}

