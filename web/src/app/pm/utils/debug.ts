// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * Debug Engine for PM Module
 * 
 * Provides categorized debug logging that can be enabled/disabled for performance testing.
 * When disabled, all debug calls are no-ops with zero overhead.
 * 
 * Usage:
 *   import { debug } from '~/app/pm/utils/debug';
 *   debug.time('Component rendered');
 *   debug.api('Fetching tasks', { projectId });
 *   debug.filter('Filtering tasks', { count: tasks.length });
 * 
 * Enable/Disable:
 *   - In browser console: localStorage.setItem('pm:debug:enabled', 'true')
 *   - Enable specific categories: localStorage.setItem('pm:debug:categories', '["time","api"]')
 *   - Or use: debug.setEnabled(true) and debug.setCategories(['time', 'api'])
 */

export type DebugCategory = 
  | 'time'        // Performance timing logs
  | 'api'         // API request/response logs
  | 'filter'      // Data filtering logs
  | 'state'       // State management logs
  | 'render'      // Component rendering logs
  | 'dnd'         // Drag and drop logs
  | 'storage'     // LocalStorage operations
  | 'project'     // Project switching/logic
  | 'task'        // Task-related operations
  | 'column'      // Column/status operations
  | 'all';        // All categories

export interface DebugConfig {
  enabled: boolean;
  categories: Set<DebugCategory>;
  includeTimestamp: boolean;
  includePerformance: boolean;
}

// Default configuration - can be overridden via localStorage
const DEFAULT_CONFIG: DebugConfig = {
  enabled: false, // Disabled by default for performance
  categories: new Set<DebugCategory>(['all']),
  includeTimestamp: true,
  includePerformance: true,
};

// Load configuration from localStorage
function loadConfig(): DebugConfig {
  if (typeof window === 'undefined') {
    return { ...DEFAULT_CONFIG, enabled: false };
  }

  try {
    // Check if debug is explicitly enabled/disabled in localStorage
    // If the key doesn't exist, enable by default in development mode
    const enabledValue = localStorage.getItem('pm:debug:enabled');
    let enabled: boolean;
    
    if (enabledValue === null) {
      // No setting in localStorage - enable by default in development
      enabled = process.env.NODE_ENV === 'development';
    } else {
      // Respect the explicit setting
      enabled = enabledValue === 'true';
    }
    
    const categoriesStr = localStorage.getItem('pm:debug:categories');
    const categories = categoriesStr 
      ? new Set<DebugCategory>(JSON.parse(categoriesStr))
      : new Set<DebugCategory>(['all']);
    
    const includeTimestamp = localStorage.getItem('pm:debug:timestamp') !== 'false';
    const includePerformance = localStorage.getItem('pm:debug:performance') !== 'false';

    return {
      enabled,
      categories,
      includeTimestamp,
      includePerformance,
    };
  } catch (error) {
    // Silently fail - don't pollute console if localStorage is unavailable
    return DEFAULT_CONFIG;
  }
}

// Save configuration to localStorage
function saveConfig(config: DebugConfig): void {
  if (typeof window === 'undefined') return;
  
  try {
    localStorage.setItem('pm:debug:enabled', String(config.enabled));
    localStorage.setItem('pm:debug:categories', JSON.stringify(Array.from(config.categories)));
    localStorage.setItem('pm:debug:timestamp', String(config.includeTimestamp));
    localStorage.setItem('pm:debug:performance', String(config.includePerformance));
  } catch (error) {
    // Silently fail - don't pollute console if localStorage is unavailable
  }
}

// Global configuration instance
let config = loadConfig();

// Performance timing storage
const timings = new Map<string, number>();

/**
 * Debug Engine Class
 * 
 * Provides categorized debug logging with zero overhead when disabled.
 */
class DebugEngine {
  private config: DebugConfig = config;

  /**
   * Enable or disable debug logging
   */
  setEnabled(enabled: boolean): void {
    this.config.enabled = enabled;
    saveConfig(this.config);
    if (enabled) {
      console.log('[Debug] Debug logging enabled. Categories:', Array.from(this.config.categories));
    } else {
      console.log('[Debug] Debug logging disabled');
    }
  }

  /**
   * Enable or disable specific categories
   */
  setCategories(categories: DebugCategory[]): void {
    this.config.categories = new Set(categories);
    saveConfig(this.config);
    console.log('[Debug] Categories updated:', Array.from(this.config.categories));
  }

