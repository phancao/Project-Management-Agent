// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import {
  Plus,
  Search,
  CheckCircle,
  XCircle,
  RefreshCw,
  Trash2,
  Edit,
  AlertCircle,
  Key,
  Star,
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
import { Switch } from "~/components/ui/switch";
import {
  listSearchProviders,
  saveSearchProvider,
  deleteSearchProvider,
  testSearchProviderConnection,
  type SearchProviderConfig,
  type SearchProviderRequest,
} from "~/core/api/search-providers";
import { cn } from "~/lib/utils";

const SEARCH_PROVIDER_TYPES = [
  { id: "tavily", name: "Tavily", description: "AI-powered search engine", requiresApiKey: true },
  { id: "brave_search", name: "Brave Search", description: "Privacy-focused search", requiresApiKey: true },
  { id: "duckduckgo", name: "DuckDuckGo", description: "Privacy-first search engine", requiresApiKey: false },
  { id: "searx", name: "Searx", description: "Self-hosted metasearch engine", requiresApiKey: false, requiresBaseUrl: true },
  { id: "wikipedia", name: "Wikipedia", description: "Wikipedia search", requiresApiKey: false },
  { id: "arxiv", name: "ArXiv", description: "Academic paper search", requiresApiKey: false },
];

export function SearchProviderManagementView() {
  const [providers, setProviders] = useState<SearchProviderConfig[]>([]);
  const [isLoadingProviders, setIsLoadingProviders] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<SearchProviderConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [providerToDelete, setProviderToDelete] = useState<SearchProviderConfig | null>(null);
  const [apiKeyError, setApiKeyError] = useState<string | null>(null);
  const [isValidating, setIsValidating] = useState(false);

  // Form state
  const [formData, setFormData] = useState<SearchProviderRequest>({
    provider_id: "",
    provider_name: "",
    api_key: "",
    base_url: "",
    is_active: true,
    is_default: false,
  });

  // Load providers on mount
  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    setIsLoadingProviders(true);
    try {
      const providerList = await listSearchProviders();
      setProviders(providerList);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load search providers");
    } finally {
      setIsLoadingProviders(false);
    }
  };

  const handleEdit = (provider: SearchProviderConfig) => {
    setEditingProvider(provider);
    const providerType = SEARCH_PROVIDER_TYPES.find((p) => p.id === provider.provider_id);
    setFormData({
      provider_id: provider.provider_id,
      provider_name: provider.provider_name,
      api_key: "", // Don't pre-fill API key for security
      base_url: provider.base_url || "",
      is_active: provider.is_active,
      is_default: provider.is_default,
    });
    setIsDialogOpen(true);
  };

  const handleDeleteClick = (provider: SearchProviderConfig) => {
    setProviderToDelete(provider);
    setDeleteConfirmOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!providerToDelete) return;

    setIsLoading(true);
    setError(null);
    try {
      await deleteSearchProvider(providerToDelete.provider_id);
      setSuccessMessage("Search provider deleted successfully");
      await loadProviders();
      setDeleteConfirmOpen(false);
      setProviderToDelete(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete search provider");
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
      is_active: true,
      is_default: false,
    });
    setError(null);
    setApiKeyError(null);
    setIsValidating(false);
  };

  const validateApiKey = async (): Promise<boolean> => {
    const selectedProviderType = SEARCH_PROVIDER_TYPES.find((p) => p.id === formData.provider_id);
    
    if (!selectedProviderType) {
      return true; // No provider selected yet
    }
    
    // Check if API key is required and provided
    if (selectedProviderType.requiresApiKey && !formData.api_key?.trim()) {
      // When editing, if no new key provided, we'll use existing one from backend
      if (!editingProvider) {
        setApiKeyError("API key is required");
        return false;
      }
      // For editing, if no new key provided, skip validation (will use existing)
      return true;
    }
    
    // Check if base URL is required for Searx
    if (selectedProviderType.requiresBaseUrl && !formData.base_url?.trim()) {
      setApiKeyError("Base URL is required for Searx");
      return false;
    }
    
    // Test connection if API key/base URL is provided
    if (
      (selectedProviderType.requiresApiKey && formData.api_key?.trim()) ||
      (selectedProviderType.requiresBaseUrl && formData.base_url?.trim()) ||
      (!selectedProviderType.requiresApiKey && !selectedProviderType.requiresBaseUrl)
    ) {
      setIsValidating(true);
      setApiKeyError(null);
      
      try {
        const request: SearchProviderRequest = {
          provider_id: formData.provider_id,
          provider_name: formData.provider_name,
          api_key: formData.api_key,
          base_url: formData.base_url,
          additional_config: formData.additional_config,
        };
        
        const result = await testSearchProviderConnection(request);
        
        if (!result.success) {
          setApiKeyError(result.message || "Connection test failed");
          return false;
        }
        
        setApiKeyError(null);
        return true;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Connection test failed";
        setApiKeyError(errorMessage);
        return false;
      } finally {
        setIsValidating(false);
      }
    }
    
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Prevent double submission
    if (isLoading || isValidating) {
      return;
    }
    
    // Validate API key first
    const isValid = await validateApiKey();
    if (!isValid) {
      return;
    }
    
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await saveSearchProvider(formData);
      setSuccessMessage(
        editingProvider ? "Search provider updated successfully" : "Search provider saved successfully"
      );
      await loadProviders();
      handleCloseDialog();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save search provider");
    } finally {
      setIsLoading(false);
    }
  };

  const configuredProviderIds = new Set(providers.map((p) => p.provider_id));
  const selectedProviderType = SEARCH_PROVIDER_TYPES.find((p) => p.id === formData.provider_id);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Search Provider Management
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Manage API keys for web search providers
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
              Loading search providers...
            </p>
          </div>
        ) : providers.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Search className="w-16 h-16 text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No Search Providers Configured
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Add a search provider to configure API keys for web search functionality
            </p>
            <Button onClick={() => setIsDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add Your First Search Provider
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {providers.map((provider) => (
              <div
                key={provider.id}
                className={cn(
                  "bg-white dark:bg-gray-800 border rounded-lg p-4",
                  provider.is_default
                    ? "border-blue-500 dark:border-blue-400"
                    : "border-gray-200 dark:border-gray-700"
                )}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <Search className="w-6 h-6 text-gray-400" />
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-gray-900 dark:text-white">
                          {provider.provider_name}
                        </h3>
                        {provider.is_default && (
                          <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                        )}
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {provider.provider_id}
                      </p>
                      {provider.base_url && (
                        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                          {provider.base_url}
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
                          <span className="font-mono">{provider.api_key || "****"}</span>
                        ) : (
                          <span className="text-gray-400 dark:text-gray-500">Not required</span>
                        )}
                      </span>
                    </div>
                    {provider.is_default && (
                      <span className="text-xs text-blue-600 dark:text-blue-400 font-medium">
                        Default Provider
                      </span>
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
              {editingProvider ? "Edit Search Provider" : "Add Search Provider"}
            </DialogTitle>
            <DialogDescription>
              {editingProvider
                ? "Update the search provider configuration. Leave API key blank to keep existing key."
                : "Configure a search provider by selecting a provider type and entering your API key if required."}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="provider_id">Provider Type</Label>
              <Select
                value={formData.provider_id}
                onValueChange={(value) => {
                  const selected = SEARCH_PROVIDER_TYPES.find((p) => p.id === value);
                  if (selected) {
                    setFormData({
                      ...formData,
                      provider_id: selected.id,
                      provider_name: selected.name,
                    });
                  }
                }}
                disabled={!!editingProvider}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a provider" />
                </SelectTrigger>
                <SelectContent>
                  {SEARCH_PROVIDER_TYPES.map((provider) => (
                    <SelectItem
                      key={provider.id}
                      value={provider.id}
                      disabled={configuredProviderIds.has(provider.id) && !editingProvider}
                    >
                      <div className="flex items-center gap-2">
                        <span>{provider.name}</span>
                        {configuredProviderIds.has(provider.id) && !editingProvider && (
                          <span className="text-xs text-gray-400">(Already configured)</span>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedProviderType && (
                <p className="text-xs text-gray-500">{selectedProviderType.description}</p>
              )}
            </div>

            {formData.provider_id && (
              <>
                {selectedProviderType?.requiresApiKey && (
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
                      onChange={(e) => {
                        setFormData({ ...formData, api_key: e.target.value });
                        setApiKeyError(null); // Clear error when user types
                      }}
                      required={!editingProvider}
                      disabled={isValidating}
                    />
                    {apiKeyError && (
                      <p className="text-sm text-red-600 dark:text-red-400 flex items-center gap-1">
                        <AlertCircle className="w-4 h-4" />
                        {apiKeyError}
                      </p>
                    )}
                    {isValidating && (
                      <p className="text-sm text-blue-600 dark:text-blue-400 flex items-center gap-1">
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Validating API key...
                      </p>
                    )}
                  </div>
                )}

                {selectedProviderType?.requiresBaseUrl && (
                  <div className="space-y-2">
                    <Label htmlFor="base_url">
                      Base URL
                      <span className="text-red-500 ml-1">*</span>
                    </Label>
                    <Input
                      id="base_url"
                      type="text"
                      placeholder="https://searx.example.com"
                      value={formData.base_url}
                      onChange={(e) => {
                        setFormData({ ...formData, base_url: e.target.value });
                        setApiKeyError(null); // Clear error when user types
                      }}
                      required
                      disabled={isValidating}
                    />
                    {apiKeyError && (
                      <p className="text-sm text-red-600 dark:text-red-400 flex items-center gap-1">
                        <AlertCircle className="w-4 h-4" />
                        {apiKeyError}
                      </p>
                    )}
                    {isValidating && (
                      <p className="text-sm text-blue-600 dark:text-blue-400 flex items-center gap-1">
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Validating connection...
                      </p>
                    )}
                  </div>
                )}

                {!selectedProviderType?.requiresBaseUrl && (
                  <div className="space-y-2">
                    <Label htmlFor="base_url">Base URL (Optional)</Label>
                    <Input
                      id="base_url"
                      type="text"
                      placeholder="Custom base URL (if needed)"
                      value={formData.base_url}
                      onChange={(e) =>
                        setFormData({ ...formData, base_url: e.target.value })
                      }
                    />
                  </div>
                )}

                <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="space-y-0.5">
                    <Label htmlFor="is_default" className="text-sm font-medium">
                      Set as Default Provider
                    </Label>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      This provider will be used by default for web searches
                    </p>
                  </div>
                  <Switch
                    id="is_default"
                    checked={formData.is_default}
                    onCheckedChange={(checked) =>
                      setFormData({ ...formData, is_default: checked })
                    }
                  />
                </div>
              </>
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={handleCloseDialog}>
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading || isValidating || !formData.provider_id}>
                {isLoading || isValidating ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    {isValidating ? "Validating..." : editingProvider ? "Updating..." : "Saving..."}
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
            <DialogTitle>Delete Search Provider</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the search provider{" "}
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

