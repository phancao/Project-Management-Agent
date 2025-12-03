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
  Brain,
  Key,
} from "lucide-react";
import { useState, useEffect } from "react";

import { Button } from "~/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "~/components/ui/tabs";
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
  deleteProvider,
  type ProviderConfig,
  type ProjectImportRequest,
  type ProjectInfo,
} from "~/core/api/pm/providers";
import { PROVIDER_TYPES, getProviderIcon } from "~/app/pm/utils/provider-utils";
import { AIProviderManagementView } from "./ai-provider-management-view";
import { cn } from "~/lib/utils";

export function ProviderManagementView({ defaultTab = "pm" }: { defaultTab?: "pm" | "ai" } = {}) {
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [isLoadingProviders, setIsLoadingProviders] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ProviderConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [providerToDelete, setProviderToDelete] = useState<ProviderConfig | null>(null);
  const [apiKeyError, setApiKeyError] = useState<string | null>(null);
  const [isValidating, setIsValidating] = useState(false);

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
      // Error is displayed in UI via setError, no need to log to console
      setError(err instanceof Error ? err.message : "Failed to load providers");
    } finally {
      setIsLoadingProviders(false);
    }
  };

  const loadProjectsForProvider = async (provider: ProviderConfig) => {
    if (!provider.id) {
      // Silently skip if provider ID is missing
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
      // Error is displayed in UI via setProjects with error state, no need to log to console
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
      username: provider.username ?? "",
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
    setApiKeyError(null);
    setIsValidating(false);
  };

  const validateApiKey = async (): Promise<boolean> => {
    // Check if API key/token is required and provided
    const needsApiKey = 
      formData.provider_type === "openproject" ||
      formData.provider_type === "openproject_v13" ||
      formData.provider_type === "clickup";
    const needsApiToken = formData.provider_type === "jira";
    
    // For JIRA, both username (email) and API token are required
    if (needsApiToken) {
      if (!formData.username?.trim()) {
        setApiKeyError("Email address (username) is required for JIRA");
        return false;
      }
      if (!formData.api_token?.trim()) {
        // When editing, if no new token provided, we'll use existing one from backend
        if (!editingProvider) {
          setApiKeyError("API token is required");
          return false;
        }
        // For editing, if no new token provided, skip validation (will use existing)
        return true;
      }
    }
    
    if (needsApiKey && !formData.api_key?.trim()) {
      setApiKeyError("API key is required");
      return false;
    }
    
    // Test connection if API key/token is provided
    if ((needsApiKey && formData.api_key?.trim()) || (needsApiToken && formData.api_token?.trim())) {
      setIsValidating(true);
      setApiKeyError(null);
      
      try {
        const request: ProjectImportRequest = {
          provider_type: formData.provider_type,
          base_url: formData.base_url.trim(),
          import_options: {
            skip_existing: true,
            auto_sync: false,
          },
        };
        
        if (needsApiKey) {
          request.api_key = formData.api_key;
        } else if (needsApiToken) {
          request.api_token = formData.api_token;
        }
        
        // For JIRA, username is required
        if (formData.provider_type === "jira") {
          if (!formData.username?.trim()) {
            setApiKeyError("Email address (username) is required for JIRA");
            setIsValidating(false);
            return false;
          }
          request.username = formData.username;
        } else if (formData.username) {
          request.username = formData.username;
        }
        
        if (formData.organization_id) {
          request.organization_id = formData.organization_id;
        }
        
        if (formData.workspace_id) {
          request.workspace_id = formData.workspace_id;
        }
        
        const { testProviderConnection } = await import("~/core/api/pm/providers");
        const result = await testProviderConnection(request);
        
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
    
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);
    setApiKeyError(null);

    try {
      // Validate API key first
      const isValid = await validateApiKey();
      if (!isValid) {
        setIsLoading(false);
        return;
      }
      
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
      if (
        formData.provider_type === "openproject" ||
        formData.provider_type === "openproject_v13" ||
        formData.provider_type === "clickup"
      ) {
        request.api_key = formData.api_key;
      } else if (formData.provider_type === "jira") {
        request.api_token = formData.api_token;
      }

      // For JIRA, username should be the email address
      // OpenProject (both v13 and v16) doesn't require username
      if (
        formData.username &&
        formData.provider_type !== "openproject" &&
        formData.provider_type !== "openproject_v13"
      ) {
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
            [response.provider_config_id ?? ""]: {
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

  const handleDeleteClick = (provider: ProviderConfig) => {
    if (!provider.id) {
      setError("Provider ID is missing");
      return;
    }
    setProviderToDelete(provider);
    setDeleteConfirmOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!providerToDelete?.id) {
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);
    setDeleteConfirmOpen(false);

    try {
      await deleteProvider(providerToDelete.id);
      setSuccessMessage("Provider deleted successfully!");
      // Remove from local state
      setProviders((prev) => prev.filter((p) => p.id !== providerToDelete.id));
      // Remove projects for this provider
      setProjects((prev) => {
        const newProjects = { ...prev };
        delete newProjects[providerToDelete.id!];
        return newProjects;
      });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to delete provider",
      );
    } finally {
      setIsLoading(false);
      setProviderToDelete(null);
    }
  };


  return (
    <div className="h-full flex flex-col">
      <Tabs defaultValue={defaultTab} className="h-full flex flex-col">
        <TabsList className="mx-4 mt-4">
          <TabsTrigger value="pm" className="flex items-center gap-2">
            <Server className="w-4 h-4" />
            PM Providers
          </TabsTrigger>
          <TabsTrigger value="ai" className="flex items-center gap-2">
            <Brain className="w-4 h-4" />
            AI Providers
          </TabsTrigger>
        </TabsList>

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

        <TabsContent value="pm" className="flex-1 flex flex-col mt-0">
          <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Project Management Providers
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Connect to external project management systems
              </p>
            </div>
            <Button onClick={() => setIsDialogOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add PM Provider
            </Button>
          </div>

          {/* PM Provider List */}
          <div className="flex-1 overflow-auto p-4">
        {isLoadingProviders ? (
          <div className="flex flex-col items-center justify-center h-full">
            <RefreshCw className="w-8 h-8 text-gray-400 mb-4 animate-spin" />
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Loading providers...
            </p>
          </div>
        ) : providers.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <div className="max-w-md">
              <Server className="w-20 h-20 text-gray-400 dark:text-gray-500 mx-auto mb-6" />
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">
                No Project Management Providers Configured
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                Connect to your project management system to start managing projects, tasks, and sprints.
              </p>
              
              {/* Supported Providers */}
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 mb-6 text-left">
                <p className="text-sm font-medium text-gray-900 dark:text-white mb-3">
                  Supported Providers:
                </p>
                <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                  <li className="flex items-center gap-2">
                    <span className="text-lg">{getProviderIcon("openproject")}</span>
                    <span><strong>OpenProject</strong> - Open-source project management</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-lg">{getProviderIcon("openproject_v13")}</span>
                    <span><strong>OpenProject v13</strong> - Legacy OpenProject instances</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-lg">{getProviderIcon("jira")}</span>
                    <span><strong>JIRA</strong> - Atlassian JIRA Cloud or Server</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-lg">{getProviderIcon("clickup")}</span>
                    <span><strong>ClickUp</strong> - All-in-one productivity platform</span>
                  </li>
                </ul>
              </div>

              {/* Quick Start Guide */}
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6 text-left">
                <p className="text-sm font-medium text-blue-900 dark:text-blue-200 mb-2">
                  Quick Start:
                </p>
                <ol className="text-sm text-blue-800 dark:text-blue-300 space-y-1.5 list-decimal list-inside">
                  <li>Click the button below to add your first provider</li>
                  <li>Select your project management system type</li>
                  <li>Enter your server URL and API credentials</li>
                  <li>Import your projects and start managing them</li>
                </ol>
              </div>

              <Button 
                onClick={() => setIsDialogOpen(true)}
                size="lg"
                className="w-full sm:w-auto"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Your First Provider
              </Button>
            </div>
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
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteClick(provider)}
                        disabled={isLoading || !provider.id}
                      >
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
                      ) : (providerProjects?.projects?.length ?? 0) > 0 ? (
                        <div className="space-y-2">
                          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            Projects (
                            {providerProjects?.projects?.length ?? 0}):
                          </p>
                          <div className="space-y-1">
                            {providerProjects?.projects?.slice(0, 3).map((project) => {
                              // Construct external URL for the project
                              const getProjectUrl = (provider: ProviderConfig, projectId: string): string | null => {
                                if (!provider.base_url) return null;
                                
                                const baseUrl = provider.base_url.replace(/\/$/, '');
                                const providerType = provider.provider_type;
                                switch (providerType) {
                                  case "jira":
                                    // JIRA: try /browse/{projectKey} first, fallback to /projects/{projectKey}
                                    return `${baseUrl}/browse/${projectId}`;
                                  case "openproject":
                                  case "openproject_v13":
                                    // OpenProject: projects are at /projects/{projectId}
                                    return `${baseUrl}/projects/${projectId}`;
                                  case "clickup":
                                    // ClickUp: projects/spaces might be at different URLs
                                    // For now, try a common pattern
                                    return `${baseUrl.replace('/api/v2', '')}/p/${projectId}`;
                                  default:
                                    return null;
                                }
                              };
                              
                              const projectUrl = getProjectUrl(provider, project.id);
                              
                              return (
                                <div
                                  key={project.id}
                                  className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-900 rounded"
                                >
                                  <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                                      {project.name}
                                    </p>
                                    {project.description && (
                                      <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                                        {project.description.length > 100 
                                          ? `${project.description.substring(0, 100)}...`
                                          : project.description}
                                      </p>
                                    )}
                                  </div>
                                  {projectUrl ? (
                                    <a
                                      href={projectUrl}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors shrink-0 ml-2"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      <ExternalLink className="w-4 h-4" />
                                    </a>
                                  ) : (
                                    <ExternalLink className="w-4 h-4 text-gray-400 shrink-0 ml-2" />
                                  )}
                                </div>
                              );
                            })}
                            {providerProjects?.projects?.length > 3 && (
                              <p className="text-xs text-gray-500 dark:text-gray-400 pt-1">
                                +{providerProjects.projects.length - 3} more project{providerProjects.projects.length - 3 !== 1 ? 's' : ''}
                              </p>
                            )}
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
        </TabsContent>

        <TabsContent value="ai" className="flex-1 flex flex-col mt-0">
          <AIProviderManagementView />
        </TabsContent>
      </Tabs>

      {/* Add/Edit PM Provider Dialog */}
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
                  {PROVIDER_TYPES.map((type) => (
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
                        formData.provider_type === "openproject_v13" ||
                        formData.provider_type === "clickup") && (
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
                                : "Enter API key"
                            }
                            value={formData.api_key}
                            onChange={(e) => {
                              setFormData({ ...formData, api_key: e.target.value });
                              setApiKeyError(null);
                            }}
                            required={!editingProvider}
                            className={apiKeyError ? "border-red-500 focus:border-red-500 focus:ring-red-500" : ""}
                            disabled={isValidating}
                          />
                          {apiKeyError && (
                            <p className="text-sm text-red-500 flex items-center gap-1">
                              <AlertCircle className="w-4 h-4" />
                              {apiKeyError}
                            </p>
                          )}
                          {isValidating && !apiKeyError && (
                            <p className="text-sm text-blue-500 flex items-center gap-1">
                              <RefreshCw className="w-4 h-4 animate-spin" />
                              Testing connection...
                            </p>
                          )}
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
                    <span className="text-red-500 ml-1">*</span>
                  </Label>
                  <Input
                    id="username"
                    type="email"
                    placeholder="your-email@example.com"
                    value={formData.username}
                    onChange={(e) => {
                      setFormData({ ...formData, username: e.target.value });
                      setApiKeyError(null); // Clear error when user types
                    }}
                    required
                    className={apiKeyError && apiKeyError.includes("Email") ? "border-red-500 focus:border-red-500 focus:ring-red-500" : ""}
                    disabled={isValidating}
                  />
                  {apiKeyError && apiKeyError.includes("Email") && (
                    <p className="text-sm text-red-500 flex items-center gap-1">
                      <AlertCircle className="w-4 h-4" />
                      {apiKeyError}
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="api_token">
                    API Token
                    {editingProvider && (
                      <span className="text-xs text-gray-500 ml-2">
                        (leave blank to keep existing)
                      </span>
                    )}
                    {!editingProvider && <span className="text-red-500 ml-1">*</span>}
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
                    onChange={(e) => {
                      setFormData({ ...formData, api_token: e.target.value });
                      setApiKeyError(null);
                    }}
                    required={!editingProvider}
                    className={apiKeyError ? "border-red-500 focus:border-red-500 focus:ring-red-500" : ""}
                    disabled={isValidating}
                  />
                  {apiKeyError && (
                    <p className="text-sm text-red-500 flex items-center gap-1">
                      <AlertCircle className="w-4 h-4" />
                      {apiKeyError}
                    </p>
                  )}
                  {isValidating && !apiKeyError && (
                    <p className="text-sm text-blue-500 flex items-center gap-1">
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Testing connection...
                    </p>
                  )}
                </div>
              </>
            )}

            {formData.provider_type !== "jira" && formData.provider_type !== "openproject" && (
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
                    <Button 
                      type="submit" 
                      disabled={isLoading || isValidating || !!apiKeyError}
                      className={apiKeyError ? "opacity-50 cursor-not-allowed" : ""}
                    >
                      {isLoading || isValidating ? (
                        <>
                          <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                          {isValidating ? "Testing..." : editingProvider ? "Updating..." : "Connecting..."}
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

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Provider</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the provider{" "}
              <strong>{providerToDelete?.provider_type.toUpperCase()}</strong> at{" "}
              <strong>{providerToDelete?.base_url}</strong>? This action cannot be undone.
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
