"use client";

import React, { useState } from "react";
import { useDashboardStore } from "~/core/store/use-dashboard-store";
import { useStoreRegistry } from "../dashboards/registry";
import { Button } from "~/components/ui/button";
import { Settings, X, Save, AlertCircle, Trash2, Loader2 } from "lucide-react";
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

interface CustomDashboardViewProps {
    instanceId: string;
    onRemove?: () => void;
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
                    <SheetContent>
                        <SheetHeader>
                            <SheetTitle>Configure Dashboard</SheetTitle>
                            <p className="text-sm text-gray-500">
                                Customize settings for this <strong>{plugin.meta.title}</strong> instance.
                            </p>
                        </SheetHeader>

                        <ScrollArea className="h-[calc(100vh-200px)] mt-6 pr-4">
                            <div className="space-y-6">
                                {schema &&
                                    Object.entries(schema).map(([key, field]) => (
                                        <div key={key}>{renderConfigField(key, field)}</div>
                                    ))}
                            </div>
                        </ScrollArea>

                        <SheetFooter className="mt-8">
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
