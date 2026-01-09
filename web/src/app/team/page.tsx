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
import { LineChart, Timer } from "lucide-react";
import { useTeamDataContext } from "./context/team-data-context";
import { TeamPageLoadingOverlay } from "./components/team-page-loading-overlay";
import { MemberProfileDialog } from "./components/member-profile-dialog";

// Context for member profile dialog
interface MemberProfileContextType {
    openMemberProfile: (memberId: string) => void;
}
const MemberProfileContext = createContext<MemberProfileContextType | null>(null);

export function useMemberProfile() {
    const context = useContext(MemberProfileContext);
    if (!context) {
        throw new Error('useMemberProfile must be used within MemberProfileProvider');
    }
    return context;
}

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

    return (
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
                    Project Assignation
                </TabsTrigger>
                <TabsTrigger value="planning" className="rounded-lg data-[state=active]:bg-white dark:data-[state=active]:bg-gray-800 data-[state=active]:shadow-sm">
                    <LineChart className="w-4 h-4 mr-2" />
                    Planning
                </TabsTrigger>
                <TabsTrigger value="worklogs" className="rounded-lg data-[state=active]:bg-white dark:data-[state=active]:bg-gray-800 data-[state=active]:shadow-sm">
                    <ClipboardList className="w-4 h-4 mr-2" />
                    Worklogs
                </TabsTrigger>
                <TabsTrigger value="efficiency" className="rounded-lg data-[state=active]:bg-white dark:data-[state=active]:bg-gray-800 data-[state=active]:shadow-sm">
                    <Timer className="w-4 h-4 mr-2" />
                    Efficiency (EE)
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

            <TabsContent value="planning" className="space-y-6 animate-in fade-in-50 duration-300">
                <CapacityPlanningView />
            </TabsContent>

            <TabsContent value="worklogs" className="space-y-6 animate-in fade-in-50 duration-300">
                <TeamWorklogs />
            </TabsContent>

            <TabsContent value="efficiency" className="space-y-6 animate-in fade-in-50 duration-300">
                <EfficiencyView />
            </TabsContent>
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
