import { useState, useEffect } from "react";
import { TeamList } from "./team-list";
import { TeamRoster } from "./team-roster";
import { useTeams } from "~/core/hooks/use-teams";
import { usePrefetchUsers } from "~/core/hooks/use-prefetch-users";
import { Users } from "lucide-react";
import { WorkspaceLoading } from "~/components/ui/workspace-loading";

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
        return (
            <WorkspaceLoading
                title="Loading Teams"
                subtitle="Loading team configurations..."
                items={[
                    { label: "Teams", isLoading: isLoading, count: teams.length },
                    { label: "Users", isLoading: isLoadingUsers, count: users?.length || 0 },
                ]}
                icon={<Users className="w-6 h-6 text-white" />}
            />
        );
    }

    return (
        <div className="flex gap-4 h-[calc(100vh-220px)] min-h-[600px] overflow-hidden">
            <div className="w-[280px] shrink-0 h-full">
                <TeamList
                    teams={teams}
                    selectedTeamId={selectedTeamId}
                    onTeamSelect={setSelectedTeamId}
                    onCreateTeam={addTeam}
                    onDeleteTeam={deleteTeam}
                />
            </div>
            <div className="flex-1 h-full overflow-y-auto pr-2">
                <TeamRoster
                    team={selectedTeam}
                    onAddMember={(userId) => selectedTeamId && addMemberToTeam(selectedTeamId, userId)}
                    onRemoveMember={(userId) => selectedTeamId && removeMemberFromTeam(selectedTeamId, userId)}
                />
            </div>
        </div>
    );
}
