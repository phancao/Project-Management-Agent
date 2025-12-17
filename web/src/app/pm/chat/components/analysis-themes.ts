// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * Color themes for different analysis block types
 */

export interface AnalysisTheme {
  primary: string;
  gradient: string;
  border: string;
  background: string;
  text: string;
  iconBg: string;
  icon: string;
  name: string;
}

export const reactTheme: AnalysisTheme = {
  primary: "yellow",
  gradient: "from-yellow-500 to-amber-500",
  border: "border-yellow-500",
  background: "bg-yellow-50 dark:bg-yellow-950",
  text: "text-yellow-700 dark:text-yellow-300",
  iconBg: "from-yellow-500/20 to-amber-500/20",
  icon: "⚡",
  name: "ReAct Analysis",
};

export const plannerTheme: AnalysisTheme = {
  primary: "blue",
  gradient: "from-blue-500 to-cyan-500",
  border: "border-blue-500",
  background: "bg-blue-50 dark:bg-blue-950",
  text: "text-blue-700 dark:text-blue-300",
  iconBg: "from-blue-500/20 to-cyan-500/20",
  icon: "📋",
  name: "Planner Analysis",
};

