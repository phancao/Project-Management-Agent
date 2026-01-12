import { create } from "zustand";
import { persist } from "zustand/middleware";
import { v4 as uuidv4 } from "uuid";
import { getDashboardPlugin } from "../../app/pm/chat/components/dashboards/registry";

export interface DashboardInstance {
    instanceId: string;
    pluginId: string;
    config: Record<string, any>;
    createdAt: number;
}

interface DashboardStore {
    pages: DashboardInstance[];
    widgets: DashboardInstance[];

    // Actions
    installPlugin: (plugin: any) => void; // Smart install accepting full plugin object
    uninstallInstance: (instanceId: string) => void;
    updateInstanceConfig: (instanceId: string, newConfig: Record<string, any>) => void;
    getInstance: (instanceId: string) => DashboardInstance | undefined;
    movePage: (oldIndex: number, newIndex: number) => void; // Reorder pages
}

export const useDashboardStore = create<DashboardStore>()(
    persist(
        (set, get) => ({
            pages: [],
            widgets: [],

            installPlugin: (plugin: any) => {
                // plugin is now the full object passed from the UI
                if (!plugin) return;

                // Construct default config from schema
                const defaultConfig: Record<string, any> = {};
                if (plugin.configSchema) {
                    Object.entries(plugin.configSchema).forEach(([key, field]: [string, any]) => {
                        defaultConfig[key] = field.defaultValue;
                    });
                }

                const newInstance: DashboardInstance = {
                    instanceId: uuidv4(),
                    pluginId: plugin.id,
                    config: defaultConfig,
                    createdAt: Date.now(),
                };

                if (plugin.type === 'widget') {
                    set((state) => ({
                        widgets: [...state.widgets, newInstance],
                    }));
                } else {
                    set((state) => ({
                        pages: [...state.pages, newInstance],
                    }));
                }
            },

            uninstallInstance: (instanceId: string) => {
                set((state) => ({
                    pages: state.pages.filter((i) => i.instanceId !== instanceId),
                    widgets: state.widgets.filter((i) => i.instanceId !== instanceId),
                }));
            },

            updateInstanceConfig: (instanceId: string, newConfig: Record<string, any>) => {
                set((state) => ({
                    pages: state.pages.map((i) =>
                        i.instanceId === instanceId ? { ...i, config: { ...i.config, ...newConfig } } : i
                    ),
                    widgets: state.widgets.map((i) =>
                        i.instanceId === instanceId ? { ...i, config: { ...i.config, ...newConfig } } : i
                    ),
                }));
            },

            getInstance: (instanceId: string) => {
                const { pages, widgets } = get();
                return pages.find((i) => i.instanceId === instanceId) || widgets.find((i) => i.instanceId === instanceId);
            },

            movePage: (oldIndex: number, newIndex: number) => {
                set((state) => {
                    const newPages = [...state.pages];
                    if (oldIndex >= 0 && oldIndex < newPages.length) {
                        const [removed] = newPages.splice(oldIndex, 1);
                        if (removed) {
                            newPages.splice(newIndex, 0, removed);
                        }
                    }
                    return { pages: newPages };
                });
            },
        }),
        {
            name: "pm-dashboard-store-v2", // New version key
        }
    )
);
