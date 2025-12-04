// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import {
  Plus,
  Brain,
  CheckCircle,
  XCircle,
  RefreshCw,
  Trash2,
  Edit,
  AlertCircle,
  Key,
  Eye,
  EyeOff,
} from "lucide-react";
import { useState, useEffect } from "react";

import { Button } from "~/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "~/components/ui/dialog";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select";
import {
  listAIProviders,
  saveAIProvider,
  deleteAIProvider,
  type AIProviderAPIKey,
  type AIProviderAPIKeyRequest,
} from "~/core/api/ai-providers";
import { useConfig } from "~/core/api/hooks";
import { cn } from "~/lib/utils";

export function AIProviderManagementView() {
  const { config } = useConfig();
  const [providers, setProviders] = useState<AIProviderAPIKey[]>([]);
  const [isLoadingProviders, setIsLoadingProviders] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<AIProviderAPIKey | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [providerToDelete, setProviderToDelete] = useState<AIProviderAPIKey | null>(null);
  const [showApiKey, setShowApiKey] = useState<Record<string, boolean>>({});

  // Form state
  const [formData, setFormData] = useState<AIProviderAPIKeyRequest>({
    provider_id: "",
    provider_name: "",
    api_key: "",
    base_url: "",
    model_name: "",
    is_active: true,
  });

  // Load providers on mount
  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    setIsLoadingProviders(true);
    try {
      const providerList = await listAIProviders();
      setProviders(providerList);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load AI providers");
    } finally {
      setIsLoadingProviders(false);
    }
  };

  const handleEdit = (provider: AIProviderAPIKey) => {
    setEditingProvider(provider);
    setFormData({
      provider_id: provider.provider_id,
      provider_name: provider.provider_name,
      api_key: "", // Don't pre-fill API key for security
      base_url: provider.base_url || "",
      model_name: provider.model_name || "",
      is_active: provider.is_active,
    });
    setIsDialogOpen(true);
  };

  const handleDeleteClick = (provider: AIProviderAPIKey) => {
    setProviderToDelete(provider);
    setDeleteConfirmOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!providerToDelete) return;

    setIsLoading(true);
    setError(null);
    try {
      await deleteAIProvider(providerToDelete.provider_id);
      setSuccessMessage("AI provider deleted successfully");
      await loadProviders();
      setDeleteConfirmOpen(false);
      setProviderToDelete(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete AI provider");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
    setEditingProvider(null);
    setFormData({
      provider_id: "",
      provider_name: "",
      api_key: "",
      base_url: "",
      model_name: "",
      is_active: true,
    });
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await saveAIProvider(formData);
      setSuccessMessage(
        editingProvider ? "AI provider updated successfully" : "AI provider saved successfully"
      );
      await loadProviders();
      handleCloseDialog();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save AI provider");
    } finally {
      setIsLoading(false);
    }
  };

  const availableProviders = config.providers || [];
  const configuredProviderIds = new Set(providers.map((p) => p.provider_id));

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            AI Provider Management
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Manage API keys for AI/LLM providers
          </p>
        </div>
        <Button onClick={() => setIsDialogOpen(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Add Provider
        </Button>
      </div>

      {/* Messages */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
          <span className="text-sm text-red-800 dark:text-red-200">{error}</span>
        </div>
      )}

      {successMessage && (
        <div className="mx-4 mt-4 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
          <span className="text-sm text-green-800 dark:text-green-200">
            {successMessage}
          </span>
        </div>
      )}

      {/* Provider List */}
      <div className="flex-1 overflow-auto p-4">
        {isLoadingProviders ? (
          <div className="flex flex-col items-center justify-center h-full">
            <RefreshCw className="w-8 h-8 text-gray-400 mb-4 animate-spin" />
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Loading AI providers...
            </p>
          </div>
        ) : providers.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Brain className="w-16 h-16 text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No AI Providers Configured
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Add an AI provider to configure API keys for different LLM services
            </p>
            <Button onClick={() => setIsDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add Your First AI Provider
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {providers.map((provider) => (
              <div
                key={provider.id}
                className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">
                      {availableProviders.find((p) => p.id === provider.provider_id)?.icon || "🤖"}
                    </span>
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-white">
                        {provider.provider_name}
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {provider.provider_id}
                      </p>
                      {provider.base_url && (
                        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                          {provider.base_url}
                        </p>
                      )}
                      {provider.model_name && (
                        <p className="text-xs text-gray-400 dark:text-gray-500">
                          Default model: {provider.model_name}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEdit(provider)}
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteClick(provider)}
                      disabled={isLoading}
                    >
                      <Trash2 className="w-4 h-4 text-red-600" />
                    </Button>
                  </div>
                </div>

                {/* API Key Status */}
                <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Key className="w-4 h-4 text-gray-400" />
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        API Key:{" "}
                        {provider.has_api_key ? (
                          <span className="font-mono">
                            {showApiKey[provider.id] ? provider.api_key : provider.api_key || "****"}
                          </span>
                        ) : (
                          <span className="text-red-600 dark:text-red-400">Not set</span>
                        )}
                      </span>
                    </div>
                    {provider.has_api_key && provider.api_key && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          setShowApiKey({
                            ...showApiKey,
                            [provider.id]: !showApiKey[provider.id],
                          })
                        }
                      >
                        {showApiKey[provider.id] ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add/Edit Provider Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={handleCloseDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingProvider ? "Edit AI Provider" : "Add AI Provider"}
            </DialogTitle>
            <DialogDescription>
              {editingProvider
                ? "Update the AI provider configuration. Leave API key blank to keep existing key."
                : "Configure an AI provider by selecting a provider and entering your API key."}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="provider_id">Provider</Label>
              <Select
                value={formData.provider_id}
                onValueChange={(value) => {
                  const selected = availableProviders.find((p) => p.id === value);
                  if (selected) {
                    setFormData({
                      ...formData,
                      provider_id: selected.id,
                      provider_name: selected.name,
                      // base_url is optional and can be set separately
                    });
                  }
                }}
                disabled={!!editingProvider}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a provider" />
                </SelectTrigger>
                <SelectContent>
                  {availableProviders.map((provider) => (
                    <SelectItem
                      key={provider.id}
                      value={provider.id}
                      disabled={configuredProviderIds.has(provider.id) && !editingProvider}
                    >
                      <div className="flex items-center gap-2">
                        <span>{provider.icon}</span>
                        <span>{provider.name}</span>
                        {configuredProviderIds.has(provider.id) && !editingProvider && (
                          <span className="text-xs text-gray-400">(Already configured)</span>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {formData.provider_id && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="api_key">
                    API Key
                    {editingProvider && (
                      <span className="text-xs text-gray-500 ml-2">
                        (leave blank to keep existing)
                      </span>
                    )}
                    {!editingProvider && <span className="text-red-500 ml-1">*</span>}
                  </Label>
                  <Input
                    id="api_key"
                    type="password"
                    placeholder={
                      editingProvider
                        ? "Enter new API key or leave blank"
                        : "Enter your API key"
                    }
                    value={formData.api_key}
                    onChange={(e) =>
                      setFormData({ ...formData, api_key: e.target.value })
                    }
                    required={!editingProvider}
                  />
                  <p className="text-xs text-gray-500">
                    {availableProviders.find((p) => p.id === formData.provider_id)?.description}
                  </p>
                </div>

                {/* Base URL is always available as an optional field */}
                <div className="space-y-2">
                  <Label htmlFor="base_url">Base URL (Optional)</Label>
                  <Input
                    id="base_url"
                    type="text"
                    placeholder="Custom base URL (e.g., https://api.openai.com/v1)"
                    value={formData.base_url}
                    onChange={(e) =>
                      setFormData({ ...formData, base_url: e.target.value })
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="model_name">Default Model (Optional)</Label>
                  <Select
                    value={formData.model_name || ""}
                    onValueChange={(value) =>
                      setFormData({ ...formData, model_name: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select a default model" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableProviders
                        .find((p) => p.id === formData.provider_id)
                        ?.models.map((model) => (
                          <SelectItem key={model} value={model}>
                            {model}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                </div>
              </>
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={handleCloseDialog}>
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading || !formData.provider_id}>
                {isLoading ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    {editingProvider ? "Updating..." : "Saving..."}
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4 mr-2" />
                    {editingProvider ? "Update" : "Save"}
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete AI Provider</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the AI provider{" "}
              <strong>{providerToDelete?.provider_name}</strong>? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setDeleteConfirmOpen(false);
                setProviderToDelete(null);
              }}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                "Delete"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

