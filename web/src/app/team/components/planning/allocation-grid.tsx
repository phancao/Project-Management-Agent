"use client";

import { Avatar, AvatarFallback, AvatarImage } from "~/components/ui/avatar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "~/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { cn } from "~/lib/utils";
import { useMemberProfile } from "../../context/member-profile-context";

interface AllocationGridProps {
    weeks: string[];
    members: Array<{
        id: string;
        name: string;
        avatar?: string;
        role?: string;
        allocations: number[]; // Array of % utilization corresponding to weeks
    }>;
}

const AllocationGrid = ({ weeks, members }: AllocationGridProps) => {
    const { openMemberProfile } = useMemberProfile();

    const getUtilizationColor = (percentage: number) => {
        if (percentage > 180) return "bg-red-500 text-white font-bold ring-2 ring-red-500 ring-offset-2 dark:ring-offset-gray-950";
        if (percentage > 100) return "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300 font-semibold border border-red-200 dark:border-red-800";
        if (percentage >= 80) return "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300 border border-yellow-200 dark:border-yellow-800";
        if (percentage > 0) return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 border border-green-200 dark:border-green-800";
        return "bg-gray-50 text-gray-400 dark:bg-gray-800/50 dark:text-gray-500 border border-gray-100 dark:border-gray-800";
    };

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="text-base">Resource Allocation</CardTitle>
                        <CardDescription>
                            Weekly utilization per member
                        </CardDescription>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <div className="rounded-md border border-gray-100 dark:border-gray-800 overflow-hidden">
                    <Table>
                        <TableHeader className="bg-muted/50">
                            <TableRow className="hover:bg-transparent">
                                <TableHead className="w-[250px] font-medium pl-4">Member</TableHead>
                                {weeks.map(week => (
                                    <TableHead key={week} className="text-center font-medium min-w-[80px]">
                                        {week}
                                    </TableHead>
                                ))}
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {members.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={weeks.length + 1} className="h-24 text-center text-muted-foreground">
                                        No members found.
                                    </TableCell>
                                </TableRow>
                            ) : null}
                            {members.map(member => (
                                <TableRow key={member.id} className="hover:bg-muted/30">
                                    <TableCell className="font-medium pl-4">
                                        <button
                                            onClick={() => openMemberProfile(member.id)}
                                            className="flex items-center gap-3 w-full text-left group"
                                        >
                                            <Avatar className="w-8 h-8 border-2 border-white dark:border-gray-900 shadow-sm group-hover:border-indigo-100 transition-colors">
                                                <AvatarImage src={member.avatar} />
                                                <AvatarFallback className="text-xs bg-indigo-50 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">
                                                    {member.name[0]}
                                                </AvatarFallback>
                                            </Avatar>
                                            <div className="min-w-0">
                                                <div className="font-medium truncate text-sm group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">{member.name}</div>
                                                <div className="text-[10px] text-muted-foreground truncate">{member.role || "Team Member"}</div>
                                            </div>
                                        </button>
                                    </TableCell>
                                    {member.allocations.map((alloc, idx) => (
                                        <TableCell key={`${member.id}-${idx}`} className="p-2 text-center">
                                            <div
                                                className={cn(
                                                    "w-full py-1.5 rounded text-xs transition-all hover:scale-105 cursor-default flex items-center justify-center",
                                                    getUtilizationColor(alloc)
                                                )}
                                                title={`${alloc}% Utilization`}
                                            >
                                                {alloc}%
                                            </div>
                                        </TableCell>
                                    ))}
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>

                {/* Legend */}
                <div className="flex flex-wrap items-center gap-6 mt-6 px-1">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <div className="w-3 h-3 bg-red-500 rounded ring-1 ring-red-500/50"></div>
                        <span>Critical (&gt;180%)</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <div className="w-3 h-3 bg-red-100 dark:bg-red-900/40 rounded border border-red-200 dark:border-red-800"></div>
                        <span>Overloaded (&gt;100%)</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <div className="w-3 h-3 bg-yellow-100 dark:bg-yellow-900/30 rounded border border-yellow-200 dark:border-yellow-800"></div>
                        <span>High (80-100%)</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <div className="w-3 h-3 bg-green-100 dark:bg-green-900/30 rounded border border-green-200 dark:border-green-800"></div>
                        <span>Healthy</span>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};

export { AllocationGrid };
