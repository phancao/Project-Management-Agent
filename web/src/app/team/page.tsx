'use client';

import { useState, createContext, useContext } from 'react';
import { PMHeader } from "../pm/components/pm-header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
// @ts-expect-error - Direct import
import Users from "lucide-react/dist/esm/icons/users";
// @ts-expect-error - Direct import
import BarChart3 from "lucide-react/dist/esm/icons/bar-chart-3";
// @ts-expect-error - Direct import
import ClipboardList from "lucide-react/dist/esm/icons/clipboard-list";
import { TeamOverview } from "./components/team-overview";
import { TeamMembers } from "./components/team-members";
import { MemberMatrix } from "./components/member-matrix";
import { TeamWorklogs } from "./components/team-worklogs";
import { CapacityPlanningView } from "./components/capacity-planning";
import { EfficiencyView } from "./components/efficiency-view";
import { LineChart, Timer, Calendar } from "lucide-react";
import Link from "next/link";
import { useTeamDataContext } from "./context/team-data-context";
import { TeamPageLoadingOverlay } from "./components/team-page-loading-overlay";
import { MemberProfileDialog } from "./components/member-profile-dialog";
import { MemberProfileContext } from "./context/member-profile-context";

/**
 * TeamContent renders the tabs only after the initial blocking load is complete.
 * This prevents heavy data (users, tasks) from being fetched during the blocking overlay.
 */
function TeamContent() {
    const [activeTab, setActiveTab] = useState("overview");
    const { isLoading } = useTeamDataContext();

    // Don't render tab content until initial load (Teams/Projects) is complete
    if (isLoading) {
        return null;
    }

    // Render only the active tab's content (lazy loading)
    // This prevents ALL tabs from mounting simultaneously and triggering redundant API calls
    const renderActiveTab = () => {
        switch (activeTab) {
            case "overview":
                return <TeamOverview />;
            case "members":
                return <TeamMembers />;
            case "assignments":
                return <MemberMatrix />;
            case "planning":
                return <CapacityPlanningView />;
            case "worklogs":
                return <TeamWorklogs />;
            case "efficiency":
                return <EfficiencyView />;
            default:
                return <TeamOverview />;
        }
    };

    return (
        <Tabs defaultValue="overview" value={activeTab} onValueChange={setActiveTab} className="space-y-6">
            <TabsList className="bg-transparent p-1 rounded-xl">
                <TabsTrigger value="overview" className="rounded-lg data-[state=active]:bg-brand data-[state=active]:text-white dark:data-[state=active]:bg-brand data-[state=active]:shadow-sm">
                    <BarChart3 className="w-4 h-4 mr-2" />
                    Overview
                </TabsTrigger>
                <TabsTrigger value="members" className="rounded-lg data-[state=active]:bg-brand data-[state=active]:text-white dark:data-[state=active]:bg-brand data-[state=active]:shadow-sm">
                    <Users className="w-4 h-4 mr-2" />
                    Teams
                </TabsTrigger>
                <TabsTrigger value="assignments" className="rounded-lg data-[state=active]:bg-brand data-[state=active]:text-white dark:data-[state=active]:bg-brand data-[state=active]:shadow-sm">
                    <BarChart3 className="w-4 h-4 mr-2" />
                    Project Assignation
                </TabsTrigger>
                <TabsTrigger value="planning" className="rounded-lg data-[state=active]:bg-brand data-[state=active]:text-white dark:data-[state=active]:bg-brand data-[state=active]:shadow-sm">
                    <LineChart className="w-4 h-4 mr-2" />
                    Planning
                </TabsTrigger>
                <TabsTrigger value="worklogs" className="rounded-lg data-[state=active]:bg-brand data-[state=active]:text-white dark:data-[state=active]:bg-brand data-[state=active]:shadow-sm">
                    <ClipboardList className="w-4 h-4 mr-2" />
                    Worklogs
                </TabsTrigger>
                <TabsTrigger value="efficiency" className="rounded-lg data-[state=active]:bg-brand data-[state=active]:text-white dark:data-[state=active]:bg-brand data-[state=active]:shadow-sm">
                    <Timer className="w-4 h-4 mr-2" />
                    Efficiency (EE)
                </TabsTrigger>
            </TabsList>

            <div className="space-y-6 animate-in fade-in-50 duration-300">
                {renderActiveTab()}
            </div>
        </Tabs>
    );
}

export default function TeamPage() {
    // State for member profile dialog
    const [selectedMemberId, setSelectedMemberId] = useState<string | null>(null);
    const [dialogOpen, setDialogOpen] = useState(false);

    const openMemberProfile = (memberId: string) => {
        setSelectedMemberId(memberId);
        setDialogOpen(true);
    };

    return (
        <MemberProfileContext.Provider value={{ openMemberProfile }}>
            <TeamPageLoadingOverlay />
            <div className="min-h-screen bg-transparent">
                <PMHeader />
                <div className="pt-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto pb-12">
                    <div className="flex items-center justify-between mb-8">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg">
                                <Users className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Team Management</h1>
                                <p className="text-sm text-gray-500 dark:text-gray-400">Manage capacity, assignments, and time logs.</p>
                            </div>
                        </div>
                        <Link
                            href="/settings/holidays"
                            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                        >
                            <Calendar className="w-4 h-4" />
                            Holidays
                        </Link>
                    </div>

                    <TeamContent />
                </div>
            </div>

            {/* Member Profile Dialog */}
            <MemberProfileDialog
                memberId={selectedMemberId}
                open={dialogOpen}
                onOpenChange={setDialogOpen}
            />
        </MemberProfileContext.Provider>
    );
}
