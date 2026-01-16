"use client"

import { useMemo, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card"
import { Button } from "~/components/ui/button"
import { useTeamDataContext, useTeamUsers, useTeamTimeEntries } from "../context/team-data-context"
import { ChevronLeft, ChevronRight, Users, Loader2 } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "~/components/ui/avatar"
import { Badge } from "~/components/ui/badge"
import { cn } from "~/lib/utils"
import { useMemberProfile } from "../context/member-profile-context"
import { useCardGlow } from "~/core/hooks/use-theme-colors"

interface TeamData {
    id: string
    name: string
    memberIds: string[]
}

// Helper to get start of week (Monday) with offset
function getWeekStart(weekOffset: number = 0): Date {
    const today = new Date()
    const day = today.getDay()
    const diff = today.getDate() - day + (day === 0 ? -6 : 1) // Monday
    today.setDate(diff + (weekOffset * 7))
    today.setHours(0, 0, 0, 0)
    return today
}

// Generate array of 7 days starting from Monday
function getWeekDays(weekStart: Date): Date[] {
    return Array.from({ length: 7 }, (_, i) => {
        const d = new Date(weekStart)
        d.setDate(d.getDate() + i)
        return d
    })
}

// Format date as YYYY-MM-DD for comparison (in LOCAL timezone, not UTC)
function formatDateKey(date: Date): string {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
}

// Format date for display
function formatDateDisplay(date: Date): string {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

// Day names
const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

interface MemberWorklogRow {
    id: string
    name: string
    avatar?: string
    dailyHours: number[] // 7 days Mon-Sun
    totalHours: number
    isUnderUtilized: boolean // <40h/week
}

// Clickable avatar cell that opens member profile dialog
function MemberAvatarCell({ member }: { member: MemberWorklogRow }) {
    const { openMemberProfile } = useMemberProfile();
    return (
        <button
            onClick={() => openMemberProfile(member.id)}
            className="flex items-center gap-2 hover:opacity-80 transition-opacity text-left"
        >
            <Avatar className="w-7 h-7">
                <AvatarImage src={member.avatar} />
                <AvatarFallback className="text-xs">{member.name?.[0]}</AvatarFallback>
            </Avatar>
            <span className="text-sm font-medium truncate max-w-[150px] hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
                {member.name}
            </span>
        </button>
    );
}

// Individual team card component with its own state
function TeamWorklogCard({ team, providerId }: { team: TeamData; providerId?: string }) {
    const [weekOffset, setWeekOffset] = useState(0)
    const cardGlow = useCardGlow()

    // Get active provider IDs from context to filter stale members
    const { activeProviderIds } = useTeamDataContext()

    // Calculate week dates based on this card's offset
    const weekRange = useMemo(() => {
        const start = getWeekStart(weekOffset)
        const end = new Date(start)
        end.setDate(end.getDate() + 6)
        return {
            start: formatDateKey(start),
            end: formatDateKey(end),
            startDate: start,
            endDate: end,
            weekDays: getWeekDays(start)
        }
    }, [weekOffset])

    // Filter memberIds to only include those from active providers
    const validMemberIds = useMemo(() => {
        if (activeProviderIds.length === 0) return team.memberIds; // Allow all if no providers loaded yet
        return team.memberIds.filter(id => {
            const providerId = id.split(':')[0] || '';
            return activeProviderIds.includes(providerId);
        });
    }, [team.memberIds, activeProviderIds])

    // Detect if team has stale provider data (members in localStorage but all filtered out)
    const hasStaleProviderData = activeProviderIds.length > 0 &&
        team.memberIds.length > 0 &&
        validMemberIds.length === 0;

    // Fetch data for this team's members only (using filtered memberIds)
    const { teamMembers, isLoading: isLoadingUsers } = useTeamUsers(validMemberIds)
    const { teamTimeEntries, isLoading: isLoadingTimeEntries, isFetching } = useTeamTimeEntries(
        validMemberIds,
        { startDate: weekRange.start, endDate: weekRange.end, providerId }
    )

    const isInitialLoading = isLoadingUsers || isLoadingTimeEntries
    const showLoadingOverlay = isFetching

    // Build worklog data
    const worklogData = useMemo((): MemberWorklogRow[] => {
        if (isInitialLoading || hasStaleProviderData) return []

        return teamMembers.map(user => {
            // Both user.id and time_entry.user_id are now composite IDs (provider:shortId)
            const userEntries = teamTimeEntries.filter(e => e.user_id === user.id)

            const dailyHours = weekRange.weekDays.map(day => {
                const dateKey = formatDateKey(day)
                const dayEntries = userEntries.filter(e => e.date?.startsWith(dateKey))
                return dayEntries.reduce((sum, e) => sum + (e.hours || 0), 0)
            })
            const totalHours = dailyHours.reduce((sum, h) => sum + h, 0)
            return {
                id: user.id,
                name: user.name || 'Unknown',
                avatar: user.avatar,
                dailyHours,
                totalHours,
                isUnderUtilized: totalHours < 40
            }
        }).sort((a, b) => a.totalHours - b.totalHours)
    }, [teamMembers, teamTimeEntries, weekRange.weekDays, isInitialLoading, hasStaleProviderData])

    // Don't render cards for truly empty teams (no members defined)
    if (!isInitialLoading && team.memberIds.length === 0) return null

    const isCurrentWeek = weekOffset === 0

    return (
        <Card className={cardGlow.className}>
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2 text-base">
                        <Users className="w-4 h-4" />
                        {team.name}
                        <Badge variant="secondary" className="ml-2">{team.memberIds.length} members</Badge>
                    </CardTitle>
                    <div className="flex items-center gap-2">
                        {/* Week navigation - same style as workload chart */}
                        <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-1">
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={() => setWeekOffset(w => w - 1)}
                            >
                                <ChevronLeft className="h-4 w-4" />
                            </Button>
                            <span className="text-sm font-medium px-2 min-w-[120px] text-center">
                                {formatDateDisplay(weekRange.startDate)} - {formatDateDisplay(weekRange.endDate)}
                            </span>
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={() => setWeekOffset(w => w + 1)}
                                disabled={isCurrentWeek}
                            >
                                <ChevronRight className="h-4 w-4" />
                            </Button>
                        </div>
                        {!isCurrentWeek && (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setWeekOffset(0)}
                            >
                                Today
                            </Button>
                        )}
                    </div>
                </div>
            </CardHeader>
            <CardContent className="relative">
                {/* Loading overlay - only for this card */}
                {showLoadingOverlay && (
                    <div className="absolute inset-0 bg-background/50 backdrop-blur-sm flex items-center justify-center z-10 rounded-lg">
                        <Loader2 className="w-6 h-6 animate-spin text-primary" />
                    </div>
                )}

                {/* Show message if provider is inactive */}
                {hasStaleProviderData ? (
                    <div className="py-8 text-center text-muted-foreground">
                        <p className="text-sm">Provider unavailable or disabled</p>
                        <p className="text-xs mt-1">This team's members belong to an inactive provider.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full border-collapse">
                            <thead>
                                <tr className="border-b">
                                    <th className="text-left p-2 font-medium text-sm w-[200px]">Member</th>
                                    {DAY_NAMES.map((day, i) => (
                                        <th key={day} className="text-center p-2 font-medium text-sm min-w-[60px]">
                                            <div>{day}</div>
                                            <div className="text-xs text-muted-foreground font-normal">
                                                {formatDateDisplay(weekRange.weekDays[i]!)}
                                            </div>
                                        </th>
                                    ))}
                                    <th className="text-center p-2 font-medium text-sm min-w-[70px] bg-muted/50">Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                {worklogData.map((member: MemberWorklogRow) => (
                                    <tr
                                        key={member.id}
                                        className={cn(
                                            "border-b hover:bg-muted/30 transition-colors",
                                            member.isUnderUtilized && "bg-red-50 dark:bg-red-950/20"
                                        )}
                                    >
                                        <td className="p-2">
                                            <MemberAvatarCell member={member} />
                                        </td>
                                        {member.dailyHours.map((hours: number, dayIndex: number) => {
                                            const isWeekday = dayIndex < 5
                                            const isFullyLogged = hours >= 8
                                            const isPartiallyLogged = hours > 0 && hours < 8
                                            const isUnlogged = hours === 0

                                            return (
                                                <td
                                                    key={dayIndex}
                                                    className={cn(
                                                        "text-center p-2 text-sm tabular-nums font-medium",
                                                        isWeekday && isFullyLogged && "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40",
                                                        isWeekday && isPartiallyLogged && "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40",
                                                        isWeekday && isUnlogged && "text-red-500 dark:text-red-400 bg-red-100 dark:bg-red-950/50 font-bold",
                                                        !isWeekday && hours === 0 && "text-muted-foreground/50",
                                                        !isWeekday && hours > 0 && "text-blue-500 dark:text-blue-400"
                                                    )}
                                                >
                                                    {hours}h
                                                </td>
                                            )
                                        })}
                                        <td className={cn(
                                            "text-center p-2 text-sm font-bold tabular-nums bg-muted/50",
                                            member.totalHours >= 40 && "text-emerald-600 dark:text-emerald-400",
                                            member.totalHours > 0 && member.totalHours < 40 && "text-amber-600 dark:text-amber-400",
                                            member.totalHours === 0 && "text-red-500 dark:text-red-400"
                                        )}>
                                            {member.totalHours}h
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </CardContent>
        </Card>
    )
}

// Props interface following Widget Autonomy Standard
interface TeamWorklogsProps {
    providerId?: string;  // Provider ID for data filtering
}

// Main component - just renders team cards
export function TeamWorklogs({ providerId }: TeamWorklogsProps) {
    const { teams } = useTeamDataContext()

    return (
        <div className="space-y-6">
            {/* Per-Team Worklog Cards - each with independent state */}
            {teams.map(team => (
                <TeamWorklogCard key={team.id} team={team} providerId={providerId} />
            ))}

            {/* Legend */}
            <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-400 dark:border-emerald-600" />
                    <span>8h+ (fully logged)</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded bg-amber-50 dark:bg-amber-950/40 border border-amber-400 dark:border-amber-600" />
                    <span>1-7h (partial)</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded bg-red-100 dark:bg-red-950/50 border border-red-400 dark:border-red-600" />
                    <span>0h (unlogged)</span>
                </div>
            </div>
        </div>
    )
}
