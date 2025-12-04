// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useTranslations } from "next-intl";
import { ChevronDown, GraduationCap, FileText, Newspaper, Users, TrendingUp } from "lucide-react";
import { Detective } from "~/components/deer-flow/icons/detective";
import { cn } from "~/lib/utils";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select";
import { setEnableBackgroundInvestigation, setReportStyle, setModelProvider, useSettingsStore } from "~/core/store";
import { useConfig } from "~/core/api/hooks";
import { listAIProviders, saveAIProvider } from "~/core/api/ai-providers";
import type { ModelProvider } from "~/core/config/types";
import { useState, useEffect } from "react";

export type ReportStyle = "academic" | "popular_science" | "news" | "social_media" | "strategic_investment";

export type AgentPreset = {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  investigation: boolean;
  reportStyle: ReportStyle;
};

// Agent presets will be created with translations in the component
const getAgentPresets = (t: (key: string) => string): AgentPreset[] => [
  {
    id: "academic_researcher",
    name: t("agentSelector.academicResearcher"),
    description: t("agentSelector.academicResearcherDesc"),
    icon: GraduationCap,
    investigation: true,
    reportStyle: "academic",
  },
  {
    id: "academic_analyst",
    name: t("agentSelector.academicAnalyst"),
    description: t("agentSelector.academicAnalystDesc"),
    icon: GraduationCap,
    investigation: false,
    reportStyle: "academic",
  },
  {
    id: "news_investigator",
    name: t("agentSelector.newsInvestigator"),
    description: t("agentSelector.newsInvestigatorDesc"),
    icon: Newspaper,
    investigation: true,
    reportStyle: "news",
  },
  {
    id: "popular_science_writer",
    name: t("agentSelector.popularScienceWriter"),
    description: t("agentSelector.popularScienceWriterDesc"),
    icon: FileText,
    investigation: true,
    reportStyle: "popular_science",
  },
  {
    id: "strategic_analyst",
    name: t("agentSelector.strategicAnalyst"),
    description: t("agentSelector.strategicAnalystDesc"),
    icon: TrendingUp,
    investigation: true,
    reportStyle: "strategic_investment",
  },
  {
    id: "social_media_creator",
    name: t("agentSelector.socialMediaCreator"),
    description: t("agentSelector.socialMediaCreatorDesc"),
    icon: Users,
    investigation: true,
    reportStyle: "social_media",
  },
];

export function AgentSelector() {
  const t = useTranslations("chat.inputBox");
  const tReportStyle = useTranslations("settings.reportStyle");
  const { config } = useConfig();
  const [configuredAIProviders, setConfiguredAIProviders] = useState<string[]>([]);
  const [loadingProviders, setLoadingProviders] = useState(true);
  
  const backgroundInvestigation = useSettingsStore(
    (state) => state.general.enableBackgroundInvestigation,
  );
  const reportStyle = useSettingsStore((state) => state.general.reportStyle);
  const modelProvider = useSettingsStore((state) => state.general.modelProvider);
  const modelName = useSettingsStore((state) => state.general.modelName);

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
      try {
        const configured = await listAIProviders();
        // Get list of provider IDs that are configured and active
        // Check both has_api_key field and if api_key exists (for backward compatibility)
        const providerIds = configured
          .filter((p) => p.is_active && (p.has_api_key || (p.api_key && p.api_key.length > 0)))
          .map((p) => p.provider_id);
        setConfiguredAIProviders(providerIds);
      } catch (error) {
        // If we can't load configured providers, show all available providers as fallback
        console.warn("Failed to load configured AI providers:", error);
        setConfiguredAIProviders([]);
      } finally {
        setLoadingProviders(false);
      }
    };

    void loadConfiguredProviders();
  }, []);

  // Filter available providers to only show configured ones
  const allProviders = config.providers || [];
  const providers = configuredAIProviders.length > 0
    ? allProviders.filter((p: ModelProvider) => configuredAIProviders.includes(p.id))
    : allProviders; // Fallback to all providers if none configured or loading failed
  
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
                base_url: providerConfig.base_url,
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

  const CurrentIcon = currentPreset.icon;

  return (
    <div className="flex items-center gap-2">
      <Select value={currentPreset.id} onValueChange={handlePresetChange}>
        <SelectTrigger
          className={cn(
            "rounded-2xl w-auto min-w-[180px]",
            "!border-brand !text-brand",
          )}
        >
          <div className="flex items-center gap-2">
            <CurrentIcon className="h-4 w-4 shrink-0" />
            <span className="font-medium">{currentPreset.name}</span>
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
                      {preset.investigation && (
                        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                          <Detective className="h-3 w-3" />
                          Investigation
                        </span>
                      )}
                      <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                        <Icon className="h-3 w-3" />
                        {tReportStyle(preset.reportStyle === "popular_science" ? "popularScience" : preset.reportStyle === "social_media" ? "socialMedia" : preset.reportStyle === "strategic_investment" ? "strategicInvestment" : preset.reportStyle)}
                      </span>
                    </div>
                  </div>
                </div>
              </SelectItem>
            );
          })}
        </SelectContent>
      </Select>

      {providers.length > 0 && (
        <Select
          value={modelProvider && currentModel ? `${modelProvider}:${currentModel}` : modelProvider || ""}
          onValueChange={handleModelChange}
        >
          <SelectTrigger
            className={cn(
              "rounded-2xl w-auto min-w-[180px]",
              "!border-brand !text-brand",
            )}
          >
            <div className="flex items-center gap-2">
              <span className="text-lg shrink-0">{currentProvider?.icon || "🤖"}</span>
              <span className="font-medium text-sm">
                {currentProvider?.name || "Model"}
                {currentModel && ` - ${currentModel}`}
              </span>
            </div>
          </SelectTrigger>
          <SelectContent className="w-[280px]">
            {providers.map((provider: ModelProvider) => (
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
            ))}
          </SelectContent>
        </Select>
      )}
    </div>
  );
}

