"use client";

import React, { useState } from "react";
import { useDashboardStore } from "~/core/store/use-dashboard-store";
import { useStoreRegistry } from "../dashboards/registry";
import { Button } from "~/components/ui/button";
import { Settings, X, Save, AlertCircle, Trash2, Loader2, Plus, Database, FolderOpen } from "lucide-react";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
    SheetFooter,
    SheetClose,
} from "~/components/ui/sheet";
import { Label } from "~/components/ui/label";
import { Input } from "~/components/ui/input";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "~/components/ui/select";
import { Switch } from "~/components/ui/switch";
import { ScrollArea } from "~/components/ui/scroll-area";
import { Badge } from "~/components/ui/badge";

interface CustomDashboardViewProps {
    instanceId: string;
    onRemove?: () => void;
}

import { useAllUsers } from "~/app/team/context/team-data-context";
import { Avatar, AvatarFallback, AvatarImage } from "~/components/ui/avatar";
import { useProviders } from "~/core/api/hooks/pm/use-providers";
import { useProjectsByProvider } from "~/core/api/hooks/pm/use-projects";

// Helper to extract a friendly display name from provider
function getProviderDisplayName(provider: { provider_type: string; base_url: string }) {
    try {
        const hostname = new URL(provider.base_url).hostname;
        // Extract meaningful part (e.g., "openproject.example.com" -> "example.com")
        const parts = hostname.split('.');
        if (parts.length >= 2) {
            return parts.slice(-2).join('.');
        }
        return hostname;
    } catch {
        return provider.base_url;
    }
}

// Helper component for Provider selection
function ProviderSelector({
    value,
    onChange
}: {
    value?: string;
    onChange: (val: string) => void;
}) {
    const { providers, loading } = useProviders();

    if (loading) {
        return (
            <div className="h-10 flex items-center gap-2 px-3 border rounded-md bg-muted/30">
                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Loading providers...</span>
            </div>
        );
    }

    const activeProviders = providers.filter(p => p.is_active);

    if (activeProviders.length === 0) {
        return (
            <div className="h-10 flex items-center gap-2 px-3 border rounded-md bg-muted/30 text-muted-foreground text-sm">
                No providers configured
            </div>
        );
    }

    // Get the selected provider for display
    const selectedProvider = activeProviders.find(p => p.id === value);

    return (
        <Select value={value || ""} onValueChange={onChange}>
            <SelectTrigger className="h-10">
                {selectedProvider ? (
                    <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="text-xs bg-brand/10 text-brand border-brand/20">
                            {selectedProvider.provider_type.toUpperCase()}
                        </Badge>
                        <span>{getProviderDisplayName(selectedProvider)}</span>
                    </div>
                ) : (
                    <SelectValue placeholder="Select a provider..." />
                )}
            </SelectTrigger>
            <SelectContent>
                {activeProviders.map(provider => (
                    <SelectItem key={provider.id} value={provider.id}>
                        <div className="flex items-center gap-2">
                            <Badge variant="secondary" className="text-xs bg-brand/10 text-brand border-brand/20">
                                {provider.provider_type.toUpperCase()}
                            </Badge>
                            <span>{getProviderDisplayName(provider)}</span>
                        </div>
                    </SelectItem>
                ))}
            </SelectContent>
        </Select>
    );
}

// Helper component for Project selection (depends on Provider)
function ProjectByProviderSelector({
    value,
    onChange,
    providerId
}: {
    value?: string;
    onChange: (val: string) => void;
    providerId?: string;
}) {
    const { projects, loading } = useProjectsByProvider(providerId);

    if (!providerId) {
        return (
            <div className="h-10 flex items-center gap-2 px-3 border rounded-md bg-muted/20 border-dashed">
                <FolderOpen className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground italic">Select a provider first</span>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="h-10 flex items-center gap-2 px-3 border rounded-md bg-muted/30">
                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Loading projects...</span>
            </div>
        );
    }

    if (projects.length === 0) {
        return (
            <div className="h-10 flex items-center gap-2 px-3 border rounded-md bg-muted/20 text-muted-foreground text-sm">
                <AlertCircle className="w-4 h-4" />
                No projects found for this provider
            </div>
        );
    }

    // Find selected project for display
    const selectedProject = projects.find(p => p.id === value);

    return (
        <Select value={value || ""} onValueChange={onChange}>
            <SelectTrigger className="h-10">
                {selectedProject ? (
                    <div className="flex items-center gap-2">
                        <FolderOpen className="w-4 h-4 text-brand" />
                        <span>{selectedProject.name}</span>
                    </div>
                ) : (
                    <SelectValue placeholder="Select a project..." />
                )}
            </SelectTrigger>
            <SelectContent>
                {projects.map(project => (
                    <SelectItem key={project.id} value={project.id}>
                        <div className="flex items-center gap-2">
                            <FolderOpen className="w-4 h-4 text-muted-foreground" />
                            {project.name}
                        </div>
                    </SelectItem>
                ))}
            </SelectContent>
        </Select>
    );
}

