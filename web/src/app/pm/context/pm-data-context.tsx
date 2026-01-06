"use client";

import React, { createContext, useContext, useMemo, type ReactNode } from "react";
import { useProviders } from "~/core/api/hooks/pm/use-providers";
import type { ProviderConfig } from "~/app/pm/types";

/**
 * Lightweight PM Data Context for the PM Chat page
 * 
 * This provider only fetches essential data (providers) to minimize initial load time.
 * Heavy data (users, tasks, time entries) is loaded by individual views as needed.
 * The views panel has its own loading states for those.
 */

interface PMDataContextValue {
    // Providers only - minimal blocking data
    providers: ProviderConfig[];

    // Loading state
    isLoading: boolean;
    isLoadingProviders: boolean;

    // Count
    providersCount: number;

    // Error
    error: Error | null;
}

const PMDataContext = createContext<PMDataContextValue | null>(null);

interface PMDataProviderProps {
    children: ReactNode;
}

export function PMDataProvider({ children }: PMDataProviderProps) {
    // Only fetch providers - this is quick and essential
    const { providers, loading: isLoadingProviders, error: providersError } = useProviders();

    // Build context value
    const value: PMDataContextValue = useMemo(() => ({
        providers: providers || [],

        isLoading: isLoadingProviders,
        isLoadingProviders,

        providersCount: providers?.length || 0,

        error: providersError || null,
    }), [providers, isLoadingProviders, providersError]);

    return (
        <PMDataContext.Provider value={value}>
            {children}
        </PMDataContext.Provider>
    );
}

/**
 * Hook to access centralized PM data.
 * Must be used within a PMDataProvider.
 */
export function usePMDataContext(): PMDataContextValue {
    const context = useContext(PMDataContext);
    if (!context) {
        throw new Error("usePMDataContext must be used within a PMDataProvider");
    }
    return context;
}

/**
 * Safe version of usePMDataContext that returns null if used outside a provider.
 * Use this when the component might be rendered before the provider is available.
 */
export function usePMDataContextOptional(): PMDataContextValue | null {
    return useContext(PMDataContext);
}



