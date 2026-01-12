"use client";

import { dashboardRegistry } from "../dashboards/registry";
import { useDashboardStore } from "~/core/store/use-dashboard-store";
import { Button } from "~/components/ui/button";
import { LayoutGrid, Download, Plus } from "lucide-react";
import { cn } from "~/lib/utils";
import { toast } from "sonner";

export function StorePanelView() {
    const { installPlugin } = useDashboardStore();

    const handleInstall = (pluginId: string, title: string, type: string) => {
        installPlugin(pluginId);
        toast.success(`Installed "${title}" ${type}`);
    };

    return (
        <div className="p-6 h-full overflow-auto">
            <div className="mb-8">
                <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100 flex items-center gap-2">
                    <LayoutGrid className="w-6 h-6 text-brand" />
                    Dashboard Pages
                </h2>
                <p className="text-gray-500 dark:text-gray-400 mt-2">
                    Extend your workspace with new full-page <strong>Dashboard Views</strong>.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {dashboardRegistry.filter(p => p.type === 'page').map((plugin) => {
                    const Icon = plugin.meta.icon;
                    const isPage = true;

                    return (
                        <div
                            key={plugin.id}
                            className="group relative border rounded-xl p-6 transition-all duration-300 bg-white dark:bg-gray-950/50 hover:shadow-lg hover:border-brand/50 border-gray-200 dark:border-gray-800"
                        >
                            <div className="flex justify-between items-start mb-4">
                                <div className="p-3 rounded-lg bg-gray-100 dark:bg-gray-900 group-hover:scale-110 transition-transform duration-300">
                                    <Icon className="w-6 h-6 text-gray-700 dark:text-gray-300 group-hover:text-brand" />
                                </div>
                                <span className="px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400">
                                    {plugin.type}
                                </span>
                            </div>

                            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                                {plugin.meta.title}
                            </h3>
                            <p className="text-sm text-gray-500 dark:text-gray-400 mb-2 min-h-[40px]">
                                {plugin.meta.description}
                            </p>

                            <div className="flex flex-wrap gap-2 mb-6">
                                <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                                    {plugin.meta.category}
                                </span>
                            </div>

                            <div className="flex items-center justify-between mt-auto pt-4 border-t border-gray-100 dark:border-gray-800">
                                <span className="text-xs text-gray-400">v{plugin.meta.version} • {plugin.meta.author}</span>
                                <Button
                                    size="sm"
                                    onClick={() => handleInstall(plugin.id, plugin.meta.title, plugin.type)}
                                    className="bg-brand hover:bg-brand/90 text-white shadow-lg shadow-brand/20"
                                >
                                    <Plus className="w-4 h-4 mr-2" />
                                    Add Tab
                                </Button>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
