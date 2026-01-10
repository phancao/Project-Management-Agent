
import { useState } from "react"
import { Card, CardHeader, CardTitle, CardContent } from "~/components/ui/card"
import { Button } from "~/components/ui/button"
import { Input } from "~/components/ui/input"
import { Avatar, AvatarFallback, AvatarImage } from "~/components/ui/avatar"
import { Badge } from "~/components/ui/badge"
// @ts-expect-error - Direct import
import Search from "lucide-react/dist/esm/icons/search";
// @ts-expect-error - Direct import
import Plus from "lucide-react/dist/esm/icons/plus";
// @ts-expect-error - Direct import
import X from "lucide-react/dist/esm/icons/x";
// @ts-expect-error - Direct import
import UserMinus from "lucide-react/dist/esm/icons/user-minus";
// @ts-expect-error - Direct import
import Users from "lucide-react/dist/esm/icons/users";
// @ts-expect-error - Direct import
import Loader2 from "lucide-react/dist/esm/icons/loader-2";
import { Sparkles, UserPlus } from "lucide-react";
import { InlineLoading } from "~/components/ui/workspace-loading";
import type { Team } from "~/core/hooks/use-teams"
import { useTeamDataContext, useTeamUsers, useAllUsers } from "../context/team-data-context"
import type { PMUser } from "~/core/api/pm/users"
import { useMemberProfile } from "../context/member-profile-context"
import { cn } from "~/lib/utils"

// Color palette for member avatars
const memberColors = [
    'ring-violet-500/60',
    'ring-blue-500/60',
    'ring-emerald-500/60',
    'ring-amber-500/60',
    'ring-rose-500/60',
    'ring-cyan-500/60',
];

const avatarGradients = [
    'from-violet-500 to-purple-600',
    'from-blue-500 to-cyan-600',
    'from-emerald-500 to-teal-600',
    'from-amber-500 to-orange-600',
    'from-rose-500 to-pink-600',
    'from-indigo-500 to-blue-600',
];

// Premium Clickable member card that opens profile dialog
function MemberClickable({ member, index }: { member: PMUser; index: number }) {
    const { openMemberProfile } = useMemberProfile();
    const ringColor = memberColors[index % memberColors.length];
    const gradient = avatarGradients[index % avatarGradients.length];

    return (
        <button
            onClick={() => openMemberProfile(member.id)}
            className="flex items-center gap-4 flex-1 min-w-0 text-left group"
        >
            <div className="relative">
                <Avatar className={cn(
                    "h-12 w-12 ring-2 ring-offset-2 ring-offset-white dark:ring-offset-slate-900 transition-all duration-300",
                    ringColor,
                    "group-hover:scale-105"
                )}>
                    <AvatarImage src={member.avatar} />
                    <AvatarFallback className={cn("text-white font-semibold bg-gradient-to-br", gradient)}>
                        {member.name[0]}
                    </AvatarFallback>
                </Avatar>
                <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-500 rounded-full border-2 border-white dark:border-slate-900" />
            </div>
            <div className="flex-1 min-w-0">
                <div className="font-semibold text-gray-900 dark:text-slate-100 truncate group-hover:text-indigo-600 dark:group-hover:text-white transition-colors">{member.name}</div>
                <div className="text-xs text-gray-500 dark:text-slate-400 truncate group-hover:text-gray-600 dark:group-hover:text-slate-300 transition-colors">{member.email}</div>
            </div>
        </button>
    );
}

// Premium Clickable user row for available users
function UserClickable({ user, index }: { user: PMUser; index: number }) {
    const { openMemberProfile } = useMemberProfile();
    const gradient = avatarGradients[index % avatarGradients.length];

    return (
        <button
            onClick={() => openMemberProfile(user.id)}
            className="flex-1 flex items-center gap-3 min-w-0 text-left group"
        >
            <Avatar className="h-10 w-10 transition-all duration-300 group-hover:scale-105">
                <AvatarImage src={user.avatar} />
                <AvatarFallback className={cn("text-white font-semibold text-sm bg-gradient-to-br", gradient)}>
                    {user.name[0]}
                </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-700 dark:text-slate-200 truncate group-hover:text-indigo-600 dark:group-hover:text-white transition-colors">{user.name}</div>
                <div className="text-xs text-gray-400 dark:text-slate-500 truncate group-hover:text-gray-500 dark:group-hover:text-slate-400 transition-colors">{user.email}</div>
            </div>
        </button>
    );
}

interface TeamRosterProps {
    team?: Team;
    onAddMember: (userId: string) => void;
    onRemoveMember: (userId: string) => void;
}

