import { useState, useEffect } from "react";
import { TeamList } from "./team-list";
import { TeamRoster } from "./team-roster";
import { useTeams } from "~/core/hooks/use-teams";
import { usePrefetchUsers } from "~/core/hooks/use-prefetch-users";
import { Loader2, Users, Briefcase } from "lucide-react";

export function TeamMembers() {
    const { teams, isLoading, addTeam, deleteTeam, addMemberToTeam, removeMemberFromTeam } = useTeams();
    const [selectedTeamId, setSelectedTeamId] = useState("");

    // Prefetch users at component mount so they're cached for search
    const { isLoading: isLoadingUsers, data: users } = usePrefetchUsers();

    // Auto-select first team on load if none selected
    useEffect(() => {
        if (!isLoading && teams.length > 0 && !selectedTeamId) {
            setSelectedTeamId(teams[0]?.id || "");
        }
    }, [teams, isLoading, selectedTeamId]);

    const selectedTeam = teams.find(t => t.id === selectedTeamId);

    if (isLoading || isLoadingUsers) {
        const loadingItems = [
            { label: "Teams", isLoading: isLoading, count: teams.length },
            { label: "Users", isLoading: isLoadingUsers, count: users?.length || 0 },
        ];
        const completedCount = loadingItems.filter(item => !item.isLoading).length;
        const progressPercent = Math.round((completedCount / loadingItems.length) * 100);

        return (
            <div className="h-full w-full flex items-center justify-center bg-muted/20 p-4">
                <div className="bg-card border rounded-xl shadow-lg p-5 w-full max-w-sm">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg flex items-center justify-center">
                            <Users className="w-5 h-5 text-indigo-600 dark:text-indigo-400 animate-pulse" />
                        </div>
                        <div>
                            <h3 className="text-sm font-semibold">Loading Teams</h3>
                            <p className="text-xs text-muted-foreground">{progressPercent}% complete</p>
                        </div>
                    </div>

                    <div className="w-full h-1.5 bg-muted rounded-full mb-4 overflow-hidden">
                        <div
                            className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500 ease-out"
                            style={{ width: `${progressPercent}%` }}
                        />
                    </div>

                    <div className="space-y-2">
                        {loadingItems.map((item, index) => (
                            <div key={index} className="flex items-center justify-between py-1.5 px-2 bg-muted/30 rounded-md">
                                <div className="flex items-center gap-2">
                                    {index === 0 ? <Briefcase className="w-3.5 h-3.5 text-indigo-500" /> : <Users className="w-3.5 h-3.5 text-purple-500" />}
                                    <span className="text-xs font-medium">{item.label}</span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <span className={`text-xs font-mono tabular-nums ${item.isLoading ? 'text-indigo-600 dark:text-indigo-400' : 'text-green-600 dark:text-green-400'}`}>
                                        {item.isLoading ? (item.count > 0 ? item.count : "...") : item.count}
                                    </span>
                                    {item.isLoading ? (
                                        <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-500" />
                                    ) : (
                                        <div className="w-3.5 h-3.5 text-green-500">✓</div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>

                    <p className="text-[10px] text-muted-foreground mt-3 text-center">
                        Loading team configurations...
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-12 gap-6 h-[700px]">
            <div className="col-span-3 h-full">
                <TeamList
                    teams={teams}
                    selectedTeamId={selectedTeamId}
                    onTeamSelect={setSelectedTeamId}
                    onCreateTeam={addTeam}
                    onDeleteTeam={deleteTeam}
                />
            </div>
            <div className="col-span-9 h-full overflow-y-auto">
                <TeamRoster
                    team={selectedTeam}
                    onAddMember={(userId) => selectedTeamId && addMemberToTeam(selectedTeamId, userId)}
                    onRemoveMember={(userId) => selectedTeamId && removeMemberFromTeam(selectedTeamId, userId)}
                />
            </div>
        </div>
    );
}
