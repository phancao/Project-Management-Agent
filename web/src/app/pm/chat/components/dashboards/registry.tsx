import React from "react";
import { LucideIcon, BarChart2, TrendingUp, Users, Activity } from "lucide-react";

export type ConfigType = "string" | "number" | "boolean" | "select";

export interface ConfigField {
    type: ConfigType;
    label: string;
    description?: string;
    options?: string[]; // For 'select' type
    defaultValue?: any;
}

export interface DashboardPlugin {
    id: string;
    meta: {
        title: string;
        description: string;
        category: "Analytics" | "Team" | "Planning" | "Other";
        icon: LucideIcon;
        author: string;
        version: string;
    };
    component: React.ComponentType<{ config: Record<string, any> }>;
    configSchema?: Record<string, ConfigField>; // Schema for user customization
}

// --- Sample Components ---

const VelocityDashboard = ({ config }: { config: Record<string, any> }) => {
    return (
        <div className="p-6">
            <h2 className="text-2xl font-bold mb-4">{config.title || "Team Velocity"}</h2>
            <div className="p-8 border-2 border-dashed rounded-xl bg-gray-50 dark:bg-gray-900/50 flex flex-col items-center justify-center gap-4">
                <TrendingUp className="w-12 h-12 text-brand" />
                <p className="text-lg text-gray-600 dark:text-gray-300">
                    Viewing <strong>{config.chartType || "Bar"}</strong> chart for <strong>{config.days || 30}</strong> days.
                </p>
                {config.showTrend && <p className="text-sm text-green-600">Trend line enabled</p>}
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
        meta: {
            title: "Team Velocity",
            description: "Analyze team velocity over time with customizable trends.",
            category: "Analytics",
            icon: TrendingUp,
            author: "System",
            version: "1.0.0",
        },
        component: VelocityDashboard,
        configSchema: {
            title: { type: "string", label: "Dashboard Title", defaultValue: "Team Velocity" },
            chartType: { type: "select", label: "Chart Type", options: ["Bar", "Line", "Area"], defaultValue: "Bar" },
            days: { type: "number", label: "History (Days)", defaultValue: 30 },
            showTrend: { type: "boolean", label: "Show Trend Line", defaultValue: true },
        },
    },
    {
        id: "member-focus",
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
