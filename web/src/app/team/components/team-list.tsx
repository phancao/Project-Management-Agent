"use client"

import { useState } from "react"
import { Button } from "~/components/ui/button"
// @ts-expect-error - Direct import
import Plus from "lucide-react/dist/esm/icons/plus";
// @ts-expect-error - Direct import
import Users from "lucide-react/dist/esm/icons/users";
// @ts-expect-error - Direct import
import MoreHorizontal from "lucide-react/dist/esm/icons/more-horizontal";
// @ts-expect-error - Direct import
import Settings from "lucide-react/dist/esm/icons/settings";
// @ts-expect-error - Direct import
import Trash2 from "lucide-react/dist/esm/icons/trash-2";
import { Input } from "~/components/ui/input"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "~/components/ui/dialog"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "~/components/ui/dropdown-menu"
import { cn } from "~/lib/utils"
// Import type from hook, not file loop
import type { Team } from "~/core/hooks/use-teams"

interface TeamListProps {
    teams: Team[];
    selectedTeamId: string;
    onTeamSelect: (teamId: string) => void;
    onCreateTeam: (name: string) => void;
    onDeleteTeam: (id: string) => void;
}

export function TeamList({ teams, selectedTeamId, onTeamSelect, onCreateTeam, onDeleteTeam }: TeamListProps) {
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [newTeamName, setNewTeamName] = useState("");
    const [deleteDialogTeam, setDeleteDialogTeam] = useState<Team | null>(null);

    const handleCreateTeam = () => {
        if (!newTeamName.trim()) return;
        onCreateTeam(newTeamName);
        setNewTeamName("");
        setIsCreateOpen(false);
    };

    const handleDeleteClick = (e: React.MouseEvent, team: Team) => {
        e.stopPropagation();
        e.preventDefault();
        // Open the delete confirmation dialog
        setDeleteDialogTeam(team);
    };

    const handleConfirmDelete = () => {
        if (deleteDialogTeam) {
            onDeleteTeam(deleteDialogTeam.id);
            setDeleteDialogTeam(null);
        }
    };

    return (
        <>
            <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900/50 rounded-xl border border-gray-200 dark:border-gray-800">
                <div className="p-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
                    <h3 className="font-semibold text-sm">Teams</h3>
                    <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                        <DialogTrigger asChild>
                            <Button size="icon" variant="ghost" className="h-8 w-8">
                                <Plus className="h-4 w-4" />
                            </Button>
                        </DialogTrigger>
                        <DialogContent>
                            <DialogHeader>
                                <DialogTitle>Create Team</DialogTitle>
                                <DialogDescription>
                                    Add a new team to organize your members.
                                </DialogDescription>
                            </DialogHeader>
                            <div className="py-4">
                                <Input
                                    placeholder="Team Name (e.g. Engineering)"
                                    value={newTeamName}
                                    onChange={(e) => setNewTeamName(e.target.value)}
                                />
                            </div>
                            <DialogFooter>
                                <Button variant="outline" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
                                <Button onClick={handleCreateTeam}>Create Team</Button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>
                </div>
                <div className="flex-1 overflow-y-auto p-2 space-y-1">
                    {teams.map(team => (
                        <div
                            key={team.id}
                            onClick={() => onTeamSelect(team.id)}
                            className={cn(
                                "flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors group",
                                selectedTeamId === team.id
                                    ? "bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700"
                                    : "hover:bg-gray-100 dark:hover:bg-gray-800/50 border border-transparent"
                            )}
                        >
                            <div className="flex items-center gap-3">
                                <div className={cn(
                                    "flex items-center justify-center w-8 h-8 rounded-full text-xs font-medium",
                                    selectedTeamId === team.id ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300" : "bg-gray-200 dark:bg-gray-800 text-gray-500"
                                )}>
                                    {team.name.substring(0, 2).toUpperCase()}
                                </div>
                                <div>
                                    <div className="font-medium text-sm">{team.name}</div>
                                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                                        <Users className="w-3 h-3" />
                                        {team.memberIds?.length || 0} members
                                    </div>
                                </div>
                            </div>
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button size="icon" variant="ghost" className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <MoreHorizontal className="w-4 h-4" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                    <DropdownMenuItem onClick={(e) => { e.stopPropagation(); /* TODO: Edit */ }}>
                                        <Settings className="w-4 h-4 mr-2" />
                                        Settings
                                    </DropdownMenuItem>
                                    <DropdownMenuItem
                                        className="text-red-600 focus:text-red-600"
                                        onClick={(e) => handleDeleteClick(e, team)}
                                    >
                                        <Trash2 className="w-4 h-4 mr-2" />
                                        Delete
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </div>
                    ))}
                </div>
            </div>

            {/* Delete Confirmation Dialog - using existing Dialog component */}
            <Dialog open={!!deleteDialogTeam} onOpenChange={(open) => !open && setDeleteDialogTeam(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Delete Team</DialogTitle>
                        <DialogDescription>
                            Are you sure you want to delete "{deleteDialogTeam?.name}"? This action cannot be undone.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDeleteDialogTeam(null)}>
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={handleConfirmDelete}
                        >
                            Delete Team
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
