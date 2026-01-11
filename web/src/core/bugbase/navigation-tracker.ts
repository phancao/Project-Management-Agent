// Copyright (c) 2025 Galaxy Technology Service
// BugBase Navigation Tracker - Tracks navigation history for bug reports

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface NavigationEntry {
    id: string;
    path: string;
    timestamp: number;
    action: 'navigate' | 'click' | 'scroll' | 'input';
    metadata?: {
        elementId?: string;
        elementText?: string;
        scrollPosition?: { x: number; y: number };
        inputName?: string;
    };
}

interface NavigationTrackerState {
    entries: NavigationEntry[];
    isTracking: boolean;
    maxEntries: number;

    // Actions
    addEntry: (entry: Omit<NavigationEntry, 'id' | 'timestamp'>) => void;
    clearHistory: () => void;
    getHistory: () => NavigationEntry[];
    startTracking: () => void;
    stopTracking: () => void;
}

const generateId = () => `nav_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

export const useNavigationTracker = create<NavigationTrackerState>()(
    persist(
        (set, get) => ({
            entries: [],
            isTracking: true,
            maxEntries: 50,

            addEntry: (entry) => {
                if (!get().isTracking) return;

                const newEntry: NavigationEntry = {
                    ...entry,
                    id: generateId(),
                    timestamp: Date.now(),
                };

                set((state) => ({
                    entries: [...state.entries, newEntry].slice(-state.maxEntries),
                }));
            },

            clearHistory: () => set({ entries: [] }),

            getHistory: () => get().entries,

            startTracking: () => set({ isTracking: true }),

            stopTracking: () => set({ isTracking: false }),
        }),
        {
            name: 'bugbase-navigation-history',
            partialize: (state) => ({
                entries: state.entries.slice(-20), // Only persist last 20 in localStorage
            }),
        }
    )
);

// Hook to track route changes - use in layout or app provider
export function trackNavigation(path: string) {
    useNavigationTracker.getState().addEntry({
        path,
        action: 'navigate',
    });
}

// Hook to track user interactions
export function trackInteraction(
    action: 'click' | 'scroll' | 'input',
    metadata?: NavigationEntry['metadata']
) {
    const currentPath = typeof window !== 'undefined' ? window.location.pathname : '/';
    useNavigationTracker.getState().addEntry({
        path: currentPath,
        action,
        metadata,
    });
}
