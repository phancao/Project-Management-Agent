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
import { Sparkles } from "lucide-react";
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

// Color palette for team badges
const teamColors = [
    { bg: 'from-violet-500 to-purple-600', text: 'text-white' },
    { bg: 'from-blue-500 to-cyan-600', text: 'text-white' },
    { bg: 'from-emerald-500 to-teal-600', text: 'text-white' },
    { bg: 'from-amber-500 to-orange-600', text: 'text-white' },
    { bg: 'from-rose-500 to-pink-600', text: 'text-white' },
    { bg: 'from-indigo-500 to-blue-600', text: 'text-white' },
];

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
        setDeleteDialogTeam(team);
    };

    const handleConfirmDelete = () => {
        if (deleteDialogTeam) {
            onDeleteTeam(deleteDialogTeam.id);
            setDeleteDialogTeam(null);
        }
    };

    const getTeamColor = (index: number) => teamColors[index % teamColors.length];

    return (
        <>
            <div className="flex flex-col h-full bg-white dark:bg-gradient-to-b dark:from-slate-900 dark:to-slate-950 rounded-2xl border border-gray-200 dark:border-0 shadow-lg dark:shadow-2xl dark:shadow-indigo-500/5 overflow-hidden">
                {/* Premium Header */}
                <div className="relative p-4 border-b border-gray-100 dark:border-slate-800/50 bg-gradient-to-r from-indigo-50 dark:from-indigo-500/10 via-violet-50/50 dark:via-violet-500/5 to-transparent">
                    <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-indigo-100/50 dark:from-indigo-500/10 via-transparent to-transparent" />
                    <div className="relative flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                                <Users className="w-4 h-4 text-white" />
                            </div>
                            <h3 className="font-bold text-base text-gray-900 dark:text-white">Teams</h3>
                        </div>
                        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                            <DialogTrigger asChild>
                                <Button size="icon" variant="ghost" className="h-8 w-8 text-gray-500 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-slate-800">
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
                                    <Button onClick={handleCreateTeam} className="bg-gradient-to-r from-indigo-500 to-violet-600 text-white border-0 hover:opacity-90">Create Team</Button>
                                </DialogFooter>
                            </DialogContent>
                        </Dialog>
                    </div>
                </div>

                {/* Teams List */}
                <div className="flex-1 overflow-y-auto p-3 space-y-2">
                    {teams.map((team, index) => {
                        const color = getTeamColor(index)!;
                        const isSelected = selectedTeamId === team.id;

                        return (
                            <div
                                key={team.id}
                                onClick={() => onTeamSelect(team.id)}
                                className={cn(
                                    "group relative flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all duration-300",
                                    isSelected
                                        ? "bg-indigo-50 dark:bg-gradient-to-r dark:from-indigo-500/20 dark:to-violet-500/10 border border-indigo-200 dark:border-indigo-500/30 shadow-lg shadow-indigo-100 dark:shadow-indigo-500/10"
                                        : "border border-transparent hover:bg-gray-50 dark:hover:bg-slate-800/50 hover:border-gray-200 dark:hover:border-slate-700/50"
                                )}
                            >
                                {/* Team Info */}
                                <div className="flex items-center gap-3">
                                    <div className={cn(
                                        "flex items-center justify-center w-10 h-10 rounded-xl text-xs font-bold shadow-lg transition-all duration-300",
                                        `bg-gradient-to-br ${color.bg} ${color.text}`,
                                        isSelected && "scale-110 shadow-indigo-500/30"
                                    )}>
                                        {team.name.substring(0, 2).toUpperCase()}
                                    </div>
                                    <div>
                                        <div className={cn(
                                            "font-semibold text-sm transition-colors",
                                            isSelected ? "text-indigo-900 dark:text-white" : "text-gray-700 dark:text-slate-300"
                                        )}>
                                            {team.name}
                                        </div>
                                        <div className="text-xs text-gray-500 dark:text-slate-500 flex items-center gap-1.5">
                                            <Users className="w-3 h-3" />
                                            <span className={cn(
                                                "font-medium",
                                                isSelected ? "text-indigo-600 dark:text-indigo-400" : "text-gray-600 dark:text-slate-400"
                                            )}>
                                                {team.memberIds?.length || 0}
                                            </span>
                                            members
                                        </div>
                                    </div>
                                </div>

                                {/* Actions Menu */}
                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                        <Button
                                            size="icon"
                                            variant="ghost"
                                            className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-slate-700"
                                        >
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
                        );
                    })}

                    {teams.length === 0 && (
                        <div className="text-center py-12 text-gray-400 dark:text-slate-500">
                            <Sparkles className="w-10 h-10 mx-auto mb-3 opacity-30" />
                            <p className="text-sm font-medium">No teams yet</p>
                            <p className="text-xs mt-1">Create your first team to get started</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Delete Confirmation Dialog */}
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
