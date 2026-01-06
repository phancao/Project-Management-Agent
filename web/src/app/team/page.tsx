'use client';

import { Suspense, useState } from 'react';
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PMHeader } from "../pm/components/pm-header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
// @ts-expect-error - Direct import
import Users from "lucide-react/dist/esm/icons/users";
// @ts-expect-error - Direct import
import BarChart3 from "lucide-react/dist/esm/icons/bar-chart-3";
// @ts-expect-error - Direct import
import Clock from "lucide-react/dist/esm/icons/clock";
// @ts-expect-error - Direct import
import Settings from "lucide-react/dist/esm/icons/settings";
import { TeamOverview } from "./components/team-overview";
import { TeamMembers } from "./components/team-members";
import { MemberMatrix } from "./components/member-matrix";
import { TeamTimesheets } from "./components/team-timesheets";
import { PMLoadingProvider } from "../pm/context/pm-loading-context";
import { PMLoadingManager } from "../pm/components/pm-loading-manager";
import { TeamDataProvider } from "./context/team-data-context";
import { TeamPageLoadingOverlay } from "./components/team-page-loading-overlay";

// Create a client
const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
            retry: 1,
        },
    },
});

export default function TeamPage() {
    const [activeTab, setActiveTab] = useState("overview");

    return (
        <Suspense fallback={<div className="flex h-screen w-screen items-center justify-center">Loading...</div>}>
            <QueryClientProvider client={queryClient}>
                <PMLoadingProvider>
                    <PMLoadingManager />
                    <TeamDataProvider>
                        <TeamPageLoadingOverlay />
                        <div className="min-h-screen bg-white dark:bg-gray-950">
                            <PMHeader />
                            <div className="pt-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto pb-12">
                                <div className="flex items-center gap-3 mb-8">
                                    <div className="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg">
                                        <Users className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
                                    </div>
                                    <div>
                                        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Team Management</h1>
                                        <p className="text-sm text-gray-500 dark:text-gray-400">Manage capacity, assignments, and time logs.</p>
                                    </div>
                                </div>

                                <Tabs defaultValue="overview" value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                                    <TabsList className="bg-gray-100 dark:bg-gray-900 p-1 rounded-xl">
                                        <TabsTrigger value="overview" className="rounded-lg data-[state=active]:bg-white dark:data-[state=active]:bg-gray-800 data-[state=active]:shadow-sm">
                                            <BarChart3 className="w-4 h-4 mr-2" />
                                            Overview
                                        </TabsTrigger>
                                        <TabsTrigger value="members" className="rounded-lg data-[state=active]:bg-white dark:data-[state=active]:bg-gray-800 data-[state=active]:shadow-sm">
                                            <Users className="w-4 h-4 mr-2" />
                                            Teams
                                        </TabsTrigger>
                                        <TabsTrigger value="assignments" className="rounded-lg data-[state=active]:bg-white dark:data-[state=active]:bg-gray-800 data-[state=active]:shadow-sm">
                                            <BarChart3 className="w-4 h-4 mr-2" />
                                            Assignments
                                        </TabsTrigger>
                                        <TabsTrigger value="timesheets" className="rounded-lg data-[state=active]:bg-white dark:data-[state=active]:bg-gray-800 data-[state=active]:shadow-sm">
                                            <Clock className="w-4 h-4 mr-2" />
                                            Timesheets
                                        </TabsTrigger>
                                        <TabsTrigger value="settings" className="rounded-lg data-[state=active]:bg-white dark:data-[state=active]:bg-gray-800 data-[state=active]:shadow-sm">
                                            <Settings className="w-4 h-4 mr-2" />
                                            Settings
                                        </TabsTrigger>
                                    </TabsList>

                                    <TabsContent value="overview" className="space-y-6 animate-in fade-in-50 duration-300">
                                        <TeamOverview />
                                    </TabsContent>

                                    <TabsContent value="members" className="space-y-6 animate-in fade-in-50 duration-300">
                                        <TeamMembers />
                                    </TabsContent>

                                    <TabsContent value="assignments" className="space-y-6 animate-in fade-in-50 duration-300">
                                        <MemberMatrix />
                                    </TabsContent>

                                    <TabsContent value="timesheets" className="space-y-6 animate-in fade-in-50 duration-300">
                                        <TeamTimesheets />
                                    </TabsContent>

                                    <TabsContent value="settings" className="space-y-6 animate-in fade-in-50 duration-300">
                                        <div className="p-8 text-center text-gray-500 border-2 border-dashed rounded-xl">
                                            Settings coming soon...
                                        </div>
                                    </TabsContent>
                                </Tabs>
                            </div>
                        </div>
                    </TeamDataProvider>
                </PMLoadingProvider>
            </QueryClientProvider>
        </Suspense>
    );
}
