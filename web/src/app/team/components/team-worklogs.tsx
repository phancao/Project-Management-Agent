"use client"

import { useMemo, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card"
import { Button } from "~/components/ui/button"
import { useTeamDataContext, useTeamUsers, useTeamTimeEntries } from "../context/team-data-context"
import { ChevronLeft, ChevronRight, Clock, AlertTriangle, Users, Loader2 } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "~/components/ui/avatar"
import { Badge } from "~/components/ui/badge"
import { cn } from "~/lib/utils"

// Helper to get start of week (Monday)
function getWeekStart(date: Date): Date {
    const d = new Date(date)
    const day = d.getDay()
    const diff = d.getDate() - day + (day === 0 ? -6 : 1) // Monday
    d.setDate(diff)
    d.setHours(0, 0, 0, 0)
    return d
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

export function TeamWorklogs() {
    const [weekOffset, setWeekOffset] = useState(0)

    // Get current week based on offset
    const currentWeekStart = useMemo(() => {
        const today = new Date()
        const start = getWeekStart(today)
        start.setDate(start.getDate() + (weekOffset * 7))
        return start
    }, [weekOffset])

    const weekDays = useMemo(() => getWeekDays(currentWeekStart), [currentWeekStart])

    // Calculate week end date
    const weekEndDate = useMemo(() => {
        const end = new Date(currentWeekStart)
        end.setDate(end.getDate() + 6)
        return end
    }, [currentWeekStart])

    // Context and data hooks
    const { allMemberIds, isLoading: isContextLoading } = useTeamDataContext()
    const { teamMembers, isLoading: isLoadingUsers, count: usersCount } = useTeamUsers(allMemberIds)
    // Use server-side date filtering for efficient queries
    const { teamTimeEntries, isLoading: isLoadingTimeEntries, count: timeEntriesCount } = useTeamTimeEntries(
        allMemberIds,
        { startDate: formatDateKey(currentWeekStart), endDate: formatDateKey(weekEndDate) }
    )

    // Build worklog data per member - only team members
    const worklogData = useMemo((): MemberWorklogRow[] => {
        if (isLoadingUsers || isLoadingTimeEntries) return []

        return teamMembers.map(user => {
            // Get time entries for this user
            const userEntries = teamTimeEntries.filter(e => e.user_id === user.id)

            // Build daily hours array (Mon-Sun)
            const dailyHours = weekDays.map(day => {
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
        }).sort((a, b) => a.totalHours - b.totalHours) // Sort by lowest hours first
    }, [teamMembers, teamTimeEntries, weekDays, isLoadingUsers, isLoadingTimeEntries])

    // Summary stats
    const stats = useMemo(() => {
        const underUtilizedCount = worklogData.filter(m => m.isUnderUtilized).length
        const avgHours = worklogData.length > 0
            ? Math.round(worklogData.reduce((sum, m) => sum + m.totalHours, 0) / worklogData.length)
            : 0
        return { underUtilizedCount, avgHours, totalMembers: worklogData.length }
    }, [worklogData])

    const isLoading = isContextLoading || isLoadingUsers || isLoadingTimeEntries

    if (isLoading) {
        const loadingItems = [
            { label: "Users", isLoading: isLoadingUsers, count: usersCount },
            { label: "Time Entries", isLoading: isLoadingTimeEntries, count: timeEntriesCount },
        ]
        const completedCount = loadingItems.filter(item => !item.isLoading).length
        const progressPercent = Math.round((completedCount / loadingItems.length) * 100)

        return (
            <div className="h-full w-full flex items-center justify-center bg-muted/20 p-4">
                <div className="bg-card border rounded-xl shadow-lg p-5 w-full max-w-sm">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center">
                            <Clock className="w-5 h-5 text-orange-600 dark:text-orange-400 animate-pulse" />
                        </div>
                        <div>
                            <h3 className="text-sm font-semibold">Loading Worklogs</h3>
                            <p className="text-xs text-muted-foreground">{progressPercent}% complete</p>
                        </div>
                    </div>
                    <div className="w-full h-1.5 bg-muted rounded-full mb-4 overflow-hidden">
                        <div
                            className="h-full bg-gradient-to-r from-orange-500 to-amber-500 rounded-full transition-all duration-500"
                            style={{ width: `${progressPercent}%` }}
                        />
                    </div>
                    <div className="space-y-2">
                        {loadingItems.map((item, index) => (
                            <div key={index} className="flex items-center justify-between py-1.5 px-2 bg-muted/30 rounded-md">
                                <div className="flex items-center gap-2">
                                    {index === 0 ? <Users className="w-3.5 h-3.5 text-blue-500" /> : <Clock className="w-3.5 h-3.5 text-orange-500" />}
                                    <span className="text-xs font-medium">{item.label}</span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <span className={`text-xs font-mono tabular-nums ${item.isLoading ? 'text-orange-600' : 'text-green-600'}`}>
                                        {item.isLoading ? (item.count > 0 ? item.count : "...") : item.count}
                                    </span>
                                    {item.isLoading ? (
                                        <Loader2 className="w-3.5 h-3.5 animate-spin text-orange-500" />
                                    ) : (
                                        <div className="w-3.5 h-3.5 text-green-500">✓</div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border-blue-200 dark:border-blue-900">
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2 mb-2">
                            <Users className="w-4 h-4 text-blue-500" />
                            <span className="text-xs text-muted-foreground">Total Members</span>
                        </div>
                        <div className="text-2xl font-bold">{stats.totalMembers}</div>
                    </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-green-500/10 to-emerald-500/10 border-green-200 dark:border-green-900">
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2 mb-2">
                            <Clock className="w-4 h-4 text-green-500" />
                            <span className="text-xs text-muted-foreground">Avg Hours/Week</span>
                        </div>
                        <div className="text-2xl font-bold">{stats.avgHours}h</div>
                    </CardContent>
                </Card>
                <Card className={cn(
                    "bg-gradient-to-br border",
                    stats.underUtilizedCount > 0
                        ? "from-red-500/10 to-orange-500/10 border-red-200 dark:border-red-900"
                        : "from-gray-500/10 to-slate-500/10 border-gray-200 dark:border-gray-800"
                )}>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2 mb-2">
                            <AlertTriangle className={cn("w-4 h-4", stats.underUtilizedCount > 0 ? "text-red-500" : "text-gray-400")} />
                            <span className="text-xs text-muted-foreground">Under 40h/week</span>
                        </div>
                        <div className={cn("text-2xl font-bold", stats.underUtilizedCount > 0 && "text-red-500")}>
                            {stats.underUtilizedCount}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Week Navigation */}
            <Card>
                <CardHeader className="pb-4">
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle className="flex items-center gap-2">
                                <Clock className="w-5 h-5" />
                                Weekly Worklogs
                            </CardTitle>
                            <CardDescription>
                                Week of {formatDateDisplay(currentWeekStart)} - {formatDateDisplay(weekDays[6]!)}
                            </CardDescription>
                        </div>
                        <div className="flex items-center gap-2">
                            <Button variant="outline" size="sm" onClick={() => setWeekOffset(w => w - 1)}>
                                <ChevronLeft className="w-4 h-4" />
                                Prev
                            </Button>
                            <Button variant="outline" size="sm" onClick={() => setWeekOffset(0)} disabled={weekOffset === 0}>
                                Today
                            </Button>
                            <Button variant="outline" size="sm" onClick={() => setWeekOffset(w => w + 1)}>
                                Next
                                <ChevronRight className="w-4 h-4" />
                            </Button>
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    {worklogData.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground">
                            No team members found.
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
                                                    {formatDateDisplay(weekDays[i]!)}
                                                </div>
                                            </th>
                                        ))}
                                        <th className="text-center p-2 font-medium text-sm min-w-[70px] bg-muted/50">Total</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {worklogData.map((member) => (
                                        <tr
                                            key={member.id}
                                            className={cn(
                                                "border-b hover:bg-muted/30 transition-colors",
                                                member.isUnderUtilized && "bg-red-50 dark:bg-red-950/20"
                                            )}
                                        >
                                            <td className="p-2">
                                                <div className="flex items-center gap-2">
                                                    <Avatar className="w-7 h-7">
                                                        <AvatarImage src={member.avatar} />
                                                        <AvatarFallback className="text-xs">{member.name?.[0]}</AvatarFallback>
                                                    </Avatar>
                                                    <span className="text-sm font-medium truncate max-w-[150px]">{member.name}</span>
                                                </div>
                                            </td>
                                            {member.dailyHours.map((hours, dayIndex) => {
                                                const isWeekday = dayIndex < 5
                                                const isFullyLogged = hours >= 8
                                                const isPartiallyLogged = hours > 0 && hours < 8
                                                const isUnlogged = hours === 0
                                                const isUnder = isWeekday && hours < 8

                                                return (
                                                    <td
                                                        key={dayIndex}
                                                        className={cn(
                                                            "text-center p-2 text-sm tabular-nums font-medium",
                                                            // Weekday styling
                                                            isWeekday && isFullyLogged && "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40",
                                                            isWeekday && isPartiallyLogged && "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40",
                                                            isWeekday && isUnlogged && "text-red-500 dark:text-red-400 bg-red-100 dark:bg-red-950/50 font-bold",
                                                            // Weekend styling (muted)
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
