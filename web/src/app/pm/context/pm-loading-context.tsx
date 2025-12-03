// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import type { ReactNode } from "react";
import type { 
  Project, 
  Sprint, 
  Status, 
  Priority, 
  Epic, 
  Task, 
  ProviderConfig,
  LoadingState,
  FilterDataState 
} from "../types";

export interface PMLoadingState {
  // Section 1: Floating Header
  providers: LoadingState<ProviderConfig[]>;
  
  // Section 2: Left Pane + Upper Body (Filter Data)
  filterData: FilterDataState & {
    loading: boolean;
    error: Error | null;
  };
  
  // Section 3: Content Area (Tasks/Issues)
  tasks: LoadingState<Task[]>;
  
  // Overall state
  isFilterDataReady: boolean;
  canLoadTasks: boolean;
}

interface PMLoadingContextType {
  state: PMLoadingState;
  setProvidersState: (state: Partial<PMLoadingState['providers']>) => void;
  setProjectsState: (state: Partial<PMLoadingState['filterData']['projects']>) => void;
  setSprintsState: (state: Partial<PMLoadingState['filterData']['sprints']>) => void;
  setStatusesState: (state: Partial<PMLoadingState['filterData']['statuses']>) => void;
  setPrioritiesState: (state: Partial<PMLoadingState['filterData']['priorities']>) => void;
  setEpicsState: (state: Partial<PMLoadingState['filterData']['epics']>) => void;
  setTasksState: (state: Partial<PMLoadingState['tasks']>) => void;
  refreshProviders: () => void;
  refreshFilterData: (projectId?: string) => void;
  refreshTasks: (projectId?: string) => void;
  refreshSection: (section: 'providers' | 'filterData' | 'tasks', projectId?: string) => void;
}

const PMLoadingContext = createContext<PMLoadingContextType | undefined>(undefined);

const createLoadingState = <T,>(): LoadingState<T> => ({
  loading: false,
  error: null,
  data: null,
});

const initialState: PMLoadingState = {
  providers: {
    loading: true,
    error: null,
    data: null,
  },
  filterData: {
    loading: true,
    error: null,
    projects: {
      loading: true,
      error: null,
      data: null,
    },
    sprints: createLoadingState<Sprint[]>(),
    statuses: createLoadingState<Status[]>(),
    priorities: createLoadingState<Priority[]>(),
    epics: createLoadingState<Epic[]>(),
  },
  tasks: createLoadingState<Task[]>(),
  isFilterDataReady: false,
  canLoadTasks: false,
};

