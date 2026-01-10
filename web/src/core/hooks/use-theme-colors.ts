// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useSettingsStore, type AccentColor, type CardStyle } from "~/core/store";

/**
 * Color theme mappings for the Galaxy AI Design System
 */
export const THEME_COLORS: Record<AccentColor, {
    // Gradient classes
    gradient: string;
    gradientHover: string;
    // Shadow classes
    shadow: string;
    darkShadow: string;
    // Text/spinner colors
    text: string;
    textDark: string;
    spinner: string;
    // Badge/background colors
    badgeBg: string;
    badgeText: string;
    // Ring/focus colors
    ring: string;
}> = {
    indigo: {
        gradient: 'from-indigo-500 to-violet-600',
        gradientHover: 'hover:from-indigo-600 hover:to-violet-700',
        shadow: 'shadow-indigo-500/30',
        darkShadow: 'dark:shadow-indigo-500/10',
        text: 'text-indigo-600',
        textDark: 'dark:text-indigo-400',
        spinner: 'text-indigo-500 dark:text-indigo-400',
        badgeBg: 'bg-indigo-100 dark:bg-indigo-900/30',
        badgeText: 'text-indigo-700 dark:text-indigo-300',
        ring: 'ring-indigo-500',
    },
    blue: {
        gradient: 'from-blue-500 to-cyan-600',
        gradientHover: 'hover:from-blue-600 hover:to-cyan-700',
        shadow: 'shadow-blue-500/30',
        darkShadow: 'dark:shadow-blue-500/10',
        text: 'text-blue-600',
        textDark: 'dark:text-blue-400',
        spinner: 'text-blue-500 dark:text-blue-400',
        badgeBg: 'bg-blue-100 dark:bg-blue-900/30',
        badgeText: 'text-blue-700 dark:text-blue-300',
        ring: 'ring-blue-500',
    },
    purple: {
        gradient: 'from-purple-500 to-pink-600',
        gradientHover: 'hover:from-purple-600 hover:to-pink-700',
        shadow: 'shadow-purple-500/30',
        darkShadow: 'dark:shadow-purple-500/10',
        text: 'text-purple-600',
        textDark: 'dark:text-purple-400',
        spinner: 'text-purple-500 dark:text-purple-400',
        badgeBg: 'bg-purple-100 dark:bg-purple-900/30',
        badgeText: 'text-purple-700 dark:text-purple-300',
        ring: 'ring-purple-500',
    },
    emerald: {
        gradient: 'from-emerald-500 to-teal-600',
        gradientHover: 'hover:from-emerald-600 hover:to-teal-700',
        shadow: 'shadow-emerald-500/30',
        darkShadow: 'dark:shadow-emerald-500/10',
        text: 'text-emerald-600',
        textDark: 'dark:text-emerald-400',
        spinner: 'text-emerald-500 dark:text-emerald-400',
        badgeBg: 'bg-emerald-100 dark:bg-emerald-900/30',
        badgeText: 'text-emerald-700 dark:text-emerald-300',
        ring: 'ring-emerald-500',
    },
    amber: {
        gradient: 'from-amber-500 to-orange-600',
        gradientHover: 'hover:from-amber-600 hover:to-orange-700',
        shadow: 'shadow-amber-500/30',
        darkShadow: 'dark:shadow-amber-500/10',
        text: 'text-amber-600',
        textDark: 'dark:text-amber-400',
        spinner: 'text-amber-500 dark:text-amber-400',
        badgeBg: 'bg-amber-100 dark:bg-amber-900/30',
        badgeText: 'text-amber-700 dark:text-amber-300',
        ring: 'ring-amber-500',
    },
    rose: {
        gradient: 'from-rose-500 to-pink-600',
        gradientHover: 'hover:from-rose-600 hover:to-pink-700',
        shadow: 'shadow-rose-500/30',
        darkShadow: 'dark:shadow-rose-500/10',
        text: 'text-rose-600',
        textDark: 'dark:text-rose-400',
        spinner: 'text-rose-500 dark:text-rose-400',
        badgeBg: 'bg-rose-100 dark:bg-rose-900/30',
        badgeText: 'text-rose-700 dark:text-rose-300',
        ring: 'ring-rose-500',
    },
};

/**
 * Card style classes
 */
export const CARD_STYLES: Record<CardStyle, {
    base: string;
    dark: string;
}> = {
    solid: {
        base: 'bg-white border border-gray-200',
        dark: 'dark:bg-slate-900 dark:border-slate-700/50',
    },
    glassmorphic: {
        base: 'bg-white/80 backdrop-blur-sm border border-gray-200/50',
        dark: 'dark:bg-slate-900/80 dark:border-slate-700/50',
    },
};

/**
 * Hook to get the current theme colors from settings
 */
export function useThemeColors() {
    const appearance = useSettingsStore((state) => state.appearance);
    const accentColor = appearance?.accentColor || 'indigo';
    const cardStyle = appearance?.cardStyle || 'solid';

    return {
        accent: THEME_COLORS[accentColor],
        card: CARD_STYLES[cardStyle],
        accentColorName: accentColor,
        cardStyleName: cardStyle,
    };
}

/**
 * Hook to get just the accent color theme
 */
export function useAccentColor() {
    const accentColor = useSettingsStore((state) => state.appearance?.accentColor || 'indigo');
    return THEME_COLORS[accentColor];
}

/**
 * Hook to get just the card style
 */
export function useCardStyle() {
    const cardStyle = useSettingsStore((state) => state.appearance?.cardStyle || 'solid');
    return CARD_STYLES[cardStyle];
}

/**
 * Get theme colors without hook (for non-component usage)
 */
export function getThemeColors(accentColor: AccentColor = 'indigo') {
    return THEME_COLORS[accentColor];
}

/**
 * Get card style classes without hook
 */
export function getCardStyles(cardStyle: CardStyle = 'solid') {
    return CARD_STYLES[cardStyle];
}
