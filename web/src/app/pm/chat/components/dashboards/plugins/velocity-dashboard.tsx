"use client";

import React, { useMemo } from "react";
import { useTasks } from "~/core/api/hooks/pm/use-tasks";
import { useSprints } from "~/core/api/hooks/pm/use-sprints";
import { useProjectData } from "~/app/pm/hooks/use-project-data";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    LineChart,
    Line,
    ReferenceLine,
} from "recharts";
import { Loader2, AlertCircle } from "lucide-react";

interface VelocityDashboardProps {
    config: Record<string, any>;
}

export const VelocityDashboard = ({ config }: VelocityDashboardProps) => {
    const { projectIdForData: projectId } = useProjectData();
    const { tasks, loading: tasksLoading } = useTasks(projectId || undefined);
    const { sprints, loading: sprintsLoading } = useSprints(projectId || "");

    const chartType = config.chartType || "Bar";
    const daysHistory = config.days || 90; // Default to last 90 days
    const showTrend = config.showTrend !== false;
    const metricLabel = config.metric || "Points"; // Could be Hours or Points

    const data = useMemo(() => {
        if (!tasks.length || !sprints.length) return [];

        // Filter relevant sprints (Completed or Current)
        // For Velocity, we usually mostly care about 'closed' sprints
        const relevantSprints = sprints
            .filter((s) => s.status === "closed" || s.status === "active")
            .sort((a, b) => new Date(a.start_date || "").getTime() - new Date(b.start_date || "").getTime());

        // Map Tasks to Sprints
        const sprintMap = new Map<string, { name: string; total: number; completed: number }>();

        relevantSprints.forEach((sprint) => {
            sprintMap.set(sprint.id, { name: sprint.name, total: 0, completed: 0 });
        });

        tasks.forEach((task) => {
            if (!task.sprint_id || !sprintMap.has(task.sprint_id)) return;

            const effort = task.estimated_hours || 0; // Using estimated_hours as proxy for points
            const entry = sprintMap.get(task.sprint_id)!;

            entry.total += effort;
            if (task.status === "Done" || task.status === "Closed" || task.status === "Resolved") {
                entry.completed += effort;
            }
        });

        return Array.from(sprintMap.values());
    }, [tasks, sprints]);

    const averageVelocity = useMemo(() => {
        if (data.length === 0) return 0;
        const totalCompleted = data.reduce((acc, curr) => acc + curr.completed, 0);
        return Math.round(totalCompleted / data.length);
    }, [data]);

    if (tasksLoading || sprintsLoading) {
        return (
            <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                <Loader2 className="w-8 h-8 animate-spin mb-2" />
                <p>Loading project data...</p>
            </div>
        );
    }

    if (!projectId) {
        return (
            <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                <AlertCircle className="w-8 h-8 mb-2" />
                <p>Please select a project to view velocity.</p>
            </div>
        );
    }

    if (data.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                <p>No sprint data found for this project.</p>
                <p className="text-sm mt-2">Ensure you have created sprints and assigned tasks.</p>
            </div>
        );
    }

    return (
        <div className="p-4 h-full flex flex-col">
            <div className="mb-4">
                <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">{config.title || "Team Velocity"}</h2>
                <div className="flex items-center gap-4 text-sm text-gray-500 mt-1">
                    <span className="bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 px-2 py-0.5 rounded-full">Avg: {averageVelocity} {metricLabel}</span>
                    <span>{data.length} Sprints</span>
                </div>
            </div>

            <div className="flex-1 min-h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    {chartType === "Line" ? (
                        <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 40 }}>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                            <XAxis dataKey="name" angle={-45} textAnchor="end" height={60} />
                            <YAxis />
                            <Tooltip
                                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                            />
                            <Legend verticalAlign="top" />
                            <Line type="monotone" dataKey="completed" name={`Completed (${metricLabel})`} stroke="#8884d8" strokeWidth={2} activeDot={{ r: 8 }} />
                            <Line type="monotone" dataKey="total" name={`Committed (${metricLabel})`} stroke="#82ca9d" strokeDasharray="5 5" />
                            {showTrend && <ReferenceLine y={averageVelocity} label="Avg" stroke="red" strokeDasharray="3 3" opacity={0.5} />}
                        </LineChart>
                    ) : (
                        <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 40 }}>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                            <XAxis dataKey="name" angle={-45} textAnchor="end" height={60} />
                            <YAxis />
                            <Tooltip
                                cursor={{ fill: 'transparent' }}
                                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                            />
                            <Legend verticalAlign="top" />
                            <Bar dataKey="completed" name={`Completed (${metricLabel})`} fill="#8884d8" radius={[4, 4, 0, 0]} />
                            <Bar dataKey="total" name={`Committed (${metricLabel})`} fill="#82ca9d" radius={[4, 4, 0, 0]} opacity={0.3} />
                            {showTrend && <ReferenceLine y={averageVelocity} label="Avg" stroke="#ff7300" strokeDasharray="3 3" />}
                        </BarChart>
                    )}
                </ResponsiveContainer>
            </div>
        </div>
    );
};
