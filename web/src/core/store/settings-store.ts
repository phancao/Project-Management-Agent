// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { create } from "zustand";

import type { MCPServerMetadata, SimpleMCPServerMetadata } from "../mcp";

const SETTINGS_KEY = "deerflow.settings";

// Brand colors from company guidelines
export type LoadingTheme = 'darkBlue' | 'teal' | 'orange' | 'lightBlue' | 'green' | 'pink';
export type AccentColor = LoadingTheme; // Same options as loading theme
export type HoverColor = LoadingTheme; // Hover color uses same palette
export type CardStyle = 'solid' | 'glassmorphic';
export type BackgroundColor = 'white' | 'cream' | 'warmGray' | 'coolGray' | 'slate' | 'lavender' | 'mint' | 'rose' | 'sky' | 'sand';

// Theme-specific appearance settings
export type ThemeAppearance = {
  loadingTheme: LoadingTheme;
  accentColor: AccentColor;
  hoverColor: HoverColor;
  cardStyle: CardStyle;
  backgroundColor: BackgroundColor;
};

const DEFAULT_LIGHT_APPEARANCE: ThemeAppearance = {
  loadingTheme: 'darkBlue',
  accentColor: 'darkBlue',
  hoverColor: 'teal',
  cardStyle: 'solid',
  backgroundColor: 'cream',
};

const DEFAULT_DARK_APPEARANCE: ThemeAppearance = {
  loadingTheme: 'teal',
  accentColor: 'teal',
  hoverColor: 'lightBlue',
  cardStyle: 'solid',
  backgroundColor: 'white', // Not used in dark mode, but keep for consistency
};

const DEFAULT_SETTINGS: SettingsState = {
  general: {
    autoAcceptedPlan: false,
    enableClarification: false,
    maxClarificationRounds: 3,
    enableDeepThinking: false,
    enableBackgroundInvestigation: false,
    maxPlanIterations: 1,
    maxStepNum: 3,
    maxSearchResults: 3,
    reportStyle: "generic",
    modelProvider: undefined,
    modelName: undefined,
    searchProvider: undefined, // Search provider ID (e.g., "duckduckgo", "tavily")
  },
  // Legacy appearance field for backwards compatibility (will be migrated)
  appearance: DEFAULT_LIGHT_APPEARANCE,
  // New separate theme appearances
  lightAppearance: DEFAULT_LIGHT_APPEARANCE,
  darkAppearance: DEFAULT_DARK_APPEARANCE,
  mcp: {
    servers: [],
  },
};

export type SettingsState = {
  general: {
    autoAcceptedPlan: boolean;
    enableClarification: boolean;
    maxClarificationRounds: number;
    enableDeepThinking: boolean;
    enableBackgroundInvestigation: boolean;
    maxPlanIterations: number;
    maxStepNum: number;
    maxSearchResults: number;
    reportStyle: "generic" | "project_management";
    modelProvider?: string; // Provider ID (e.g., "openai", "anthropic")
    modelName?: string; // Model name (e.g., "gpt-4o", "claude-3-5-sonnet-20241022")
    searchProvider?: string; // Search provider ID (e.g., "duckduckgo", "tavily", "brave_search")
  };
  // Legacy appearance (for backwards compatibility)
  appearance: ThemeAppearance;
  // Separate theme appearances
  lightAppearance: ThemeAppearance;
  darkAppearance: ThemeAppearance;
  mcp: {
    servers: MCPServerMetadata[];
  };
};

export const useSettingsStore = create<SettingsState>(() => ({
  ...DEFAULT_SETTINGS,
}));

export const useSettings = (key: keyof SettingsState) => {
  return useSettingsStore((state) => state[key]);
};

export const changeSettings = (settings: SettingsState) => {
  useSettingsStore.setState(settings);
};

