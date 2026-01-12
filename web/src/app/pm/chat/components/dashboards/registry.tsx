import React from "react";
import type { LucideIcon } from "lucide-react";
import { BarChart2, TrendingUp, Users, Activity, Calendar, LineChart, Timer, PieChart, Clock, FileText, CheckSquare, LayoutGrid } from "lucide-react";

export type ConfigType = "string" | "number" | "boolean" | "select";

export interface ConfigField {
    type: ConfigType;
    label: string;
    description?: string;
    options?: string[]; // For 'select' type
    defaultValue?: any;
}

export type PluginType = "page" | "widget";

export interface DashboardPlugin {
    id: string;
    type: PluginType;
    meta: {
        title: string;
        description: string;
        category: "Analytics" | "Team" | "Planning" | "Other";
        icon: LucideIcon;
        author: string;
        version: string;
        size?: { w: number; h: number }; // For widgets: width/height in grid units (1-4)
        shortTitle?: string; // Optional shorter title for tabs
    };
    component: React.ComponentType<{ config: Record<string, any> }>;
    configSchema?: Record<string, ConfigField>; // Schema for user customization
}

// --- Sample Components ---



const SprintStatusWidget = ({ config }: { config: Record<string, any> }) => {
    return (
        <div className="flex flex-col h-full bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-2 text-gray-500 dark:text-gray-400">
                <Activity className="w-4 h-4" />
                <span className="text-xs font-medium uppercase tracking-wider">{config.title || "Sprint Health"}</span>
            </div>
            <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                    <div className="text-3xl font-bold text-gray-900 dark:text-gray-100">On Track</div>
                    <div className="text-sm text-green-600 dark:text-green-500 mt-1">3 days remaining</div>
                </div>
            </div>
        </div>
    );
};

const MemberFocusDashboard = ({ config }: { config: Record<string, any> }) => {
    return (
        <div className="p-6">
            <h2 className="text-2xl font-bold mb-4">{config.title || "Member Focus"}</h2>
            <div className="p-8 border-2 border-dashed rounded-xl bg-gray-50 dark:bg-gray-900/50 flex flex-col items-center justify-center gap-4">
                <Users className="w-12 h-12 text-blue-500" />
                <p className="text-lg text-gray-600 dark:text-gray-300">
                    Analyzing focus breakdown by <strong>{config.grouping || "Day"}</strong>.
                </p>
            </div>
        </div>
    );
};

// --- Icon Map for Remote Resolution ---
// Since we get icon names as strings from the API, we need to map them back to components.
const ICON_MAP: Record<string, LucideIcon> = {
    "TrendingUp": TrendingUp,
    "LineChart": LineChart,
    "FileText": FileText,
    "BarChart2": BarChart2,
    "Clock": Clock,
    "PieChart": PieChart,
    "Calendar": Calendar,
    "Timer": Timer,
    "Users": Users,
    "Activity": Activity,
    "CheckSquare": CheckSquare,
};

// --- Hook for Accessing the Registry ---

import { useState, useEffect } from "react";

export function useStoreRegistry() {
    const [plugins, setPlugins] = useState<DashboardPlugin[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchRegistry() {
            try {
                // Fetch from our new API route
                const res = await fetch('/api/pm-store', { cache: 'no-store' });
                const manifest = await res.json();

                // Hydrate the manifest with actual components and icons
                const hydratedPlugins: DashboardPlugin[] = manifest.map((item: any) => {
                    const Component = COMPONENT_MAP[item.id];
                    if (!Component) console.warn(`Component not found for plugin ${item.id}`);

                    const Icon = ICON_MAP[item.meta.icon] || LayoutGrid; // Default icon

                    return {
                        ...item,
                        meta: {
                            ...item.meta,
                            icon: Icon
                        },
                        component: Component
                    };
                }).filter((p: any) => p.component !== undefined); // Filter out items with missing code

                setPlugins(hydratedPlugins);
            } catch (error) {
                console.error("Failed to fetch plugin registry:", error);
            } finally {
                setLoading(false);
            }
        }

        fetchRegistry();
    }, []);

    const getPlugin = (id: string) => plugins.find(p => p.id === id);

    return { plugins, loading, getPlugin };
}

// --- The Registry (Deprecated/Legacy Export) ---
// We keep this temporarily if needed, but it should be empty or unused.
export const dashboardRegistry: DashboardPlugin[] = [];


// --- Imported Standard Views ---
import { ChartsPanelView } from "../views/charts-panel-view";
import { TimelineView } from "../views/timeline-view";
import { EfficiencyPanelView } from "../views/efficiency-panel-view";
import { TeamAssignmentsView } from "../views/team-assignments-view";
import {
    BurndownPage,
    VelocityPage,
    SprintReportPage,
    CFDPage,
    CycleTimePage,
    WorkDistributionPage,
    IssueTrendPage,
    WorklogsPage
} from "./plugins/standard-charts";

// Map IDs to actual components
export const COMPONENT_MAP: Record<string, React.ComponentType<{ config: Record<string, any> }>> = {
    // Pages
    "team-velocity": VelocityPage,
    "burndown-chart": BurndownPage,
    "sprint-report": SprintReportPage,
    "cfd-chart": CFDPage,
    "cycle-time": CycleTimePage,
    "work-distribution": WorkDistributionPage,
    "issue-trend": IssueTrendPage,
    "worklogs": WorklogsPage,
    "timeline-view": TimelineView,
    "efficiency-view": EfficiencyPanelView,
    "team-view": TeamAssignmentsView,

    // Widgets
    "sprint-health-widget": SprintStatusWidget,

    // Custom Samples
    "member-focus": MemberFocusDashboard,
};

export function getDashboardPlugin(id: string): DashboardPlugin | undefined {
    // This function will now need to be context-aware or replaced by a hook
    // For now, allow it to return a skeletal object if needed, but ideally we move away from synchronous static registry access.
    // However, for backward compatibility during migration, we might need a fallback.
    // Ideally, consumers should use useStoreRegistry() instead of this function.

    // Fallback: If we can't find metadata synchronously, we return undefined.
    return undefined;
}
