// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useEffect, useState, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    Legend,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import { format, startOfWeek, endOfWeek, eachWeekOfInterval, parseISO } from "date-fns";

import { Card } from "~/components/ui/card";
import { WorkspaceLoading } from "~/components/ui/workspace-loading";
import { listTimeEntries, type PMTimeEntry } from "~/core/api/pm/time-entries";
import { listUsers, type PMUser } from "~/core/api/pm/users";

// Color palette for team members
const MEMBER_COLORS = [
    "#3b82f6", // blue
    "#10b981", // emerald
    "#f59e0b", // amber
    "#ef4444", // red
    "#8b5cf6", // violet
    "#ec4899", // pink
    "#06b6d4", // cyan
    "#84cc16", // lime
    "#f97316", // orange
    "#6366f1", // indigo
];

// Color palette for activity types
const ACTIVITY_COLORS = [
    "#22c55e", // green
    "#3b82f6", // blue
    "#f59e0b", // amber
    "#ef4444", // red
    "#8b5cf6", // violet
    "#ec4899", // pink
    "#14b8a6", // teal
    "#f97316", // orange
];

interface WeeklyWorklogData {
    week: string;
    weekLabel: string;
    [memberId: string]: number | string;
}

export function WorklogsView({ configuredMemberIds, instanceId }: { configuredMemberIds?: string[]; instanceId?: string }) {
    const searchParams = useSearchParams();
    const projectId = searchParams?.get("project");

    const [timeEntries, setTimeEntries] = useState<PMTimeEntry[]>([]);
    const [users, setUsers] = useState<PMUser[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Fetch data
    useEffect(() => {
        // If neither project nor members are selected, we might want to show a global view or prompt?
        // User requested "global query" support, so we proceed.

        const loadData = async () => {
            setIsLoading(true);
            setError(null);

            try {
                // Fetch time entries (last 3 months by default)
                const endDate = new Date();
                const startDate = new Date();
                startDate.setMonth(startDate.getMonth() - 3); // Default 3 months

                const fetchOptions: any = {
                    startDate: format(startDate, "yyyy-MM-dd"),
                    endDate: format(endDate, "yyyy-MM-dd"),
                };

                // Filter Strategy:
                // 1. If members are configured, filter by them (ignore project scope to show their cross-project work? Or implicit intersection?)
                //    User said: "don't querry using Project ID by default. It should querry from each members or global"
                //    So we prefer Member IDs.
                if (configuredMemberIds && configuredMemberIds.length > 0) {
                    fetchOptions.userIds = configuredMemberIds;
                } else if (projectId) {
                    // 2. If no specific members, fall back to Project scope
                    fetchOptions.projectId = projectId;
                }
                // 3. If neither, it fetches GLOBAL entries (as requested)

                const [entries, userList] = await Promise.all([
                    listTimeEntries(fetchOptions),
                    listUsers(),
                ]);

                setTimeEntries(entries);
                setUsers(userList);
            } catch (err) {
                setError(err instanceof Error ? err.message : "Failed to load worklogs");
            } finally {
                setIsLoading(false);
            }
        };

        void loadData();
    }, [projectId, configuredMemberIds]);

    // Create user id → name/color mapping
    const userMap = useMemo(() => {
        const map: Record<string, { name: string; color: string }> = {};
        users.forEach((user, index) => {
            map[user.id] = {
                name: user.name || user.email || `User ${user.id}`,
                color: MEMBER_COLORS[index % MEMBER_COLORS.length] || "#888888",
            };
        });
        return map;
    }, [users]);

    // Get unique member IDs from time entries, OR use configured members
    const activeMemberIds = useMemo(() => {
        // If explicitly configured, use those (and only those)
        if (configuredMemberIds && configuredMemberIds.length > 0) {
            return configuredMemberIds;
        }

        // Default: Auto-detect from time entries
        const ids = new Set<string>();
        timeEntries.forEach((entry) => {
            if (entry.user_id) ids.add(entry.user_id);
        });
        return Array.from(ids);
    }, [timeEntries, configuredMemberIds]);

    // Aggregate data by week
    const chartData = useMemo(() => {
        if (timeEntries.length === 0) return [];

        // Find date range from entries
        const dates = timeEntries.map((e) => parseISO(e.date));
        const minDate = new Date(Math.min(...dates.map((d) => d.getTime())));
        const maxDate = new Date(Math.max(...dates.map((d) => d.getTime())));

        // Get all weeks in range
        const weeks = eachWeekOfInterval(
            { start: minDate, end: maxDate },
            { weekStartsOn: 1 } // Monday
        );

        // Initialize data structure
        const weeklyData: WeeklyWorklogData[] = weeks.map((weekStart) => {
            const weekEnd = endOfWeek(weekStart, { weekStartsOn: 1 });
            const weekKey = format(weekStart, "yyyy-MM-dd");
            const weekLabel = `${format(weekStart, "MMM d")} - ${format(weekEnd, "MMM d")}`;

            const data: WeeklyWorklogData = { week: weekKey, weekLabel };

            // Initialize all members to 0
            activeMemberIds.forEach((memberId) => {
                data[memberId] = 0;
            });

            return data;
        });

        // Aggregate hours by week and member
        timeEntries.forEach((entry) => {
            const entryDate = parseISO(entry.date);
            const weekStart = startOfWeek(entryDate, { weekStartsOn: 1 });
            const weekKey = format(weekStart, "yyyy-MM-dd");

            const weekData = weeklyData.find((w) => w.week === weekKey);
            if (weekData && entry.user_id) {
                const current = (weekData[entry.user_id] as number) || 0;
                weekData[entry.user_id] = current + entry.hours;
            }
        });

        return weeklyData;
    }, [timeEntries, activeMemberIds]);

    // Calculate totals
    const totalHours = useMemo(() => {
        return timeEntries.reduce((sum, entry) => sum + entry.hours, 0);
    }, [timeEntries]);

    // Aggregate by activity type
    const activityData = useMemo(() => {
        const activityMap: Record<string, number> = {};
        timeEntries.forEach((entry) => {
            const activityName = entry.activity_type || "Unknown";
            activityMap[activityName] = (activityMap[activityName] || 0) + entry.hours;
        });
        return Object.entries(activityMap)
            .map(([name, hours], index) => ({
                name,
                hours,
                percentage: totalHours > 0 ? ((hours / totalHours) * 100).toFixed(1) : "0",
                color: ACTIVITY_COLORS[index % ACTIVITY_COLORS.length],
            }))
            .sort((a, b) => b.hours - a.hours);
    }, [timeEntries, totalHours]);

    // Loading state
    if (isLoading) {
        return (
            <WorkspaceLoading
                title="Loading Worklogs"
                subtitle="Aggregating time entries..."
                items={[
                    { label: "Time Entries", isLoading: true },
                    { label: "Team Members", isLoading: true },
                ]}
            />
        );
    }



    // Error state
    if (error) {
        return (
            <div className="space-y-6 p-6">
                <Card className="p-6 text-center">
                    <div className="mx-auto max-w-md space-y-4">
                        <div className="flex justify-center">
                            <div className="rounded-full bg-red-100 p-3 dark:bg-red-900/30">
                                <span className="text-2xl">📊</span>
                            </div>
                        </div>
                        <div>
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                                Unable to Load Worklogs Chart
                            </h3>
                            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{error}</p>
                        </div>
                    </div>
                </Card>
            </div>
        );
    }

    // No data
    if (chartData.length === 0) {
        return (
            <div className="space-y-6 p-6">
                <Card className="p-6 text-center">
                    <div className="mx-auto max-w-md space-y-4">
                        <div className="flex justify-center">
                            <div className="rounded-full bg-gray-100 p-3 dark:bg-gray-800">
                                <span className="text-2xl">📊</span>
                            </div>
                        </div>
                        <div>
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                                No Worklogs Found
                            </h3>
                            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                                No time entries were found for this project in the last 3 months.
                            </p>
                        </div>
                    </div>
                </Card>
            </div>
        );
    }

    return (
        <div className="space-y-6 p-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Team Worklogs</h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                        {totalHours.toFixed(1)} hours logged across {activeMemberIds.length} team members
                    </p>
                </div>
            </div>

            {/* Activity Type Pie Chart */}
            {activityData.length > 0 && (
                <Card className="p-6 border-indigo-500/20 dark:border-indigo-500/30 shadow-lg shadow-indigo-500/10 dark:shadow-indigo-500/20 ring-1 ring-indigo-500/10 dark:ring-indigo-500/15">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                        Hours by Activity Type
                    </h3>
                    <div className="flex flex-col lg:flex-row items-center gap-8">
                        <div className="w-full lg:w-1/2">
                            <ResponsiveContainer width="100%" height={280}>
                                <PieChart>
                                    <Pie
                                        data={activityData}
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={60}
                                        outerRadius={100}
                                        fill="#8884d8"
                                        dataKey="hours"
                                        paddingAngle={2}
                                    >
                                        {activityData.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={entry.color} />
                                        ))}
                                    </Pie>
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: "rgba(255, 255, 255, 0.95)",
                                            border: "1px solid #ccc",
                                            borderRadius: "8px",
                                        }}
                                        formatter={(value, name) => [`${Number(value).toFixed(1)} hours`, name]}
                                    />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                        {/* Activity Summary Table */}
                        <div className="w-full lg:w-1/2">
                            <div className="space-y-3">
                                {activityData.map((activity) => (
                                    <div key={activity.name} className="flex items-center gap-3">
                                        <div
                                            className="w-4 h-4 rounded-sm flex-shrink-0"
                                            style={{ backgroundColor: activity.color }}
                                        />
                                        <div className="flex-1 min-w-0">
                                            <div className="flex justify-between items-baseline">
                                                <span className="font-medium text-gray-900 dark:text-white truncate">
                                                    {activity.name}
                                                </span>
                                                <span className="text-sm font-semibold text-gray-700 dark:text-gray-300 ml-2">
                                                    {activity.hours.toFixed(1)}h
                                                </span>
                                            </div>
                                            <div className="mt-1 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                                                <div
                                                    className="h-2 rounded-full transition-all duration-300"
                                                    style={{
                                                        width: `${activity.percentage}%`,
                                                        backgroundColor: activity.color
                                                    }}
                                                />
                                            </div>
                                            <span className="text-xs text-gray-500 dark:text-gray-400">
                                                {activity.percentage}% of total
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </Card>
            )}

            {/* Stacked Bar Chart */}
            <Card className="p-6 border-indigo-500/20 dark:border-indigo-500/30 shadow-lg shadow-indigo-500/10 dark:shadow-indigo-500/20 ring-1 ring-indigo-500/10 dark:ring-indigo-500/15">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                    Weekly Worklogs by Team Member
                </h3>
                <ResponsiveContainer width="100%" height={400}>
                    <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                        <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                        <XAxis
                            dataKey="weekLabel"
                            angle={-45}
                            textAnchor="end"
                            height={80}
                            tick={{ fontSize: 11 }}
                        />
                        <YAxis
                            label={{ value: "Hours", angle: -90, position: "insideLeft" }}
                            tick={{ fontSize: 12 }}
                        />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: "rgba(255, 255, 255, 0.95)",
                                border: "1px solid #ccc",
                                borderRadius: "8px",
                            }}
                            formatter={(value, name) => [
                                `${Number(value ?? 0).toFixed(1)} hours`,
                                userMap[String(name)]?.name || String(name),
                            ]}
                            labelFormatter={(label) => `Week: ${label}`}
                        />
                        <Legend
                            wrapperStyle={{ paddingTop: "20px" }}
                            formatter={(value) => userMap[value]?.name || value}
                        />
                        {activeMemberIds.map((memberId, index) => (
                            <Bar
                                key={memberId}
                                dataKey={memberId}
                                name={memberId}
                                stackId="worklogs"
                                fill={userMap[memberId]?.color || MEMBER_COLORS[index % MEMBER_COLORS.length]}
                            />
                        ))}
                    </BarChart>
                </ResponsiveContainer>
            </Card>

            {/* Summary Table */}
            <Card className="p-6 border-indigo-500/20 dark:border-indigo-500/30 shadow-lg shadow-indigo-500/10 dark:shadow-indigo-500/20 ring-1 ring-indigo-500/10 dark:ring-indigo-500/15">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                    Member Summary
                </h3>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead className="border-b border-gray-200 dark:border-gray-700">
                            <tr className="text-left">
                                <th className="pb-3 font-semibold text-gray-900 dark:text-white">Team Member</th>
                                <th className="pb-3 font-semibold text-gray-900 dark:text-white text-right">
                                    Total Hours
                                </th>
                                <th className="pb-3 font-semibold text-gray-900 dark:text-white text-right">
                                    % of Total
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {activeMemberIds.map((memberId) => {
                                const memberHours = timeEntries
                                    .filter((e) => e.user_id === memberId)
                                    .reduce((sum, e) => sum + e.hours, 0);
                                const percentage = totalHours > 0 ? (memberHours / totalHours) * 100 : 0;

                                return (
                                    <tr key={memberId} className="border-b border-gray-100 dark:border-gray-800">
                                        <td className="py-3">
                                            <div className="flex items-center gap-2">
                                                <div
                                                    className="w-3 h-3 rounded-full"
                                                    style={{ backgroundColor: userMap[memberId]?.color }}
                                                />
                                                <span className="font-medium text-gray-900 dark:text-white">
                                                    {userMap[memberId]?.name || memberId}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="py-3 text-right text-gray-700 dark:text-gray-300">
                                            {memberHours.toFixed(1)}h
                                        </td>
                                        <td className="py-3 text-right text-gray-700 dark:text-gray-300">
                                            {percentage.toFixed(1)}%
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </Card>

            {/* Description */}
            <Card className="p-6 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                    📊 What is the Worklogs Chart?
                </h3>
                <p className="text-sm text-gray-700 dark:text-gray-300">
                    The worklogs chart shows time logged by each team member on a weekly basis. Use this chart to:
                </p>
                <ul className="text-sm text-gray-700 dark:text-gray-300 mt-2 space-y-1 list-disc list-inside">
                    <li>Track team activity and engagement over time</li>
                    <li>Identify workload distribution across the team</li>
                    <li>Spot weeks with low or high activity</li>
                    <li>Ensure fair workload distribution among team members</li>
                </ul>
            </Card>
        </div>
    );
}
