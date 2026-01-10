"use client";

import { useEffect, useState, useMemo, use } from 'react';
import { Clock, Download, Share2, Filter, ArrowLeft, FolderKanban } from "lucide-react";
import { notFound } from 'next/navigation';
import Link from 'next/link';
import { format, startOfMonth, endOfMonth } from 'date-fns';
import type { DateRange } from 'react-day-picker';
import { WorkspaceLoading } from '~/components/ui/workspace-loading';

import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { Button } from "~/components/ui/button";
import { EfficiencyDashboard } from '~/components/efficiency/efficiency-dashboard';
import { type MemberPeriod } from '~/components/efficiency/member-duration-manager';


import { listTasks, type PMTask } from '~/core/api/pm/tasks';
import { listTimeEntries, type PMTimeEntry } from '~/core/api/pm/time-entries';
import { useProjects } from '~/core/api/hooks/pm/use-projects'; // To get project name
import { useTeamUsers } from '~/app/team/context/team-data-context'; // To get members

// We can reuse useTeamUsers if we wrap this page in TeamDataContext? 
// Or just fetch users directly. useTeamUsers depends on Context.
// Better to fetch users independently or assume global context? 
// The TeamDataContext is at `app/team/layout.tsx`. Projects are outside.
// So we need to fetch users. Let's use `listUsers` directly if available.
import { listUsers, type PMUser } from '~/core/api/pm/users';

