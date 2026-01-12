import React from "react";
import type { LucideIcon } from "lucide-react";
import { BarChart2, TrendingUp, Users, Activity } from "lucide-react";

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
    };
    component: React.ComponentType<{ config: Record<string, any> }>;
    configSchema?: Record<string, ConfigField>; // Schema for user customization
}

// --- Sample Components ---

import { VelocityDashboard } from "./plugins/velocity-dashboard";

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

// --- The Registry ---

export const dashboardRegistry: DashboardPlugin[] = [
    {
        id: "team-velocity",
        type: "page",
        meta: {
            title: "Team Velocity",
            description: "Analyze team velocity over time (Completed vs Committed).",
            category: "Analytics",
            icon: TrendingUp,
            author: "System",
            version: "1.1.0",
        },
        component: VelocityDashboard,
        configSchema: {
            title: { type: "string", label: "Dashboard Title", defaultValue: "Team Velocity" },
            chartType: { type: "select", label: "Chart Type", options: ["Bar", "Line"], defaultValue: "Bar" },
            showTrend: { type: "boolean", label: "Show Average Trend", defaultValue: true },
            metric: { type: "select", label: "Metric Label", options: ["Points", "Hours"], defaultValue: "Hours" },
        },
    },
    {
        id: "sprint-health-widget",
        type: "widget",
        meta: {
            title: "Sprint Health",
            description: "Quick glance at current sprint status and timeline.",
            category: "Planning",
            icon: Activity,
            author: "System",
            version: "1.0.0",
            size: { w: 1, h: 1 },
        },
        component: SprintStatusWidget,
        configSchema: {
            title: { type: "string", label: "Widget Title", defaultValue: "Sprint Health" },
        },
    },
    {
        id: "member-focus",
        type: "page",
        meta: {
            title: "Member Focus",
            description: "Deep dive into individual member focus time patterns.",
            category: "Team",
            icon: Users,
            author: "System",
            version: "0.5.0",
        },
        component: MemberFocusDashboard,
        configSchema: {
            title: { type: "string", label: "Dashboard Title", defaultValue: "Member Focus" },
            grouping: { type: "select", label: "Group By", options: ["Day", "Week", "Sprint"], defaultValue: "Day" },
        },
    },
];

export function getDashboardPlugin(id: string): DashboardPlugin | undefined {
    return dashboardRegistry.find((p) => p.id === id);
}
