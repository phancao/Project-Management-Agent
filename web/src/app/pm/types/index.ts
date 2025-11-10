// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * Shared types for the PM (Project Management) module
 */

export interface Project {
  id: string;
  name: string;
  description?: string;
  status: string;
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  estimated_hours?: number;
  start_date?: string;
  due_date?: string;
  assigned_to?: string;
  assignee_id?: string;
  project_name?: string;
  sprint_id?: string | null;
  epic_id?: string | null;
  project_id?: string;
}

export interface Status {
  id: string;
  name: string;
  color?: string;
  is_closed?: boolean;
  is_default?: boolean;
}

export interface Priority {
  id: string;
  name: string;
  color?: string;
  is_default?: boolean;
  position?: number;
}

export interface Epic {
  id: string;
  name: string;
  description?: string;
  project_id?: string;
  status?: string;
  priority?: string;
  start_date?: string;
  end_date?: string;
  owner_id?: string;
  color?: string;
}

export interface Sprint {
  id: string;
  name: string;
  start_date?: string;
  end_date?: string;
  status: string;
}

export interface User {
  id: string;
  name: string;
  email?: string;
  username?: string;
  avatar_url?: string;
}

export interface ProviderConfig {
  id: string;
  provider_type: string;
  base_url: string;
  username?: string;
  organization_id?: string;
  workspace_id?: string;
}

export type PMView = "backlog" | "board" | "charts" | "timeline" | "team";

export interface LoadingState<T = any> {
  loading: boolean;
  error: Error | null;
  data: T | null;
}

export interface FilterDataState {
  projects: LoadingState<Project[]>;
  sprints: LoadingState<Sprint[]>;
  statuses: LoadingState<Status[]>;
  priorities: LoadingState<Priority[]>;
  epics: LoadingState<Epic[]>;
}

