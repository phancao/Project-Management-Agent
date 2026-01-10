"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import * as React from "react";
import { useEffect } from "react";
import { useSettingsStore, type AccentColor, type BackgroundColor, type HoverColor } from "~/core/store";

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
 * Background color options for light theme
 */
const BACKGROUND_HEX: Record<BackgroundColor, { bg: string; card: string; appBg: string }> = {
  white: { bg: '#ffffff', card: '#ffffff', appBg: '#f8fafc' },
  cream: { bg: '#fdfbf7', card: '#ffffff', appBg: '#f5f2ed' },
  warmGray: { bg: '#f5f5f4', card: '#fafaf9', appBg: '#e7e5e4' },
  coolGray: { bg: '#f1f5f9', card: '#f8fafc', appBg: '#e2e8f0' },
  slate: { bg: '#e2e8f0', card: '#f1f5f9', appBg: '#cbd5e1' },
  lavender: { bg: '#f5f3ff', card: '#faf5ff', appBg: '#ede9fe' },
  mint: { bg: '#f0fdf4', card: '#f0fdf9', appBg: '#dcfce7' },
  rose: { bg: '#fff1f2', card: '#fff5f6', appBg: '#ffe4e6' },
  sky: { bg: '#f0f9ff', card: '#f0fdff', appBg: '#e0f2fe' },
  sand: { bg: '#faf5eb', card: '#fdfaf3', appBg: '#f5ebb8' },
};

/**
 * Background color options for dark theme
 */
