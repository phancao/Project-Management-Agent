import { useState, useEffect } from "react";
import { TeamList } from "./team-list";
import { TeamRoster } from "./team-roster";
import { useTeams } from "~/core/hooks/use-teams";
import { usePrefetchUsers } from "~/core/hooks/use-prefetch-users";

export function TeamMembers() {
    const { teams, isLoading, addTeam, deleteTeam, addMemberToTeam, removeMemberFromTeam } = useTeams();
    const [selectedTeamId, setSelectedTeamId] = useState("");

    // Prefetch users at component mount so they're cached for search
    const { isLoading: isLoadingUsers } = usePrefetchUsers();

    // Auto-select first team on load if none selected
    useEffect(() => {
        if (!isLoading && teams.length > 0 && !selectedTeamId) {
            setSelectedTeamId(teams[0]?.id || "");
        }
    }, [teams, isLoading, selectedTeamId]);

    const selectedTeam = teams.find(t => t.id === selectedTeamId);

    if (isLoading) {
        return <div className="p-8 text-center text-muted-foreground">Loading teams...</div>;
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

