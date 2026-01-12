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
    installPlugin: (pluginId: string) => void; // Smart install
    uninstallInstance: (instanceId: string) => void;
    updateInstanceConfig: (instanceId: string, newConfig: Record<string, any>) => void;
    getInstance: (instanceId: string) => DashboardInstance | undefined;
}

export const useDashboardStore = create<DashboardStore>()(
    persist(
        (set, get) => ({
            pages: [],
            widgets: [],

            installPlugin: (pluginId: string) => {
                const plugin = getDashboardPlugin(pluginId);
                if (!plugin) return;

                // Construct default config from schema
                const defaultConfig: Record<string, any> = {};
                if (plugin.configSchema) {
                    Object.entries(plugin.configSchema).forEach(([key, field]) => {
                        defaultConfig[key] = field.defaultValue;
                    });
                }

                const newInstance: DashboardInstance = {
                    instanceId: uuidv4(),
                    pluginId: pluginId,
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
        }),
        {
            name: "pm-dashboard-store-v2", // New version key
        }
    )
);
