"use client";

import { useMemo } from "react";
import {
    ComposedChart,
    Bar,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    ReferenceLine
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { useTheme } from "next-themes";

interface CapacityChartProps {
    data: Array<{
        week: string;
        capacity: number;
        [key: string]: string | number; // Project IDs as keys
    }>;
    projects: Array<{
        id: string;
        name: string;
        color: string;
    }>;
    totalCapacity: number;
}

const CapacityChart = ({ data, projects, totalCapacity }: CapacityChartProps) => {
    const { theme } = useTheme();
    const isDark = theme === "dark";

    const projectBars = useMemo(() => {
        return projects.map((project) => (
            <Bar
                key={project.id}
                dataKey={project.id}
                name={project.name}
                stackId="a"
                fill={project.color}
                radius={[0, 0, 0, 0]}
                maxBarSize={50}
            />
        ));
    }, [projects]);

    return (
        <Card>
            <CardHeader>
                <CardTitle>Resource Demand vs Capacity</CardTitle>
                <CardDescription>
                    Estimated hours per week compared to total team capacity ({totalCapacity}h)
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="h-[400px] w-full overflow-hidden">
                    <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart
                            data={data}
                            margin={{
                                top: 20,
                                right: 20,
                                bottom: 20,
                                left: 20,
                            }}
                        >
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={isDark ? "#374151" : "#e5e7eb"} />
                            <XAxis
                                dataKey="week"
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: isDark ? "#9ca3af" : "#6b7280", fontSize: 12 }}
                                dy={10}
                            />
                            <YAxis
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: isDark ? "#9ca3af" : "#6b7280", fontSize: 12 }}
                                unit="h"
                            />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: isDark ? "#1f2937" : "#ffffff",
                                    borderColor: isDark ? "#374151" : "#e5e7eb",
                                    borderRadius: "0.5rem",
                                    color: isDark ? "#f3f4f6" : "#111827",
                                }}
                                itemStyle={{ color: isDark ? "#d1d5db" : "#374151" }}
                            />
                            {/* Legend removed to prevent layout break with many projects */}

                            {/* Capacity Line */}
                            <Line
                                type="monotone"
                                dataKey="capacity"
                                name="Total Capacity"
                                stroke="#6366f1" // Indigo-500
                                strokeWidth={2}
                                strokeDasharray="5 5"
                                dot={false}
                            />

                            {/* Reference Line for Max Capacity Highlight */}
                            <ReferenceLine y={totalCapacity} stroke="red" strokeDasharray="3 3" opacity={0.5} />

                            {projectBars}
                        </ComposedChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
};

export { CapacityChart };
