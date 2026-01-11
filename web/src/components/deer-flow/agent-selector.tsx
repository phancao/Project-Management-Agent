// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useTranslations } from "next-intl";
import { ChevronDown, Globe, Briefcase } from "lucide-react";
import { cn } from "~/lib/utils";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select";
import { setEnableBackgroundInvestigation, setReportStyle, setModelProvider, setSearchProvider, useSettingsStore } from "~/core/store";
import { useConfig } from "~/core/api/hooks";
import { listAIProviders, saveAIProvider } from "~/core/api/ai-providers";
import { listSearchProviders, type SearchProviderConfig } from "~/core/api/search-providers";
import type { ModelProvider } from "~/core/config/types";
import { useState, useEffect } from "react";
import { Search } from "lucide-react";

export type ReportStyle = "generic" | "project_management";

export type AgentPreset = {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  investigation: boolean;
  reportStyle: ReportStyle;
};

// Simplified agent modes: Generic (web research) and Project Management
const getAgentPresets = (t: (key: string) => string): AgentPreset[] => [
  {
    id: "generic",
    name: "Generic",
    description: "Web research and general queries",
    icon: Globe,
    investigation: true,
    reportStyle: "generic",
  },
  {
    id: "project_management",
    name: "Project Management",
    description: "PM tasks, analytics, and data queries",
    icon: Briefcase,
    investigation: false,
    reportStyle: "project_management",
  },
];

