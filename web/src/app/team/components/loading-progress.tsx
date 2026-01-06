"use client";

// @ts-expect-error - Direct import
import Loader2 from "lucide-react/dist/esm/icons/loader-2";
// @ts-expect-error - Direct import
import CheckCircle from "lucide-react/dist/esm/icons/check-circle";
// @ts-expect-error - Direct import  
import Users from "lucide-react/dist/esm/icons/users";
// @ts-expect-error - Direct import
import ListTodo from "lucide-react/dist/esm/icons/list-todo";
// @ts-expect-error - Direct import
import Clock from "lucide-react/dist/esm/icons/clock";
// @ts-expect-error - Direct import
import FolderKanban from "lucide-react/dist/esm/icons/folder-kanban";
// @ts-expect-error - Direct import
import Folder from "lucide-react/dist/esm/icons/folder";

interface LoadingProgressProps {
    isLoadingUsers: boolean;
    isLoadingTasks: boolean;
    isLoadingTimeEntries: boolean;
    isLoadingTeams?: boolean;
    isLoadingProjects?: boolean;
    usersCount?: number;
    tasksCount?: number;
    timeEntriesCount?: number;
    teamsCount?: number;
    projectsCount?: number;
}

interface LoadingItemProps {
    label: string;
    isLoading: boolean;
    count: number;
    icon: React.ReactNode;
}

function LoadingItem({ label, isLoading, count, icon }: LoadingItemProps) {
    return (
        <div className="flex items-center gap-3 py-2.5 px-3 bg-muted/30 rounded-lg">
            <div className="w-8 h-8 flex items-center justify-center bg-background rounded-lg shadow-sm">
                {icon}
            </div>
            <div className="flex-1">
                <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{label}</span>
                    <div className="flex items-center gap-2">
                        {isLoading ? (
                            <span className="text-xs font-mono text-blue-600 dark:text-blue-400 tabular-nums">
                                {count > 0 ? count : "..."}
                            </span>
                        ) : (
                            <span className="text-xs font-mono text-green-600 dark:text-green-400 tabular-nums">
                                {count}
                            </span>
                        )}
                        {isLoading ? (
                            <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                        ) : (
                            <CheckCircle className="w-4 h-4 text-green-500" />
                        )}
                    </div>
                </div>
                <p className="text-xs text-muted-foreground">
                    {isLoading
                        ? (count > 0 ? `Loading... ${count} items so far` : "Fetching from providers...")
                        : `${count} items loaded`
                    }
                </p>
            </div>
        </div>
    );
}

export function LoadingProgress({
    isLoadingUsers,
    isLoadingTasks,
    isLoadingTimeEntries,
    isLoadingTeams = false,
    isLoadingProjects = false,
    usersCount = 0,
    tasksCount = 0,
    timeEntriesCount = 0,
    teamsCount = 0,
    projectsCount = 0,
}: LoadingProgressProps) {
    const allComplete = !isLoadingUsers && !isLoadingTasks && !isLoadingTimeEntries && !isLoadingTeams && !isLoadingProjects;

    // Calculate overall progress
    const loadingItems = [isLoadingTeams, isLoadingProjects, isLoadingUsers, isLoadingTasks, isLoadingTimeEntries];
    const completedCount = loadingItems.filter(l => !l).length;
    const totalCount = loadingItems.length;
    const progressPercent = Math.round((completedCount / totalCount) * 100);

    if (allComplete) {
        return null; // Don't show when all complete
    }

    return (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center">
            <div className="bg-card border rounded-xl shadow-2xl p-6 w-[420px]">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold flex items-center gap-2">
                        <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                            <Loader2 className="w-5 h-5 animate-spin text-blue-600 dark:text-blue-400" />
                        </div>
                        Loading Team Data
                    </h2>
                    <span className="text-sm font-mono text-muted-foreground">
                        {progressPercent}%
                    </span>
                </div>

                {/* Progress bar */}
                <div className="w-full h-2 bg-muted rounded-full mb-4 overflow-hidden">
                    <div
                        className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-500 ease-out"
                        style={{ width: `${progressPercent}%` }}
                    />
                </div>

                <div className="space-y-2">
                    <LoadingItem
                        label="Teams"
                        isLoading={isLoadingTeams}
                        count={teamsCount}
                        icon={<FolderKanban className="w-4 h-4 text-purple-500" />}
                    />
                    <LoadingItem
                        label="Projects"
                        isLoading={isLoadingProjects}
                        count={projectsCount}
                        icon={<Folder className="w-4 h-4 text-amber-500" />}
                    />
                    <LoadingItem
                        label="Users"
                        isLoading={isLoadingUsers}
                        count={usersCount}
                        icon={<Users className="w-4 h-4 text-blue-500" />}
                    />
                    <LoadingItem
                        label="Tasks / Work Packages"
                        isLoading={isLoadingTasks}
                        count={tasksCount}
                        icon={<ListTodo className="w-4 h-4 text-green-500" />}
                    />
                    <LoadingItem
                        label="Time Entries"
                        isLoading={isLoadingTimeEntries}
                        count={timeEntriesCount}
                        icon={<Clock className="w-4 h-4 text-orange-500" />}
                    />
                </div>

                <p className="text-xs text-muted-foreground mt-4 text-center">
                    Fetching data from PM providers...
                </p>
            </div>
        </div>
    );
}

