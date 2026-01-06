
import { useState, useMemo } from "react"
import Link from "next/link"
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
import type { Team } from "~/core/hooks/use-teams"
import { useTeamDataContext, useTeamUsers } from "../context/team-data-context"
import type { PMUser } from "~/core/api/pm/users"

interface TeamRosterProps {
    team?: Team;
    onAddMember: (userId: string) => void;
    onRemoveMember: (userId: string) => void;
}

export function TeamRoster({ team, onAddMember, onRemoveMember }: TeamRosterProps) {
    const [searchQuery, setSearchQuery] = useState("");

    // Get memberIds from context and load users
    const { allMemberIds: contextMemberIds } = useTeamDataContext();
    const { allUsers, isLoading } = useTeamUsers(contextMemberIds);

    // Filter to get members of this specific team
    const members = useMemo(() =>
        allUsers.filter((u: PMUser) => (team?.memberIds || []).includes(u.id)),
        [allUsers, team?.memberIds]
    );

    // Filter available users for "Add Member"
    // Users NOT in the current team
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
            <div className="flex h-full items-center justify-center text-muted-foreground">
                Select a team to view members
            </div>
        );
    }

    return (
        <Card className="h-full border-none shadow-none bg-transparent">
            <CardHeader className="px-0 pt-0">
                <div className="space-y-1">
                    <CardTitle className="text-lg">{team.name} Roster</CardTitle>
                    <p className="text-sm text-muted-foreground">
                        {isLoading ? "Loading members..." : `${members.length} members`}
                    </p>
                </div>
            </CardHeader>
            <CardContent className="px-0">
                {isLoading ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    </div>
                ) : (
                    <>
                        {/* Current Team Members */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {members.map((member: PMUser) => (
                                <div key={member.id} className="group relative flex items-center gap-4 p-4 rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900/40 hover:border-gray-200 dark:hover:border-gray-700 transition-all">
                                    <Link href={`/team/member/${encodeURIComponent(member.id)}?returnTab=members`} className="flex items-center gap-4 flex-1 min-w-0">
                                        <Avatar className="h-12 w-12 border border-gray-100 dark:border-gray-800 hover:opacity-80 transition-opacity">
                                            <AvatarImage src={member.avatar} />
                                            <AvatarFallback className="bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400">
                                                {member.name[0]}
                                            </AvatarFallback>
                                        </Avatar>
                                        <div className="flex-1 min-w-0">
                                            <div className="font-medium truncate hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">{member.name}</div>
                                            <div className="text-xs text-muted-foreground truncate">{member.email}</div>
                                        </div>
                                    </Link>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="absolute top-2 right-2 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                                        onClick={() => onRemoveMember(member.id)}
                                    >
                                        <UserMinus className="w-4 h-4" />
                                    </Button>
                                </div>
                            ))}
                            {members.length === 0 && (
                                <div className="col-span-full border-2 border-dashed border-gray-200 dark:border-gray-800 rounded-xl p-12 text-center">
                                    <Users className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-700 mb-4" />
                                    <h3 className="font-medium text-gray-900 dark:text-gray-100">No members yet</h3>
                                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                                        Add members from the list below.
                                    </p>
                                </div>
                            )}
                        </div>

                        {/* Available Users Section */}
                        {availableUsers.length > 0 && (
                            <div className="mt-8">
                                <div className="flex items-center justify-between mb-4">
                                    <div>
                                        <h3 className="text-sm font-semibold text-muted-foreground">Available Users</h3>
                                        <p className="text-xs text-muted-foreground">{availableUsers.length} users not in this team</p>
                                    </div>
                                    <div className="relative w-64">
                                        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                                        <Input
                                            placeholder="Search users..."
                                            className="pl-9 h-9"
                                            value={searchQuery}
                                            onChange={(e) => setSearchQuery(e.target.value)}
                                        />
                                        {searchQuery && (
                                            <button
                                                className="absolute right-2 top-2 text-muted-foreground hover:text-foreground"
                                                onClick={() => setSearchQuery("")}
                                            >
                                                <X className="h-4 w-4" />
                                            </button>
                                        )}
                                    </div>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                    {(searchQuery ? filteredAvailable : availableUsers).slice(0, 12).map((user: PMUser) => (
                                        <div
                                            key={user.id}
                                            className="flex items-center gap-3 p-3 rounded-lg border border-dashed border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-700 hover:bg-indigo-50/50 dark:hover:bg-indigo-900/20 transition-all text-left group"
                                        >
                                            <Link href={`/team/member/${encodeURIComponent(user.id)}?returnTab=members`} className="flex-1 flex items-center gap-3 min-w-0">
                                                <Avatar className="h-10 w-10 hover:opacity-80 transition-opacity">
                                                    <AvatarImage src={user.avatar} />
                                                    <AvatarFallback className="bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 text-sm">
                                                        {user.name[0]}
                                                    </AvatarFallback>
                                                </Avatar>
                                                <div className="flex-1 min-w-0">
                                                    <div className="text-sm font-medium truncate hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">{user.name}</div>
                                                    <div className="text-xs text-muted-foreground truncate">{user.email}</div>
                                                </div>
                                            </Link>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-8 w-8 hover:bg-transparent"
                                                onClick={() => handleAddMember(user.id)}
                                            >
                                                <Plus className="w-4 h-4 text-muted-foreground group-hover:text-indigo-500 flex-shrink-0" />
                                            </Button>
                                        </div>
                                    ))}
                                </div>
                                {availableUsers.length > 12 && !searchQuery && (
                                    <p className="text-xs text-center text-muted-foreground mt-3">
                                        Showing 12 of {availableUsers.length} available users. Use search to find more.
                                    </p>
                                )}
                            </div>
                        )}
                    </>
                )}
            </CardContent>
        </Card>
    );
}