export function AgentSelector() {
  const t = useTranslations("chat.inputBox");
  const tReportStyle = useTranslations("settings.reportStyle");
  const { config, loading: configLoading } = useConfig();
  const [configuredAIProviders, setConfiguredAIProviders] = useState<string[]>([]);
  const [loadingProviders, setLoadingProviders] = useState(true);
  const [searchProviders, setSearchProviders] = useState<SearchProviderConfig[]>([]);
  const [loadingSearchProviders, setLoadingSearchProviders] = useState(true);

  const backgroundInvestigation = useSettingsStore(
    (state) => state.general.enableBackgroundInvestigation,
  );
  const reportStyle = useSettingsStore((state) => state.general.reportStyle);
  const modelProvider = useSettingsStore((state) => state.general.modelProvider);
  const modelName = useSettingsStore((state) => state.general.modelName);
  const searchProvider = useSettingsStore((state) => state.general.searchProvider);

  // Get presets with translations
  const AGENT_PRESETS = getAgentPresets(t);

  // Find current preset based on settings
  const currentPreset = AGENT_PRESETS.find(
    (preset) =>
      preset.investigation === backgroundInvestigation &&
      preset.reportStyle === reportStyle,
  ) || AGENT_PRESETS[0]!; // Default to first preset

  const handlePresetChange = (presetId: string) => {
    const preset = AGENT_PRESETS.find((p) => p.id === presetId);
    if (preset) {
      setEnableBackgroundInvestigation(preset.investigation);
      setReportStyle(preset.reportStyle);
    }
  };

  // Load configured AI providers from database
  useEffect(() => {
    const loadConfiguredProviders = async () => {
      // Add timeout to prevent blocking
      const timeoutId = setTimeout(() => {
        console.warn("Loading AI providers timed out, using fallback");
        setLoadingProviders(false);
      }, 5000); // 5 second timeout for loading state

      try {
        const configured = await listAIProviders();
        clearTimeout(timeoutId);
        // Get list of provider IDs that are configured and active
        // Check both has_api_key field and if api_key exists (for backward compatibility)
        const providerIds = configured
          .filter((p) => p.is_active && (p.has_api_key || (p.api_key && p.api_key.length > 0)))
          .map((p) => p.provider_id);
        setConfiguredAIProviders(providerIds);
      } catch (error) {
        clearTimeout(timeoutId);
        // If we can't load configured providers, show all available providers as fallback
        console.warn("Failed to load configured AI providers:", error);
        setConfiguredAIProviders([]);
      } finally {
        setLoadingProviders(false);
      }
    };

    void loadConfiguredProviders();
  }, []);

  // Load search providers from database
  useEffect(() => {
    const loadSearchProviders = async () => {
      try {
        const providers = await listSearchProviders();
        setSearchProviders(providers);
        // Set default to DuckDuckGo if no provider is selected and DuckDuckGo is available
        if (!searchProvider) {
          const duckduckgo = providers.find((p) => p.provider_id === "duckduckgo");
          if (duckduckgo || providers.length === 0) {
            // DuckDuckGo is always available as default (free, no API key needed)
            setSearchProvider("duckduckgo");
          } else if (providers.length > 0) {
            // Use first available provider
            setSearchProvider(providers[0]!.provider_id);
          }
        }
      } catch (error) {
        console.warn("Failed to load search providers:", error);
        // Set DuckDuckGo as default even if loading fails
        // DuckDuckGo doesn't need to be in the database - it's always available
        if (!searchProvider) {
          setSearchProvider("duckduckgo");
        }
        // Don't set providers to empty array - keep it empty so we show DuckDuckGo as default
        setSearchProviders([]);
      } finally {
        setLoadingSearchProviders(false);
      }
    };

    void loadSearchProviders();
  }, [searchProvider]);

  // Filter available providers to only show configured ones
  const allProviders = config.providers || [];
  // Show providers based on configuration status
  // If we're still loading config or providers, show all providers
  // If loading is done and we have configured providers, show only configured ones
  // If loading is done and no providers are configured, show all providers as fallback
  const providers = !configLoading && !loadingProviders && configuredAIProviders.length > 0
    ? allProviders.filter((p: ModelProvider) => configuredAIProviders.includes(p.id))
    : allProviders; // Show all providers while loading or if none configured

  const currentProvider = providers.find((p: ModelProvider) => p.id === modelProvider);
  const currentModel = currentProvider?.models.find((m) => m === modelName) || currentProvider?.models[0];

  const handleModelChange = async (value: string) => {
    // Format: "providerId:modelName" or just "providerId"
    const [providerId, selectedModel] = value.includes(":") ? value.split(":") : [value, undefined];

    // Update local state immediately
    setModelProvider(providerId, selectedModel);

    // Also update the default model in the database for this provider
    if (providerId && selectedModel) {
      try {
        // Get the current provider configuration
        const providers = await listAIProviders();
        const existingProvider = providers.find((p) => p.provider_id === providerId);

        if (existingProvider) {
          // Update the provider's default model in the database
          await saveAIProvider({
            provider_id: providerId,
            provider_name: existingProvider.provider_name,
            model_name: selectedModel,
            base_url: existingProvider.base_url || undefined,
            is_active: existingProvider.is_active,
            // Don't send api_key - it will be preserved on the backend
          });
        } else {
          // Provider not configured yet, try to get info from config
          const providerConfig = allProviders.find((p: ModelProvider) => p.id === providerId);
          if (providerConfig) {
            // Create new provider entry with just the model name
            // Note: This will fail without API key, but that's okay - user can add it later
            try {
              await saveAIProvider({
                provider_id: providerId,
                provider_name: providerConfig.name,
                model_name: selectedModel,
                // base_url is optional and can be set separately if needed
                is_active: true,
              });
            } catch (error) {
              // If it fails (e.g., no API key), that's okay - model selection still works for this session
              console.warn("Could not save model to database (provider may not be configured yet):", error);
            }
          }
        }
      } catch (error) {
        // If database update fails, log but don't block the UI update
        console.warn("Failed to update default model in database:", error);
      }
    }
  };

  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const CurrentIcon = currentPreset.icon;

  return (
    <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
      <Select value={currentPreset.id} onValueChange={handlePresetChange}>
        <SelectTrigger
          className={cn(
            "rounded-2xl w-auto h-8 text-xs shrink-0 px-3",
            "bg-brand border-brand text-white shadow-lg shadow-brand/40 hover:bg-brand/90 hover:shadow-xl hover:shadow-brand/50",
          )}
        >
          <div className="flex items-center gap-1.5">
            <CurrentIcon className="h-3.5 w-3.5 shrink-0" />
            <span className="font-normal text-[10px] sm:text-xs truncate">
              {isMobile ? currentPreset.name.split(' ')[0] : currentPreset.name}
            </span>
          </div>
        </SelectTrigger>
        <SelectContent className="w-[280px]">
          {AGENT_PRESETS.map((preset) => {
            const Icon = preset.icon;

            return (
              <SelectItem
                key={preset.id}
                value={preset.id}
                className="cursor-pointer"
              >
                <div className="flex items-start gap-3 w-full">
                  <Icon className="mt-0.5 h-5 w-5 shrink-0" />
                  <div className="flex-1 space-y-0.5 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{preset.name}</span>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">
                      {preset.description}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                        <Icon className="h-3 w-3" />
                        {preset.reportStyle === "generic" ? "Generic" : "Project Management"}
                      </span>
                    </div>
                  </div>
                </div>
              </SelectItem>
            );
          })}
        </SelectContent>
      </Select>

      {/* Always show AI provider selector - it will show providers from config even if database call fails */}
      <Select
        value={modelProvider && currentModel ? `${modelProvider}:${currentModel}` : modelProvider || ""}
        onValueChange={handleModelChange}
        disabled={configLoading || (loadingProviders && allProviders.length === 0)}
      >
        <SelectTrigger
          className={cn(
            "rounded-2xl w-auto h-8 text-xs shrink-0 px-3",
            "bg-brand border-brand text-white shadow-lg shadow-brand/40 hover:bg-brand/90 hover:shadow-xl hover:shadow-brand/50",
          )}
        >
          <div className="flex items-center gap-1.5">
            <span className="text-sm shrink-0">{currentProvider?.icon || "🤖"}</span>
            <span className="font-normal text-[10px] sm:text-xs truncate">
              {currentProvider?.name || "Model"}
              {!isMobile && currentModel && ` - ${currentModel}`}
            </span>
          </div>
        </SelectTrigger>
        <SelectContent className="w-[280px]">
          {providers.length > 0 ? (
            providers.map((provider: ModelProvider) => (
              <div key={provider.id}>
                <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                  {provider.icon} {provider.name}
                </div>
                {provider.models.map((model) => {
                  const value = `${provider.id}:${model}`;

                  return (
                    <SelectItem
                      key={value}
                      value={value}
                      className="cursor-pointer pl-6"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-sm">{model}</span>
                      </div>
                    </SelectItem>
                  );
                })}
              </div>
            ))
          ) : (
            <div className="px-2 py-4 text-center text-sm text-muted-foreground">
              {configLoading || loadingProviders
                ? "Loading providers..."
                : "No providers available. Please configure providers in Settings."}
            </div>
          )}
        </SelectContent>
      </Select>

      {/* Search Provider Selector */}
      <Select
        value={searchProvider || "duckduckgo"}
        onValueChange={(value) => setSearchProvider(value)}
      >
        <SelectTrigger
          className={cn(
            "rounded-2xl w-auto h-8 text-xs shrink-0 px-3",
            "bg-brand border-brand text-white shadow-lg shadow-brand/40 hover:bg-brand/90 hover:shadow-xl hover:shadow-brand/50",
          )}
        >
          <div className="flex items-center gap-1.5">
            <Search className="h-3.5 w-3.5 shrink-0" />
            <span className="font-normal text-[10px] sm:text-xs truncate">
              {searchProviders.find((p) => p.provider_id === searchProvider)?.provider_name ||
                (searchProvider === "duckduckgo" ? "DuckDuckGo" : "Search")}
            </span>
          </div>
        </SelectTrigger>
        <SelectContent className="w-[240px]">
          {/* Always show DuckDuckGo as default free option */}
          <SelectItem value="duckduckgo" className="cursor-pointer">
            <div className="flex items-center gap-2">
              <span className="text-sm">🦆 DuckDuckGo</span>
              <span className="text-xs text-muted-foreground">(Free)</span>
            </div>
          </SelectItem>
          {/* Show configured providers */}
          {searchProviders
            .filter((p) => p.provider_id !== "duckduckgo" && p.is_active)
            .map((provider) => (
              <SelectItem
                key={provider.id}
                value={provider.provider_id}
                className="cursor-pointer"
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm">{provider.provider_name}</span>
                  {provider.is_default && (
                    <span className="text-xs text-muted-foreground">(Default)</span>
                  )}
                </div>
              </SelectItem>
            ))}
        </SelectContent>
      </Select>
    </div>
  );
}