  /**
   * Add categories to enabled list
   */
  addCategories(categories: DebugCategory[]): void {
    categories.forEach(cat => this.config.categories.add(cat));
    saveConfig(this.config);
  }

  /**
   * Remove categories from enabled list
   */
  removeCategories(categories: DebugCategory[]): void {
    categories.forEach(cat => this.config.categories.delete(cat));
    saveConfig(this.config);
  }

  /**
   * Check if a category is enabled
   * This is the critical performance check - should be fast when disabled
   */
  isEnabled(category: DebugCategory): boolean {
    if (!this.config.enabled) return false;
    return this.config.categories.has('all') || this.config.categories.has(category);
  }

  /**
   * Get current configuration
   */
  getConfig(): Readonly<DebugConfig> {
    return { ...this.config };
  }

  /**
   * Format log message with optional data
   */
  private formatMessage(
    category: DebugCategory,
    emoji: string,
    message: string
  ): string {
    const parts: string[] = [];
    
    if (this.config.includeTimestamp) {
      const timestamp = performance.now();
      parts.push(`[${timestamp.toFixed(2)}ms]`);
    }
    
    parts.push(`${emoji} [${category.toUpperCase()}]`, message);
    
    return parts.join(' ');
  }

  /**
   * Log a message if the category is enabled
   * This method is only called if isEnabled() returns true, so it's safe to do formatting
   */
  private log(
    category: DebugCategory,
    emoji: string,
    message: string,
    data?: any,
    level: 'log' | 'warn' | 'error' = 'log'
  ): void {
    // Double-check (defensive programming, but should already be checked by caller)
    if (!this.isEnabled(category)) return;

    const formattedMessage = this.formatMessage(category, emoji, message);
    
    if (data !== undefined) {
      console[level](formattedMessage, data);
    } else {
      console[level](formattedMessage);
    }
  }

  /**
   * Time debug logs - Performance timing
   */
  time(message: string, data?: any): void {
    if (!this.isEnabled('time')) return;
    this.log('time', '⏱️', message, data);
  }

  /**
   * Start a performance timer
   */
  timeStart(label: string): void {
    if (!this.isEnabled('time') || !this.config.includePerformance) return;
    timings.set(label, performance.now());
  }

  /**
   * End a performance timer and log the duration
   */
  timeEnd(label: string, message?: string): void {
    if (!this.isEnabled('time') || !this.config.includePerformance) return;
    
    const startTime = timings.get(label);
    if (startTime === undefined) {
      console.warn(`[Debug] Timer "${label}" was not started`);
      return;
    }
    
    const duration = performance.now() - startTime;
    const msg = message || `Timer "${label}" completed`;
    this.log('time', '⏱️', `${msg} (took ${duration.toFixed(2)}ms)`, { label, duration });
    timings.delete(label);
  }

  /**
   * API debug logs - API requests and responses
   */
  api(message: string, data?: any): void {
    if (!this.isEnabled('api')) return;
    this.log('api', '🌐', message, data);
  }

  /**
   * Filter debug logs - Data filtering operations
   */
  filter(message: string, data?: any): void {
    if (!this.isEnabled('filter')) return;
    this.log('filter', '🔍', message, data);
  }

  /**
   * State debug logs - State management
   */
  state(message: string, data?: any): void {
    if (!this.isEnabled('state')) return;
    this.log('state', '📊', message, data);
  }

  /**
   * Render debug logs - Component rendering
   */
  render(message: string, data?: any): void {
    if (!this.isEnabled('render')) return;
    this.log('render', '🎨', message, data);
  }

  /**
   * DnD debug logs - Drag and drop operations
   */
  dnd(message: string, data?: any): void {
    if (!this.isEnabled('dnd')) return;
    this.log('dnd', '🖱️', message, data);
  }

  /**
   * Storage debug logs - LocalStorage operations
   */
  storage(message: string, data?: any): void {
    if (!this.isEnabled('storage')) return;
    this.log('storage', '💾', message, data);
  }

  /**
   * Project debug logs - Project switching and logic
   */
  project(message: string, data?: any): void {
    if (!this.isEnabled('project')) return;
    this.log('project', '📁', message, data);
  }

