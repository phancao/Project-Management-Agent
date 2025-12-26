// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * Color themes for different analysis block types
 * Updated with Brand Guideline Pantone Colors
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

// Brand Colors (Hex approx from Pantone)
// Pantone Blue 072 CP: #162B75
// Pantone 233 CP (Magenta): #CE007C
// Pantone 2382 CP (Cyan): #009CDF
// Pantone 485 CP (Red): #DA291C
// Pantone 2400 CP (Teal): #009682
// Pantone Orange 021 CP: #FE5000
// Pantone 376 CP (Green): #84BD00
// Pantone Cool Gray 5 C: #B1B3B3

export const reactTheme: AnalysisTheme = {
  // Using Pantone Blue 072 CP as primary
  primary: "#162B75",
  gradient: "from-[#162B75] to-[#009CDF]",
  border: "border-[#162B75]",
  background: "bg-white dark:bg-[#162B75]/20",
  text: "text-[#162B75] dark:text-[#009CDF]",
  iconBg: "from-[#162B75]/20 to-[#009CDF]/20",
  icon: "⚡",
  name: "ReAct Analysis",
};

export const plannerTheme: AnalysisTheme = {
  // Using Pantone 2400 CP (Teal) as primary
  primary: "#009682",
  gradient: "from-[#009682] to-[#84BD00]",
  border: "border-[#009682]",
  background: "bg-white dark:bg-[#009682]/20",
  text: "text-[#009682] dark:text-[#84BD00]",
  iconBg: "from-[#009682]/20 to-[#84BD00]/20",
  icon: "📋",
  name: "Planner Analysis",
};
