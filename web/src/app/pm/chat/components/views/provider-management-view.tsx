// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import {
  Plus,
  Server,
  CheckCircle,
  XCircle,
  RefreshCw,
  ExternalLink,
  Trash2,
  Edit,
  AlertCircle,
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
  importProjectsFromProvider,
  listProviders,
  getProviderProjects,
  updateProvider,
  // getProviderTypes, // Not used - endpoint doesn't exist yet
  type ProviderConfig,
  type ProjectImportRequest,
  type ProjectInfo,
} from "~/core/api/pm/providers";
import { cn } from "~/lib/utils";

export function ProviderManagementView() {
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [isLoadingProviders, setIsLoadingProviders] = useState(true);
  const [providerTypes, setProviderTypes] = useState<
    Array<{ type: string; display_name: string }>
  >([
    { type: "openproject", display_name: "OpenProject" },
    { type: "jira", display_name: "JIRA" },
    { type: "clickup", display_name: "ClickUp" },
  ]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ProviderConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState<ProjectImportRequest>({
    provider_type: "openproject",
    base_url: "",
    api_key: "",
    api_token: "",
    username: "",
  });

  const [projects, setProjects] = useState<
    Record<string, { projects: ProjectInfo[]; loading: boolean; error?: string }>
  >({});

  // Load providers on mount
  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    setIsLoadingProviders(true);
    try {
      const providerList = await listProviders();
      setProviders(providerList);
      
      // Load projects for each provider
      for (const provider of providerList) {
        await loadProjectsForProvider(provider);
      }
    } catch (err) {
      console.error("Failed to load providers:", err);
      setError(err instanceof Error ? err.message : "Failed to load providers");
    } finally {
      setIsLoadingProviders(false);
    }
  };

  const loadProjectsForProvider = async (provider: ProviderConfig) => {
    if (!provider.id) {
      console.error("Provider ID is required to load projects");
      return;
    }
    
    const providerKey = provider.id;
    
    // Skip if already loading or loaded
    if (projects[providerKey]?.loading) {
      return;
    }
    
    setProjects((prev) => ({
      ...prev,
      [providerKey]: { projects: [], loading: true },
    }));

    try {
      // Use the new endpoint that uses stored credentials
      const response = await getProviderProjects(provider.id);
      setProjects((prev) => ({
        ...prev,
        [providerKey]: {
          projects: response.projects,
          loading: false,
          error: undefined,
        },
      }));
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load projects";
      console.error(`Failed to load projects for provider ${providerKey}:`, err);
      setProjects((prev) => ({
        ...prev,
        [providerKey]: { 
          projects: [], 
          loading: false,
          error: errorMessage,
        },
      }));
    }
  };

  const handleEdit = (provider: ProviderConfig) => {
    setEditingProvider(provider);
    setFormData({
      provider_type: provider.provider_type,
      base_url: provider.base_url,
      api_key: "", // Don't pre-fill for security
      api_token: "", // Don't pre-fill for security
      username: provider.username || "",
      organization_id: provider.organization_id,
      workspace_id: provider.workspace_id,
    });
    setIsDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
    setEditingProvider(null);
    setFormData({
      provider_type: "openproject",
      base_url: "",
      api_key: "",
      api_token: "",
      username: "",
    });
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      // Prepare request based on provider type
      const request: ProjectImportRequest = {
        provider_type: formData.provider_type,
        base_url: formData.base_url.trim(),
        import_options: {
          skip_existing: true,
          auto_sync: false,
        },
      };

      // Add provider-specific fields
      if (formData.provider_type === "openproject" || formData.provider_type === "clickup") {
        request.api_key = formData.api_key;
      } else if (formData.provider_type === "jira") {
        request.api_token = formData.api_token;
      }

      // For JIRA, username should be the email address
      if (formData.username) {
        request.username = formData.username;
      }

      if (formData.organization_id) {
        request.organization_id = formData.organization_id;
      }

      if (formData.workspace_id) {
        request.workspace_id = formData.workspace_id;
      }

      if (editingProvider?.id) {
        // Update existing provider
        await updateProvider(editingProvider.id, request);
        setSuccessMessage("Provider updated successfully!");
        await loadProviders();
        handleCloseDialog();
      } else {
        // Create new provider
        const response = await importProjectsFromProvider(request);

        if (response.success) {
          setSuccessMessage(
            `Provider configured successfully! Found ${response.total_projects} projects.`,
          );
          setProjects((prev) => ({
            ...prev,
            [response.provider_config_id || ""]: {
              projects: response.projects,
              loading: false,
            },
          }));
          // Reload providers list to include the new one
          await loadProviders();
          handleCloseDialog();
        } else {
          setError(
            response.errors?.[0]?.error ||
              response.message ||
              "Failed to configure provider",
          );
        }
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to configure provider",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const loadProjects = async (providerId: string, config: ProviderConfig) => {
    await loadProjectsForProvider(config);
  };

  const getProviderIcon = (type: string) => {
    switch (type) {
      case "openproject":
        return "🔧";
      case "jira":
        return "🎯";
      case "clickup":
        return "📋";
      default:
        return "📦";
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Provider Management
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Connect to external project management systems
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
          <span className="text-sm text-red-800 dark:text-red-200">
            {error}
          </span>
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
              Loading providers...
            </p>
          </div>
        ) : providers.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Server className="w-16 h-16 text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No Providers Configured
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Add a provider to connect to external project management systems
            </p>
            <Button onClick={() => setIsDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add Your First Provider
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {providers.map((provider) => {
              const providerKey =
                provider.id || `${provider.provider_type}-${provider.base_url}`;
              const providerProjects = projects[providerKey];

              return (
                <div
                  key={providerKey}
                  className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">
                        {getProviderIcon(provider.provider_type)}
                      </span>
                      <div>
                        <h3 className="font-semibold text-gray-900 dark:text-white">
                          {provider.provider_type.toUpperCase()}
                        </h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          {provider.base_url}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => loadProjects(providerKey, provider)}
                      >
                        <RefreshCw className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEdit(provider)}
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="sm">
                        <Trash2 className="w-4 h-4 text-red-600" />
                      </Button>
                    </div>
                  </div>

                  {/* Projects List */}
                  {providerProjects && (
                    <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                      {providerProjects.loading ? (
                        <div className="flex items-center justify-center py-4">
                          <RefreshCw className="w-4 h-4 animate-spin text-gray-400" />
                        </div>
                      ) : providerProjects?.error ? (
                        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2">
                          <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
                          <div className="flex-1">
                            <p className="text-sm font-medium text-red-800 dark:text-red-200">
                              Failed to load projects
                            </p>
                            <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                              {providerProjects?.error || "Unknown error"}
                            </p>
                          </div>
                        </div>
                      ) : (providerProjects?.projects?.length || 0) > 0 ? (
                        <div className="space-y-2">
                          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            Projects (
                            {providerProjects?.projects?.length || 0}):
                          </p>
                          <div className="space-y-1">
                            {providerProjects?.projects?.map((project) => (
                              <div
                                key={project.id}
                                className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-900 rounded"
                              >
                                <div className="flex-1">
                                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                                    {project.name}
                                  </p>
                                  {project.description && (
                                    <p className="text-xs text-gray-500 dark:text-gray-400">
                                      {project.description}
                                    </p>
                                  )}
                                </div>
                                <ExternalLink className="w-4 h-4 text-gray-400" />
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          No projects found
                        </p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Add/Edit Provider Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={handleCloseDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingProvider ? "Edit Provider" : "Add Provider"}
            </DialogTitle>
            <DialogDescription>
              {editingProvider
                ? "Update the provider configuration. Leave API key/token blank to keep existing credentials."
                : "Connect to an external project management system. Projects will be loaded dynamically and not saved to our database."}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="provider_type">Provider Type</Label>
              <Select
                value={formData.provider_type}
                onValueChange={(value) =>
                  setFormData({ ...formData, provider_type: value as any })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {providerTypes.map((type) => (
                    <SelectItem key={type.type} value={type.type}>
                      {type.display_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="base_url">Base URL / IP Address</Label>
              <Input
                id="base_url"
                type="text"
                placeholder="http://localhost:8080 or https://your-domain.atlassian.net"
                value={formData.base_url}
                onChange={(e) =>
                  setFormData({ ...formData, base_url: e.target.value })
                }
                required
              />
            </div>

                                  {(formData.provider_type === "openproject" ||
                        formData.provider_type === "clickup") && (
                        <div className="space-y-2">
                          <Label htmlFor="api_key">
                            API Key
                            {editingProvider && (
                              <span className="text-xs text-gray-500 ml-2">
                                (leave blank to keep existing)
                              </span>
                            )}
                          </Label>
                          <Input
                            id="api_key"
                            type="password"
                            placeholder={
                              editingProvider
                                ? "Enter new API key or leave blank"
                                : "Enter API key"
                            }
                            value={formData.api_key}
                            onChange={(e) =>
                              setFormData({ ...formData, api_key: e.target.value })
                            }
                            required={!editingProvider}
                          />
                        </div>
                      )}

            {formData.provider_type === "jira" && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="username">
                    Username
                    <span className="text-muted-foreground ml-1">
                      (use your email address for JIRA Cloud)
                    </span>
                  </Label>
                  <Input
                    id="username"
                    type="email"
                    placeholder="your-email@example.com"
                    value={formData.username}
                    onChange={(e) =>
                      setFormData({ ...formData, username: e.target.value })
                    }
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="api_token">
                    API Token
                    {editingProvider && (
                      <span className="text-xs text-gray-500 ml-2">
                        (leave blank to keep existing)
                      </span>
                    )}
                  </Label>
                  <Input
                    id="api_token"
                    type="password"
                    placeholder={
                      editingProvider
                        ? "Enter new API token or leave blank"
                        : "Enter API token"
                    }
                    value={formData.api_token}
                    onChange={(e) =>
                      setFormData({ ...formData, api_token: e.target.value })
                    }
                    required={!editingProvider}
                  />
                </div>
              </>
            )}

            {formData.provider_type !== "jira" && (
              <div className="space-y-2">
                <Label htmlFor="username">Username (Optional)</Label>
                <Input
                  id="username"
                  type="text"
                  placeholder="Optional username"
                  value={formData.username}
                  onChange={(e) =>
                    setFormData({ ...formData, username: e.target.value })
                  }
                />
              </div>
            )}

                              <DialogFooter>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleCloseDialog}
                    >
                      Cancel
                    </Button>
                    <Button type="submit" disabled={isLoading}>
                      {isLoading ? (
                        <>
                          <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                          {editingProvider ? "Updating..." : "Connecting..."}
                        </>
                      ) : (
                        <>
                          <CheckCircle className="w-4 h-4 mr-2" />
                          {editingProvider ? "Update" : "Connect"}
                        </>
                      )}
                    </Button>
                  </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