const DARK_BACKGROUND_HEX: Record<BackgroundColor, { bg: string; card: string; appBg: string }> = {
  white: { bg: '#1a1a1a', card: '#262626', appBg: '#0f0f0f' },       // Pure dark
  cream: { bg: '#1c1917', card: '#292524', appBg: '#0c0a09' },       // Warm dark
  warmGray: { bg: '#1f1f1f', card: '#2a2a2a', appBg: '#141414' },    // Neutral dark
  coolGray: { bg: '#1e293b', card: '#334155', appBg: '#0f172a' },    // Slate dark
  slate: { bg: '#0f172a', card: '#1e293b', appBg: '#020617' },       // Deep slate
  lavender: { bg: '#1e1b2e', card: '#2a2640', appBg: '#13111c' },    // Purple dark
  mint: { bg: '#14231a', card: '#1a2f23', appBg: '#0d1711' },        // Green dark
  rose: { bg: '#231419', card: '#2f1a20', appBg: '#170d10' },        // Rose dark
  sky: { bg: '#141d26', card: '#1a2633', appBg: '#0d131a' },         // Blue dark
  sand: { bg: '#1f1b14', card: '#29241a', appBg: '#14110d' },        // Sand dark
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
 * AccentColorProvider injects dynamic CSS variables based on the selected settings.
 * Uses theme-specific settings (lightAppearance/darkAppearance) for each mode.
 */
function AccentColorProvider({ children }: { children: React.ReactNode }) {
  // Get theme-specific appearance settings
  const lightAppearance = useSettingsStore((state) => state.lightAppearance);
  const darkAppearance = useSettingsStore((state) => state.darkAppearance);
  // Legacy fallback
  const legacyAppearance = useSettingsStore((state) => state.appearance);

  useEffect(() => {
    const root = document.documentElement;

    // Determine current theme
    const isDarkMode = root.classList.contains('dark');

    // Select appropriate appearance settings based on theme
    const appearance = isDarkMode
      ? (darkAppearance || legacyAppearance)
      : (lightAppearance || legacyAppearance);

    const accentColor = appearance?.accentColor || 'darkBlue';
    const hoverColor = appearance?.hoverColor || 'teal';
    const backgroundColor = appearance?.backgroundColor || 'cream';

    const colors = ACCENT_HEX[accentColor] || ACCENT_HEX.darkBlue;
    const hoverColors = ACCENT_HEX[hoverColor] || ACCENT_HEX.teal;
    // Use appropriate background palette based on theme
    const bgColors = isDarkMode
      ? (DARK_BACKGROUND_HEX[backgroundColor] || DARK_BACKGROUND_HEX.cream)
      : (BACKGROUND_HEX[backgroundColor] || BACKGROUND_HEX.cream);

    // Set accent color CSS properties
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

    // Set hover color CSS properties
    root.style.setProperty('--hover', hoverColors.primary);
    root.style.setProperty('--hover-rgb', hexToRgb(hoverColors.primary));
    root.style.setProperty('--hover-light', hoverColors.light);

    // Set background color CSS properties (for both light and dark modes now)
    root.style.setProperty('--background', bgColors.bg);
    root.style.setProperty('--card', bgColors.card);
    root.style.setProperty('--app-background', bgColors.appBg);
    // Also set Tailwind color variable to ensure it updates
    root.style.setProperty('--color-app', bgColors.appBg);
    root.style.setProperty('--color-background', bgColors.bg);
    // Force body background update
    if (document.body) {
      document.body.style.backgroundColor = bgColors.appBg;
    }
  }, [lightAppearance, darkAppearance, legacyAppearance]);

  // Re-apply when theme class changes
  useEffect(() => {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === 'class') {
          // Trigger re-render by dispatching a custom event
          window.dispatchEvent(new CustomEvent('theme-changed'));
        }
      });
    });

    observer.observe(document.documentElement, { attributes: true });

    const handleThemeChange = () => {
      // Force re-apply CSS variables when theme changes
      const root = document.documentElement;
      const isDarkMode = root.classList.contains('dark');

      const appearance = isDarkMode
        ? (darkAppearance || legacyAppearance)
        : (lightAppearance || legacyAppearance);

      const accentColor = appearance?.accentColor || 'darkBlue';
      const hoverColor = appearance?.hoverColor || 'teal';
      const backgroundColor = appearance?.backgroundColor || 'cream';

      const colors = ACCENT_HEX[accentColor] || ACCENT_HEX.darkBlue;
      const hoverColors = ACCENT_HEX[hoverColor] || ACCENT_HEX.teal;
      // Use appropriate background palette based on theme
      const bgColors = isDarkMode
        ? (DARK_BACKGROUND_HEX[backgroundColor] || DARK_BACKGROUND_HEX.cream)
        : (BACKGROUND_HEX[backgroundColor] || BACKGROUND_HEX.cream);

      root.style.setProperty('--accent-primary', colors.primary);
      root.style.setProperty('--accent-gradient', colors.gradient);
      root.style.setProperty('--accent-light', colors.light);
      root.style.setProperty('--accent-primary-rgb', hexToRgb(colors.primary));
      root.style.setProperty('--brand', colors.primary);
      root.style.setProperty('--primary', colors.primary);
      root.style.setProperty('--ring', colors.primary);
      root.style.setProperty('--sidebar-primary', colors.primary);
      root.style.setProperty('--sidebar-ring', colors.primary);
      root.style.setProperty('--hover', hoverColors.primary);
      root.style.setProperty('--hover-rgb', hexToRgb(hoverColors.primary));
      root.style.setProperty('--hover-light', hoverColors.light);

      // Set background color CSS properties (for both modes)
      root.style.setProperty('--background', bgColors.bg);
      root.style.setProperty('--card', bgColors.card);
      root.style.setProperty('--app-background', bgColors.appBg);
      root.style.setProperty('--color-app', bgColors.appBg);
      root.style.setProperty('--color-background', bgColors.bg);
      // Force body background update
      if (document.body) {
        document.body.style.backgroundColor = bgColors.appBg;
      }
    };

    window.addEventListener('theme-changed', handleThemeChange);

    return () => {
      observer.disconnect();
      window.removeEventListener('theme-changed', handleThemeChange);
    };
  }, [lightAppearance, darkAppearance, legacyAppearance]);

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