export function PMLoadingProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<PMLoadingState>(initialState);

  // Update providers state
  const setProvidersState = useCallback((updates: Partial<PMLoadingState['providers']>) => {
    setState(prev => ({
      ...prev,
      providers: {
        ...prev.providers,
        ...updates,
      },
    }));
  }, []);

  // Update projects state
  const setProjectsState = useCallback((updates: Partial<PMLoadingState['filterData']['projects']>) => {
    setState(prev => ({
      ...prev,
      filterData: {
        ...prev.filterData,
        projects: {
          ...prev.filterData.projects,
          ...updates,
        },
      },
    }));
  }, []);

  // Update sprints state
  const setSprintsState = useCallback((updates: Partial<PMLoadingState['filterData']['sprints']>) => {
    setState(prev => ({
      ...prev,
      filterData: {
        ...prev.filterData,
        sprints: {
          ...prev.filterData.sprints,
          ...updates,
        },
      },
    }));
  }, []);

  // Update statuses state
  const setStatusesState = useCallback((updates: Partial<PMLoadingState['filterData']['statuses']>) => {
    setState(prev => ({
      ...prev,
      filterData: {
        ...prev.filterData,
        statuses: {
          ...prev.filterData.statuses,
          ...updates,
        },
      },
    }));
  }, []);

  // Update priorities state
  const setPrioritiesState = useCallback((updates: Partial<PMLoadingState['filterData']['priorities']>) => {
    setState(prev => ({
      ...prev,
      filterData: {
        ...prev.filterData,
        priorities: {
          ...prev.filterData.priorities,
          ...updates,
        },
      },
    }));
  }, []);

  // Update epics state
  const setEpicsState = useCallback((updates: Partial<PMLoadingState['filterData']['epics']>) => {
    setState(prev => ({
      ...prev,
      filterData: {
        ...prev.filterData,
        epics: {
          ...prev.filterData.epics,
          ...updates,
        },
      },
    }));
  }, []);

  // Update tasks state
  const setTasksState = useCallback((updates: Partial<PMLoadingState['tasks']>) => {
    setState(prev => ({
      ...prev,
      tasks: {
        ...prev.tasks,
        ...updates,
      },
    }));
  }, []);

  // Refresh providers
  const refreshProviders = useCallback(() => {
    setProvidersState({ loading: true, error: null });
    // This will be handled by the component that uses this context
  }, [setProvidersState]);

  // Refresh filter data
  const refreshFilterData = useCallback((projectId?: string) => {
    setState(prev => ({
      ...prev,
      filterData: {
        ...prev.filterData,
        loading: true,
        error: null,
        projects: { ...prev.filterData.projects, loading: true },
        sprints: { ...prev.filterData.sprints, loading: true },
        statuses: { ...prev.filterData.statuses, loading: true },
        priorities: { ...prev.filterData.priorities, loading: true },
        epics: { ...prev.filterData.epics, loading: true },
      },
    }));
    // This will be handled by the component that uses this context
  }, []);

  // Refresh tasks
  const refreshTasks = useCallback((projectId?: string) => {
    setTasksState({ loading: true, error: null });
    // This will be handled by the component that uses this context
  }, [setTasksState]);

  // Refresh a specific section
  const refreshSection = useCallback((section: 'providers' | 'filterData' | 'tasks', projectId?: string) => {
    if (section === 'providers') {
      refreshProviders();
    } else if (section === 'filterData') {
      refreshFilterData(projectId);
    } else if (section === 'tasks') {
      refreshTasks(projectId);
    }
  }, [refreshProviders, refreshFilterData, refreshTasks]);

  // Calculate if filter data is ready
  useEffect(() => {
    const filterData = state.filterData;
    const isReady = 
      !filterData.projects.loading &&
      !filterData.sprints.loading &&
      !filterData.statuses.loading &&
      !filterData.priorities.loading &&
      !filterData.epics.loading &&
      filterData.projects.data !== null;

    const canLoad = 
      !state.providers.loading &&
      isReady;

    setState(prev => ({
      ...prev,
      isFilterDataReady: isReady,
      canLoadTasks: canLoad,
      filterData: {
        ...prev.filterData,
        loading: filterData.projects.loading || 
                 filterData.sprints.loading || 
                 filterData.statuses.loading || 
                 filterData.priorities.loading || 
                 filterData.epics.loading,
      },
    }));
  }, [
    state.filterData.projects.loading,
    state.filterData.sprints.loading,
    state.filterData.statuses.loading,
    state.filterData.priorities.loading,
    state.filterData.epics.loading,
    state.filterData.projects.data,
    state.providers.loading,
  ]);

  const value: PMLoadingContextType = {
    state,
    setProvidersState,
    setProjectsState,
    setSprintsState,
    setStatusesState,
    setPrioritiesState,
    setEpicsState,
    setTasksState,
    refreshProviders,
    refreshFilterData,
    refreshTasks,
    refreshSection,
  };

  return (
    <PMLoadingContext.Provider value={value}>
      {children}
    </PMLoadingContext.Provider>
  );
}

export function usePMLoading() {
  const context = useContext(PMLoadingContext);
  if (context === undefined) {
    throw new Error('usePMLoading must be used within a PMLoadingProvider');
  }
  return context;
}