  /**
   * Task debug logs - Task-related operations
   */
  task(message: string, data?: any): void {
    if (!this.isEnabled('task')) return;
    this.log('task', '📋', message, data);
  }

  /**
   * Column debug logs - Column/status operations
   */
  column(message: string, data?: any): void {
    if (!this.isEnabled('column')) return;
    this.log('column', '📊', message, data);
  }

  /**
   * Warning log (always shown if debug is enabled, regardless of category)
   */
  warn(message: string, data?: any): void {
    if (!this.config.enabled) return;
    this.log('all', '⚠️', message, data, 'warn');
  }

  /**
   * Error log (always shown if debug is enabled, regardless of category)
   */
  error(message: string, data?: any): void {
    if (!this.config.enabled) return;
    this.log('all', '❌', message, data, 'error');
  }

  /**
   * Reload configuration from localStorage
   */
  reloadConfig(): void {
    this.config = loadConfig();
  }
}

// Export singleton instance
export const debug = new DebugEngine();

// Export utility functions for easy access
export const enableDebug = (categories?: DebugCategory[]) => {
  debug.setEnabled(true);
  if (categories) {
    debug.setCategories(categories);
  }
};

export const disableDebug = () => {
  debug.setEnabled(false);
  // Also clear from localStorage to ensure it stays disabled
  if (typeof window !== 'undefined') {
    try {
      localStorage.removeItem('pm:debug:enabled');
    } catch (error) {
      // Silently fail
    }
  }
};

// Auto-reload config in development (for hot-reloading during testing)
if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
  // Reload config every 2 seconds in development (allows toggling via localStorage)
  setInterval(() => {
    debug.reloadConfig();
  }, 2000);
  
  // Log debug status on load
  const currentConfig = debug.getConfig();
  if (currentConfig.enabled) {
    console.log('%c[PM Debug] ✅ Debug logging is ENABLED', 'color: green; font-weight: bold;', {
      categories: Array.from(currentConfig.categories),
      enabled: currentConfig.enabled
    });
    console.log('%c[PM Debug]', 'color: blue;', 'To disable: window.pmDebug.disable()');
    console.log('%c[PM Debug]', 'color: blue;', 'To filter categories: window.pmDebug.setCategories(["dnd", "column"])');
  } else {
    console.log('%c[PM Debug] ❌ Debug logging is DISABLED', 'color: orange; font-weight: bold;');
    console.log('%c[PM Debug]', 'color: blue;', 'Quick enable: window.pmDebug.enable()');
    console.log('%c[PM Debug]', 'color: blue;', 'Or: localStorage.setItem("pm:debug:enabled", "true") then refresh');
  }
}

// Expose debug controls to window for easy access in browser console
if (typeof window !== 'undefined') {
  (window as any).pmDebug = {
    enable: () => {
      enableDebug();
      console.log('%c[PM Debug] ✅ Debug enabled! All categories active.', 'color: green; font-weight: bold;');
      console.log('Available categories: time, api, filter, state, render, dnd, storage, project, task, column, all');
      console.log('Example: window.pmDebug.setCategories(["dnd", "column"]) to filter categories');
    },
    disable: () => {
      disableDebug();
      console.log('%c[PM Debug] ❌ Debug disabled', 'color: gray;');
    },
    setCategories: (cats: DebugCategory[]) => {
      debug.setCategories(cats);
      console.log('%c[PM Debug] Categories updated:', 'color: blue;', Array.from(debug.getConfig().categories));
    },
    addCategories: (cats: DebugCategory[]) => {
      debug.addCategories(cats);
      console.log('%c[PM Debug] Categories added:', 'color: blue;', cats);
    },
    removeCategories: (cats: DebugCategory[]) => {
      debug.removeCategories(cats);
      console.log('%c[PM Debug] Categories removed:', 'color: blue;', cats);
    },
    getConfig: () => {
      const config = debug.getConfig();
      console.log('%c[PM Debug] Current config:', 'color: blue;', {
        enabled: config.enabled,
        categories: Array.from(config.categories),
        includeTimestamp: config.includeTimestamp,
        includePerformance: config.includePerformance
      });
      return config;
    },
    reload: () => {
      debug.reloadConfig();
      const config = debug.getConfig();
      console.log('%c[PM Debug] Config reloaded:', 'color: blue;', {
        enabled: config.enabled,
        categories: Array.from(config.categories)
      });
    },
  };
}

