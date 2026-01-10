// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Palette, Layers, Sun, Moon, Monitor, PaintBucket, MousePointerClick, AlertCircle } from "lucide-react";
import { useTheme } from "next-themes";
import { cn } from "~/lib/utils";
import type { SettingsState, AccentColor, CardStyle, BackgroundColor, HoverColor, ThemeAppearance } from "~/core/store";
import type { Tab } from "./types";
import { useEffect, useState } from "react";

// Brand colors with hex values
const ACCENT_COLORS: { id: AccentColor; name: string; hex: string; secondary?: string }[] = [
    { id: 'darkBlue', name: 'Dark Blue', hex: '#1E398D', secondary: '#14B795' },
    { id: 'teal', name: 'Teal', hex: '#14B795' },
    { id: 'orange', name: 'Orange', hex: '#F47920' },
    { id: 'lightBlue', name: 'Light Blue', hex: '#1C9AD6' },
    { id: 'green', name: 'Green', hex: '#8DC63F' },
    { id: 'pink', name: 'Pink', hex: '#CF2C91' },
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

const BACKGROUND_COLORS: { id: BackgroundColor; name: string; hex: string }[] = [
    { id: 'white', name: 'White', hex: '#ffffff' },
    { id: 'cream', name: 'Cream', hex: '#fdfbf7' },
    { id: 'warmGray', name: 'Warm', hex: '#f5f5f4' },
    { id: 'coolGray', name: 'Cool', hex: '#f1f5f9' },
    { id: 'slate', name: 'Slate', hex: '#e2e8f0' },
    { id: 'lavender', name: 'Lavender', hex: '#f5f3ff' },
    { id: 'mint', name: 'Mint', hex: '#f0fdf4' },
    { id: 'rose', name: 'Rose', hex: '#fff1f2' },
    { id: 'sky', name: 'Sky', hex: '#f0f9ff' },
    { id: 'sand', name: 'Sand', hex: '#faf5eb' },
];

// Dark theme background colors
const DARK_BACKGROUND_COLORS: { id: BackgroundColor; name: string; hex: string }[] = [
    { id: 'white', name: 'Pure Dark', hex: '#1a1a1a' },
    { id: 'cream', name: 'Warm Dark', hex: '#1c1917' },
    { id: 'warmGray', name: 'Neutral', hex: '#1f1f1f' },
    { id: 'coolGray', name: 'Slate', hex: '#1e293b' },
    { id: 'slate', name: 'Deep Slate', hex: '#0f172a' },
    { id: 'lavender', name: 'Purple', hex: '#1e1b2e' },
    { id: 'mint', name: 'Forest', hex: '#14231a' },
    { id: 'rose', name: 'Wine', hex: '#231419' },
    { id: 'sky', name: 'Navy', hex: '#141d26' },
    { id: 'sand', name: 'Espresso', hex: '#1f1b14' },
];

export const AppearanceTab: Tab = ({ settings, onChange }) => {
    const { theme = 'system', setTheme, resolvedTheme } = useTheme();
    const [mounted, setMounted] = useState(false);

    // Check if we're in dark mode (considering 'system' which resolves to actual theme)
    const isDarkMode = resolvedTheme === 'dark';

    // Get the appropriate appearance settings based on current theme
    const currentAppearance: ThemeAppearance = isDarkMode
        ? (settings.darkAppearance || settings.appearance)
        : (settings.lightAppearance || settings.appearance);

    const accentColor = currentAppearance?.accentColor || 'darkBlue';
    const hoverColor = currentAppearance?.hoverColor || 'teal';
    const cardStyle = currentAppearance?.cardStyle || 'solid';
    const backgroundColor = currentAppearance?.backgroundColor || 'cream';

    // Handle hydration
    useEffect(() => {
        setMounted(true);
    }, []);

    const handleAccentChange = (color: AccentColor) => {
        const updatedAppearance: ThemeAppearance = {
            ...currentAppearance,
            loadingTheme: color,
            accentColor: color,
        };

        if (isDarkMode) {
            onChange({
                darkAppearance: updatedAppearance,
                // Keep legacy appearance in sync with light theme
                appearance: settings.lightAppearance || settings.appearance,
            });
        } else {
            onChange({
                lightAppearance: updatedAppearance,
                appearance: updatedAppearance, // Keep legacy in sync
            });
        }
    };

    const handleHoverChange = (color: HoverColor) => {
        const updatedAppearance: ThemeAppearance = {
            ...currentAppearance,
            hoverColor: color,
        };

        if (isDarkMode) {
            onChange({ darkAppearance: updatedAppearance });
        } else {
            onChange({
                lightAppearance: updatedAppearance,
                appearance: updatedAppearance,
            });
        }
    };

    const handleCardStyleChange = (style: CardStyle) => {
        const updatedAppearance: ThemeAppearance = {
            ...currentAppearance,
            cardStyle: style,
        };

        if (isDarkMode) {
            onChange({ darkAppearance: updatedAppearance });
        } else {
            onChange({
                lightAppearance: updatedAppearance,
                appearance: updatedAppearance,
            });
        }
    };

    const handleThemeModeChange = (mode: string) => {
        setTheme(mode);
    };

    const handleBackgroundChange = (bg: BackgroundColor) => {
        const updatedAppearance: ThemeAppearance = {
            ...currentAppearance,
            backgroundColor: bg,
        };

        if (isDarkMode) {
            onChange({ darkAppearance: updatedAppearance });
        } else {
            onChange({
                lightAppearance: updatedAppearance,
                appearance: updatedAppearance,
            });
        }
    };

    const selectedColor = ACCENT_COLORS.find(c => c.id === accentColor);

    return (
        <div className="space-y-8">
            <div>
                <h3 className="text-lg font-semibold mb-1">Appearance</h3>
                <p className="text-sm text-muted-foreground">
                    Customize the look and feel of the application.
                </p>
                {mounted && (
                    <div className={cn(
                        "mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium",
                        isDarkMode
                            ? "bg-gray-800 text-gray-200 border border-gray-700"
                            : "bg-amber-50 text-amber-700 border border-amber-200"
                    )}>
                        {isDarkMode ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
                        Configuring {isDarkMode ? 'Dark' : 'Light'} Theme
                    </div>
                )}
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
                        Brand Accent Color
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
                                {/* Color swatch with gradient for darkBlue */}
                                <div
                                    className="w-10 h-10 rounded-xl shadow-lg"
                                    style={{
                                        background: color.secondary
                                            ? `linear-gradient(135deg, ${color.hex} 0%, ${color.secondary} 100%)`
                                            : color.hex
                                    }}
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

            {/* Hover Color */}
            <div className="space-y-4">
                <div>
                    <label className="text-sm font-medium flex items-center gap-2">
                        <MousePointerClick className="w-4 h-4" />
                        Hover Color
                    </label>
                    <p className="text-xs text-muted-foreground mb-3">
                        Color shown when hovering over buttons and interactive elements.
                    </p>

                    <div className="grid grid-cols-3 gap-3">
                        {ACCENT_COLORS.map((color) => (
                            <button
                                key={color.id}
                                onClick={() => handleHoverChange(color.id)}
                                className={cn(
                                    "relative flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all",
                                    hoverColor === color.id
                                        ? "border-primary bg-primary/5 shadow-md"
                                        : "border-transparent bg-muted/30 hover:bg-muted/50"
                                )}
                            >
                                <div
                                    className="w-10 h-10 rounded-xl shadow-lg"
                                    style={{ background: color.hex }}
                                />
                                <span className="text-xs font-medium">{color.name}</span>

                                {hoverColor === color.id && (
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

            {/* Background Color */}
            <div className="space-y-4">
                <div>
                    <label className="text-sm font-medium flex items-center gap-2">
                        <PaintBucket className="w-4 h-4" />
                        Background Color {isDarkMode ? '(Dark Mode)' : '(Light Mode)'}
                    </label>
                    <p className="text-xs text-muted-foreground mb-3">
                        {isDarkMode
                            ? 'Choose your preferred dark theme background.'
                            : 'Adjust brightness of the light theme background.'}
                    </p>

                    <div className="grid grid-cols-5 gap-2">
                        {(isDarkMode ? DARK_BACKGROUND_COLORS : BACKGROUND_COLORS).map((bg) => (
                            <button
                                key={bg.id}
                                onClick={() => handleBackgroundChange(bg.id)}
                                className={cn(
                                    "relative flex flex-col items-center gap-1.5 p-3 rounded-xl border-2 transition-all",
                                    backgroundColor === bg.id
                                        ? "border-primary bg-primary/5 shadow-md"
                                        : "border-transparent bg-muted/30 hover:bg-muted/50"
                                )}
                            >
                                <div
                                    className={cn(
                                        "w-8 h-8 rounded-lg shadow-sm border",
                                        isDarkMode ? "border-gray-600" : "border-gray-300"
                                    )}
                                    style={{ backgroundColor: bg.hex }}
                                />
                                <span className="text-[10px] font-medium">{bg.name}</span>

                                {backgroundColor === bg.id && (
                                    <div className="absolute top-1 right-1 w-3 h-3 rounded-full bg-primary flex items-center justify-center">
                                        <span className="text-[6px] text-primary-foreground">✓</span>
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
                        className="w-12 h-12 rounded-xl shadow-lg flex items-center justify-center"
                        style={{
                            background: selectedColor?.secondary
                                ? `linear-gradient(135deg, ${selectedColor.hex} 0%, ${selectedColor.secondary} 100%)`
                                : selectedColor?.hex
                        }}
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
        </div >
    );
};

AppearanceTab.displayName = "AppearanceTab";
AppearanceTab.icon = Palette;
