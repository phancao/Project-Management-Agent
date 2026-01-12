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
    instances: DashboardInstance[];

    // Actions
    installInstance: (pluginId: string) => void;
    uninstallInstance: (instanceId: string) => void;
    updateInstanceConfig: (instanceId: string, newConfig: Record<string, any>) => void;
    getInstance: (instanceId: string) => DashboardInstance | undefined;
}

export const useDashboardStore = create<DashboardStore>()(
    persist(
        (set, get) => ({
            instances: [],

            installInstance: (pluginId: string) => {
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

                set((state) => ({
                    instances: [...state.instances, newInstance],
                }));
            },

            uninstallInstance: (instanceId: string) => {
                set((state) => ({
                    instances: state.instances.filter((i) => i.instanceId !== instanceId),
                }));
            },

            updateInstanceConfig: (instanceId: string, newConfig: Record<string, any>) => {
                set((state) => ({
                    instances: state.instances.map((i) =>
                        i.instanceId === instanceId ? { ...i, config: { ...i.config, ...newConfig } } : i
                    ),
                }));
            },

            getInstance: (instanceId: string) => {
                return get().instances.find((i) => i.instanceId === instanceId);
            },
        }),
        {
            name: "pm-dashboard-instances-store", // LocalStorage key
        }
    )
);