export const loadSettings = () => {
  if (typeof window === "undefined") {
    return;
  }
  const json = localStorage.getItem(SETTINGS_KEY);
  if (json) {
    const settings = JSON.parse(json);
    // Ensure general defaults
    for (const key in DEFAULT_SETTINGS.general) {
      if (!(key in settings.general)) {
        settings.general[key as keyof SettingsState["general"]] =
          DEFAULT_SETTINGS.general[key as keyof SettingsState["general"]];
      }
    }
    // Ensure appearance defaults
    if (!settings.appearance) {
      settings.appearance = DEFAULT_SETTINGS.appearance;
    } else {
      for (const key in DEFAULT_SETTINGS.appearance) {
        if (!(key in settings.appearance)) {
          settings.appearance[key as keyof ThemeAppearance] =
            DEFAULT_SETTINGS.appearance[key as keyof ThemeAppearance];
        }
      }
    }

    // Migrate to new lightAppearance/darkAppearance structure
    if (!settings.lightAppearance) {
      // Use existing appearance as light theme settings
      settings.lightAppearance = { ...settings.appearance };
    }
    if (!settings.darkAppearance) {
      // Use default dark theme settings
      settings.darkAppearance = { ...DEFAULT_DARK_APPEARANCE };
    }

    try {
      useSettingsStore.setState(settings);
    } catch (error) {
      console.error(error);
    }
  }
};

export const saveSettings = () => {
  const latestSettings = useSettingsStore.getState();
  const json = JSON.stringify(latestSettings);
  localStorage.setItem(SETTINGS_KEY, json);
};

export const getChatStreamSettings = () => {
  let mcpSettings:
    | {
      servers: Record<
        string,
        MCPServerMetadata & {
          enabled_tools: string[];
          add_to_agents: string[];
        }
      >;
    }
    | undefined = undefined;
  const { mcp, general } = useSettingsStore.getState();
  const mcpServers = mcp.servers.filter((server) => server.enabled);
  if (mcpServers.length > 0) {
    mcpSettings = {
      servers: mcpServers.reduce((acc, cur) => {
        const { transport, env, headers } = cur;
        let server: SimpleMCPServerMetadata;
        if (transport === "stdio") {
          server = {
            name: cur.name,
            transport,
            env,
            command: cur.command,
            args: cur.args,
          };
        } else {
          server = {
            name: cur.name,
            transport,
            headers,
            url: cur.url,
          };
        }
        // PM MCP server should be added to researcher, coder, and pm_agent
        const addToAgents = cur.name === "pm-server" || cur.name.includes("pm")
          ? ["pm_agent"]  // Only PM Agent should have PM tools
          : ["researcher"];

        return {
          ...acc,
          [cur.name]: {
            ...server,
            enabled_tools: cur.tools.map((tool) => tool.name),
            add_to_agents: addToAgents,
          },
        };
      }, {}),
    };
  }
  return {
    ...general,
    mcpSettings,
  };
};

export function setReportStyle(
  value: "generic" | "project_management",
) {
  useSettingsStore.setState((state) => ({
    general: {
      ...state.general,
      reportStyle: value,
    },
  }));
  saveSettings();
}

export function setEnableDeepThinking(value: boolean) {
  useSettingsStore.setState((state) => ({
    general: {
      ...state.general,
      enableDeepThinking: value,
    },
  }));
  saveSettings();
}

export function setEnableBackgroundInvestigation(value: boolean) {
  useSettingsStore.setState((state) => ({
    general: {
      ...state.general,
      enableBackgroundInvestigation: value,
    },
  }));
  saveSettings();
}

export function setModelProvider(providerId: string | undefined, modelName?: string) {
  useSettingsStore.setState((state) => ({
    general: {
      ...state.general,
      modelProvider: providerId,
      modelName: modelName,
    },
  }));
  saveSettings();
}

export function setSearchProvider(providerId: string | undefined) {
  useSettingsStore.setState((state) => ({
    general: {
      ...state.general,
      searchProvider: providerId,
    },
  }));
  saveSettings();
}

export function setEnableClarification(value: boolean) {
  useSettingsStore.setState((state) => ({
    general: {
      ...state.general,
      enableClarification: value,
    },
  }));
  saveSettings();
}
loadSettings();
