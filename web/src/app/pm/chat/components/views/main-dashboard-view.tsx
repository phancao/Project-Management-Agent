"use client";

import { useState } from "react";
import { useDashboardStore } from "~/core/store/use-dashboard-store";
import { CustomDashboardView } from "./custom-dashboard-view";
import { Button } from "~/components/ui/button";
import { Plus, LayoutTemplate, Box } from "lucide-react";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
    SheetDescription,
} from "~/components/ui/sheet";
import { dashboardRegistry } from "../dashboards/registry";
import { toast } from "sonner";
import { ScrollArea } from "~/components/ui/scroll-area";

export function MainDashboardView() {
    const { widgets, uninstallInstance, installPlugin } = useDashboardStore();
    const [storeOpen, setStoreOpen] = useState(false);

    const availableWidgets = dashboardRegistry.filter(plugin => plugin.type === 'widget');

    const handleAddWidget = (pluginId: string, title: string) => {
        installPlugin(pluginId);
        toast.success(`Added ${title} widget`);
        setStoreOpen(false);
    }

    const WidgetStoreSheet = () => (
        <Sheet open={storeOpen} onOpenChange={setStoreOpen}>
            <SheetTrigger asChild>
                <Button variant="outline" size="sm">
                    <Plus className="w-4 h-4 mr-2" />
                    Add Widget
                </Button>
            </SheetTrigger>
            <SheetContent className="w-[400px] sm:w-[540px]">
                <SheetHeader>
                    <SheetTitle>Add Widget</SheetTitle>
                    <SheetDescription>
                        Choose a widget to add to your dashboard.
                    </SheetDescription>
                </SheetHeader>
                <ScrollArea className="h-[calc(100vh-100px)] mt-6 pr-4">
                    <div className="grid grid-cols-1 gap-4">
                        {availableWidgets.map((plugin) => {
                            const Icon = plugin.meta.icon || Box;
                            return (
                                <div
                                    key={plugin.id}
                                    className="flex items-start gap-4 p-4 rounded-xl border border-gray-100 dark:border-gray-800 hover:border-brand/50 hover:bg-gray-50 dark:hover:bg-gray-900/50 transition-all cursor-pointer group"
                                    onClick={() => handleAddWidget(plugin.id, plugin.meta.title)}
                                >
                                    <div className="p-3 rounded-lg bg-gray-100 dark:bg-gray-900 text-gray-500 group-hover:text-brand group-hover:bg-brand/10 transition-colors">
                                        <Icon className="w-5 h-5" />
                                    </div>
                                    <div className="flex-1">
                                        <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-1">
                                            {plugin.meta.title}
                                        </h4>
                                        <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
                                            {plugin.meta.description}
                                        </p>
                                    </div>
                                    <Button size="sm" variant="ghost" className="opacity-0 group-hover:opacity-100 self-center">
                                        Add
                                    </Button>
                                </div>
                            );
                        })}
                        {availableWidgets.length === 0 && (
                            <div className="text-center py-12 text-gray-500">
                                <Box className="w-12 h-12 mx-auto mb-3 opacity-20" />
                                <p>No widgets available yet.</p>
                            </div>
                        )}
                    </div>
                </ScrollArea>
            </SheetContent>
        </Sheet>
    );

    return (
        <div className="p-6 h-full overflow-auto">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-3">
                        <LayoutTemplate className="w-8 h-8 text-brand" />
                        Dashboard
                    </h1>
                    <p className="text-gray-500 dark:text-gray-400 mt-1">
                        Overview of your project health and key metrics.
                    </p>
                </div>
                <div className="flex gap-2">
                    <WidgetStoreSheet />
                </div>
            </div>

            {widgets.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-12 border-2 border-dashed border-gray-200 dark:border-gray-800 rounded-xl bg-gray-50/50 dark:bg-gray-900/50">
                    <div className="p-4 bg-white dark:bg-gray-800 rounded-full mb-4 shadow-sm">
                        <LayoutTemplate className="w-8 h-8 text-gray-400" />
                    </div>
                    <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
                        Your dashboard is empty
                    </h3>
                    <p className="text-gray-500 dark:text-gray-400 text-center max-w-sm mb-6">
                        Add widgets to create a personalized overview of your team's progress.
                    </p>
                    <div className="flex justify-center">
                        <WidgetStoreSheet />
                    </div>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 auto-rows-[minmax(300px,auto)]">
                    {widgets.map((widget) => {
                        return (
                            <div key={widget.instanceId} className="bg-white dark:bg-gray-950 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 overflow-hidden relative group">
                                {/* The view handles its own content. We just constrain it here. */}
                                <div className="absolute inset-0">
                                    <CustomDashboardView
                                        instanceId={widget.instanceId}
                                        onRemove={() => uninstallInstance(widget.instanceId)}
                                    />
                                </div>
                            </div>
                        )
                    })}
                </div>
            )}
        </div>
    );
}
