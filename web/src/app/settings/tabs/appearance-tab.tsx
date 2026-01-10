// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { Palette } from "lucide-react";
import { cn } from "~/lib/utils";
import type { SettingsState, LoadingTheme } from "~/core/store";
import type { Tab } from "./types";

const LOADING_THEMES: { id: LoadingTheme; name: string; gradient: string; ring: string }[] = [
    { id: 'indigo', name: 'Indigo', gradient: 'from-indigo-500 to-violet-600', ring: 'ring-indigo-500' },
    { id: 'blue', name: 'Blue', gradient: 'from-blue-500 to-cyan-600', ring: 'ring-blue-500' },
    { id: 'purple', name: 'Purple', gradient: 'from-purple-500 to-pink-600', ring: 'ring-purple-500' },
    { id: 'emerald', name: 'Emerald', gradient: 'from-emerald-500 to-teal-600', ring: 'ring-emerald-500' },
    { id: 'amber', name: 'Amber', gradient: 'from-amber-500 to-orange-600', ring: 'ring-amber-500' },
    { id: 'rose', name: 'Rose', gradient: 'from-rose-500 to-pink-600', ring: 'ring-rose-500' },
];

export const AppearanceTab: Tab = ({ settings, onChange }) => {
    const currentTheme = settings.appearance?.loadingTheme || 'indigo';

    const handleThemeChange = (theme: LoadingTheme) => {
        onChange({
            appearance: {
                ...settings.appearance,
                loadingTheme: theme,
            },
        });
    };

    return (
        <div className="space-y-6">
            <div>
                <h3 className="text-lg font-semibold mb-1">Appearance</h3>
                <p className="text-sm text-muted-foreground">
                    Customize the look and feel of the application.
                </p>
            </div>

            <div className="space-y-4">
                <div>
                    <label className="text-sm font-medium">Loading Theme Color</label>
                    <p className="text-xs text-muted-foreground mb-3">
                        Select an accent color for loading indicators throughout the app.
                    </p>

                    <div className="grid grid-cols-3 gap-3">
                        {LOADING_THEMES.map((theme) => (
                            <button
                                key={theme.id}
                                onClick={() => handleThemeChange(theme.id)}
                                className={cn(
                                    "relative flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all",
                                    currentTheme === theme.id
                                        ? "border-primary bg-primary/5 shadow-md"
                                        : "border-transparent bg-muted/30 hover:bg-muted/50"
                                )}
                            >
                                {/* Color Preview */}
                                <div
                                    className={cn(
                                        "w-10 h-10 rounded-xl bg-gradient-to-br shadow-lg",
                                        theme.gradient
                                    )}
                                />
                                <span className="text-xs font-medium">{theme.name}</span>

                                {/* Selected Indicator */}
                                {currentTheme === theme.id && (
                                    <div className="absolute top-2 right-2 w-4 h-4 rounded-full bg-primary flex items-center justify-center">
                                        <span className="text-[8px] text-primary-foreground">✓</span>
                                    </div>
                                )}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Preview */}
                <div className="mt-6 p-4 rounded-xl bg-muted/30 border">
                    <label className="text-sm font-medium mb-3 block">Preview</label>
                    <div className="flex items-center gap-4">
                        <div
                            className={cn(
                                "w-12 h-12 rounded-xl bg-gradient-to-br shadow-lg flex items-center justify-center",
                                LOADING_THEMES.find(t => t.id === currentTheme)?.gradient
                            )}
                        >
                            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        </div>
                        <div>
                            <p className="text-sm font-medium">Loading indicator</p>
                            <p className="text-xs text-muted-foreground">
                                This color will be used for all loading states
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

AppearanceTab.displayName = "AppearanceTab";
AppearanceTab.icon = Palette;