// Helper component to avoid hook rules issues in renderConfigField
function TeamMemberSelector({
    value,
    onChange
}: {
    value?: string[];
    onChange: (val: string[]) => void;
}) {
    const { allUsers: users, isLoading: loading } = useAllUsers(true);
    const [searchTerm, setSearchTerm] = useState("");

    const selected = new Set(value || []);

    const toggleMember = (id: string, add: boolean) => {
        const newSet = new Set(selected);
        if (add) {
            newSet.add(id);
        } else {
            newSet.delete(id);
        }
        onChange(Array.from(newSet));
    };

    // Word-boundary search filter
    const filteredUsers = users.filter(user => {
        if (!searchTerm.trim()) return true;
        const searchLower = searchTerm.toLowerCase().trim();
        const name = (user.name || "").toLowerCase();
        const email = (user.email || "").toLowerCase();
        // Split by word boundaries (space, dot, @)
        const nameWords = name.split(/[\s.@]+/);
        const emailWords = email.split(/[\s.@]+/);
        return [...nameWords, ...emailWords].some(word => word.startsWith(searchLower));
    });

    const selectedUsers = users.filter(u => selected.has(u.id));
    const availableUsers = filteredUsers.filter(u => !selected.has(u.id));

    if (loading) {
        return <div className="text-sm text-gray-500 flex items-center gap-2"><Loader2 className="w-3 h-3 animate-spin" /> Loading members...</div>;
    }

    if (users.length === 0) {
        return <div className="text-sm text-gray-500">No members found.</div>;
    }

    return (
        <div className="flex flex-col min-w-0 overflow-hidden h-full">
            {/* Selected Members Section - Dynamic height with max */}
            <div className="shrink-0 border rounded-lg mb-3 flex flex-col overflow-hidden" style={{ maxHeight: '150px' }}>
                <div className="p-2 border-b bg-brand/5 text-xs font-medium text-muted-foreground shrink-0 flex items-center justify-between">
                    <span>Selected Members</span>
                    <span className="bg-brand/20 text-brand px-1.5 py-0.5 rounded-full text-[10px]">
                        {selectedUsers.length}
                    </span>
                </div>
                <div className="flex-1 overflow-y-auto p-2 [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-muted-foreground/40 [&::-webkit-scrollbar-track]:bg-transparent">
                    {selectedUsers.length === 0 ? (
                        <div className="text-center py-4 text-sm text-muted-foreground">
                            No members selected
                        </div>
                    ) : (
                        <div className="flex flex-wrap gap-1.5">
                            {selectedUsers.map(user => (
                                <div
                                    key={user.id}
                                    className="flex items-center gap-1.5 bg-brand/10 border border-brand/20 px-2 py-1 rounded-full text-xs"
                                >
                                    <span className="truncate max-w-[120px]">{user.name || user.email}</span>
                                    <button
                                        onClick={() => toggleMember(user.id, false)}
                                        className="w-4 h-4 rounded-full hover:bg-destructive/20 hover:text-destructive flex items-center justify-center shrink-0"
                                    >
                                        <X className="w-3 h-3" />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Search Input - Sandwiched */}
            <div className="shrink-0 pb-3">
                <Input
                    placeholder="Search users..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="h-9"
                />
            </div>

            {/* Available Users Section */}
            <div className="flex-1 min-h-0 min-w-0 border rounded-lg flex flex-col overflow-hidden">
                <div className="p-2 border-b bg-muted/30 text-xs font-medium text-muted-foreground shrink-0 flex items-center justify-between">
                    <span>Available Users</span>
                    <span className="text-[10px]">{availableUsers.length}</span>
                </div>
                <div className="flex-1 overflow-y-auto p-1 [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-muted-foreground/40 [&::-webkit-scrollbar-track]:bg-transparent">
                    {availableUsers.length === 0 ? (
                        <div className="text-center py-4 text-sm text-muted-foreground">
                            {selected.size > 0 ? "All users selected" : "No users found"}
                        </div>
                    ) : (
                        availableUsers.map((user) => (
                            <div
                                key={user.id}
                                className="flex items-center gap-2 p-2 pr-1 rounded hover:bg-muted/50 group flex-nowrap"
                                style={{ maxWidth: '100%' }}
                            >
                                <Avatar className="h-6 w-6 shrink-0 flex-none">
                                    <AvatarImage src={user.avatar} />
                                    <AvatarFallback className="text-[10px] bg-muted">
                                        {user.name?.charAt(0) || "?"}
                                    </AvatarFallback>
                                </Avatar>
                                <div className="flex-1 min-w-0 overflow-hidden">
                                    <span className="text-sm font-medium block truncate">
                                        {user.name || user.email || user.id}
                                    </span>
                                </div>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => toggleMember(user.id, true)}
                                    className="h-7 w-7 p-0 shrink-0 flex-none border hover:bg-brand/10 hover:text-brand hover:border-brand"
                                >
                                    <Plus className="w-4 h-4" />
                                </Button>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}

export function CustomDashboardView({ instanceId, onRemove }: CustomDashboardViewProps) {
    const { getInstance, updateInstanceConfig } = useDashboardStore();
    const instance = getInstance(instanceId);
    const [configOpen, setConfigOpen] = useState(false);

    // Use the dynamic registry hook instead of static lookup
    const { getPlugin, loading } = useStoreRegistry();

    // 1. Hoist state initialization
    // Use an empty object fallback if instance is missing to satisfy the hook rule
    const [tempConfig, setTempConfig] = useState(instance?.config || {});

    // 2. Derive logic safely
    const plugin = instance ? getPlugin(instance.pluginId) : undefined;

    // 3. Early returns ONLY after all hooks are called
    if (!instance) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <AlertCircle className="w-12 h-12 mb-4 text-red-400" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">Dashboard Instance Not Found</h3>
                <p>The dashboard instance "{instanceId}" is missing.</p>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <Loader2 className="w-8 h-8 animate-spin mb-4" />
                <p>Loading plugin...</p>
            </div>
        )
    }

    if (!plugin) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <AlertCircle className="w-12 h-12 mb-4 text-orange-400" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">Plugin Missing</h3>
                <p>The plugin "{instance.pluginId}" is no longer available.</p>
            </div>
        );
    }

    const Component = plugin.component;
    const schema = plugin.configSchema;

    const handleSaveConfig = () => {
        updateInstanceConfig(instanceId, tempConfig);
        setConfigOpen(false);
    };

    const renderConfigField = (key: string, field: any) => {
        switch (field.type) {
            case "string":
                return (
                    <div className="space-y-2">
                        <Label htmlFor={key}>{field.label}</Label>
                        <Input
                            id={key}
                            value={tempConfig[key] || ""}
                            onChange={(e) => setTempConfig({ ...tempConfig, [key]: e.target.value })}
                        />
                    </div>
                );
            case "number":
                return (
                    <div className="space-y-2">
                        <Label htmlFor={key}>{field.label}</Label>
                        <Input
                            id={key}
                            type="number"
                            value={tempConfig[key] || 0}
                            onChange={(e) => setTempConfig({ ...tempConfig, [key]: Number(e.target.value) })}
                        />
                    </div>
                );
            case "boolean":
                return (
                    <div className="flex items-center justify-between py-2">
                        <Label htmlFor={key}>{field.label}</Label>
                        <Switch
                            id={key}
                            checked={!!tempConfig[key]}
                            onCheckedChange={(checked) => setTempConfig({ ...tempConfig, [key]: checked })}
                        />
                    </div>
                );
            case "select":
                return (
                    <div className="space-y-2">
                        <Label htmlFor={key}>{field.label}</Label>
                        <Select
                            value={tempConfig[key]}
                            onValueChange={(val) => setTempConfig({ ...tempConfig, [key]: val })}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="Select..." />
                            </SelectTrigger>
                            <SelectContent>
                                {field.options?.map((opt: string) => (
                                    <SelectItem key={opt} value={opt}>
                                        {opt}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                );
            case "team-members":
                return (
                    <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
                        <Label htmlFor={key} className="mt-3">{field.label}</Label>
                        <p className="text-xs text-muted-foreground mb-3 shrink-0">{field.description}</p>
                        <div className="flex-1 min-h-0 overflow-hidden">
                            <TeamMemberSelector
                                value={tempConfig[key]}
                                onChange={(val) => setTempConfig({ ...tempConfig, [key]: val })}
                            />
                        </div>
                    </div>
                );
            case "provider":
                return (
                    <div className="space-y-3 pt-2">
                        <Label className="flex items-center gap-2">
                            <Database className="w-4 h-4 text-muted-foreground" />
                            {field.label}
                        </Label>
                        {field.description && (
                            <p className="text-xs text-muted-foreground">{field.description}</p>
                        )}
                        <ProviderSelector
                            value={tempConfig[key]}
                            onChange={(val) => {
                                // When provider changes, also clear the dependent project field
                                const dependentField = Object.entries(schema || {}).find(
                                    ([, f]: [string, any]) => f.dependsOn === key
                                );
                                if (dependentField) {
                                    setTempConfig({ ...tempConfig, [key]: val, [dependentField[0]]: undefined });
                                } else {
                                    setTempConfig({ ...tempConfig, [key]: val });
                                }
                            }}
                        />
                    </div>
                );
            case "project-by-provider":
                return (
                    <div className="space-y-3 pt-4">
                        <Label className="flex items-center gap-2">
                            <FolderOpen className="w-4 h-4 text-muted-foreground" />
                            {field.label}
                        </Label>
                        {field.description && (
                            <p className="text-xs text-muted-foreground">{field.description}</p>
                        )}
                        <ProjectByProviderSelector
                            value={tempConfig[key]}
                            onChange={(val) => setTempConfig({ ...tempConfig, [key]: val })}
                            providerId={tempConfig[field.dependsOn]}
                        />
                    </div>
                );
            default:
                return null;
        }
    };

    return (
        <div className="relative h-full w-full flex flex-col">
            {/* Header / Toolbar */}
            <div className="flex items-center justify-end px-4 py-2 border-b border-gray-100 dark:border-gray-800 bg-white/50 dark:bg-gray-950/20 backdrop-blur-sm z-10 gap-1">
                <Sheet open={configOpen} onOpenChange={setConfigOpen}>
                    <SheetTrigger asChild>
                        <Button variant="ghost" size="icon" className="w-8 h-8 text-gray-400 hover:text-brand hover:bg-brand/5" title="Configure">
                            <Settings className="w-4 h-4" />
                        </Button>
                    </SheetTrigger>
                    <SheetContent className="flex flex-col h-full">
                        <SheetHeader>
                            <SheetTitle>Configure Dashboard</SheetTitle>
                            <p className="text-sm text-gray-500">
                                Customize settings for this <strong>{plugin.meta.title}</strong> instance.
                            </p>
                        </SheetHeader>

                        <div className="flex-1 min-w-0 overflow-hidden flex flex-col px-6">
                            <div className="flex flex-col flex-1 min-h-0 min-w-0 overflow-hidden">
                                {schema &&
                                    Object.entries(schema).map(([key, field]) => (
                                        <div key={key} className={field.type === 'team-members' ? 'flex-1 min-h-0 overflow-hidden flex flex-col' : ''}>{renderConfigField(key, field)}</div>
                                    ))}
                            </div>
                        </div>

                        <SheetFooter className="flex-none border-t pt-4 mt-4 bg-background">
                            <SheetClose asChild>
                                <Button variant="outline">Cancel</Button>
                            </SheetClose>
                            <Button onClick={handleSaveConfig} className="bg-brand text-white hover:bg-brand/90">
                                <Save className="w-4 h-4 mr-2" />
                                Save Changes
                            </Button>
                        </SheetFooter>
                    </SheetContent>
                </Sheet>

                {onRemove && (
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onRemove}
                        className="w-8 h-8 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                        title="Remove Widget"
                    >
                        <Trash2 className="w-4 h-4" />
                    </Button>
                )}
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-auto animate-in fade-in duration-300">
                <Component config={instance.config} />
            </div>
        </div>
    );
}
