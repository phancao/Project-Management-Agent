"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import * as React from "react";
import { useEffect } from "react";
import { useSettingsStore, type AccentColor } from "~/core/store";

/**
 * Brand color hex values for CSS injection
 */
const ACCENT_HEX: Record<AccentColor, { primary: string; gradient: string; light: string }> = {
  darkBlue: { primary: '#1E398D', gradient: '#14B795', light: '#5a7fd9' },
  teal: { primary: '#14B795', gradient: '#0f9678', light: '#4fd9bc' },
  orange: { primary: '#F47920', gradient: '#e06512', light: '#f9a05c' },
  lightBlue: { primary: '#1C9AD6', gradient: '#1483b8', light: '#5cb8e6' },
  green: { primary: '#8DC63F', gradient: '#7ab335', light: '#a8d46a' },
  pink: { primary: '#CF2C91', gradient: '#b5257f', light: '#e066b5' },
};

/**
 * Convert hex color to RGB string for use in rgba()
 */
function hexToRgb(hex: string): string {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result || !result[1] || !result[2] || !result[3]) return '30, 57, 141'; // fallback to dark blue
  return `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`;
}

/**
 * AccentColorProvider injects dynamic CSS variables based on the selected accent color.
 * This allows the entire UI to update when the user changes the accent in Settings.
 */
function AccentColorProvider({ children }: { children: React.ReactNode }) {
  const accentColor = useSettingsStore((state) => state.appearance?.accentColor || 'darkBlue');

  useEffect(() => {
    const colors = ACCENT_HEX[accentColor] || ACCENT_HEX.darkBlue;
    const root = document.documentElement;

    // Set CSS custom properties for dynamic theming
    root.style.setProperty('--accent-primary', colors.primary);
    root.style.setProperty('--accent-gradient', colors.gradient);
    root.style.setProperty('--accent-light', colors.light);
    root.style.setProperty('--accent-primary-rgb', hexToRgb(colors.primary));

    // Update brand/primary colors to match accent
    root.style.setProperty('--brand', colors.primary);
    root.style.setProperty('--primary', colors.primary);
    root.style.setProperty('--ring', colors.primary);
    root.style.setProperty('--sidebar-primary', colors.primary);
    root.style.setProperty('--sidebar-ring', colors.primary);
  }, [accentColor]);

  return <>{children}</>;
}

/**
 * ThemeProvider combines next-themes with dynamic accent color injection
 */
export function ThemeProvider({
  children,
  ...props
}: React.ComponentProps<typeof NextThemesProvider>) {
  return (
    <NextThemesProvider {...props}>
      <AccentColorProvider>{children}</AccentColorProvider>
    </NextThemesProvider>
  );
}
