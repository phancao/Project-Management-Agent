// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useSettingsStore, type AccentColor, type CardStyle } from "~/core/store";

/**
 * Brand Color Palette
 * Main Colors:
 *   - Dark Blue (Xanh Đậm): #1E398D
 *   - Teal (Xanh Ngọc): #14B795
 * Sub-Colors:
 *   - Orange (Cam): #F47920
 *   - Light Blue (Xanh Nhạt): #1C9AD6 
 *   - Green (Xanh Lá): #8DC63F
 *   - Pink (Hồng): #CF2C91
 *   - Red (Đỏ): #ED1C29 (reserved for errors/danger)
 */

/**
 * Color theme mappings for the Galaxy AI Design System
 * Using brand guideline colors with custom Tailwind classes
 */
export const THEME_COLORS: Record<AccentColor, {
    // Hex value for custom styling
    hex: string;
    // Gradient classes (using arbitrary values for brand colors)
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
    // CSS custom property style for dynamic use
    style: { '--accent-color': string };
    // Card glow effect classes (border, shadow, ring)
    cardGlow: {
        border: string;
        shadow: string;
        ring: string;
    };
    // Stat card glow effect classes (smaller cards for metrics)
    statCardGlow: {
        border: string;
        shadow: string;
        ring: string;
    };
}> = {
    darkBlue: {
        hex: '#1E398D',
        gradient: 'from-[#1E398D] to-[#14B795]',
        gradientHover: 'hover:from-[#162c6f] hover:to-[#0f9678]',
        shadow: 'shadow-[#1E398D]/30',
        darkShadow: 'dark:shadow-[#1E398D]/10',
        text: 'text-[#1E398D]',
        textDark: 'dark:text-[#5a7fd9]',
        spinner: 'text-[#1E398D] dark:text-[#5a7fd9]',
        badgeBg: 'bg-[#1E398D]/10 dark:bg-[#1E398D]/30',
        badgeText: 'text-[#1E398D] dark:text-[#5a7fd9]',
        ring: 'ring-[#1E398D]',
        style: { '--accent-color': '#1E398D' },
        cardGlow: {
            border: 'border-[#1E398D]/40 dark:border-[#1E398D]/50',
            shadow: 'shadow-lg shadow-[#1E398D]/30 dark:shadow-[#1E398D]/40',
            ring: 'ring-1 ring-[#1E398D]/30 dark:ring-[#1E398D]/40',
        },
        statCardGlow: {
            border: 'border-[#1E398D]/40 dark:border-[#1E398D]/50',
            shadow: 'shadow-lg shadow-[#1E398D]/25 dark:shadow-[#1E398D]/35',
            ring: 'ring-1 ring-[#1E398D]/25 dark:ring-[#1E398D]/35',
        },
    },
    teal: {
        hex: '#14B795',
        gradient: 'from-[#14B795] to-[#0f9678]',
        gradientHover: 'hover:from-[#0f9678] hover:to-[#0a7a5f]',
        shadow: 'shadow-[#14B795]/30',
        darkShadow: 'dark:shadow-[#14B795]/10',
        text: 'text-[#14B795]',
        textDark: 'dark:text-[#4fd9bc]',
        spinner: 'text-[#14B795] dark:text-[#4fd9bc]',
        badgeBg: 'bg-[#14B795]/10 dark:bg-[#14B795]/30',
        badgeText: 'text-[#14B795] dark:text-[#4fd9bc]',
        ring: 'ring-[#14B795]',
        style: { '--accent-color': '#14B795' },
        cardGlow: {
            border: 'border-[#14B795]/40 dark:border-[#14B795]/50',
            shadow: 'shadow-lg shadow-[#14B795]/30 dark:shadow-[#14B795]/40',
            ring: 'ring-1 ring-[#14B795]/30 dark:ring-[#14B795]/40',
        },
        statCardGlow: {
            border: 'border-[#14B795]/40 dark:border-[#14B795]/50',
            shadow: 'shadow-lg shadow-[#14B795]/25 dark:shadow-[#14B795]/35',
            ring: 'ring-1 ring-[#14B795]/25 dark:ring-[#14B795]/35',
        },
    },
    orange: {
        hex: '#F47920',
        gradient: 'from-[#F47920] to-[#e06512]',
        gradientHover: 'hover:from-[#e06512] hover:to-[#c55610]',
        shadow: 'shadow-[#F47920]/30',
        darkShadow: 'dark:shadow-[#F47920]/10',
        text: 'text-[#F47920]',
        textDark: 'dark:text-[#f9a05c]',
        spinner: 'text-[#F47920] dark:text-[#f9a05c]',
        badgeBg: 'bg-[#F47920]/10 dark:bg-[#F47920]/30',
        badgeText: 'text-[#F47920] dark:text-[#f9a05c]',
        ring: 'ring-[#F47920]',
        style: { '--accent-color': '#F47920' },
        cardGlow: {
            border: 'border-[#F47920]/40 dark:border-[#F47920]/50',
            shadow: 'shadow-lg shadow-[#F47920]/30 dark:shadow-[#F47920]/40',
            ring: 'ring-1 ring-[#F47920]/30 dark:ring-[#F47920]/40',
        },
        statCardGlow: {
            border: 'border-[#F47920]/40 dark:border-[#F47920]/50',
            shadow: 'shadow-lg shadow-[#F47920]/25 dark:shadow-[#F47920]/35',
            ring: 'ring-1 ring-[#F47920]/25 dark:ring-[#F47920]/35',
        },
    },
    lightBlue: {
        hex: '#1C9AD6',
        gradient: 'from-[#1C9AD6] to-[#1483b8]',
        gradientHover: 'hover:from-[#1483b8] hover:to-[#0f6d9a]',
        shadow: 'shadow-[#1C9AD6]/30',
        darkShadow: 'dark:shadow-[#1C9AD6]/10',
        text: 'text-[#1C9AD6]',
        textDark: 'dark:text-[#5cb8e6]',
        spinner: 'text-[#1C9AD6] dark:text-[#5cb8e6]',
        badgeBg: 'bg-[#1C9AD6]/10 dark:bg-[#1C9AD6]/30',
        badgeText: 'text-[#1C9AD6] dark:text-[#5cb8e6]',
        ring: 'ring-[#1C9AD6]',
        style: { '--accent-color': '#1C9AD6' },
        cardGlow: {
            border: 'border-[#1C9AD6]/40 dark:border-[#1C9AD6]/50',
            shadow: 'shadow-lg shadow-[#1C9AD6]/30 dark:shadow-[#1C9AD6]/40',
            ring: 'ring-1 ring-[#1C9AD6]/30 dark:ring-[#1C9AD6]/40',
        },
        statCardGlow: {
            border: 'border-[#1C9AD6]/40 dark:border-[#1C9AD6]/50',
            shadow: 'shadow-lg shadow-[#1C9AD6]/25 dark:shadow-[#1C9AD6]/35',
            ring: 'ring-1 ring-[#1C9AD6]/25 dark:ring-[#1C9AD6]/35',
        },
    },
    green: {
        hex: '#8DC63F',
        gradient: 'from-[#8DC63F] to-[#7ab335]',
        gradientHover: 'hover:from-[#7ab335] hover:to-[#67992d]',
        shadow: 'shadow-[#8DC63F]/30',
        darkShadow: 'dark:shadow-[#8DC63F]/10',
        text: 'text-[#8DC63F]',
        textDark: 'dark:text-[#a8d46a]',
        spinner: 'text-[#8DC63F] dark:text-[#a8d46a]',
        badgeBg: 'bg-[#8DC63F]/10 dark:bg-[#8DC63F]/30',
        badgeText: 'text-[#8DC63F] dark:text-[#a8d46a]',
        ring: 'ring-[#8DC63F]',
        style: { '--accent-color': '#8DC63F' },
        cardGlow: {
            border: 'border-[#8DC63F]/40 dark:border-[#8DC63F]/50',
            shadow: 'shadow-lg shadow-[#8DC63F]/30 dark:shadow-[#8DC63F]/40',
            ring: 'ring-1 ring-[#8DC63F]/30 dark:ring-[#8DC63F]/40',
        },
        statCardGlow: {
            border: 'border-[#8DC63F]/40 dark:border-[#8DC63F]/50',
            shadow: 'shadow-lg shadow-[#8DC63F]/25 dark:shadow-[#8DC63F]/35',
            ring: 'ring-1 ring-[#8DC63F]/25 dark:ring-[#8DC63F]/35',
        },
    },
    pink: {
        hex: '#CF2C91',
        gradient: 'from-[#CF2C91] to-[#b5257f]',
        gradientHover: 'hover:from-[#b5257f] hover:to-[#9a1f6c]',
        shadow: 'shadow-[#CF2C91]/30',
        darkShadow: 'dark:shadow-[#CF2C91]/10',
        text: 'text-[#CF2C91]',
        textDark: 'dark:text-[#e066b5]',
        spinner: 'text-[#CF2C91] dark:text-[#e066b5]',
        badgeBg: 'bg-[#CF2C91]/10 dark:bg-[#CF2C91]/30',
        badgeText: 'text-[#CF2C91] dark:text-[#e066b5]',
        ring: 'ring-[#CF2C91]',
        style: { '--accent-color': '#CF2C91' },
        cardGlow: {
            border: 'border-[#CF2C91]/40 dark:border-[#CF2C91]/50',
            shadow: 'shadow-lg shadow-[#CF2C91]/30 dark:shadow-[#CF2C91]/40',
            ring: 'ring-1 ring-[#CF2C91]/30 dark:ring-[#CF2C91]/40',
        },
        statCardGlow: {
            border: 'border-[#CF2C91]/40 dark:border-[#CF2C91]/50',
            shadow: 'shadow-lg shadow-[#CF2C91]/25 dark:shadow-[#CF2C91]/35',
            ring: 'ring-1 ring-[#CF2C91]/25 dark:ring-[#CF2C91]/35',
        },
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
    const accentColor = appearance?.accentColor || 'darkBlue';
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
    const accentColor = useSettingsStore((state) => state.appearance?.accentColor || 'darkBlue');
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
export function getThemeColors(accentColor: AccentColor = 'darkBlue') {
    return THEME_COLORS[accentColor];
}

/**
 * Get card style classes without hook
 */
export function getCardStyles(cardStyle: CardStyle = 'solid') {
    return CARD_STYLES[cardStyle];
}

/**
 * Hook to get card glow classes that follow the accent color setting
 * Returns a combined className string for easy use in components
 */
export function useCardGlow() {
    const accentColor = useSettingsStore((state) => state.appearance?.accentColor || 'darkBlue');
    const glow = THEME_COLORS[accentColor].cardGlow;

    return {
        // Combined className for easy use
        className: `${glow.border} ${glow.shadow} ${glow.ring}`,
        // Individual classes for more control
        border: glow.border,
        shadow: glow.shadow,
        ring: glow.ring,
    };
}

/**
 * Hook to get stat card glow classes that follow the accent color setting
 * (For smaller metric cards)
 */
export function useStatCardGlow() {
    const accentColor = useSettingsStore((state) => state.appearance?.accentColor || 'darkBlue');
    const glow = THEME_COLORS[accentColor].statCardGlow;

    return {
        className: `${glow.border} ${glow.shadow} ${glow.ring}`,
        border: glow.border,
        shadow: glow.shadow,
        ring: glow.ring,
    };
}

/**
 * Get card glow classes without hook (for non-component usage)
 */
export function getCardGlow(accentColor: AccentColor = 'darkBlue') {
    const glow = THEME_COLORS[accentColor].cardGlow;
    return {
        className: `${glow.border} ${glow.shadow} ${glow.ring}`,
        border: glow.border,
        shadow: glow.shadow,
        ring: glow.ring,
    };
}
