// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Palette, Layers, Sun, Moon, Monitor } from "lucide-react";
import { useTheme } from "next-themes";
import { cn } from "~/lib/utils";
import type { SettingsState, AccentColor, CardStyle } from "~/core/store";
import type { Tab } from "./types";

const ACCENT_COLORS: { id: AccentColor; name: string; gradient: string }[] = [
    { id: 'indigo', name: 'Indigo', gradient: 'from-indigo-500 to-violet-600' },
    { id: 'blue', name: 'Blue', gradient: 'from-blue-500 to-cyan-600' },
    { id: 'purple', name: 'Purple', gradient: 'from-purple-500 to-pink-600' },
    { id: 'emerald', name: 'Emerald', gradient: 'from-emerald-500 to-teal-600' },
    { id: 'amber', name: 'Amber', gradient: 'from-amber-500 to-orange-600' },
    { id: 'rose', name: 'Rose', gradient: 'from-rose-500 to-pink-600' },
];

const CARD_STYLES: { id: CardStyle; name: string; description: string }[] = [
    { id: 'solid', name: 'Solid', description: 'Clean, solid backgrounds' },
    { id: 'glassmorphic', name: 'Glass', description: 'Frosted glass with blur' },
];

const THEME_MODES = [
    { id: 'light', name: 'Light', icon: Sun, description: 'Light mode' },
    { id: 'dark', name: 'Dark', icon: Moon, description: 'Dark mode' },
    { id: 'system', name: 'System', icon: Monitor, description: 'Follow system' },
] as const;

export const AppearanceTab: Tab = ({ settings, onChange }) => {
    const accentColor = settings.appearance?.accentColor || 'indigo';
    const cardStyle = settings.appearance?.cardStyle || 'solid';
    const { theme = 'system', setTheme } = useTheme();

    const handleAccentChange = (color: AccentColor) => {
        onChange({
            appearance: {
                ...settings.appearance,
                loadingTheme: color, // Keep loading theme in sync with accent
                accentColor: color,
            },
        });
    };

    const handleCardStyleChange = (style: CardStyle) => {
        onChange({
            appearance: {
                ...settings.appearance,
                cardStyle: style,
            },
        });
    };

    const handleThemeModeChange = (mode: string) => {
        setTheme(mode);
    };

    return (
        <div className="space-y-8">
            <div>
                <h3 className="text-lg font-semibold mb-1">Appearance</h3>
                <p className="text-sm text-muted-foreground">
                    Customize the look and feel of the application.
                </p>
            </div>

            {/* Theme Mode */}
            <div className="space-y-4">
                <div>
                    <label className="text-sm font-medium flex items-center gap-2">
                        <Sun className="w-4 h-4" />
                        Theme Mode
                    </label>
                    <p className="text-xs text-muted-foreground mb-3">
                        Choose between light, dark, or system preference.
                    </p>

                    <div className="grid grid-cols-3 gap-3">
                        {THEME_MODES.map((mode) => (
                            <button
                                key={mode.id}
                                onClick={() => handleThemeModeChange(mode.id)}
                                className={cn(
                                    "relative flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all",
                                    theme === mode.id
                                        ? "border-primary bg-primary/5 shadow-md"
                                        : "border-transparent bg-muted/30 hover:bg-muted/50"
                                )}
                            >
                                <mode.icon className="w-6 h-6" />
                                <span className="text-xs font-medium">{mode.name}</span>

                                {theme === mode.id && (
                                    <div className="absolute top-2 right-2 w-4 h-4 rounded-full bg-primary flex items-center justify-center">
                                        <span className="text-[8px] text-primary-foreground">✓</span>
                                    </div>
                                )}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Accent Color */}
            <div className="space-y-4">
                <div>
                    <label className="text-sm font-medium flex items-center gap-2">
                        <Palette className="w-4 h-4" />
                        Accent Color
                    </label>
                    <p className="text-xs text-muted-foreground mb-3">
                        Primary color for buttons, badges, and loading indicators.
                    </p>

                    <div className="grid grid-cols-3 gap-3">
                        {ACCENT_COLORS.map((color) => (
                            <button
                                key={color.id}
                                onClick={() => handleAccentChange(color.id)}
                                className={cn(
                                    "relative flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all",
                                    accentColor === color.id
                                        ? "border-primary bg-primary/5 shadow-md"
                                        : "border-transparent bg-muted/30 hover:bg-muted/50"
                                )}
                            >
                                <div
                                    className={cn(
                                        "w-10 h-10 rounded-xl bg-gradient-to-br shadow-lg",
                                        color.gradient
                                    )}
                                />
                                <span className="text-xs font-medium">{color.name}</span>

                                {accentColor === color.id && (
                                    <div className="absolute top-2 right-2 w-4 h-4 rounded-full bg-primary flex items-center justify-center">
                                        <span className="text-[8px] text-primary-foreground">✓</span>
                                    </div>
                                )}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Card Style */}
            <div className="space-y-4">
                <div>
                    <label className="text-sm font-medium flex items-center gap-2">
                        <Layers className="w-4 h-4" />
                        Card Style
                    </label>
                    <p className="text-xs text-muted-foreground mb-3">
                        Background style for cards and panels.
                    </p>

                    <div className="grid grid-cols-2 gap-3">
                        {CARD_STYLES.map((style) => (
                            <button
                                key={style.id}
                                onClick={() => handleCardStyleChange(style.id)}
                                className={cn(
                                    "relative flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all",
                                    cardStyle === style.id
                                        ? "border-primary bg-primary/5 shadow-md"
                                        : "border-transparent bg-muted/30 hover:bg-muted/50"
                                )}
                            >
                                {/* Style Preview */}
                                <div className={cn(
                                    "w-full h-12 rounded-lg border",
                                    style.id === 'solid'
                                        ? "bg-white dark:bg-slate-800 border-gray-200 dark:border-slate-700"
                                        : "bg-white/60 dark:bg-slate-800/60 backdrop-blur-sm border-gray-200/50 dark:border-slate-700/50"
                                )} />
                                <div>
                                    <span className="text-xs font-medium">{style.name}</span>
                                    <p className="text-[10px] text-muted-foreground">{style.description}</p>
                                </div>

                                {cardStyle === style.id && (
                                    <div className="absolute top-2 right-2 w-4 h-4 rounded-full bg-primary flex items-center justify-center">
                                        <span className="text-[8px] text-primary-foreground">✓</span>
                                    </div>
                                )}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Preview */}
            <div className="p-4 rounded-xl bg-muted/30 border">
                <label className="text-sm font-medium mb-3 block">Preview</label>
                <div className="flex items-center gap-4">
                    <div
                        className={cn(
                            "w-12 h-12 rounded-xl bg-gradient-to-br shadow-lg flex items-center justify-center",
                            ACCENT_COLORS.find(c => c.id === accentColor)?.gradient
                        )}
                    >
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    </div>
                    <div
                        className={cn(
                            "flex-1 p-3 rounded-lg border",
                            cardStyle === 'solid'
                                ? "bg-white dark:bg-slate-800 border-gray-200 dark:border-slate-700"
                                : "bg-white/60 dark:bg-slate-800/60 backdrop-blur-sm border-gray-200/50 dark:border-slate-700/50"
                        )}
                    >
                        <p className="text-sm font-medium">Sample Card</p>
                        <p className="text-xs text-muted-foreground">Preview of card style</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

AppearanceTab.displayName = "AppearanceTab";
AppearanceTab.icon = Palette;
