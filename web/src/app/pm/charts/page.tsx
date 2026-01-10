// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { Card } from "~/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { useProjectSummary } from "~/core/api/hooks/pm/use-analytics";
import { useProjects } from "~/core/api/hooks/pm/use-projects";

import { BurndownView } from "../chat/components/views/burndown-view";
import { CFDView } from "../chat/components/views/cfd-view";
import { CycleTimeView } from "../chat/components/views/cycle-time-view";
import { SprintReportView } from "../chat/components/views/sprint-report-view";
import { VelocityView } from "../chat/components/views/velocity-view";
import { PMHeader } from "../components/pm-header";
import { PMLoadingManager } from "../components/pm-loading-manager";
import { PMLoadingProvider } from "../context/pm-loading-context";

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function ChartsPageContent() {
  const searchParams = useSearchParams();
  const projectId = searchParams?.get("project");
  const { projects } = useProjects();
  const activeProject = projects.find(p => p.id === projectId);
  const { data: summary } = useProjectSummary(projectId);
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <PMLoadingProvider>
      <div className="flex min-h-screen flex-col bg-transparent">
        <PMHeader />
        <PMLoadingManager />

        <main className="flex-1 px-6 py-8">
          <div className="mx-auto max-w-7xl">
            {/* Page Header */}
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                Analytics & Charts
              </h1>
              <p className="mt-2 text-gray-600 dark:text-gray-400">
                {activeProject?.name ?? "Select a project"} - Comprehensive project insights and metrics
              </p>
            </div>

            {/* Project Summary Cards */}
            {summary && (
              <div className="mb-8 grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className="p-4">
                  <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Current Sprint</div>
                  <div className="text-xl font-bold text-gray-900 dark:text-white">
                    {summary.current_sprint?.name ?? "No active sprint"}
                  </div>
                  {summary.current_sprint && (
                    <div className="mt-2">
                      <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
                        <span>Progress</span>
                        <span>{summary.current_sprint.progress.toFixed(0)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div
                          className="h-2 rounded-full bg-blue-500"
                          style={{ width: `${summary.current_sprint.progress}%` }}
                        ></div>
                      </div>
                    </div>
                  )}
                </Card>

                <Card className="p-4">
                  <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Average Velocity</div>
                  <div className="text-xl font-bold text-blue-600">
                    {summary.velocity.average.toFixed(1)} pts
                  </div>
                  <div className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                    Latest: {summary.velocity.latest.toFixed(1)} pts
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Completion Rate</div>
                  <div className="text-xl font-bold text-green-600">
                    {summary.overall_stats.completion_rate.toFixed(0)}%
                  </div>
                  <div className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                    {summary.overall_stats.completed_items} / {summary.overall_stats.total_items} items
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Velocity Trend</div>
                  <div className={`text-xl font-bold ${summary.velocity.trend === 'increasing' ? 'text-green-600' : summary.velocity.trend === 'decreasing' ? 'text-red-600' : 'text-gray-600'}`}>
                    {summary.velocity.trend === 'increasing' && '↗ Increasing'}
                    {summary.velocity.trend === 'decreasing' && '↘ Decreasing'}
                    {summary.velocity.trend === 'stable' && '→ Stable'}
                  </div>
                  <div className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                    Team size: {summary.team_size}
                  </div>
                </Card>
              </div>
            )}

            {/* Charts Tabs */}
            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
              <TabsList className="grid w-full grid-cols-6 lg:w-auto lg:inline-grid">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="burndown">Burndown</TabsTrigger>
                <TabsTrigger value="velocity">Velocity</TabsTrigger>
                <TabsTrigger value="sprint-report">Sprint Report</TabsTrigger>
                <TabsTrigger value="cfd">CFD</TabsTrigger>
                <TabsTrigger value="cycle-time">Cycle Time</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-6">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Mini Burndown */}
                  <Card className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Sprint Burndown</h3>
                      <button
                        onClick={() => setActiveTab("burndown")}
                        className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                      >
                        View Details →
                      </button>
                    </div>
                    <div className="h-64">
                      <BurndownView />
                    </div>
                  </Card>

                  {/* Mini Velocity */}
                  <Card className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Team Velocity</h3>
                      <button
                        onClick={() => setActiveTab("velocity")}
                        className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                      >
                        View Details →
                      </button>
                    </div>
                    <div className="h-64">
                      <VelocityView />
                    </div>
                  </Card>
                </div>

                {/* Quick Actions */}
                <Card className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Available Charts</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
                    <button
                      onClick={() => setActiveTab("sprint-report")}
                      className="p-4 text-left border-2 border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-500 dark:hover:border-blue-400 transition-colors"
                    >
                      <div className="text-2xl mb-2">📊</div>
                      <div className="font-semibold text-gray-900 dark:text-white">View Sprint Report</div>
                      <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        Comprehensive sprint summary with insights
                      </div>
                    </button>

                    <button
                      onClick={() => setActiveTab("burndown")}
                      className="p-4 text-left border-2 border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-500 dark:hover:border-blue-400 transition-colors"
                    >
                      <div className="text-2xl mb-2">📉</div>
                      <div className="font-semibold text-gray-900 dark:text-white">Track Burndown</div>
                      <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        Monitor sprint progress and forecast completion
                      </div>
                    </button>

                    <button
                      onClick={() => setActiveTab("velocity")}
                      className="p-4 text-left border-2 border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-500 dark:hover:border-blue-400 transition-colors"
                    >
                      <div className="text-2xl mb-2">⚡</div>
                      <div className="font-semibold text-gray-900 dark:text-white">Analyze Velocity</div>
                      <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        Review team performance and capacity
                      </div>
                    </button>

                    <button
                      onClick={() => setActiveTab("cfd")}
                      className="p-4 text-left border-2 border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-500 dark:hover:border-blue-400 transition-colors"
                    >
                      <div className="text-2xl mb-2">📈</div>
                      <div className="font-semibold text-gray-900 dark:text-white">Cumulative Flow</div>
                      <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        Visualize work flow and identify bottlenecks
                      </div>
                    </button>

                    <button
                      onClick={() => setActiveTab("cycle-time")}
                      className="p-4 text-left border-2 border-gray-200 dark:border-gray-700 rounded-lg hover:border-blue-500 dark:hover:border-blue-400 transition-colors"
                    >
                      <div className="text-2xl mb-2">⏱️</div>
                      <div className="font-semibold text-gray-900 dark:text-white">Cycle Time</div>
                      <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        Track delivery speed and predictability
                      </div>
                    </button>
                  </div>
                </Card>
              </TabsContent>

              <TabsContent value="burndown">
                <BurndownView />
              </TabsContent>

              <TabsContent value="velocity">
                <VelocityView />
              </TabsContent>

              <TabsContent value="sprint-report">
                <SprintReportView />
              </TabsContent>

              <TabsContent value="cfd">
                <CFDView />
              </TabsContent>

              <TabsContent value="cycle-time">
                <CycleTimeView />
              </TabsContent>
            </Tabs>
          </div>
        </main>
      </div>
    </PMLoadingProvider>
  );
}

export default function ChartsPage() {
  return (
    <QueryClientProvider client={queryClient}>
      <ChartsPageContent />
    </QueryClientProvider>
  );
}