export default function ProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
    const resolvedParams = use(params);
    const projectId = decodeURIComponent(resolvedParams.id);
    const { projects, loading: projectsLoading } = useProjects();

    // Derived Project State
    const project = useMemo(() => {
        return projects.find(p => p.id === projectId);
    }, [projects, projectId]);

    // Data State
    const [activeTab, setActiveTab] = useState("overview");
    const [tasks, setTasks] = useState<PMTask[]>([]);
    const [users, setUsers] = useState<PMUser[]>([]);
    const [timeEntries, setTimeEntries] = useState<PMTimeEntry[]>([]);
    const [isLoadingData, setIsLoadingData] = useState(false);

    // Date Range for Efficiency (Local State here so we can fetch when it changes)
    const [dateRange, setDateRange] = useState<DateRange | undefined>({
        from: startOfMonth(new Date()),
        to: new Date(),
    });

    // Member Active Periods (Persistence)
    const [activePeriods, setActivePeriods] = useState<Record<string, MemberPeriod[]>>({});

    // Load from localStorage
    useEffect(() => {
        if (!resolvedParams.id) return;
        try {
            const saved = localStorage.getItem(`ee-durations-project-${resolvedParams.id}`);
            if (saved) {
                const parsed = JSON.parse(saved);
                const hydrated: Record<string, MemberPeriod[]> = {};

                Object.keys(parsed).forEach(key => {
                    hydrated[key] = parsed[key].map((item: any) => {
                        // Migration: Handle old DateRange format vs new MemberPeriod format
                        const isOldFormat = item.from || item.to; // Old format was just the DateRange object

                        if (isOldFormat && !item.range) {
                            return {
                                range: {
                                    from: item.from ? new Date(item.from) : undefined,
                                    to: item.to ? new Date(item.to) : undefined
                                },
                                allocation: 100
                            };
                        } else {
                            // New format
                            return {
                                range: {
                                    from: item.range?.from ? new Date(item.range.from) : undefined,
                                    to: item.range?.to ? new Date(item.range.to) : undefined
                                },
                                allocation: item.allocation || 100
                            };
                        }
                    });
                });
                setActivePeriods(hydrated);
            }
        } catch (e) {
            console.error("Failed to load active periods", e);
        }
    }, [resolvedParams.id]);

    const handleActivePeriodsChange = (periods: Record<string, MemberPeriod[]>) => {
        setActivePeriods(periods);
        if (resolvedParams.id) {
            localStorage.setItem(`ee-durations-project-${resolvedParams.id}`, JSON.stringify(periods));
        }
    };

    // Fetch Users on Mount (Base Data)
    useEffect(() => {
        const loadUsers = async () => {
            // Only set loading if we don't have users yet? 
            // Better to keep simple loading state logic or split it.
            if (users.length === 0) setIsLoadingData(true);
            try {
                const fetchedUsers = await listUsers();
                setUsers(fetchedUsers);
            } catch (error) {
                console.error("Failed to load users", error);
            } finally {
                if (users.length === 0) setIsLoadingData(false);
            }
        };

        void loadUsers();
    }, []); // Run once on mount

    // Fetch Project Data (Tasks & Time Entries) when Date Range or Project Changes
    useEffect(() => {
        const loadProjectData = async () => {
            if (!projectId || !dateRange?.from || !dateRange?.to) return;

            setIsLoadingData(true);
            try {
                const sDate = format(dateRange.from, 'yyyy-MM-dd');
                const eDate = format(dateRange.to, 'yyyy-MM-dd');

                // Parallel fetch with date filters
                const [fetchedTasks, fetchedEntries] = await Promise.all([
                    listTasks({
                        project_id: projectId,
                        startDate: sDate,
                        endDate: eDate
                    }),
                    listTimeEntries({
                        projectId: projectId,
                        startDate: sDate,
                        endDate: eDate
                    })
                ]);

                setTasks(fetchedTasks);
                setTimeEntries(fetchedEntries);

            } catch (error) {
                console.error("Failed to load project data", error);
            } finally {
                setIsLoadingData(false);
            }
        };

        void loadProjectData();
    }, [projectId, dateRange]); // Re-run when project or date changes




    if (projectsLoading || isLoadingData) {
        return (
            <WorkspaceLoading
                title="Loading Project"
                subtitle="Fetching project data..."
                items={[
                    { label: "Project Details", isLoading: projectsLoading },
                    { label: "Tasks & Time Entries", isLoading: isLoadingData },
                ]}
                icon={<FolderKanban className="w-6 h-6 text-white" />}
                height="h-screen"
            />
        );
    }

    if (!project) {
        return <div>Project not found</div>;
    }

    return (
        <div className="min-h-screen bg-white text-gray-900 dark:bg-gray-950 dark:text-gray-100 font-sans selection:bg-indigo-100 dark:selection:bg-indigo-900/30">
            {/* Header */}
            <div className="border-b border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-950/80 backdrop-blur-md sticky top-0 z-20">
                <div className="container mx-auto max-w-7xl px-4 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link href="/projects" className="p-2 -ml-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
                            <ArrowLeft className="w-5 h-5" />
                        </Link>
                        <div className="text-4xl mb-4">📊</div>
                        <h3 className="text-lg font-medium text-gray-900 text-center">Project Overview</h3>
                    </div>
                </div>
            </div>

            <main className="container mx-auto max-w-7xl px-4 py-8">
                <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                    <TabsList>
                        <TabsTrigger value="overview">Overview</TabsTrigger>
                        <TabsTrigger value="efficiency">Efficiency</TabsTrigger>
                    </TabsList>

                    <TabsContent value="overview">
                        <div className="text-center py-12">
                            <p className="text-gray-500">
                                Task lists and sprint plans will appear here.
                            </p>
                            <p className="mt-4 text-sm text-gray-400">
                                (This is a placeholder for the default project view)
                            </p>
                        </div>
                    </TabsContent>

                    <TabsContent value="efficiency" className="mt-0">
                        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
                            <EfficiencyDashboard
                                // Filter members to "Project Team" (active in this project or assigned to tasks)
                                members={users.filter(u => tasks.some(t => t.assignee_id === u.id))}
                                tasks={tasks}
                                timeEntries={timeEntries}
                                isLoading={isLoadingData}
                                dateRange={dateRange}
                                onDateRangeChange={setDateRange}
                                activePeriods={activePeriods}
                                onActivePeriodsChange={handleActivePeriodsChange}
                                title="Project Efficiency"
                            />
                        </div>
                    </TabsContent>
                </Tabs>
            </main>
        </div >
    );
}
