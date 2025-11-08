// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * Temporary debug shim.
 *
 * We keep the public surface to avoid touching every call site, but all
 * methods are no-ops so the existing debug noise is fully silenced.
 */

export type DebugCategory = 
  | 'time'
  | 'api'
  | 'filter'
  | 'state'
  | 'render'
  | 'dnd'
  | 'storage'
  | 'project'
  | 'task'
  | 'column'
  | 'all';

export interface DebugConfig {
  enabled: boolean;
  categories: Set<DebugCategory>;
  includeTimestamp: boolean;
  includePerformance: boolean;
}

const noop = () => {
  // Intentionally empty
};

const defaultConfig: DebugConfig = {
  enabled: false,
  categories: new Set<DebugCategory>(),
  includeTimestamp: false,
  includePerformance: false,
};

type LogFn = (message: string, data?: unknown) => void;
type TimerFn = (label: string, message?: string) => void;

interface DebugAPI {
  time: LogFn;
  timeStart: (label: string) => void;
  timeEnd: TimerFn;
  api: LogFn;
  filter: LogFn;
  state: LogFn;
  render: LogFn;
  dnd: LogFn;
  storage: LogFn;
  project: LogFn;
  task: LogFn;
  column: LogFn;
  warn: LogFn;
  error: LogFn;
  setEnabled: (enabled: boolean) => void;
  setCategories: (categories: DebugCategory[]) => void;
  addCategories: (categories: DebugCategory[]) => void;
  removeCategories: (categories: DebugCategory[]) => void;
  isEnabled: (category: DebugCategory) => boolean;
  getConfig: () => Readonly<DebugConfig>;
  reloadConfig: () => void;
    }
    
const debugImpl: DebugAPI = {
  time: noop,
  timeStart: noop,
  timeEnd: noop,
  api: noop,
  filter: noop,
  state: noop,
  render: noop,
  dnd: noop,
  storage: noop,
  project: noop,
  task: noop,
  column: noop,
  warn: noop,
  error: noop,
  setEnabled: noop,
  setCategories: noop,
  addCategories: noop,
  removeCategories: noop,
  isEnabled: () => false,
  getConfig: () => ({ ...defaultConfig }),
  reloadConfig: noop,
};

export const debug = debugImpl;

export const enableDebug = (_categories?: DebugCategory[]) => {
  // no-op
};

export const disableDebug = () => {
  // no-op
};