export function TeamRoster({ team, onAddMember, onRemoveMember }: TeamRosterProps) {
    const [searchQuery, setSearchQuery] = useState("");

    // Use the team's memberIds directly (not context), so newly added members show immediately
    const teamMemberIds = team?.memberIds || [];

    // Load ONLY this team's members (fast - just fetches specific IDs)
    const { teamMembers: members, isLoading: isLoadingTeamMembers } = useTeamUsers(teamMemberIds);

    // Load ALL users for the "Add Member" dropdown
    const { allUsers, isLoading: isLoadingAllUsers } = useAllUsers(true);

    // Filter available users for "Add Member" - Users NOT in the current team
    const availableUsers = allUsers.filter((u: PMUser) => !(team?.memberIds || []).includes(u.id));

    const filteredAvailable = availableUsers.filter((u: PMUser) =>
        u.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (u.email || "").toLowerCase().includes(searchQuery.toLowerCase())
    );

    const handleAddMember = (userId: string) => {
        onAddMember(userId);
        setSearchQuery("");
    };

    if (!team) {
        return (
            <div className="flex h-full items-center justify-center text-gray-400 dark:text-slate-500">
                <div className="text-center">
                    <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
                    <p className="font-medium">Select a team to view members</p>
                </div>
            </div>
        );
    }

    return (
        <div className="h-full">
            {/* Premium Header */}
            <div className="mb-6">
                <div className="flex items-center gap-3 mb-1">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                        <Users className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-gray-900 dark:text-white">{team.name} Roster</h2>
                        <p className="text-sm text-gray-500 dark:text-slate-400">
                            {isLoadingTeamMembers ? "Loading members..." : (
                                <span className="flex items-center gap-1">
                                    <span className="text-indigo-600 dark:text-indigo-400 font-semibold">{members.length}</span> members
                                </span>
                            )}
                        </p>
                    </div>
                </div>
            </div>

            {isLoadingTeamMembers ? (
                <InlineLoading message="Loading team members..." />
            ) : (
                <>
                    {/* Current Team Members */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {members.map((member: PMUser, index: number) => (
                            <div
                                key={member.id}
                                className={cn(
                                    "group relative flex items-center gap-4 p-4 rounded-xl transition-all duration-300",
                                    "bg-white dark:bg-slate-800/80",
                                    "border border-gray-200 dark:border-slate-700/50",
                                    "hover:border-indigo-300 dark:hover:border-indigo-500/50",
                                    "hover:shadow-lg hover:shadow-indigo-100 dark:hover:shadow-indigo-500/10"
                                )}
                            >
                                <MemberClickable member={member} index={index} />
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="absolute top-2 right-2 h-8 w-8 text-gray-400 dark:text-slate-500 opacity-0 group-hover:opacity-100 transition-all hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/50"
                                    onClick={() => onRemoveMember(member.id)}
                                >
                                    <UserMinus className="w-4 h-4" />
                                </Button>
                            </div>
                        ))}
                        {members.length === 0 && (
                            <div className="col-span-full border-2 border-dashed border-gray-200 dark:border-slate-700 rounded-2xl p-12 text-center">
                                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gray-100 dark:bg-slate-800 flex items-center justify-center">
                                    <Users className="w-8 h-8 text-gray-400 dark:text-slate-600" />
                                </div>
                                <h3 className="font-semibold text-gray-700 dark:text-slate-200">No members yet</h3>
                                <p className="text-sm text-gray-400 dark:text-slate-500 mt-1">
                                    Add members from the list below.
                                </p>
                            </div>
                        )}
                    </div>

                    {/* Available Users Section */}
                    <div className="mt-10">
                        <div className="flex items-center justify-between mb-4">
                            <div>
                                <h3 className="text-base font-semibold text-gray-700 dark:text-slate-200 flex items-center gap-2">
                                    <UserPlus className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
                                    Available Users
                                </h3>
                                <p className="text-xs text-gray-400 dark:text-slate-500 mt-0.5">
                                    {isLoadingAllUsers
                                        ? "Loading users..."
                                        : `${availableUsers.length} users not in this team`}
                                </p>
                            </div>
                            <div className="relative w-72">
                                <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400 dark:text-slate-500" />
                                <Input
                                    placeholder="Search users..."
                                    className="pl-10 h-10 bg-gray-50 dark:bg-slate-800/50 border-gray-200 dark:border-slate-700/50 text-gray-700 dark:text-slate-200 placeholder:text-gray-400 dark:placeholder:text-slate-500 focus:border-indigo-300 dark:focus:border-indigo-500/50 focus:ring-indigo-200 dark:focus:ring-indigo-500/20 rounded-xl"
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    disabled={isLoadingAllUsers}
                                />
                                {searchQuery && (
                                    <button
                                        className="absolute right-3 top-2.5 text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300 transition-colors"
                                        onClick={() => setSearchQuery("")}
                                    >
                                        <X className="h-4 w-4" />
                                    </button>
                                )}
                            </div>
                        </div>

                        {isLoadingAllUsers ? (
                            <InlineLoading message="Loading available users..." />
                        ) : availableUsers.length > 0 ? (
                            <>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                    {(searchQuery ? filteredAvailable : availableUsers).slice(0, 12).map((user: PMUser, index: number) => (
                                        <div
                                            key={user.id}
                                            className={cn(
                                                "group flex items-center gap-3 p-3 rounded-xl transition-all duration-300",
                                                "border-2 border-dashed border-gray-200 dark:border-slate-700/50",
                                                "hover:border-indigo-300 dark:hover:border-indigo-500/50 hover:bg-indigo-50/50 dark:hover:bg-indigo-500/5"
                                            )}
                                        >
                                            <UserClickable user={user} index={index} />
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-9 w-9 text-gray-400 dark:text-slate-500 hover:text-indigo-500 dark:hover:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-500/10 transition-all"
                                                onClick={() => handleAddMember(user.id)}
                                            >
                                                <Plus className="w-5 h-5" />
                                            </Button>
                                        </div>
                                    ))}
                                </div>
                                {availableUsers.length > 12 && !searchQuery && (
                                    <p className="text-xs text-center text-gray-400 dark:text-slate-500 mt-4">
                                        Showing 12 of {availableUsers.length} available users. Use search to find more.
                                    </p>
                                )}
                            </>
                        ) : (
                            <div className="text-center py-10 text-gray-400 dark:text-slate-500">
                                <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-30" />
                                <p className="text-sm">No available users to add</p>
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    );
}
